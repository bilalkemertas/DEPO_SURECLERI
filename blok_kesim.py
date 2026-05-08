import streamlit as st
import pandas as pd
import re
import os

def run_blok_kesim(conn):
    # --- AYARLAR ---
    LOCAL_MAPPING_FILE = "eslesme_hafizasi.csv"

    # --- 1. ATOMİK TEMİZLİK (PATRONUN ÇÖZÜMÜ) ---
    def clean_code(val):
        if pd.isna(val):
            return ""
        # 12345.0 -> 12345 yap ve rakam dışındakileri at
        val = str(val).split(".")[0].strip()
        return re.sub(r'\D', '', val)

    # --- YAN YANA GERİ BUTONLARI ---
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 4])
    with c_back1:
        if st.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
    with c_back2:
        if st.session_state.get('main_data') is not None:
            if st.button("⬅️ TEMİZLE", use_container_width=True):
                if 'main_data' in st.session_state: del st.session_state['main_data']
                st.rerun()
    
    st.title("✂️ Blok & Rulo Kesim")
    
    # --- 2. HAFIZAYI YÜKLE ---
    def load_mapping():
        if os.path.exists(LOCAL_MAPPING_FILE):
            df = pd.read_csv(LOCAL_MAPPING_FILE)
        else:
            try:
                df = conn.read(worksheet="Eşleşmeler", ttl=0)
                df.to_csv(LOCAL_MAPPING_FILE, index=False)
            except:
                cols = ["FORM SÜNGER KOD", "FORM SÜNGER ÜRÜN ADI", "BRN KOD", "BRN ÜRÜN ADI", "DANSİTE", "ÖZELLİK", "RENK", "KALIP"]
                df = pd.DataFrame(columns=cols)
        
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df

    # --- 3. DOSYA YÜKLEME ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı (Main sheet)**")
        uploaded_file = st.file_uploader("Excel Yükle", type=['xlsx'], key="bk_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
                mapping_df = load_mapping()

                # Excel kodlarını senin temizlik mantığınla temizle
                df_main['TEMİZ_KOD'] = df_main['Malzeme Kodu'].apply(clean_code)
                
                # Hafıza kodlarını da aynı mantıkla temizle
                if 'FORM SÜNGER KOD' in mapping_df.columns:
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                else:
                    mapping_df['FORM_TEMİZ'] = "YOK"

                # MERGE: Artık 12345 == 12345
                df_final = df_main.merge(
                    mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], 
                    left_on='TEMİZ_KOD', 
                    right_on='FORM_TEMİZ', 
                    how='left'
                )
                
                st.session_state['main_data'] = df_final
                st.session_state['current_mapping'] = mapping_df
                st.success("✅ Eşleşme kontrolü başarıyla tamamlandı.")
                
            except Exception as e:
                st.error(f"Hata: {e}")

    # --- 4. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        mapping_df = st.session_state['current_mapping']
        
        # Eşleşmeyenleri bul (BRN KOD sütunu NaN veya boş olanlar)
        unmapped = df[df['BRN KOD'].isna() | (df['BRN KOD'].astype(str).str.strip() == "")][['Malzeme Kodu', 'Malzeme Tanımı', 'TEMİZ_KOD']].drop_duplicates()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Eşleşen", len(df[df['BRN KOD'].notna() & (df['BRN KOD'].astype(str) != "")] ))
        c3.metric("Bekleyen", len(unmapped))

        if not unmapped.empty:
            with st.expander("⚠️ Yeni Eşleşme Tanımla", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Form Sünger: {target_row['Malzeme Tanımı']} (Kod: {target_row['TEMİZ_KOD']})")
                
                n_kod = st.text_input("BRN Kodu:")
                n_ad = st.text_input("BRN Ürün Adı:")
                
                if st.button("🚀 HAFIZAYA GÖM VE DRIVE'A KAYDET"):
                    if n_kod and n_ad:
                        # MÜKERRER KAYIT KONTROLÜ (Senin uyardığın nokta)
                        if not ((mapping_df['FORM_TEMİZ'] == target_row['TEMİZ_KOD']).any()):
                            yeni_kayit = pd.DataFrame([{
                                "FORM SÜNGER KOD": str(target_row['TEMİZ_KOD']),
                                "FORM SÜNGER ÜRÜN ADI": str(target_row['Malzeme Tanımı']).strip(),
                                "BRN KOD": str(n_kod).strip(),
                                "BRN ÜRÜN ADI": str(n_ad).strip(),
                                "DANSİTE": "-", "ÖZELLİK": "-", "RENK": "-", "KALIP": "-"
                            }])
                            
                            guncel_df = pd.concat([mapping_df.drop(columns=['FORM_TEMİZ'], errors='ignore'), yeni_kayit], ignore_index=True)
                            
                            # Lokal Kayıt
                            guncel_df.to_csv(LOCAL_MAPPING_FILE, index=False)
                            # Drive Güncelleme
                            try: conn.update(worksheet="Eşleşmeler", data=guncel_df)
                            except: pass
                            
                            if 'main_data' in st.session_state: del st.session_state['main_data']
                            st.success("Hafıza güncellendi! Kodu şimdi tanıyacak.")
                            st.rerun()
                        else:
                            st.warning("Bu kod zaten hafızada var, eşleşme tipinde bir uyuşmazlık olabilir.")

        # --- 5. OPERASYON ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input).strip()]
            if not match.empty:
                item = match.iloc[0]
                # KeyError Riski Çözüldü: Büyük harf kullanımı
                if pd.notna(item['BRN KOD']) and str(item['BRN KOD']) != "":
                    st.success(f"Ürün: {item['BRN ÜRÜN ADI']}")
                    st.info(f"BRN Kodu: {item['BRN KOD']}")
                    if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                        st.balloons()
            else:
                st.error("Parti bulunamadı veya henüz eşleşmemiş.")
    else:
        st.info("İşlem için Excel dosyasını yükleyin.")

    st.markdown("---")
    st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b></div>", unsafe_allow_html=True)
