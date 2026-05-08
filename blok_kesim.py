import streamlit as st
import pandas as pd

def run_blok_kesim(conn):
    st.title("✂️ Blok & Rulo Kesim")
    
    # --- 1. HAFIZAYI (MAPPING) YÜKLE ---
    try:
        mapping_df = conn.read(worksheet="Eşleşmeler", ttl="0")
    except Exception:
        cols = ["Form Sünger Kod", "Form Sünger Ürün Adı", "BRN Kod", "BRN Ürün Adı", "Dansite", "Özellik", "RENK", "KALIP"]
        mapping_df = pd.DataFrame(columns=cols)
        st.warning("⚠️ 'Eşleşmeler' sekmesi bulunamadı, ilk kayıtta oluşturulacak.")

    # --- 2. DOSYA YÜKLEME ALANI (ANA EKRAN) ---
    with st.container(border=True):
        st.write("📁 **Veri Kaynağı**")
        uploaded_file = st.file_uploader("DataGrid Excel Dosyasını Yükleyin", type=['xlsx'], key="blok_kesim_uploader", label_visibility="collapsed")
        
        if uploaded_file:
            try:
                df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
                df_sunger = pd.read_excel(uploaded_file, sheet_name='Sünger')
                
                # Sınıflandırma Mantığı
                def classify(tanim):
                    tanim_up = str(tanim).upper()
                    if "BLOKCM" in tanim_up: return "Blok"
                    elif "RULO" in tanim_up: return "Rulo"
                    elif "DUZ" in tanim_up: return "Plaka"
                    return "Diğer"

                df_main['Kategori'] = df_main['Malzeme Tanımı'].apply(classify)
                
                # --- ZIRHLI VERİ TEMİZLİĞİ (EŞLEŞME GARANTİSİ) ---
                # Excel kodlarını temizle (Nokta, virgül, boşluk ve .0 siler)
                df_main['Malzeme Kodu'] = df_main['Malzeme Kodu'].astype(str).str.replace(r'[\.,\s]', '', regex=True).str.replace(r'\.0$', '', regex=True).str.strip()
                
                # Sheets kodlarını temizle
                mapping_df['Form Sünger Kod'] = mapping_df['Form Sünger Kod'].astype(str).str.replace(r'[\.,\s]', '', regex=True).str.replace(r'\.0$', '', regex=True).str.strip()

                # Merge işlemi (Yeni sütun isimlerine göre)
                df_final = df_main.merge(
                    mapping_df[['Form Sünger Kod', 'BRN Kod', 'BRN Ürün Adı']], 
                    left_on='Malzeme Kodu', 
                    right_on='Form Sünger Kod', 
                    how='left'
                )
                
                st.session_state['main_data'] = df_final
                st.session_state['sunger_data'] = df_sunger
                st.success(f"✅ Analiz Tamamlandı! {len(df_main)} satır işlendi.")
            except Exception as e:
                st.error(f"Dosya okuma hatası: {e}")

    # --- 3. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        unmapped = df[df['BRN Kod'].isna()][['Malzeme Kodu', 'Malzeme Tanımı']].drop_duplicates()

        # Özet Metrikler
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Satır", len(df))
        c2.metric("Tanınan Ürünler", len(df[df['BRN Kod'].notna()]))
        c3.metric("Bekleyen Yeni SKU", len(unmapped))

        # --- AKILLI EŞLEŞTİRME ---
        if not unmapped.empty:
            with st.expander("⚠️ Yeni Ürün Tiplerini Tanımla", expanded=True):
                target_row = unmapped.iloc[0]
                st.info(f"Bekleyen: **{target_row['Malzeme Tanımı']}** ({target_row['Malzeme Kodu']})")
                
                search_query = st.text_input("BRN Stok Kartı Ara (Kod veya İsim):", key="sku_search")
                
                if search_query:
                    filtered_skus = st.session_state['sunger_data'][
                        st.session_state['sunger_data']['isim'].str.contains(search_query, case=False, na=False) |
                        st.session_state['sunger_data']['kod'].str.contains(search_query, case=False, na=False)
                    ].head(10)
                    
                    if not filtered_skus.empty:
                        selected_sku = st.radio("En Yakın Sonuçlar:", filtered_skus['isim'].tolist(), key="sku_radio")
                        
                        if st.button("🚀 EŞLEŞTİR VE KAYDET", key="btn_eslestir"):
                            bir_kart = filtered_skus[filtered_skus['isim'] == selected_sku].iloc[0]
                            
                            # Yeni sütun yapısına uygun kayıt
                            yeni_kayit = pd.DataFrame([{
                                "Form Sünger Kod": str(target_row['Malzeme Kodu']).strip(),
                                "Form Sünger Ürün Adı": str(target_row['Malzeme Tanımı']).strip(),
                                "BRN Kod": str(bir_kart['kod']).strip(),
                                "BRN Ürün Adı": str(bir_kart['isim']).strip(),
                                "Dansite": "-", "Özellik": "-", "RENK": "-", "KALIP": "-"
                            }])
                            
                            guncel_df = pd.concat([mapping_df, yeni_kayit], ignore_index=True)
                            conn.update(worksheet="Eşleşmeler", data=guncel_df)
                            
                            # Hafızayı temizle ki yeni tabloyla tekrar analiz yapsın
                            if 'main_data' in st.session_state: del st.session_state['main_data']
                            st.success("Hafızaya alındı!")
                            st.rerun()

        # --- 4. OPERASYON: PARTİ SORGULAMA ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No (Barkod) Okutun:", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input)]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN Kod']):
                    with st.container(border=True):
                        st.success(f"Ürün Tanındı: **{item['BRN Ürün Adı']}**")
                        st.caption(f"BRN Kodu: {item['BRN Kod']} | Kategori: {item['Kategori']}")
                        
                        m = item['Teslimat Miktarı']
                        if item['Kategori'] == "Blok": st.info(f"📏 Yükseklik: {m} cm")
                        elif item['Kategori'] == "Rulo": st.info(f"🌀 Uzunluk: {m} mt")
                        elif item['Kategori'] == "Plaka": st.info(f"📦 Paket İçi: {int(m)} Adet")
                        
                        if st.button("🔥 HAREKETİ KAYDET", use_container_width=True):
                            st.balloons()
            else:
                st.error("Bu ürün henüz eşleştirilmemiş.")
    else:
        st.info("Lütfen Excel dosyasını yükleyin.")

    # --- SAYFA SONU İMZASI ---
    st.markdown("---")
    col_sign1, col_sign2 = st.columns([3, 1])
    with col_sign2:
        st.markdown(
            """
            <div style='text-align: right;'>
                <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p>
                <p style='margin:0; font-size: 12px; color: gray;'>Logistics Solutions</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
