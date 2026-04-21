import streamlit as st
import pandas as pd

# --- SAYFA VE SEKME AYARLARI ---
st.set_page_config(page_title="Depo Süreçleri Yönetimi", page_icon="📦", layout="centered")

# --- OTURUM (SESSION) YÖNETİMİ ---
# Kullanıcının hangi sayfada olduğunu aklında tutar. İlk açılışta 'home' (Ana Menü) yapar.
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# --- YÖNLENDİRME FONKSİYONLARI ---
def go_to_stok():
    st.session_state.page = 'stok'

def go_to_uretim():
    st.session_state.page = 'uretim'

def go_home():
    st.session_state.page = 'home'

# ==========================================
# 1. ANA MENÜ (GİRİŞ EKRANI)
# ==========================================
if st.session_state.page == 'home':
    st.title("📦 Depo Süreçleri Kontrol Paneli")
    st.markdown("Lütfen yapmak istediğiniz işlemi seçin:")
    
    st.write("") # Boşluk
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, on_click=go_to_stok, type="primary")
    with col2:
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, on_click=go_to_uretim, type="primary")

# ==========================================
# 2. STOK İŞLEMLERİ EKRANI (Eski Sistemin)
# ==========================================
elif st.session_state.page == 'stok':
    if st.sidebar.button("⬅️ Ana Menüye Dön"):
        go_home()
        st.rerun()
        
    st.header("Stok İşlemleri")
    
    # Eski sistemindeki gibi 2 sekme
    tab1, tab2 = st.tabs(["İşlem Ekranı", "Transfer Ekranı"])
    
    with tab1:
        st.subheader("İşlem Ekranı")
        st.info("Eski v11.9 İşlem Ekranı kodlarınızı buraya entegre edebilirsiniz.")
        # Örn: barkod okutma, miktar girme, veritabanına yazma kodları...
        
    with tab2:
        st.subheader("Transfer Ekranı")
        st.info("Eski v11.9 Akıllı Transfer kodlarınızı buraya entegre edebilirsiniz.")
        # Örn: Ürün adı otomatik bulma ve transfer kaydı kodları...

# ==========================================
# 3. ÜRETİM HAZIRLIK EKRANI (Yeni Geliştirmemiz)
# ==========================================
elif st.session_state.page == 'uretim':
    if st.sidebar.button("⬅️ Ana Menüye Dön"):
        go_home()
        st.rerun()
        
    st.header("Üretim Hazırlık Süreci")
    
    # 3.A - İŞ EMRİ YÜKLEME ALANI
    with st.expander("📥 Yeni İş Emri (Excel) Yükle", expanded=False):
        uploaded_file = st.file_uploader("HAZIRLIK sekmesi içeren Excel dosyasını seçin", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            try:
                # Dosya isminden iş emrini çıkarma
                is_emri_no = uploaded_file.name.split('.')[0]
                
                # Başlık satırını dinamik bulma ("KODU" kelimesini arar)
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                header_index = 0
                for index, row in df_raw.iterrows():
                    if row.astype(str).str.contains("KODU").any():
                        header_index = index
                        break
                
                # Excel'i doğru başlıktan itibaren okuma ve birleştirilmiş hücreleri (NaN) doldurma
                df_is_emri = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=header_index)
                df_is_emri = df_is_emri.ffill()
                
                # Sütunları dinamik eşleştirme
                kodu_col = [col for col in df_is_emri.columns if "KODU" in str(col).upper()][0]
                adi_col = [col for col in df_is_emri.columns if "ADI" in str(col).upper()][0]
                ihtiyac_col = [col for col in df_is_emri.columns if "İHTİYAÇ" in str(col).upper()][0]
                
                # Sadece gerekli sütunları alma
                df_temiz = df_is_emri[[kodu_col, adi_col, ihtiyac_col]].copy()
                df_temiz.columns = ["Ürün Kodu", "Ürün Adı", "İhtiyaç Miktarı"]
                df_temiz.insert(0, "İş Emri", is_emri_no)
                df_temiz["Hazırlanan Adet"] = 0
                
                st.success(f"'{is_emri_no}' başarıyla okundu! Lütfen Google Sheets'e kaydedin.")
                st.dataframe(df_temiz)
                
                # BURAYA GOOGLE SHEETS "IS_EMIRLERI" SAYFASINA KAYDETME KODU EKLENECEK
                
            except Exception as e:
                st.error(f"Dosya işlenirken hata oluştu. Lütfen sekme adının 'HAZIRLIK' olduğundan emin olun. Hata: {e}")

    st.markdown("---")
    
    # 3.B - İŞ EMRİ SEÇİM VE HAZIRLIK ALANI (PERSONEL EKRANI)
    st.subheader("📋 Günlük Hazırlık Listesi")
    
    # NOT: Gerçekte bu listeyi Google Sheets'ten "Is_Emirleri" sayfasındaki benzersiz iş emirlerinden çekeceğiz.
    # Şimdilik UI test için örnek liste koyuyorum.
    is_emirleri_listesi = ["Seçiniz...", "WO-2023-001", "WO-2023-002"] 
    secilen_is_emri = st.selectbox("Lütfen hazırlayacağınız İş Emrini seçin:", is_emirleri_listesi)
    
    if secilen_is_emri != "Seçiniz...":
        st.info(f"Aktif İş Emri: **{secilen_is_emri}** - Lütfen hazırlanan miktarları girin.")
        
        # NOT: Gerçekte burası seçilen iş emrine göre Google Sheets'ten filtrelenip gelecek.
        df_ornek = pd.DataFrame({
            "İş Emri": [secilen_is_emri, secilen_is_emri],
            "Ürün Kodu": ["RM-001", "RM-002"],
            "Ürün Adı": ["Plastik Hammadde", "Boya Bileşeni"],
            "İhtiyaç Miktarı": [500, 150],
            "Hazırlanan Adet": [0, 0]
        })
        
        # Etkileşimli tablo (Sadece "Hazırlanan Adet" düzenlenebilir)
        edited_df = st.data_editor(
            df_ornek,
            disabled=["İş Emri", "Ürün Kodu", "Ürün Adı", "İhtiyaç Miktarı"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Hazırlığı Sisteme Kaydet", type="primary"):
            # BURAYA EDITED_DF VERİSİNİ GOOGLE SHEETS'TE GÜNCELLEME KODU EKLENECEK
            st.success("Miktarlar başarıyla kaydedildi!")
