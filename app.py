import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# 1. GITHUB'DAKİ TÜM MODÜLLERİ VE YENİ ÜRETİM BİTİŞ MODÜLÜNÜ İÇE AKTARIYORUZ
import teslim_alma
import blok_kesim  # Yeni modüler paket yapısını tetikler (blok_kesim/ klasörünü okur)
import modul_stok
import modul_uretim
import modul_sayim
import modul_rapor
import modul_uretim_bitis  # 🆕 Yeni Eklenen Mamül Bazlı Üretim Bitiş Modülü

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
# 🟢 "centered" ekranı boğup butonları birbirine soktuğu için "wide" (geniş) yapıya geri alındı.
st.set_page_config(page_title="BRN WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# 🖥️ STREAMLIT OTURUMU CANLI TUTMA SİHİRBAZI (KEEP-ALIVE)
components.html("""
    <script>
    const interval = setInterval(function() {
        window.parent.postMessage({type: 'streamlit:render'}, '*');
    }, 30000); // 30 Saniyede bir tetikler
    </script>
""", height=0)

# Garantili, Simetrik ve Ferah CSS Tasarımı
st.markdown("""
    <style>
        /* Ekran boşluklarını normalleştirme (Sıkışıklığı çözer) */
        .block-container { padding: 2rem 1rem !important; max-width: 100%; }
        header { visibility: hidden; height: 0 !important; }
        footer { visibility: hidden; height: 0 !important; }
        
        /* 🟢 SATIR ARASI BOŞLUK (GAP) DÜZELTİLDİ: Butonların ve öğelerin birbirine yapışması engellendi */
        [data-testid="stVerticalBlock"] { gap: 1rem !important; }
        
        /* 🟢 BAŞLIK MARJİNLERİ DÜZELTİLDİ: Başlıkların butonlara ve tablolara yapışmaması için boşluk bırakıldı */
        h1, h2, h3 { 
            font-size: 1.3rem !important; 
            margin-top: 15px !important; 
            margin-bottom: 15px !important; 
            padding: 0 !important; 
            color: #0b3c5d;
        }
        
        /* 1. SADECE ANA MENÜ KUTULARI İÇİN (Primary Butonlar) */
        button[kind="primary"] {
            height: 100px !important; /* Mobilde ve Web'de ideal yükseklik, yazılar ezilmez */
            width: 100% !important;
            border-radius: 10px !important;
            font-size: 16px !important;
            font-weight: bold !important;
            background-color: #ffffff !important;
            color: #0b3c5d !important;
            border: 2px solid #dcdcdc !important;
            transition: all 0.3s ease !important;
            white-space: pre-wrap !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
        }
        button[kind="primary"]:hover {
            background-color: #0b3c5d !important;
            color: #ffffff !important;
            border-color: #11caa0 !important;
            transform: translateY(-2px);
        }
        
        /* 2. STANDART BUTONLAR İÇİN (Çıkış, Geri Dön, Giriş) */
        button[kind="secondary"] {
            height: 50px !important;
            border-radius: 8px !important;
            font-size: 15px !important;
            font-weight: bold !important;
            border: 1px solid #dcdcdc !important;
            color: #0b3c5d !important;
            transition: all 0.2s ease !important;
        }
        button[kind="secondary"]:hover {
            border-color: #11caa0 !important;
            color: #11caa0 !important;
            background-color: #f8f9fa !important;
        }
        
        /* Kurumsal Header - Düzenlendi */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .erp-title { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 1px; }
        .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Bağlantısı
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    conn = None 

# --- OTURUM (SESSION) YÖNETİMİ VE GÜVENLİK AĞI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'kullanici_adi' not in st.session_state:
    st.session_state['kullanici_adi'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = 'main'

# Güvenli Yönlendirme Kontrolü
gecerli_sayfalar = ['main', 'home', 'mal_kabul', 'blok_kesim', 'uretim', 'stok', 'sayim', 'rapor', 'uretim_bitis']
if st.session_state['page'] not in gecerli_sayfalar:
    st.session_state['page'] = 'main'

# --- 1. KULLANICI GİRİŞ (LOGIN) EKRANI ---
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: #0b3c5d; margin-bottom: 20px;'>🏢 BRN WMS Giriş</h2>", unsafe_allow_html=True)
            kadi = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adınızı girin")
            sifre = st.text_input("Şifre", type="password", placeholder="Şifrenizi girin")
            if st.button("Sisteme Giriş Yap", use_container_width=True):
                if "users" in st.secrets:
                    kullanici_listesi = st.secrets["users"]
                    if kadi in kullanici_listesi and kullanici_listesi[kadi] == sifre: 
                        st.session_state['logged_in'] = True
                        st.session_state['kullanici_adi'] = kadi.capitalize() 
                        # Sayım ve Üretim modüllerinin beklediği ortak değişkeni senkronize ediyoruz
                        st.session_state['user'] = kadi.capitalize()
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre!")
                else:
                    st.error("Sistem Hatası: Secrets içinde [users] bloğu bulunamadı.")

# --- 2. ANA UYGULAMA (GİRİŞ YAPILDIYSA) ---
else:
    st.markdown(f"""
        <div class="erp-header">
            <p class="erp-title">BRN WMS Enterprise</p>
            <p class="erp-user">👤 {st.session_state['kullanici_adi']}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- ANA MENÜ ---
    if st.session_state['page'] in ['main', 'home']:
        st.markdown("<h3 style='margin-bottom: 15px; color:#0b3c5d;'>Uygulama Menüsü</h3>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦\nMal Kabul", type="primary", use_container_width=True):
                st.session_state['page'] = 'mal_kabul'
                st.rerun()
        with col2:
            if st.button("✂️\nBlok Kesim", type="primary", use_container_width=True):
                st.session_state['page'] = 'blok_kesim'
                st.rerun()
        with col3:
            if st.button("🏗️\nÜretim Haz.", type="primary", use_container_width=True):
                st.session_state['page'] = 'uretim'
                st.rerun()

        col4, col5, col6 = st.columns(3)
        with col4:
            if st.button("🏭\nÜretim Bitiş", type="primary", use_container_width=True):
                st.session_state['page'] = 'uretim_bitis'
                st.rerun()
        with col5:
            if st.button("📍\nStok Yönetimi", type="primary", use_container_width=True):
                st.session_state['page'] = 'stok'
                st.rerun()
        with col6:
            if st.button("📊\nDepo Sayim", type="primary", use_container_width=True):
                st.session_state['page'] = 'sayim'
                st.rerun()
                
        col7, col8, col9 = st.columns(3)
        with col7:
            if st.button("📈\nRaporlar", type="primary", use_container_width=True):
                st.session_state['page'] = 'rapor'
                st.rerun()
                
        st.write("") # Ekstra boşluk
        if st.button("🚪 Güvenli Çıkış Yap"):
            st.session_state.update({'logged_in': False, 'kullanici_adi': "", 'user': ""})
            st.rerun()

    # --- MODÜL YÖNLENDİRMELERİ ---
    else:
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            if 'sayim_page' in st.session_state:
                st.session_state.sayim_page = 'menu'
            st.rerun()

        if st.session_state['page'] == 'mal_kabul':
            teslim_alma.run(conn)
        elif st.session_state['page'] == 'blok_kesim':
            # Yeni klasör altındaki __init__.py üzerinden yönlendirilen ana fonksiyon çağrılır
            blok_kesim.run_blok_kesim(conn)
        elif st.session_state['page'] == 'uretim':
            modul_uretim.goster() 
        elif st.session_state['page'] == 'uretim_bitis':
            modul_uretim_bitis.run_uretim_bitis(conn)
        elif st.session_state['page'] == 'stok':
            modul_stok.goster() 
        elif st.session_state['page'] == 'sayim':
            modul_sayim.goster(conn)
        elif st.session_state['page'] == 'rapor':
            modul_rapor.goster()
