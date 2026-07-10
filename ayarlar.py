import streamlit as st

def page_ayarlar():
    # Ekranı tekrar o eski ferah ve düzgün "wide" (geniş) haline getiriyoruz
    st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")
    st.markdown("""
        <style>
        /* Streamlit varsayılan üst menü ve footer'ını gizle */
        #MainMenu, footer, header, .stDeployButton {display: none !important;}
        
        /* Ana konteyner boşlukları tekrar ferahlatıldı. Maksimum genişlik ile ekran ortalandı */
        .block-container { 
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 1200px; 
            margin: 0 auto; 
        }
        
        /* Expander (Açılır kapanır menü) için şık çerçeve bırakıldı */
        [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; }
        
        /* Mobil cihazlarda (telefonlar) ufak metrik düzeltmeleri */
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
        # Başlık tekrar ferah bir boyuta alındı
        st.markdown("<h2 style='text-align:center; color: #0b3c5d;'>🛡️ Bilal BRN Depo Giriş</h2>", unsafe_allow_html=True)
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

def imza_yazdir():
    """Tüm sayfalarda standart imza ve reklam alanını şık ve dengeli şekilde basar."""
    st.markdown(
        """
        <div style='text-align: right; border-top: 1px solid #ddd; margin-top: 30px; padding-top: 10px;'>
            <p style='margin:0; font-size: 13px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş <span style='color: gray; font-size: 12px;'>| BRN 2026</span></p>
        </div>
        """, 
        unsafe_allow_html=True
    )
