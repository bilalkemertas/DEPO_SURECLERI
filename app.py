import streamlit as st
import ana_sayfa
import modul_sayim
# Not: Diğer modüllerin varsa buraya ekle (import modul_stok vb.)

# --- GLOBAL SAYFA AYARLARI ---
st.set_page_config(
    page_title="BRN Depo Yönetimi",
    page_icon="📦",
    layout="centered"
)

# --- GLOBAL CSS (Padding ve Punto Ayarı) ---
st.markdown("""
    <style>
        /* Ana içeriği siyah barın altına girmeyecek şekilde 60px aşağı it */
        .main .block-container {
            padding-top: 60px !important;
        }
        /* Başlıkları mobil için küçült */
        h1, h2, h3 { font-size: 20px !important; }
        /* Araç çubuğunu (siyah barı) biraz daha şeffaf yapabilir veya gizleyebilirsin */
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE BAŞLATMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# --- YÖNLENDİRME MANTIĞI ---
def main():
    # 1. Eğer kullanıcı giriş yapmamışsa LOGIN EKRANI göster
    if st.session_state.user is None:
        st.subheader("🔐 BRN Depo Girişi")
        with st.form("login_form"):
            kullanici = st.text_input("Kullanıcı Adı:")
            sifre = st.text_input("Parola:", type="password")
            if st.form_submit_button("GİRİŞ YAP"):
                # Buraya kendi kullanıcı/şifre mantığını ekleyebilirsin
                if kullanici == "admin" and sifre == "brn123":
                    st.session_state.user = "Depo_Yöneticisi"
                    st.session_state.page = 'home'
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")

    # 2. Giriş yapılmışsa sayfaları göster
    else:
        if st.session_state.page == 'home':
            ana_sayfa.goster()
        elif st.session_state.page == 'sayim':
            modul_sayim.goster()
        # Varsa diğer modüllerini buraya ekle:
        # elif st.session_state.page == 'stok': modul_stok.goster()

if __name__ == "__main__":
    main()
