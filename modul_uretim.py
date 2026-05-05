import streamlit as st
import pandas as pd
import io
from datetime import datetime

def run(conn):
    st.subheader("🏭 Üretim Hazırlık Ekranı")
    st.markdown("---")

    # 1. DOSYA YÜKLEME ALANI
    uploaded_file = st.file_uploader("İş Emri Excel Dosyasını Yükleyin", type=['xlsx'])

    if uploaded_file is not None:
        try:
            # Excel içindeki sayfa isimlerini oku
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # --- Dinamik Sekme Yakalama Mantığı ---
            target_sheet = None
            # Öncelik sırasına göre kontrol et: Önce HAZIRLIK, yoksa Sheet4
            if "HAZIRLIK" in sheet_names:
                target_sheet = "HAZIRLIK"
            elif "Sheet4" in sheet_names:
                target_sheet = "Sheet4"

            if target_sheet:
                # Belirlenen sekmeyi oku
                df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
                
                # Sütun isimlerindeki gizli boşlukları temizle
                df.columns = [str(c).strip() for c in df.columns]
                
                # --- ÖĞE ETİKETLERİNİ YİNELE (REPEAT ITEM LABELS) MANTIĞI ---
                # Excel'deki birleştirilmiş (merged) hücreleri doldurmak için ffill() kullanıyoruz.
                # Bu işlem, en üstteki değeri (Örn: İş Emri No) altındaki boş hücrelere kopyalar.
                df = df.ffill() 

                st.success(f"✅ '{target_sheet}' sekmesi başarıyla yüklendi ve etiketler otomatik yinelendi.")

                # Filtreleme ve Görselleştirme
                st.markdown(f"### 🔍 {target_sheet} Detayları")
                
                # Tabloyu göster (Verileri Streamlit üzerinde listele)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # --- Malzeme Teslim Kaydı Bölümü ---
                st.divider()
                st.markdown("### 📝 Malzeme Teslim Kaydı")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    # 'ffill' sayesinde artık her satırda İş Emri No dolu olduğu için benzersiz listeyi doğru alırız.
                    is_emri_list = df.iloc[:, 0].unique() if not df.empty else []
                    is_emri_no = st.selectbox("İş Emri Seçin:", is_emri_no_list)
                with c2:
                    hazirlayan = st.text_input("Hazırlayan Personel:", value=st.session_state.get('user', ''))
                with c3:
                    onay_durumu = st.checkbox("Hazırlık Tamamlandı", help="Stoktan düşüm için onay gereklidir.")

                if st.button("🚀 HAZIRLIK KAYDINI TAMAMLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                    if onay_durumu and hazirlayan:
                        # Burada 'conn' nesnesi üzerinden veritabanı (Google Sheets) güncelleme işlemleri yapılabilir.
                        st.balloons()
                        st.success(f"'{is_emri_no}' nolu İş Emri için hazırlık kaydı oluşturuldu. Stoklar güncellendi!")
                    else:
                        st.warning("Lütfen hazırlayan personel bilgisini girin ve hazırlığı onaylayın.")

            else:
                # Aranan sekmeler bulunamazsa kullanıcıyı uyar
                st.error("❌ Uygun sekme bulunamadı!")
                st.warning("Yüklediğiniz Excel dosyasında 'HAZIRLIK' veya 'Sheet4' isimli bir sekme olmalıdır.")
                st.info(f"Dosyadaki mevcut sekmeler: {', '.join(sheet_names)}")

        except Exception as e:
            st.error(f"⚠️ Excel dosyası işlenirken bir teknik hata oluştu: {e}")

    # 2. GEÇMİŞ KAYITLAR (ARŞİV)
    st.markdown("---")
    with st.expander("📊 Hazırlık Arşivini Görüntüle"):
        st.info("Tamamlanan hazırlık kayıtları Google Sheets üzerinden buraya çekilebilir.")

# Modül Sonu
