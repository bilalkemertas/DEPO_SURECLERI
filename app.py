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

/* DÜZELTME: Alanlar arası boşluk - eskiden 0.3rem/2px idi, üst üste binmeye
   sebep oluyordu. Emoji + 11pt satırların gerçek yüksekliği bu boşluğa
   sığmıyordu. Şimdi elemanların rahatça nefes alması için büyütüldü. */
[data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
.element-container { margin-bottom: 8px !important; }

/* DÜZELTME: Eskiden burada etiket (label) ve kutuyu (input) yan yana
   zorlayan, label genişliğini 130px'e sabitleyen ve white-space: nowrap
   uygulayan 3 kural vardı. Uzun Türkçe etiketler (örn. "🔌 Tedarikçi
   Barkodu / Parti No:") bu dar alana sığmayıp kutunun üzerine taşıyordu.
   O kurallar tamamen kaldırıldı; Streamlit'in varsayılan davranışına
   (etiket kutunun ÜSTÜNDE) dönüldü - bu, üst üste binmeyi kökünden
   engeller ve el terminali/mobil ekranlarda da daha güvenlidir. */

/* DÜZELTME: Expander (aç/kapa panel) başlığındaki ok ikonu ile yazının
   çakışmasını önlemek için minimum yükseklik ve normal satır kaydırma. */
[data-testid="stExpander"] summary {
    min-height: 42px !important;
    display: flex !important;
    align-items: center !important;
    line-height: 1.4 !important;
    padding: 8px 4px !important;
}
[data-testid="stExpander"] summary p {
    margin: 0 !important;
    white-space: normal !important;
}

/* ANA MENÜ TERMİNAL BUTON KUTULARI (Primary) */
button[kind="primary"] {
    min-height: 48px !important;   /* DÜZELTME: height yerine min-height */
    height: auto !important;       /* DÜZELTME: 2 satıra düşen yazı artık kesilmiyor */
    width: 100% !important;
    border-radius: 4px !important;
    font-size: 11pt !important;
    font-weight: bold !important;
    background-color: #ffffff !important;
    color: #0b3c5d !important;
    border: 1px solid #dcdcdc !important;
    transition: all 0.2s ease !important;
    white-space: normal !important;   /* DÜZELTME: pre-wrap yerine normal */
    line-height: 1.3 !important;      /* DÜZELTME: çok satırlı metin nefes alsın */
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    padding: 8px 10px !important;
}
button[kind="primary"]:hover {
    background-color: #0b3c5d !important;
    color: #ffffff !important;
    border-color: #11caa0 !important;
}

/* STANDART İKİNCİL BUTONLAR (Geri Dön, Çıkış vs.) */
button[kind="secondary"] {
    min-height: 35px !important;   /* DÜZELTME: height yerine min-height */
    height: auto !important;
    border-radius: 4px !important;
    font-size: 11pt !important;
    font-weight: bold !important;
    line-height: 1.3 !important;
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

    /* 2. EKRAN BOŞLUKLARINI KOMPAKT TUT */
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

    /* DÜZELTME: satır arası boşluk büyütüldü (eskiden 0.3rem/2px idi,
       üst üste binmeye sebep oluyordu) */
    [data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
    .element-container { margin-bottom: 8px !important; }

    /* DÜZELTME: Etiket/kutu yan yana zorlayan ve genişliği 130px'e
       sabitleyen kurallar kaldırıldı - etiket artık kutunun üstünde,
       taşma/çakışma imkansız. */

    /* DÜZELTME: Expander başlığı ok ikonu ile yazı çakışmasını önle */
    [data-testid="stExpander"] summary {
        min-height: 42px !important;
        display: flex !important;
        align-items: center !important;
        line-height: 1.4 !important;
        padding: 8px 4px !important;
    }
    [data-testid="stExpander"] summary p {
        margin: 0 !important;
        white-space: normal !important;
    }

    /* 3. KOMPAKT STANDART BUTONLAR */
    .stButton>button {
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #11caa0 !important;
        font-size: 11pt !important;
        font-weight: bold !important;
        min-height: 40px !important;   /* DÜZELTME: height yerine min-height */
        height: auto !important;
        line-height: 1.3 !important;   /* DÜZELTME: çok satırlı metin nefes alsın */
        white-space: normal !important;
        padding: 8px 6px !important;
        transition: all 0.2s ease;
        background-color: #ffffff !important;
        color: #0b3c5d !important;
    }
    .stButton>button:hover {
        background-color: #11caa0 !important;
        color: white !important;
    }

    /* 4. MİNİMALİST HEADER DÜZENİ */
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

    /* 5. METRİK KUTULARI */
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
