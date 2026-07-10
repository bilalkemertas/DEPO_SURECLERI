import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# 1. TÜM MODÜLLERİ VE YENİ ÜRETİM BİTİŞ MODÜLÜNÜ İÇE AKTARIYORUZ
import teslim_alma
import blok_kesim  # Yeni modüler paket yapısını tetikler (blok_kesim/ klasörünü okur)
import modul_stok
import modul_uretim
import modul_sayim
import modul_rapor
import modul_uretim_bitis  # Yeni Eklenen Mamül Bazlı Üretim Bitiş Modülü

# --- SAYFA AYARLARI VE ENDÜSTRİYEL TEMA ---
st.set_page_config(page_title="BRN WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# 🖥️ STREAMLIT OTURUMU CANLI TUTMA SİHİRBAZI (KEEP-ALIVE)
components.html("""
    <script>
    const interval = setInterval(function() {
        window.parent.postMessage({type: 'streamlit:render'}, '*');
    }, 30000); // 30 Saniyede bir tetikler
    </script>
""", height=0)

# Tam Ekran, 12 Punto Endüstriyel WMS CSS Tasarımı
st.markdown("""
    <style>
        /* GENEL 12 PUNTO SABİTLEMESİ */
        html, body, [class*="css"], p, span, div, label, input, select, button {
            font-size: 11pt !important;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        }

        h1, h2, h3, .erp-title { 
            font-size: 12pt !important; 
            font-weight: bold !important;
            margin-top: 4px !important; 
            margin-bottom: 6px !important; 
            padding: 0 !important;
            color: #0b3c5d !important;
        }

        .block-container { padding: 0.5rem !important; max-width: 100%; }
        header { visibility: hidden; height: 0 !important; }
        footer { visibility: hidden; height: 0 !important; }
        [data-testid="stHeader"] {display: none !important;}
        
        /* ALANLAR ARASINDAKİ 2-3 SATIRLIK BOŞLUKLARI SIFIRLAMA */
        [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
        .element-container { margin-bottom: 2px !important; }

        /* YENİ: ALAN İSMİ (LABEL) VE KUTUYU YAN YANA GETİRME (YATAY DÜZEN) */
        div[data-testid="stTextInput"], 
        div[data-testid="stNumberInput"], 
        div[data-testid="stSelectbox"] {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;
        }

        /* YENİ: KISA ALAN İSİMLERİ İÇİN GENİŞLİĞİ SABİTLE (SATIR İSRAFINI ÖNLE) */
        div[data-testid="stTextInput"] label, 
        div[data-testid="stNumberInput"] label, 
        div[data-testid="stSelectbox"] label {
            min-width: 100px !important; 
            max-width: 130px !important;
            margin-bottom: 0px !important;
            padding-right: 10px !important;
            white-space: nowrap !important;
            flex-shrink: 0 !important;
        }

        /* YENİ: İÇ KUTULARI (INPUT/SELECT) KALAN BOŞLUĞA TAM YAY */
        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stNumberInput"] div[data-baseweb="input"],
        div[data-testid="stSelectbox"] div[data-baseweb="select"] {
            flex-grow: 1 !important;
            width: 100% !important;
        }
        
        /* ANA MENÜ TERMİNAL BUTON KUTULARI (Primary) */
        button[kind="primary"] {
            height: 48px !important; /* Sıkıştırılmış, el terminaline tam oturan yükseklik */
            width: 100% !important;
            border-radius: 4px !important;
            font-size: 11pt !important;
            font-weight: bold !important;
            background-color: #ffffff !important;
            color: #0b3c5d !important;
            border: 1px solid #dcdcdc !important;
            transition: all 0.2s ease !important;
            white-space: pre-wrap !important;
            display: flex !important;
            flex-direction: row !important; /* Yan yana ikon ve metin yerleşimi space harcamaz */
            align-items: center !important;
            justify-content: center !important;
            gap: 8px !important;
        }
        button[kind="primary"]:hover {
            background-color: #0b3c5d !important;
            color: #ffffff !important;
            border-color: #11caa0 !important;
        }
        
        /* STANDART İKİNCİL BUTONLAR (Geri Dön, Çıkış vs.) */
        button[kind="secondary"] {
            height: 35px !important;
            border-radius: 4px !important;
            font-size: 11pt !important;
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
        
        /* Üst Bilgi Barı */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 6px 12px;
            border-radius: 4px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .erp-title { margin: 0; font-size: 12pt !important; color: white !important; letter-spacing: 0.5px; }
        .erp-user { margin: 0; font-size: 10pt !important; opacity: 0.95; }
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
    col1, col2, col3 = st.columns([1.2, 1.2, 1.2])
    with col2:
        with st.container(border=True):
            st.markdown("<h3>🏢 BRN WMS Giriş</h3>", unsafe_allow_html=True)
            kadi = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adı")
            sifre = st.text_input("Şifre", type="password", placeholder="Şifre")
            if st.button("Sisteme Giriş Yap", use_container_width=True):
                if "users" in st.secrets:
                    kullanici_listesi = st.secrets["users"]
                    if kadi in kullanici_listesi and kullanici_listesi[kadi] == sifre: 
                        st.session_state['logged_in'] = True
                        st.session_state['kullanici_adi'] = kadi.capitalize() 
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

    # --- ANA MENÜ PANELİ (Endüstriyel Grid Düzen) ---
    if st.session_state['page'] in ['main', 'home']:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦 Mal Kabul", type="primary", use_container_width=True):
                st.session_state['page'] = 'mal_kabul'
                st.rerun()
            if st.button("🏭 Üretim Bitiş", type="primary", use_container_width=True):
                st.session_state['page'] = 'uretim_bitis'
                st.rerun()
        with col2:
            if st.button("✂️ Blok Kesim", type="primary", use_container_width=True):
                st.session_state['page'] = 'blok_kesim'
                st.rerun()
            if st.button("📍 Stok Yönetimi", type="primary", use_container_width=True):
                st.session_state['page'] = 'stok'
                st.rerun()
        with col3:
            if st.button("🏗️ Üretim Haz.", type="primary", use_container_width=True):
                st.session_state['page'] = 'uretim'
                st.rerun()
            if st.button("📊 Depo Sayım", type="primary", use_container_width=True):
                st.session_state['page'] = 'sayim'
                st.rerun()
                
        col_rep, col_out = st.columns([2, 1])
        with col_rep:
            if st.button("📈 Raporlar", type="primary", use_container_width=True):
                st.session_state['page'] = 'rapor'
                st.rerun()
        with col_out:
            if st.button("🚪 Güvenli Çıkış", use_container_width=True):
                st.session_state.update({'logged_in': False, 'kullanici_adi': "", 'user': ""})
                st.rerun()

    # --- MODÜL YÖNLENDİRMELERİ ---
    else:
        if st.button("⬅️ Ana Menüye Dön", use_container_width=True):
            st.session_state['page'] = 'main'
            if 'sayim_page' in st.session_state:
                st.session_state.sayim_page = 'menu'
            st.rerun()

        if st.session_state['page'] == 'mal_kabul':
            teslim_alma.run(conn)
        elif st.session_state['page'] == 'blok_kesim':
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


def page_ayarlar():
    """Tüm sayfalarda geçerli olacak kurumsal, kompakt ve endüstriyel WMS arayüz ayarları"""
    
    st.markdown("""
    <style>
    /* 1. KATI 12 PUNTO KURALI VE ENDÜSTRİYEL FONT */
    html, body, [class*="css"], p, span, div, label, input, select, button {
        font-size: 11pt !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* BAŞLIKLAR MAKSİMUM 12 PUNTO (Şık ve net) */
    h1, h2, h3, .erp-title { 
        font-size: 12pt !important; 
        font-weight: bold !important;
        margin-top: 4px !important; 
        margin-bottom: 6px !important; 
        padding: 0 !important;
        color: #0b3c5d !important;
    }

    /* 2. EKRAN BOŞLUKLARINI SIFIRA YAKIN TUT (Scroll eziyetini bitirir) */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    /* ÜST VE ALT STANDART MENÜLERİ GİZLE */
    header {visibility: hidden; height: 0 !important;}
    footer {visibility: hidden; height: 0 !important;}
    [data-testid="stHeader"] {display: none !important;}

    /* SATIR ARASI GEREKSİZ SARKMALARI ÖNLE */
    [data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    .element-container { margin-bottom: 2px !important; }

    /* ETİKET (LABEL) VE KUTUYU YAN YANA ALMA */
    div[data-testid="stTextInput"], 
    div[data-testid="stNumberInput"], 
    div[data-testid="stSelectbox"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-start !important;
    }

    div[data-testid="stTextInput"] label, 
    div[data-testid="stNumberInput"] label, 
    div[data-testid="stSelectbox"] label {
        min-width: 100px !important;
        max-width: 130px !important;
        margin-bottom: 0px !important;
        padding-right: 10px !important;
        white-space: nowrap !important;
        flex-shrink: 0 !important;
    }

    div[data-testid="stTextInput"] div[data-baseweb="input"],
    div[data-testid="stNumberInput"] div[data-baseweb="input"],
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        flex-grow: 1 !important;
        width: 100% !important;
    }

    /* 3. KOMPAKT STANDART BUTONLAR */
    .stButton>button {
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #11caa0 !important;
        font-size: 11pt !important;
        font-weight: bold !important;
        height: 35px !important; /* Standart basılabilir terminal yüksekliği */
        padding: 0px 5px !important;
        transition: all 0.2s ease;
        background-color: #ffffff !important;
        color: #0b3c5d !important;
    }
    
    .stButton>button:hover {
        background-color: #11caa0 !important;
        color: white !important;
    }
    
    /* 4. MİNİMALİST SIK_ŞIK HEADER DÜZENİ */
    .erp-header {
        background-color: #0b3c5d;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .erp-user { margin: 0; font-size: 10pt !important; opacity: 0.95; }

    /* 5. VERİ SIKIŞTIRILMIŞ METRİK KUTULARI */
    .stMetric {
        background-color: #f8f9fa;
        padding: 6px !important;
        border-radius: 4px;
        border-left: 4px solid #11caa0;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 12pt !important;
        font-weight: bold !important;
    }
    .stMetric [data-testid="stMetricLabel"] {
        font-size: 9pt !important;
    }
    </style>
    """, unsafe_allow_html=True)

def session_kontrol():
    """Kritik state'lerin başlatılması"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None

def imza_yazdir():
    """Tüm sayfalarda standart imza alanını en alt kısıma ince şerit olarak basar."""
    st.markdown("""
    <div style='text-align: center; color: #a0aec0; font-size: 9pt; margin-top: 20px; padding-top: 5px; border-top: 1px solid #e2e8f0;'>
        🚀 Bilal Kemertaş | BRN 2026
    </div>
    """, unsafe_allow_html=True)
