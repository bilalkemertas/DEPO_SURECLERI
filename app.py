import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Modülleri içe aktar
import blok_kesim, teslim_alma

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
st.set_page_config(page_title="WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Kurumsal ERP (SAP Fiori / Oracle) Hissiyatı İçin CSS */
        .block-container { padding: 1rem !important; max-width: 800px; margin: 0 auto; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* Genel Font ve Arka Plan */
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f5f7;
        }
        
        /* Ana Menü Karo (Tile) Tasarımı */
        button[kind="primary"] {
            width: 100%;
            height: 110px;
            border-radius: 10px;
            background-color: #ffffff;
            color: #0b3c5d;
            border: 1px solid #dcdcdc;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s ease;
            white-space: pre-wrap;
        }
        button[kind="primary"]:hover {
            border-color: #328cc1;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
            color: #328cc1;
        }
        button[kind="primary"]:active {
            transform: translateY(0);
        }
        
        /* Kurumsal Header */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .erp-title { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 1px; }
        .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }
        
        /* Çıkış Butonu Özel Ayarı */
        .logout-box {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            height: 100%;
        }
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\nMal Kabul", type="primary", use_container_width=True):
            st.session_state['page'] = 'mal_kabul'
            st.rerun()
            
    with col2:
        if st.button("✂️\nBlok & Rulo Kesim", type="primary", use_container_width=True):
            st.session_state['page'] = 'blok_kesim'
            st.rerun()

elif st.session_state['page'] == 'mal_kabul':
    if st.button("⬅️ Ana Menüye Dön"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    teslim_alma.run(conn)

elif st.session_state['page'] == 'blok_kesim':
    if st.button("⬅️ Ana Menüye Dön"):
        st.session_state['page'] = 'main'
        st.rerun()
    st.divider()
    blok_kesim.run_blok_kesim(conn)
