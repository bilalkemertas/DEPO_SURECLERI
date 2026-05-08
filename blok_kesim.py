import streamlit as st
import pandas as pd
import re

def run_blok_kesim(conn):
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
    
    # --- 1. DRİVE'DAKİ "EŞLEŞMELER" TABLOSUNU YÜKLE ---
    try:
        # Drive'daki dosyadan "Eşleşmeler" sekmesini oku
        mapping_df = conn.read(worksheet="Eşleşmeler", ttl=0)
        # Sütun isimlerini standartlaştır (Büyük harf ve temizlik)
        mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
    except Exception:
        cols = ["FORM SÜNGER KOD", "FORM SÜNGER ÜRÜN ADI", "BRN KOD", "BRN ÜRÜN ADI", "DANSİTE", "ÖZELLİK", "RENK", "KALIP"]
        mapping_df = pd.DataFrame(columns=cols)
        st.error("⚠️ Drive'da 'Eşleşmeler' sekmesi bulunamadı!")

    # --- 2. DOSYA YÜKLEME (SADECE MAIN SHEET) ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı (Main sheet)**")
        uploaded_file = st.file_uploader("Excel Yükle", type=['xlsx'], key="bk_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                # TALİMAT: Sadece "Main sheet" sekmesi okunur
                df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
                
                # ATOMİK TEMİZLİK (Sayı dışındaki karakterleri temizle)
                def clean_code(val):
                    c = re.sub(r'\D', '', str(val))
                    return c.strip()

                # TALİMAT: Excel'deki "Malzeme Kodu" sütununu al ve temizle
                df_main['TEMİZ_KOD'] = df_main['Malzeme Kodu'].apply(clean_code)
                
                # Drive tarafındaki "FORM SÜNGER KOD" sütununu temizle
                if 'FORM SÜNGER KOD' in mapping_df.columns:
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                else:
                    mapping_df['FORM_TEMİZ'] = "YOK"

                # TALİMAT: Drive'daki "Eşleşmeler" ile arama yap ve "BRN KOD"u getir
                df_final = df_main.merge(
                    mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], 
                    left_on='TEMİZ_KOD', 
                    right_on='FORM_TEMİZ', 
                    how='left'
                )
                
                st.session_state['main_data'] = df_final
                st.success(f"✅ 'Main sheet' işlendi. {len(df_main)} satır analiz edildi.")
            except Exception as e:
                st.error(f"Hata: {e}")

    # --- 3. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        # BRN KODU olmayanları bul (NaN veya Boş)
        unmapped = df[df['BRN KOD'].isna() | (df['BRN KOD'].astype(str).str.strip() == "")][['Malzeme Kodu', 'Malzeme Tanımı', 'TEMİZ_KOD']].drop_duplicates()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Eşleşen (BRN)", len(df[df['BRN KOD'].notna() & (df['BRN KOD'].astype(str).str.strip() != "")]))
        c3.metric("Yeni Tanımlanacak", len(unmapped))

        if not unmapped.empty:
            with st.expander("⚠️ Yeni Eşleşme Tanımla (Drive'a Kaydeder)", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Form Sünger: **{target_row['Malzeme Tanımı']}** (Kod: {target_row['TEMİZ_KOD']})")
                
                # Manuel eşleştirme girişi
                new_brn_kod = st.text_input("Atanacak BRN Kodu:")
                new_brn_ad = st.text_input("Atanacak BRN Ürün Adı:")
                
                if st.button("🚀 EŞLEŞTİR VE HAFIZAYA AL"):
                    if new_brn_kod and new_brn_ad:
                        yeni_kayit = pd.DataFrame([{
                            "FORM SÜNGER KOD": str(target_row['TEMİZ_KOD']),
                            "FORM SÜNGER ÜRÜN ADI": str(target_row['Malzeme Tanımı']).strip(),
                            "BRN KOD": str(new_brn_kod).strip(),
                            "BRN ÜRÜN ADI": str(new_brn_ad).strip(),
                            "DANSİTE": "-", "ÖZELLİK": "-", "RENK": "-", "KALIP": "-"
                        }])
                        
                        # TALİMAT: Drive'daki "Eşleşmeler" sekmesini güncelle
                        guncel_df = pd.concat([mapping_df.drop(columns=['FORM_TEMİZ'], errors='ignore'), yeni_kayit], ignore_index=True)
                        conn.update(worksheet="Eşleşmeler", data=guncel_df)
                        
                        if 'main_data' in st.session_state: del st.session_state['main_data']
                        st.success("Kayıt başarılı! Bir sonraki yüklemede otomatik tanınacak.")
                        st.rerun()
                    else:
                        st.warning("Lütfen BRN kodu ve adını girin.")

        # --- 4. OPERASYON ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input).strip()]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN KOD']) and str(item['BRN KOD']).strip() != "":
                    with st.container(border=True):
                        st.success(f"Eşleşen Ürün: **{item['BRN Ürün Adı']}**")
                        st.write(f"BRN Kodu: {item['BRN KOD']}")
                        st.info(f"Miktar: {item['Teslimat Miktarı']}")
                        if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                            st.balloons()
            else:
                st.error("Bu parti numarası listede yok veya henüz eşleşmemiş.")
    else:
        st.info("Lütfen Excel dosyasını yükleyin.")

    # --- İMZA ---
    st.markdown("---")
    _, col_sign = st.columns([3, 1])
    with col_sign:
        st.markdown(
            """
            <div style='text-align: right;'>
                <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p>
                <p style='margin:0; font-size: 12px; color: gray;'>Logistics Solutions</p>
            </div>
            """, unsafe_allow_html=True
        )
