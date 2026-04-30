import streamlit as st
import ana_sayfa
import modul_sayim
import modul_stok
import modul_uretim
import modul_rapor

# --- GLOBAL SAYFA AYARLARI ---
st.set_page_config(
    page_title="BRN Depo Yönetimi",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GLOBAL CSS (Padding ve Yerleşim Düzeltme) ---
st.markdown("""
    <style>
        /* Ana içerik alanını siyah barın altına girmeyecek şekilde aşağı it */
        .main .block-container {
            padding-top: 70px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Başlık puntolarını mobil uyumlu küçült */
        h1 { font-size: 22px !important; }
        h2 { font-size: 20px !important; }
        h3 { font-size: 18px !important; }
        
        /* Gereksiz boşlukları temizle */
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE BAŞLATMA ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# --- ANA YÖNLENDİRME MANTIĞI ---
def main():
    # 1. Giriş Kontrolü (Secrets üzerinden)
    if st.session_state.user is None:
        st.markdown("<div style='padding-top: 20px;'></div>", unsafe_allow_html=True)
        st.subheader("🔐 BRN Depo Girişi")
        
        # Secrets'tan veriyi çekme
        try:
            # Streamlit Secrets alanındaki [passwords] başlığını okur
            creds = st.secrets["passwords"]
        except Exception:
            st.error("Secrets ayarlarında [passwords] başlığı bulunamadı!")
            return

        with st.form("login_form"):
            kullanici_input = st.text_input("Kullanıcı Adı:")
            sifre_input = st.text_input("Parola:", type="password")
            submit = st.form_submit_button("GİRİŞ YAP", use_container_width=True)
            
            if submit:
                # Secrets içindeki kullanıcıları ve şifreleri kontrol et
                if kullanici_input in creds and str(sifre_input) == str(creds[kullanici_input]):
                    st.session_state.user = kullanici_input
                    st.session_state.page = 'home'
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre!")
    
    # 2. Giriş Yapılmışsa Sayfa Yönlendirmeleri
    else:
        if st.session_state.page == 'home':
            ana_sayfa.goster()
        
        elif st.session_state.page == 'sayim':
            modul_sayim.goster()
            
        elif st.session_state.page == 'stok':
            modul_stok.goster()
            
        elif st.session_state.page == 'uretim':
            modul_uretim.goster()
            
        elif st.session_state.page == 'rapor':
            # import adına göre düzeltildi (modul_rapor)
            modul_rapor.goster()
            
        # Kullanıcı varsa ama sayfa login'de kalmışsa ana sayfaya döndür
        elif st.session_state.page == 'login':
            st.session_state.page = 'home'
            st.rerun()

if __name__ == "__main__":
    main()
