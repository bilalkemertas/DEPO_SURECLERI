import streamlit as st

def page_ayarlar():
    st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")
    st.markdown("""
        <style>
        #MainMenu, footer, header, .stDeployButton {display: none !important;}
        
        /* Ana konteyner boşlukları çok daraltıldı */
        .block-container { padding: 0.5rem 0.5rem !important; max-width: 100%; }
        
        /* Input fontları ve Yükseklikleri optimize edildi */
        input { font-size: 14px !important; }
        .stButton>button { height: 2.8em; font-size: 14px !important; }
        [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 8px; }
        
        /* Dikey elemanlar arası boşlukları (gap) sıfıra yakın yapıyoruz ki Ekle butonu ekrana sığsın */
        [data-testid="stVerticalBlock"] { gap: 0.4rem !important; }
        
        /* Bölüm başlıkları küçültüldü ve gereksiz marginleri silindi */
        h1, h2, h3, h4, h5 { font-size: 1.1rem !important; margin: 0 !important; padding: 0 !important;}
        
        @media (max-width: 640px) {
            .stMetric { padding: 3px !important; border: 1px solid #eee; margin-bottom: 3px; }
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
        st.markdown("<h3 style='text-align:center; color: #0b3c5d; font-size: 1.2rem !important;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
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
    """Tüm sayfalarda standart imza ve reklam alanını en dar şekilde basar."""
    # Ekranı gereksiz uzatan st.columns ve divider iptal edildi. İnce tek satır bir şerit eklendi.
    st.markdown(
        """
        <div style='text-align: right; border-top: 1px solid #eee; margin-top: 10px; padding-top: 5px;'>
            <p style='margin:0; font-size: 11px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş <span style='color: gray; font-size: 10px;'>| BRN 2026</span></p>
        </div>
        """, 
        unsafe_allow_html=True
    )
