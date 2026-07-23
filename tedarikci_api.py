"""
tedarikci_api.py
-----------------
Formsünger Tedarikçi Portalı (TDP) entegrasyon katmanı.

Kullanım akışı:
  1) Kullanıcı kendi TDP kullanıcı adı / şifresini bir kere girer (bkz. render_login_sidebar).
  2) mal kabul / sayım / sünger kesim ekranlarından "Sevkiyat Verisini Çek" butonuna basılır.
  3) API'den dönen kayıtlar {barkod: {...}} sözlüğüne çevrilip
     st.session_state.api_sevk_haritasi içine yazılır.
  4) Tüm barkod okuma fonksiyonları (teslim_alma.handle_barcode,
     modul_sayim.handle_supplier_barcode, blok_kesim.py'deki tarama bloğu)
     önce bu haritaya bakar, bulamazsa kendi mevcut (Excel/GSheets) mantığına düşer.

⚠️ ÖNEMLİ - TEYİT EDİLMESİ GEREKEN NOKTALAR (Talha Bakhtır ile netleştirin):
  - Kimlik doğrulama yöntemi: Basic Auth mi, yoksa ayrı bir /login veya /token
    endpoint'i üzerinden Bearer token mı alınıyor? Aşağıdaki kod Basic Auth
    varsayıyor (auth=(kullanici, sifre)). Farklıysa sadece get_shipping_report
    fonksiyonundaki istek kısmını güncellemeniz yeterli.
  - API'nin döndürdüğü JSON'daki gerçek alan adları (barkod, malzeme kodu,
    miktar vb.). sevkiyat_to_barkod_haritasi() fonksiyonundaki .get(...)
    anahtarlarını, ilk gerçek API yanıtını gördükten sonra düzeltin.
    Bunun için debug_ham_yaniti_goster() fonksiyonunu kullanın.
"""

import requests
import streamlit as st
from datetime import datetime, timedelta

BASE_URL = "https://tdp.formsunger.com.tr/webapi"
ENDPOINT = "/ShippingReport/GetShippingReportForIntegration"


# ──────────────────────────────────────────────────────────────
# KİMLİK BİLGİLERİ (Streamlit session_state üzerinde tutulur)
# ──────────────────────────────────────────────────────────────
def render_login_sidebar():
    """
    Ayarlar sayfasına veya herhangi bir modülün sidebar'ına eklenebilecek
    basit login formu. Kullanıcı bir kere girer, session boyunca hatırlanır.
    """
    with st.sidebar.expander("🌐 Tedarikçi Portalı (TDP) Girişi", expanded=False):
        st.session_state.tdp_kullanici = st.text_input(
            "TDP Kullanıcı Adı:",
            value=st.session_state.get("tdp_kullanici", ""),
            key="tdp_kullanici_input"
        )
        st.session_state.tdp_sifre = st.text_input(
            "TDP Şifre:",
            value=st.session_state.get("tdp_sifre", ""),
            type="password",
            key="tdp_sifre_input"
        )
        if st.session_state.tdp_kullanici and st.session_state.tdp_sifre:
            st.success("✅ TDP kimlik bilgileri kaydedildi (bu oturum için).")


def _get_credentials():
    kullanici = st.session_state.get("tdp_kullanici", "")
    sifre = st.session_state.get("tdp_sifre", "")
    return kullanici, sifre


# ──────────────────────────────────────────────────────────────
# API ÇAĞRISI
# ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="🌐 Tedarikçi portalından sevkiyat verisi çekiliyor...")
def get_shipping_report(shipping_document_no: str, start_date: str, end_date: str,
                         kullanici: str, sifre: str):
    """
    ShippingReport/GetShippingReportForIntegration çağrısını yapar.
    start_date / end_date formatı: 'YYYY-MM-DD' (mailde belirtildiği gibi zorunlu).
    Not: shipping_document_no zorunlu parametre, boş bırakılamaz.
    """
    if not shipping_document_no:
        st.error("❌ ShippingDocumentNo boş olamaz (API dokümantasyonunda zorunlu belirtilmiş).")
        return None

    params = {
        "ShippingDocumentNo": shipping_document_no,
        "StartDate": start_date,
        "EndDate": end_date,
    }
    try:
        resp = requests.get(
            f"{BASE_URL}{ENDPOINT}",
            params=params,
            auth=(kullanici, sifre),  # TODO: Basic Auth değilse burayı güncelleyin
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        status = resp.status_code if 'resp' in locals() else "?"
        st.error(f"❌ API HTTP Hatası ({status}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API bağlantı hatası: {e}")
        return None


def son_n_gun_sevkiyat(shipping_document_no: str, gun: int = 5,
                        kullanici: str = None, sifre: str = None):
    """Son N güne ait sevkiyat raporunu çeker (varsayılan 5 gün)."""
    if kullanici is None or sifre is None:
        kullanici, sifre = _get_credentials()
    bugun = datetime.now()
    baslangic = bugun - timedelta(days=gun)
    return get_shipping_report(
        shipping_document_no,
        baslangic.strftime("%Y-%m-%d"),
        bugun.strftime("%Y-%m-%d"),
        kullanici,
        sifre,
    )


# ──────────────────────────────────────────────────────────────
# DEBUG YARDIMCISI - gerçek alan adlarını görmek için
# ──────────────────────────────────────────────────────────────
def debug_ham_yaniti_goster(api_response):
    """İlk entegrasyon denemesinde JSON'un gerçek yapısını görmek için kullanın."""
    with st.expander("🔍 API Ham Yanıtı (Debug)", expanded=True):
        st.json(api_response)


# ──────────────────────────────────────────────────────────────
# BARKOD HARİTASI ÜRETİMİ
# ──────────────────────────────────────────────────────────────
def sevkiyat_to_barkod_haritasi(api_response, shipping_document_no: str = ""):
    """
    API'den dönen sevkiyat kayıtlarını {barkod: {...}} sözlüğüne çevirir.

    ⚠️ Aşağıdaki .get(...) anahtar isimleri TAHMİNİDİR. İlk gerçek yanıtı
    debug_ham_yaniti_goster() ile inceleyip gerçek alan adlarına göre
    güncelleyin (örn. "Barkod" yerine API "LotNo" dönebilir).
    """
    harita = {}
    if not api_response:
        return harita

    if isinstance(api_response, list):
        kayitlar = api_response
    elif isinstance(api_response, dict):
        kayitlar = api_response.get("Data") or api_response.get("data") or api_response.get("Result") or []
    else:
        kayitlar = []

    for kayit in kayitlar:
        barkod = str(
            kayit.get("Barkod") or kayit.get("BarcodeNo") or
            kayit.get("PartiNo") or kayit.get("LotNo") or ""
        ).strip()
        if not barkod:
            continue
        harita[barkod] = {
            "MalzemeKodu": str(kayit.get("MalzemeKodu") or kayit.get("StokKodu") or kayit.get("ItemCode") or "").strip(),
            "MalzemeAdi": str(kayit.get("MalzemeAdi") or kayit.get("StokAdi") or kayit.get("ItemName") or "").strip(),
            "Miktar": kayit.get("Miktar") or kayit.get("SevkMiktari") or kayit.get("Quantity") or 0,
            "SevkiyatBelgeNo": kayit.get("ShippingDocumentNo") or shipping_document_no,
            "Tedarikci": str(kayit.get("Tedarikci") or kayit.get("FirmaAdi") or kayit.get("SupplierName") or "").strip(),
        }
    return harita


def sevkiyat_verisini_cek_ve_kaydet(shipping_document_no: str, gun: int = 5, debug: bool = False):
    """
    Tüm modüllerin çağırabileceği tek noktadan işlem:
    API'den çeker, haritaya çevirir, st.session_state.api_sevk_haritasi'na yazar.
    Dönen değer: (basarili: bool, mesaj: str, eklenen_kayit_sayisi: int)
    """
    kullanici, sifre = _get_credentials()
    if not kullanici or not sifre:
        return False, "Önce TDP kullanıcı adı / şifrenizi girin.", 0

    sonuc = son_n_gun_sevkiyat(shipping_document_no, gun, kullanici, sifre)
    if debug:
        debug_ham_yaniti_goster(sonuc)

    harita_yeni = sevkiyat_to_barkod_haritasi(sonuc, shipping_document_no)
    if not harita_yeni:
        return False, "Sevkiyat verisi bulunamadı veya API boş yanıt döndü.", 0

    mevcut = st.session_state.get("api_sevk_haritasi", {})
    mevcut.update(harita_yeni)
    st.session_state.api_sevk_haritasi = mevcut
    return True, f"{len(harita_yeni)} barkod kaydı çekildi ve hafızaya alındı.", len(harita_yeni)
