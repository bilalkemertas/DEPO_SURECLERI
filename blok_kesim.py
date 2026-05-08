import streamlit as st
import pandas as pd
import re

def run_blok_kesim(conn):
    st.title("✂️ Blok & Rulo Kesim")
    
    # --- 1. DRİVE'DAKİ EŞLEŞMELER TABLOSUNU YÜKLE ---
    try:
        mapping_df = conn.read(worksheet="Eşleşmeler", ttl=0)
        mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
    except Exception:
        cols = ["FORM SÜNGER KOD", "FORM SÜNGER ÜRÜN ADI", "BRN KOD", "BRN ÜRÜN ADI", "DANSİTE", "ÖZELLİK", "RENK", "KALIP"]
        mapping_df = pd.DataFrame(columns=cols)
        st.warning("⚠️ Drive'da 'Eşleşmeler' sekmesi okunamadı.")

    # --- 2. DOSYA YÜKLEME ALANI ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı**")
        uploaded_file = st.file_uploader("Excel Yükle", type=['xlsx'], key="bk_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                # Dinamik sekme okuma: İlk sekmeyi 'Main sheet' kabul et
                excel_obj = pd.ExcelFile(uploaded_file)
                df_main = pd.read_excel(uploaded_file, sheet_name=excel_obj.sheet_names[0])
                
                # Eğer dosyada 'Sünger' sekmesi varsa oku, yoksa boş DataFrame oluştur (Hata almamak için)
                if 'Sünger' in excel_obj.sheet_names:
                    df_sunger = pd.read_excel(uploaded_file, sheet_name='Sünger')
                else:
                    df_sunger = pd.DataFrame(columns=['kod', 'isim'])

                # ATOMİK TEMİZLİK (Sayı dışındaki her şeyi siler)
                def clean_code(val):
                    c = re.sub(r'\D', '', str(val))
                    return c.strip()

                # Excel'deki "Malzeme Kodu" sütununu temizle
                # Not: Sütun isminin tam "Malzeme Kodu" olduğundan emin ol patron
                df_main['TEMİZ_KOD'] = df_main['Malzeme Kodu'].apply(clean_code)
                
                # Drive'daki "FORM SÜNGER KOD" sütununu temizle
                if 'FORM SÜNGER KOD' in mapping_df.columns:
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                else:
                    mapping_df['FORM_TEMİZ'] = "YOK"

                # MERGE: Malzeme Kodu (Excel) == FORM SÜNGER KOD (Drive)
                df_final = df_main.merge(
                    mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], 
                    left_on='TEMİZ_KOD', 
                    right_on='FORM_TEMİZ', 
                    how='left'
                )
                
                st.session_state['main_data'] = df_final
                st.session_state['sunger_data'] = df_sunger
                st.success(f"✅ {excel_obj.sheet_names[0]} sekmesi başarıyla işlendi.")
                
            except Exception as e:
                st.error(f"Sistem Hatası: {e}")

    # --- 3. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        unmapped = df[df['BRN KOD'].isna() | (df['BRN KOD'].astype(str).str.strip() == "")][['Malzeme Kodu', 'Malzeme Tanımı', 'TEMİZ_KOD']].drop_duplicates()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Tanınan Ürünler", len(df[df['BRN KOD'].notna() & (df['BRN KOD'].astype(str).str.strip() != "")]))
        c3.metric("Bekleyen Yeni SKU", len(unmapped))

        if not unmapped.empty:
            with st.expander("⚠️ Yeni Ürün Tiplerini Tanımla", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Bekleyen: **{target_row['Malzeme Tanımı']}**")
                
                search_query = st.text_input("BRN Stok Kartı Ara (Kod/İsim):", key="sku_search")
                
                if search_query:
                    # 'Sünger' sekmesi yoksa bu kısım boş gelir, manuel yazman gerekir
                    filtered_skus = st.session_state['sunger_data'][
                        st.session_state['sunger_data']['isim'].str.contains(search_query, case=False, na=False) |
                        st.session_state['sunger_data']['kod'].astype(str).str.contains(search_query, case=False, na=False)
                    ].head(10)
                    
                    if not filtered_skus.empty:
                        selected_sku = st.radio("Seçiniz:", filtered_skus['isim'].tolist(), key="sku_radio")
                        
                        if st.button("🚀 EŞLEŞTİR VE DRİVE'A KAYDET", key="btn_eslestir"):
                            bir_kart = filtered_skus[filtered_skus['isim'] == selected_sku].iloc[0]
                            
                            yeni_kayit = pd.DataFrame([{
                                "FORM SÜNGER KOD": str(target_row['TEMİZ_KOD']),
                                "FORM SÜNGER ÜRÜN ADI": str(target_row['Malzeme Tanımı']).strip(),
                                "BRN KOD": str(bir_kart['kod']).strip(),
                                "BRN ÜRÜN ADI": str(bir_kart['isim']).strip(),
                                "DANSİTE": "-", "ÖZELLİK": "-", "RENK": "-", "KALIP": "-"
                            }])
                            
                            # Drive güncelleme
                            guncel_df = pd.concat([mapping_df.drop(columns=['FORM_TEMİZ'], errors='ignore'), yeni_kayit], ignore_index=True)
                            conn.update(worksheet="Eşleşmeler", data=guncel_df)
                            
                            if 'main_data' in st.session_state: del st.session_state['main_data']
                            st.success("Kayıt başarılı! Liste yenileniyor...")
                            st.rerun()

        # --- 4. OPERASYON ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No (Barkod) Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input).strip()]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN KOD']) and str(item['BRN KOD']).strip() != "":
                    with st.container(border=True):
                        st.success(f"Ürün: **{item['BRN Ürün Adı']}**")
                        st.write(f"BRN Kodu: {item['BRN KOD']}")
                        st.info(f"Miktar: {item['Teslimat Miktarı']}")
                        if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                            st.balloons()
            else:
                st.error("Ürün bulunamadı veya eşleşmemiş.")
    else:
        st.info("Lütfen Excel dosyasını yükleyin.")

    # --- İMZA ---
    st.markdown("---")
    _, col_sign = st.columns([3, 1])
    with col_sign:
        st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>Logistics Solutions</small></div>", unsafe_allow_html=True)
