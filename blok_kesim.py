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
    
    # --- 1. DOSYA YÜKLEME ALANI ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı (Main sheet)**")
        uploaded_file = st.file_uploader("Excel Yükle", type=['xlsx'], key="bk_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                # ADIM A: Yerel Excel'i oku (Main sheet)
                df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
                
                # ADIM B: TALİMAT - Excel yüklendiği anda Drive'a gidip veri çekiyoruz
                with st.spinner('Drive ile eşleştirme yapılıyor...'):
                    mapping_df = conn.read(worksheet="Eşleşmeler", ttl=0)
                    mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]

                # ADIM C: Temizlik İşlemleri
                def clean_code(val):
                    c = re.sub(r'\D', '', str(val))
                    return c.strip()

                df_main['TEMİZ_KOD'] = df_main['Malzeme Kodu'].apply(clean_code)
                
                if 'FORM SÜNGER KOD' in mapping_df.columns:
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                else:
                    mapping_df['FORM_TEMİZ'] = "YOK"

                # ADIM D: DÜŞEY ARA (MERGE)
                # Drive'daki veriyi alıp Excel'deki verinin karşısına getiriyoruz
                df_final = df_main.merge(
                    mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], 
                    left_on='TEMİZ_KOD', 
                    right_on='FORM_TEMİZ', 
                    how='left'
                )
                
                # Sonuçları belleğe at
                st.session_state['main_data'] = df_final
                st.session_state['drive_mapping'] = mapping_df # Güncelleme için sakla
                st.success(f"✅ Eşleşme Tamamlandı! {len(df_main)} satır kontrol edildi.")
                
            except Exception as e:
                st.error(f"Hata oluştu: {e}")

    # --- 2. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        mapping_df = st.session_state['drive_mapping']
        unmapped = df[df['BRN KOD'].isna() | (df['BRN KOD'].astype(str).str.strip() == "")][['Malzeme Kodu', 'Malzeme Tanımı', 'TEMİZ_KOD']].drop_duplicates()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Eşleşen (BRN)", len(df[df['BRN KOD'].notna()]))
        c3.metric("Yeni Tanımlanacak", len(unmapped))

        if not unmapped.empty:
            with st.expander("⚠️ Yeni Eşleşme Tanımla", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Form Sünger: **{target_row['Malzeme Tanımı']}** (Kod: {target_row['TEMİZ_KOD']})")
                
                new_brn_kod = st.text_input("Atanacak BRN Kodu:")
                new_brn_ad = st.text_input("Atanacak BRN Ürün Adı:")
                
                if st.button("🚀 EŞLEŞTİR VE DRIVE'A KAYDET"):
                    if new_brn_kod and new_brn_ad:
                        yeni_kayit = pd.DataFrame([{
                            "FORM SÜNGER KOD": str(target_row['TEMİZ_KOD']),
                            "FORM SÜNGER ÜRÜN ADI": str(target_row['Malzeme Tanımı']).strip(),
                            "BRN KOD": str(new_brn_kod).strip(),
                            "BRN ÜRÜN ADI": str(new_brn_ad).strip()
                        }])
                        
                        guncel_df = pd.concat([mapping_df.drop(columns=['FORM_TEMİZ'], errors='ignore'), yeni_kayit], ignore_index=True)
                        conn.update(worksheet="Eşleşmeler", data=guncel_df)
                        
                        del st.session_state['main_data']
                        st.success("Drive güncellendi! Yeniden yükleme yapılıyor...")
                        st.rerun()

        # --- 3. OPERASYON ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input).strip()]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN KOD']):
                    with st.container(border=True):
                        st.success(f"Ürün: **{item['BRN Ürün Adı']}**")
                        st.write(f"BRN Kodu: {item['BRN KOD']}")
                        if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                            st.balloons()
            else:
                st.error("Eşleşme bulunamadı.")
    else:
        st.info("Lütfen işlem yapmak için Excel dosyasını yükleyin.")

    # --- İMZA ---
    st.markdown("---")
    st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b></div>", unsafe_allow_html=True)
