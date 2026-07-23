"""
tedarikci_api.py
-----------------
Formsünger Tedarikçi Portalı (TDP) entegrasyon katmanı.

Kullanım akışı:
  1) TDP kullanıcı adı / şifresi operatörlere GÖSTERİLMEZ. secrets.toml
     içindeki [tdp] bloğundan (kullanici, sifre) okunur - bkz. _get_credentials().
  2) mal kabul / sayım / sünger kesim ekranlarından "Sevkiyat Verisini Çek" butonuna basılır.
  3) API'den dönen kayıtlar {barkod: {...}} sözlüğüne çevrilip
     st.session_state.api_sevk_haritasi içine yazılır.
  4) Tüm barkod okuma fonksiyonları (teslim_alma.handle_barcode,
     modul_sayim.handle_supplier_barcode, blok_kesim.py'deki tarama bloğu)
     önce bu haritaya bakar, bulamazsa kendi mevcut (Excel/GSheets) mantığına düşer.

secrets.toml'a eklenmesi gereken blok (Streamlit Cloud: Manage app → Settings → Secrets):

    [tdp]
    kullanici = "tdp_kullanici_adi"
    sifre = "tdp_sifresi"

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
# KİMLİK BİLGİLERİ (secrets.toml'dan okunur - operatörlere GÖSTERİLMEZ)
# ──────────────────────────────────────────────────────────────
def _get_credentials():
    """
    TDP kullanıcı adı/şifresini secrets.toml içindeki [tdp] bloğundan okur.
    Hiçbir ekranda kullanıcıya gösterilmez, sadece API çağrısında arka planda
    kullanılır. secrets.toml'da tanımlı değilse ikisi de boş string döner.
    """
    tdp_secrets = st.secrets.get("tdp", {})
    return tdp_secrets.get("kullanici", ""), tdp_secrets.get("sifre", "")


def baglanti_durumu_goster():
    """
    Operatörlere şifreyi göstermeden, sadece bağlantının tanımlı olup
    olmadığını gösteren bilgi satırı. "Sevkiyat Çek" panelinin başına koy.
    """
    kullanici, sifre = _get_credentials()
    if kullanici and sifre:
        st.caption(f"🔒 Tedarikçi portalı bağlantısı sistem tarafından yönetiliyor (kullanıcı: {kullanici[:2]}{'*' * max(len(kullanici) - 2, 3)}).")
    else:
        st.error(
            "❌ Tedarikçi portalı kimlik bilgileri tanımlı değil. "
            "Bir yöneticinin secrets.toml içine [tdp] kullanici/sifre eklemesi gerekiyor."
        )


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
        return False, ("Tedarikçi portalı bağlantısı tanımlı değil. "
                        "Bir yöneticinin secrets.toml içine [tdp] kullanici/sifre eklemesi gerekiyor."), 0

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
