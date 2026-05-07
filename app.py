import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Modülleri aynı dizinden içe aktar
import blok_kesim
import teslim_alma
# İleride eklenecek modüller için dosyaları oluşturduğunda bu yorum satırlarını açabilirsin:
# import uretim_hazirlik
# import depo_sayim

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
st.set_page_config(page_title="WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# Garantili ve Evrensel CSS Tasarımı
st.markdown("""
    <style>
        .block-container { padding: 2rem !important; max-width: 900px; margin: 0 auto; }
        
        /* Ana Menü Butonları İçin Kesin Geçerli Seçici */
        div.stButton > button {
            height: 120px !important;
            width: 100% !important;
            border-radius: 12px !important;
            font-size: 20px !important;
            font-weight: bold !important;
            background-color: #ffffff !important;
            color: #0b3c5d !important;
            border: 2px solid #0b3c5d !important;
            transition: all 0.3s ease !important;
            white-space: pre-wrap !important;
        }
        div.stButton > button:hover {
            background-color: #0b3c5d !important;
            color: #ffffff !important;
            border-color: #11caa0 !important;
            transform: translateY(-2px);
        }
        
        /* Kurumsal Header */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .erp-title { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px; }
        .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Bağlantısı (Çökmeyi önleyen hata yakalama)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Google Sheets Bağlantı Hatası: {e}")
    conn = None

# Oturum Yönetimi (Routing) ve Sıkışmış State Kurtarma
if 'page' not in st.session_state:
    st.session_state['page'] = 'main'
elif st.session_state['page'] not in ['main', 'mal_kabul', 'blok_kesim', 'uretim_hazirlik', 'depo_sayim']:
    # Eğer hafızada tanımsız bir sayfa kalmışsa otomatik olarak ana menüye at
    st.session_state['page'] = 'main'

# Kurumsal Üst Bilgi (Header)
st.markdown("""
    <div class="erp-header">
        <p class="erp-title">BRN WMS Enterprise</p>
        <p class="erp-user">Aktif Kullanıcı: Depo Yöneticisi</p>
    </div>
""", unsafe_allow_html=True)

# --- SAYFA YÖNLENDİRMELERİ ---

if st.session_state['page'] == 'main':
    st.subheader("Uygulama Menüsü")
    st.write("") # Layout düzeni için boşluk
    
    # --- 1. SATIR BUTONLARI ---
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\nMal Kabul"):
            st.session_state['page'] = 'mal_kabul'
            st.rerun()
            
    with col2:
        if st.button("✂️\nBlok & Rulo Kesim"):
            st.session_state['page'] = 'blok_kesim'
            st.rerun()

    st.write("") # Satırlar arası boşluk

    # --- 2. SATIR BUTONLARI ---
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("🔄\nÜretim Hazırlık (Kitleme)"):
            st.session_state['page'] = 'uretim_hazirlik'
            st.rerun()
            
    with col4:
        if st.button("📊\nDepo Sayım & Envanter"):
            st.session_state['page'] = 'depo_sayim'
            st.rerun()

elif st.session_state['page'] == 'mal_kabul':
    if st.button("⬅️ Ana Menüye Dön", key="back_mal_kabul_btn"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    if conn is not None:
        teslim_alma.run(conn)

elif st.session_state['page'] == 'blok_kesim':
    if st.button("⬅️ Ana Menüye Dön", key="back_blok_kesim_btn"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    if conn is not None:
        blok_kesim.run_blok_kesim(conn)

elif st.session_state['page'] == 'uretim_hazirlik':
    if st.button("⬅️ Ana Menüye Dön", key="back_uretim_btn"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    st.info("🔄 Üretim Hazırlık modülü yapım aşamasındadır. Dosya oluşturulduğunda buraya bağlanacak.")
    # İleride eklenecek: uretim_hazirlik.run(conn)

elif st.session_state['page'] == 'depo_sayim':
    if st.button("⬅️ Ana Menüye Dön", key="back_sayim_btn"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    st.info("📊 Depo Sayım modülü yapım aşamasındadır. Dosya oluşturulduğunda buraya bağlanacak.")
    # İleride eklenecek: depo_sayim.run(conn)
