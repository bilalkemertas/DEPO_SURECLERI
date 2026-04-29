import streamlit as st

def page_ayarlar():
    st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")
    st.markdown("""
        <style>
        #MainMenu, footer, header, .stDeployButton {display: none !important;}
        .block-container { padding: 0.5rem 0.5rem !important; }
        input { font-size: 16px !important; }
        .stButton>button { height: 3em; font-size: 16px !important; }
        [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
        @media (max-width: 640px) {
            .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
            .row-font { font-size: 12px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

def session_kontrol():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = None
    if 'page' not in st.session_state: st.session_state.page = 'home'

def guvenlik_duvari():
    if not st.session_state.logged_in:
        st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
        with st.form("Giriş"):
            u_raw = st.text_input("Kullanıcı:")
            p_raw = st.text_input("Parola:", type="password")
            if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_lower = u_raw.strip().lower()
                    if u_lower in users and str(users[u_lower]) == p_raw.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_lower
                        st.rerun()
                    else: st.error("Hatalı Giriş Bilgisi!")
        st.stop()
