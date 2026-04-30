import streamlit as st
import login_ekrani
import ana_sayfa
import modul_sayim
import modul_stok
import modul_uretim
import modul_raporlar

# --- GLOBAL SAYFA AYARLARI ---
st.set_page_config(
    page_title="BRN Depo Yönetimi",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GLOBAL CSS (Tüm ekranlarda barın altında kalmayı engeller) ---
st.markdown("""
    <style>
        /* Ana içerik alanını siyah barın altına girmeyecek şekilde aşağı it */
        .main .block-container {
            padding-top: 60px !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Başlık puntolarını mobil uyumlu küçült */
        h1 { font-size: 24px !important; }
        h2 { font-size: 22px !important; }
        h3 { font-size: 20px !important; }
        
        /* Streamlit standart header'ını gizle (isteğe bağlı, temiz görünüm için) */
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE BAŞLATMA ---
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'user' not in st.session_state:
    st.session_state.user = None

# --- ANA YÖNLENDİRME MANTIĞI ---
def main():
    # 1. Giriş Kontrolü (Login pencerisini zorunlu tutar)
    if st.session_state.user is None:
        login_ekrani.goster()
    
    # 2. Sayfa Yönlendirmeleri
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
            modul_raporlar.goster()
            
        # Eğer sayfa login'de kalmışsa ama kullanıcı varsa ana sayfaya at
        elif st.session_state.page == 'login':
            st.session_state.page = 'home'
            st.rerun()

if __name__ == "__main__":
    main()
