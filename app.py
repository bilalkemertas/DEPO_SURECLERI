import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Modülleri aynı dizinden içe aktar
import blok_kesim
import teslim_alma
import modul_rapor
import modul_sayim
import modul_stok
import modul_uretim
import teslim_alma

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
elif st.session_state['page'] not in ['main', 'mal_kabul', 'blok_kesim']:
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\nMal Kabul"):
            st.session_state['page'] = 'mal_kabul'
            st.rerun()
            
    with col2:
        if st.button("✂️\nBlok & Rulo Kesim"):
            st.session_state['page'] = 'blok_kesim'
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
