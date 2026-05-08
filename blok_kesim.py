import streamlit as st
import pandas as pd
import re

def run_blok_kesim(conn):
    st.title("✂️ Blok & Rulo Kesim")
    
    # --- 1. DRİVE'DAKİ EŞLEŞMELER TABLOSUNU YÜKLE ---
    try:
        # Sadece Drive'daki "Eşleşmeler" sekmesini ana referans olarak alıyoruz
        mapping_df = conn.read(worksheet="Eşleşmeler", ttl=0)
        mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
    except Exception:
        cols = ["FORM SÜNGER KOD", "FORM SÜNGER ÜRÜN ADI", "BRN KOD", "BRN ÜRÜN ADI", "DANSİTE", "ÖZELLİK", "RENK", "KALIP"]
        mapping_df = pd.DataFrame(columns=cols)
        st.warning("⚠️ Drive'daki 'Eşleşmeler' sekmesi okunamadı.")

    # --- 2. DOSYA YÜKLEME ALANI ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı**")
        uploaded_file = st.file_uploader("Excel Yükle", type=['xlsx'], key="bk_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                # TALİMAT: Sadece "Main sheet" sekmesi okunacak
                df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
                
                # ATOMİK TEMİZLİK FONKSİYONU
                def clean_code(val):
                    c = re.sub(r'\D', '', str(val))
                    return c.strip()

                # Yüklenen dosyadaki Malzeme Kodu'nu temizle
                df_main['TEMİZ_KOD'] = df_main['Malzeme Kodu'].apply(clean_code)
                
                # Drive'daki Form Sünger Kodlarını temizle
                if 'FORM SÜNGER KOD' in mapping_df.columns:
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                else:
                    mapping_df['FORM_TEMİZ'] = "YOK"

                # EŞLEŞTİRME: Main sheet (TEMİZ_KOD) <-> Drive Eşleşmeler (FORM_TEMİZ)
                df_final = df_main.merge(
                    mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], 
                    left_on='TEMİZ_KOD', 
                    right_on='FORM_TEMİZ', 
                    how='left'
                )
                
                st.session_state['main_data'] = df_final
                st.success(f"✅ 'Main sheet' başarıyla işlendi.")
            except Exception as e:
                st.error(f"Hata: {e} (Lütfen 'Main sheet' sekmesini kontrol edin)")

    # --- 3. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        unmapped = df[df['BRN KOD'].isna() | (df['BRN KOD'].astype(str).str.strip() == "")][['Malzeme Kodu', 'Malzeme Tanımı', 'TEMİZ_KOD']].drop_duplicates()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Eşleşen Ürün", len(df[df['BRN KOD'].notna()]))
        c3.metric("Eşleşme Bekleyen", len(unmapped))

        if not unmapped.empty:
            with st.expander("⚠️ Yeni Eşleşme Tanımla", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Form Sünger: **{target_row['Malzeme Tanımı']}** (Kod: {target_row['TEMİZ_KOD']})")
                
                # Yeni bir eşleşme tanımlarken manuel giriş yapıyoruz
                new_brn_kod = st.text_input("BRN Kodu Giriniz:")
                new_brn_ad = st.text_input("BRN Ürün Adı Giriniz:")
                
                if st.button("🚀 EŞLEŞTİR VE HAFIZAYA AL"):
                    if new_brn_kod and new_brn_ad:
                        yeni_kayit = pd.DataFrame([{
                            "FORM SÜNGER KOD": str(target_row['TEMİZ_KOD']),
                            "FORM SÜNGER ÜRÜN ADI": str(target_row['Malzeme Tanımı']).strip(),
                            "BRN KOD": str(new_brn_kod).strip(),
                            "BRN ÜRÜN ADI": str(new_brn_ad).strip(),
                            "DANSİTE": "-", "ÖZELLİK": "-", "RENK": "-", "KALIP": "-"
                        }])
                        
                        # Drive'daki "Eşleşmeler" sekmesini güncelle
                        guncel_df = pd.concat([mapping_df.drop(columns=['FORM_TEMİZ'], errors='ignore'), yeni_kayit], ignore_index=True)
                        conn.update(worksheet="Eşleşmeler", data=guncel_df)
                        
                        if 'main_data' in st.session_state: del st.session_state['main_data']
                        st.success("Yeni eşleşme Drive'a kaydedildi!")
                        st.rerun()
                    else:
                        st.warning("Lütfen BRN kodu ve adını doldurun.")

        # --- 4. OPERASYON ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input).strip()]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN KOD']):
                    with st.container(border=True):
                        st.success(f"Eşleşen BRN: **{item['BRN Ürün Adı']}**")
                        st.write(f"Kod: {item['BRN KOD']} | Miktar: {item['Teslimat Miktarı']}")
                        if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                            st.balloons()
            else:
                st.error("Bu parti eşleşmemiş veya listede yok.")
    else:
        st.info("Lütfen Excel dosyasını yükleyin.")

    # --- İMZA ---
    st.markdown("---")
    _, col_sign = st.columns([3, 1])
    with col_sign:
        st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>Logistics Solutions</small></div>", unsafe_allow_html=True)
