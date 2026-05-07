import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Modülleri aynı dizinden içe aktar
import blok_kesim
import teslim_alma

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
st.set_page_config(page_title="WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Kurumsal ERP Hissiyatı İçin Güvenli CSS */
        .block-container { padding: 2rem !important; max-width: 900px; margin: 0 auto; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* Ana Menü Karo (Tile) Tasarımı - Streamlit Özel Seçici */
        div[data-testid="stButton"] > button {
            width: 100%;
            height: 120px;
            border-radius: 12px;
            background-color: #ffffff;
            color: #0b3c5d !important;
            border: 1px solid #dcdcdc;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            font-size: 18px;
            font-weight: 700;
            transition: all 0.2s ease;
            white-space: pre-wrap;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #328cc1;
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
            transform: translateY(-3px);
            color: #328cc1 !important;
        }
        div[data-testid="stButton"] > button:active {
            transform: translateY(0);
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

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

# Oturum Yönetimi (Routing)
if 'page' not in st.session_state:
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
    st.write("") # Boşluk eklemek için
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\nMal Kabul", use_container_width=True):
            st.session_state['page'] = 'mal_kabul'
            st.rerun()
            
    with col2:
        if st.button("✂️\nBlok & Rulo Kesim", use_container_width=True):
            st.session_state['page'] = 'blok_kesim'
            st.rerun()

elif st.session_state['page'] == 'mal_kabul':
    if st.button("⬅️ Ana Menüye Dön", key="back_mal_kabul"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    teslim_alma.run(conn)

elif st.session_state['page'] == 'blok_kesim':
    if st.button("⬅️ Ana Menüye Dön", key="back_blok_kesim"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    blok_kesim.run_blok_kesim(conn)
