import streamlit as st
import pandas as pd

def run_blok_kesim(conn):
    st.title("✂️ Blok & Rulo Kesim")
    
    # --- 1. HAFIZAYI (MAPPING) YÜKLE ---
    try:
        mapping_df = conn.read(worksheet="Eşleşmeler", ttl="0")
    except:
        mapping_df = pd.DataFrame(columns=["Tedarikçi_Kodu", "BRN Kod", "Brn_isim"])

    with st.sidebar:
        st.header("📁 Veri Kaynağı")
        uploaded_file = st.file_uploader("DataGrid Excel Dosyasını Yükleyin", type=['xlsx'], key="blok_kesim_uploader")
        
        if uploaded_file:
            df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
            df_sunger = pd.read_excel(uploaded_file, sheet_name='Sünger')
            
            # Sınıflandırma Mantığı (Senin Kuralların)
            def classify(tanim):
                tanim_up = str(tanim).upper()
                if "BLOKCM" in tanim_up: return "Blok"
                elif "RULO" in tanim_up: return "Rulo"
                elif "DUZ" in tanim_up: return "Plaka"
                return "Diğer"

            df_main['Kategori'] = df_main['Malzeme Tanımı'].apply(classify)
            
            # 12.000 Satırı Hafızadaki Eşleşmelerle Birleştir (Hızlı Merge)
            df_final = df_main.merge(
                mapping_df[['Tedarikçi_Kodu', 'BRN Kod', 'Brn_isim']], 
                left_on='Malzeme Kodu', 
                right_on='Tedarikçi_Kodu', 
                how='left'
            )
            
            st.session_state['main_data'] = df_final
            st.session_state['sunger_data'] = df_sunger
            st.success(f"Analiz Tamamlandı! {len(df_main)} sevkiyat satırı işlendi.")

    # --- 2. EKRAN YÖNETİMİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        unmapped = df[df['BRN Kod'].isna()][['Malzeme Kodu', 'Malzeme Tanımı']].drop_duplicates()

        # Özet Bilgiler
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Toplam Satır", len(df))
        with c2: st.metric("Tanınan Ürünler", len(df[df['BRN Kod'].notna()]))
        with c3: st.metric("Bekleyen Yeni SKU", len(unmapped))

        # --- 3. AKILLI EŞLEŞTİRME (12.000 SKU İÇİNDE ARAMA) ---
        if not unmapped.empty:
            with st.expander("⚠️ Yeni Ürün Tiplerini Tanımla", expanded=True):
                target_row = unmapped.iloc[0] # Sıradaki ilk bilinmeyen ürünü getir
                st.write(f"Şu an eşleşen: **{target_row['Malzeme Tanımı']}** ({target_row['Malzeme Kodu']})")
                
                # 12.000 SKU İçinde Arama Kutusu
                search_query = st.text_input("Stok Kartı Ara (İsim veya Kod yazın...)", key="sku_search")
                
                if search_query:
                    # 12.000 SKU içinde filtreleme yapıyoruz (Büyük/Küçük harf duyarsız)
                    filtered_skus = st.session_state['sunger_data'][
                        st.session_state['sunger_data']['isim'].str.contains(search_query, case=False, na=False) |
                        st.session_state['sunger_data']['kod'].str.contains(search_query, case=False, na=False)
                    ].head(10) # Sadece ilk 10 sonucu göster ki ekran kasılmasın
                    
                    if not filtered_skus.empty:
                        selected_sku = st.radio("En Yakın Sonuçlar:", filtered_skus['isim'].tolist(), key="sku_radio")
                        
                        if st.button("BU KARTI EŞLEŞTİR VE KAYDET", key="btn_eslestir"):
                            bizim_kart = filtered_skus[filtered_skus['isim'] == selected_sku].iloc[0]
                            # Yeni eşleşmeyi listeye ekle
                            yeni_kayit = pd.DataFrame([{
                                "Tedarikçi_Kodu": target_row['Malzeme Kodu'],
                                "BRN Kod": bizim_kart['kod'],
                                "Brn_isim": bizim_kart['isim']
                            }])
                            # Google Sheets Güncelle - Append hatasını önlemek için concat + update
                            guncel_df = pd.concat([mapping_df, yeni_kayit], ignore_index=True)
                            conn.update(worksheet="Eşleşmeler", data=guncel_df)
                            st.success("Hafızaya alındı! Sayfa yenileniyor...")
                            st.rerun()
                    else:
                        st.warning("Aradığınız kriterde bir stok kartı bulunamadı.")

        # --- 4. OPERASYON: PARTİ NO İLE SORGULAMA ---
        st.divider()
        parti_input = st.text_input("🔍 Parti No (Barkod) Okutun", key="parti_arama")
        
        if parti_input:
            match = df[df['Parti No'].astype(str) == str(parti_input)]
            if not match.empty:
                item = match.iloc[0]
                if pd.notna(item['BRN Kod']):
                    with st.container(border=True):
                        st.success(f"Ürün Tanındı: **{item['Brn_isim']}**")
                        st.write(f"Tedarikçi Kodu: {item['Malzeme Kodu']} | Kategori: {item['Kategori']}")
                        
                        # Miktar Gösterimi (Senin Kuralların)
                        m = item['Teslimat Miktarı']
                        if item['Kategori'] == "Blok": st.info(f"📏 Yükseklik: {m} cm")
                        elif item['Kategori'] == "Rulo": st.info(f"🌀 Uzunluk: {m} mt")
                        elif item['Kategori'] == "Plaka": st.info(f"📦 Paket İçi: {int(m)} Adet")
                        
                        if st.button("HAREKETİ KAYDET", key="btn_kaydet_blok"):
                            st.balloons()
            else:
                st.error("Bu ürünün tipi henüz eşleştirilmemiş. Lütfen yukarıdaki panelden eşleştirin.")
    else:
        st.info("Lütfen sol menüden Excel dosyasını yükleyin.")

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
