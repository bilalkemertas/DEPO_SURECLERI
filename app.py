import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- AYARLAR VE GÜVENLİK ---
st.set_page_config(page_title="Bilal BRN Depo", page_icon="📦", layout="centered")

# Google Sheets Bağlantı Fonksiyonu
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # NOT: st.secrets içindeki 'gcp_service_account' kısmını Streamlit Cloud panelinden ayarlamış olmalısın
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    return gspread.authorize(creds)

# Veritabanı ve Sayfa İsimleri
SPREADSHEET_NAME = "Depo_Veritabani" # Google Sheets dosyanızın adı
SHEET_STOK = "Stok_Kayitlari"
SHEET_EMIRLER = "Is_Emirleri"

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

# Ürün Sözlüğü (Hız için bir kez çekilir)
if 'sku_dict' not in st.session_state:
    st.session_state.sku_dict = {
        "8690001": "Plastik Hammadde A",
        "8690002": "Metal Profil 20x20",
        "8690003": "Koli Bandı 45mm",
        # Buraya gerçek ürün listenizi manuel veya Google Sheets'ten çekerek ekleyebilirsiniz
    }

# --- YÖNLENDİRME FONKSİYONLARI ---
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'

# ==========================================
# 1. ANA MENÜ (DASHBOARD)
# ==========================================
if st.session_state.page == 'home':
    st.title("📦 BRN DEPO OPERASYONLARI")
    st.markdown("Hangi işlemi yapmak istiyorsunuz?")
    
    st.write("")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 STOK VE TRANSFER\n(Giriş/Çıkış İşlemleri)", use_container_width=True, type="primary"):
            go_stok()
            st.rerun()
            
    with col2:
        if st.button("🏭 ÜRETİM HAZIRLIK\n(İş Emri & Malzeme)", use_container_width=True, type="primary"):
            go_uretim()
            st.rerun()

# ==========================================
# 2. STOK İŞLEMLERİ EKRANI (v11.9 Geliştirilmiş)
# ==========================================
elif st.session_state.page == 'stok':
    st.sidebar.button("⬅️ Ana Menü", on_click=go_home)
    st.header("Stok ve Transfer Yönetimi")
    
    tab1, tab2 = st.tabs(["📥 İşlem Ekranı", "🔄 Akıllı Transfer"])
    
    with tab1:
        st.subheader("Ürün Giriş/Çıkış")
        with st.form("stok_form", clear_on_submit=True):
            barcode = st.text_input("Barkod Okutun / Kodu Yazın")
            sku_name = st.session_state.sku_dict.get(barcode, "⚠️ Ürün Bulunamadı")
            st.info(f"Ürün Adı: **{sku_name}**")
            
            adet = st.number_input("Miktar", min_value=1, step=1)
            adres = st.text_input("Adres (Örn: A-01-02)")
            islem_tipi = st.selectbox("İşlem Tipi", ["Giriş", "Çıkış"])
            
            submit = st.form_submit_button("Kaydı Tamamla")
            if submit:
                # Buraya Google Sheets Kayıt Kodları Gelecek
                st.success(f"{sku_name} başarıyla {islem_tipi} yapıldı!")

    with tab2:
        st.subheader("Depo İçi Transfer")
        search_sku = st.selectbox("Ürün Seçiniz (Arama Yapılabilir)", [""] + list(st.session_state.sku_dict.values()))
        
        if search_sku:
            # Seçilen isme göre kodu bul
            rev_dict = {v: k for k, v in st.session_state.sku_dict.items()}
            sku_code = rev_dict.get(search_sku)
            
            st.warning(f"Seçilen: {search_sku} ({sku_code})")
            t_adet = st.number_input("Transfer Adedi", min_value=1)
            t_hedef = st.text_input("Hedef Adres")
            
            if st.button("Transferi Gerçekleştir"):
                st.success(f"{search_sku} ürünü {t_hedef} adresine transfer edildi.")

# ==========================================
# 3. ÜRETİM HAZIRLIK EKRANI (Yeni Nesil)
# ==========================================
elif st.session_state.page == 'uretim':
    st.sidebar.button("⬅️ Ana Menü", on_click=go_home)
    st.header("Üretim Hazırlık Ekranı")
    
    # BÖLÜM 1: EXCEL YÜKLEME (OFİS)
    with st.expander("📥 Yeni İş Emri Yükle (Excel)", expanded=False):
        uploaded_file = st.file_uploader("HAZIRLIK sekmesi olan dosyayı seçin", type=["xlsx"])
        if uploaded_file:
            try:
                # Dosya Adı = İş Emri No
                is_emri_no = uploaded_file.name.split('.')[0]
                
                # Dinamik Başlık Bulucu
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                h_idx = 0
                for i, row in df_raw.iterrows():
                    if row.astype(str).str.contains("KODU").any():
                        h_idx = i
                        break
                
                # Veriyi Oku & Birleştirilmiş Hücreleri Doldur
                df_prep = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=h_idx).ffill()
                
                # Sütun Ayıklama
                k_col = [c for c in df_prep.columns if "KODU" in str(c).upper()][0]
                a_col = [c for c in df_prep.columns if "ADI" in str(c).upper()][0]
                m_col = [c for c in df_prep.columns if "İHTİYAÇ" in str(c).upper()][0]
                
                df_final = df_prep[[k_col, a_col, m_col]].copy()
                df_final.columns = ["Ürün Kodu", "Ürün Adı", "İhtiyaç Miktarı"]
                df_final.insert(0, "İş Emri", is_emri_no)
                df_final["Hazırlanan Adet"] = 0
                
                st.write("Okunan Veri Özeti:")
                st.dataframe(df_final.head())
                
                if st.button("Veritabanına İşle"):
                    st.success(f"{is_emri_no} nolu iş emri sisteme eklendi!")
            except Exception as e:
                st.error(f"Hata: {e}")

    st.markdown("---")
    
    # BÖLÜM 2: HAZIRLIK LİSTESİ (DEPO)
    st.subheader("📋 Hazırlık Seçim Ekranı")
    
    # Örnek Index Listesi (Normalde Google Sheets'ten çekilecek)
    is_emri_secimi = st.selectbox("İş Emri Seçiniz (Index):", ["Seçiniz...", "WO-1045", "WO-1046"])
    
    if is_emri_secimi != "Seçiniz...":
        st.info(f"Hazırlanan: **{is_emri_secimi}**")
        
        # Örnek Tablo (Normalde Filtrelenip gelecek)
        df_view = pd.DataFrame({
            "Ürün Kodu": ["KOD-01", "KOD-02"],
            "Ürün Adı": ["Cıvata", "Somun"],
            "İhtiyaç": [100, 200],
            "Hazırlanan": [0, 0]
        })
        
        edited_df = st.data_editor(
            df_view,
            disabled=["Ürün Kodu", "Ürün Adı", "İhtiyaç"],
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("Hazırlanan Miktarları Kaydet"):
            st.success("Veriler kaydedildi!")
