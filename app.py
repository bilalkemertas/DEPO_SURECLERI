import streamlit as st
import ana_sayfa
import modul_sayim
# Diğer modüllerini buraya ekle (import modul_stok vb.)

# --- GLOBAL SAYFA AYARLARI ---
st.set_page_config(
    page_title="BRN Depo Yönetimi",
    page_icon="📦",
    layout="centered"
)

# --- GLOBAL CSS (Siyah barın altına girmeyi engeller) ---
st.markdown("""
    <style>
        .main .block-container {
            padding-top: 65px !important;
        }
        h1, h2, h3 { font-size: 20px !important; }
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# --- YÖNLENDİRME ---
def main():
    if st.session_state.user is None:
        st.subheader("🔐 BRN Depo Girişi")
        
        # Secrets dosyasından kullanıcı bilgilerini al
        # Örn secrets formatı: [passwords] / admin = "12345"
        kullanici_listesi = st.secrets.get("passwords", {})

        with st.form("login_form"):
            kullanici = st.text_input("Kullanıcı Adı:")
            sifre = st.text_input("Parola:", type="password")
            if st.form_submit_button("GİRİŞ YAP", use_container_width=True):
                if kullanici in kullanici_listesi and sifre == kullanici_listesi[kullanici]:
                    st.session_state.user = kullanici
                    st.session_state.page = 'home'
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
    else:
        # Sayfa Yönlendirmeleri
        if st.session_state.page == 'home':
            ana_sayfa.goster()
        elif st.session_state.page == 'sayim':
            modul_sayim.goster()
        # elif st.session_state.page == 'stok': modul_stok.goster()

if __name__ == "__main__":
    main()
