import streamlit as st
import pandas as pd
import veritabani
import io

def go_home():
    st.session_state.page = 'home'

def goster():
    # Sayfa Başlığı ve Geri Butonu (Yerleşim düzeltilmiş)
    c_nav, c_title = st.columns([1, 5])
    with c_nav:
        if st.button("⬅️"): go_home(); st.rerun()
    with c_title:
        st.markdown("<h3 style='margin-top: -10px;'>🏗️ Üretim Hazırlık</h3>", unsafe_allow_html=True)

    st.markdown("---")

    # --- YENİ İŞ EMRİ YÜKLEME ---
    with st.expander("📥 Yeni İş Emri Yükle", expanded=True):
        yuklenen_dosya = st.file_uploader("Excel dosyasını seçin:", type=['xlsx'])
        
        if yuklenen_dosya is not None:
            try:
                # Excel dosyasını oku - 'HAZIRLIK' sekmesine odaklan
                df_is_emri = pd.read_excel(yuklenen_dosya, sheet_name='HAZIRLIK')
                
                # Sütun isimlerini standartlaştır (Boşlukları temizle)
                df_is_emri.columns = [str(c).strip() for c in df_is_emri.columns]
                
                # Dosya adını iş emri adı olarak kullan
                is_emri_adi = yuklenen_dosya.name.replace(".xlsx", "")
                st.info(f"📂 'HAZIRLIK' sekmesi okundu. İş Emri: {is_emri_adi}")

                # Gerekli sütunların varlığını kontrol et ve göster
                cols = ['Stok Kodu', 'Stok Adı', 'İhtiyaç Miktarı']
                if all(c in df_is_emri.columns for c in cols):
                    # Veriyi filtrele ve boş satırları temizle
                    is_emri_data = df_is_emri[cols].dropna(subset=['Stok Kodu']).copy()
                    
                    st.dataframe(is_emri_data, use_container_width=True, hide_index=True)
                    
                    if st.button("🚀 İŞ EMRİNİ SİSTEME KAYDET", type="primary", use_container_width=True):
                        # İş emri veritabanına kayıt işlemleri buraya gelecek
                        st.success(f"{is_emri_adi} başarıyla kaydedildi!")
                else:
                    st.error(f"Excel dosyasında gerekli sütunlar bulunamadı! Beklenen: {cols}")
                    st.write("Mevcut Sütunlar:", list(df_is_emri.columns))
            
            except Exception as e:
                st.error(f"Dosya okuma hatası: {e}")

    # --- MEVCUT İŞ EMRİ TAKİBİ ---
    st.markdown("---")
    st.subheader("📋 Aktif İş Emirleri")
    # Mevcut iş emirlerini listeleme mantığı...
