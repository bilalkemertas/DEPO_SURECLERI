import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# 0. MERKEZİ TEMA (SAP Fiori/Horizon esintili, turkuaz) - TEK CSS KAYNAĞI
import tema

# 1. TÜM MODÜLLERİ VE YENİ ÜRETİM BİTİŞ MODÜLÜNÜ İÇE AKTARIYORUZ
import teslim_alma
import blok_kesim  # Yeni modüler paket yapısını tetikler (blok_kesim/ klasörünü okur)
import modul_stok
import modul_uretim
import modul_sayim
import modul_rapor
import modul_uretim_bitis  # Yeni Eklenen Mamül Bazlı Üretim Bitiş Modülü

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="BRN WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# 🖥️ STREAMLIT OTURUMU CANLI TUTMA SİHİRBAZI (KEEP-ALIVE)
components.html("""
<script>
const interval = setInterval(function() {
    window.parent.postMessage({type: 'streamlit:render'}, '*');
}, 30000); // 30 Saniyede bir tetikler
</script>
""", height=0)

# DÜZELTME: Eskiden burada ~150 satırlık bir CSS bloğu vardı ve bu blok
# page_ayarlar() fonksiyonunda neredeyse birebir TEKRAR ediliyordu - iki
# kopya zamanla birbirinden sapmıştı (spagetti kodun ana kaynağı buydu).
# Artık TÜM CSS tema.py'de TEK bir yerde tanımlı. Tek satırla uygulanıyor
# ve bu uygulama tek sayfalık (session_state ile geçiş yapan) bir yapı
# olduğu için, burada bir kez çağrılması TÜM ekranlara otomatik yansır.
tema.uygula()

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
            if st.button("Sisteme Giriş Yap", use_container_width=True, type="primary"):
                if "users" in st.secrets:
                    kullanici_listesi = st.secrets["users"]
                    if kadi in kullanici_listesi and kullanici_listesi[kadi] == sifre:
                        st.session_state['logged_in'] = True
                        st.session_state['kullanici_adi'] = kadi.capitalize()
                        st.session_state['user'] = kadi.capitalize()
                        # YENİ: secrets.toml'daki [roles] tablosundan kullanıcının rolünü oku
                        # ve session_state['role'] içine yaz. yetkilendirme.py bu değeri okuyor.
                        # Rol tanımlı değilse (roles altında yoksa) varsayılan "operator" atanır.
                        roller = st.secrets.get("roles", {})
                        st.session_state['role'] = roller.get(kadi, "operator")
                        st.rerun()
                    else:
                        st.error("Hatalı kullanıcı adı veya şifre!")
                else:
                    st.error("Sistem Hatası: Secrets içinde [users] bloğu bulunamadı.")

# --- 2. ANA UYGULAMA (GİRİŞ YAPILDIYSA) ---
else:
    # DÜZELTME: Elle yazılan <div class="erp-header"> yerine tema.py'deki
    # ortak fonksiyon kullanılıyor - başlık barı artık her ekranda birebir
    # aynı görünüyor (tekrar kod yazmaya gerek yok).
    tema.baslik_bari("BRN WMS Enterprise", st.session_state['kullanici_adi'])

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
            if st.button("🚪 Güvenli Çıkış", use_container_width=True, type="secondary"):
                st.session_state.update({'logged_in': False, 'kullanici_adi': "", 'user': "", 'role': ""})
                st.rerun()

    # --- MODÜL YÖNLENDİRMELERİ ---
    else:
        if st.button("⬅️ Ana Menüye Dön", use_container_width=True, type="secondary"):
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

    tema.imza_yazdir()


# ══════════════════════════════════════════════════════════════
# GERİYE DÖNÜK UYUMLULUK (backward compatibility)
# ──────────────────────────────────────────────────────────────
# DÜZELTME: Bu üç fonksiyon eskiden burada kendi CSS/markup kodlarını
# taşıyordu (spagetti kodun bir parçası). Başka bir modül bunları
# çağırıyor olabileceği ihtimaline karşı SİLİNMEDİ, sadece içleri
# tema.py'ye yönlendirildi - davranış değişmez, kod tekrarı kalkar.
# Not: app.py'nin kendisi bu üçünü artık çağırmıyor (tema.uygula() ve
# tema.imza_yazdir() yukarıda zaten kullanıldı). Hiçbir modülde bu
# fonksiyonlara `import app` ile erişildiğini görmedim - muhtemelen
# ölü kod, ama riske girmemek için koruyorum.
# ══════════════════════════════════════════════════════════════

def page_ayarlar():
    """[ESKİ] Artık tema.uygula()'ya yönlendiriyor - geriye dönük uyumluluk için duruyor."""
    tema.uygula()


def session_kontrol():
    """Kritik state'lerin başlatılması"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None


def imza_yazdir():
    """[ESKİ] Artık tema.imza_yazdir()'a yönlendiriyor - geriye dönük uyumluluk için duruyor."""
    tema.imza_yazdir()
