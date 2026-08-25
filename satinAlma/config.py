"""
Satın Alma Gmail Modülü - Yapılandırma
"""

# ===== TEDARIKÇI BİLGİLERİ =====
TEDARIKCI_AD = "SAFAS"
TEDARIKCI_MAIL = "safas@safas.com.tr"
TEDARIKCI_MAIL_SUBJECT_KEYWORDS = ["Barkod", "Invoice", "Sevkiyat"]

# ===== GOOGLE SHEETS =====
SATIN_ALMA_SHEET_NAME = "Satin_Alma"
ESLESMELER_SHEET_NAME = "Eşleşmeler"
HAREKETLER_SHEET_NAME = "Hareketler"
STOK_SHEET_NAME = "Stok"

# ===== SATIN_ALMA SHEET SÜTUNLARI =====
SATIN_ALMA_COLUMNS = {
    'siparis_no': 'Sipariş No',
    'tedarikci': 'Tedarikçi',
    'tedarikci_barkoodu': 'Tedarikçi Barkoodu',
    'siparisi_miktari': 'Sipariş Miktarı',
    'stok_kodu': 'Stok Kodu',
    'stok_adi': 'Stok Adı',
    'gelen_miktari': 'Gelen Miktarı',
    'birim': 'Birim',
    'adet': 'Adet',
    'parti': 'Parti',
    'status': 'Status',
}

# ===== EŞLEŞMELER SHEET SÜTUNLARI =====
ESLESMELER_COLUMNS = {
    'urun_kodu': 'Ürün Kodu',
    'stok_kodu': 'BRN Kodu',
    'brn_urun_adi': 'BRN Ürün Adı',
}

# ===== SAS STATÜSÜ =====
SAS_STATUS_ACIK = "Açık"
SAS_STATUS_KISMI = "Kısmi Tamamlandı"
SAS_STATUS_TAMAMLANDI = "Tamamlandı"

SAS_STATUSES = [
    SAS_STATUS_ACIK,
    SAS_STATUS_KISMI,
    SAS_STATUS_TAMAMLANDI,
]

# ===== STOK BİRİMLERİ =====
STOK_BIRIM_M3 = "METRE"  # m³ (Sünger için ana birim)
STOK_BIRIM_ADET = "ADET"
STOK_BIRIM_PARTI = "PARTI"

# ===== HACIM HESAPLAMA =====
# Boyut cm cinsinden → m³ dönüştürme
# Formula: (En × Boy × Yükseklik) / 1,000,000
HACIM_BOLENI = 1_000_000

# ===== BARCODE KONTROL =====
BARCODE_DUPLICATE_CHECK_ENABLED = True
BARCODE_NORMALIZE_STRIP_DECIMALS = True  # .0 suffix'ini kaldır

# ===== TOLERANS SEVIYELERI =====
MIKTAR_TOLERANSI_YUZDE = 5  # %5 eksik uyarısı
TAMAMLANMA_EŞIK_YUZDE = 98  # %98 alındı = tamamlandı

# ===== GMAIL MCP AYARLARI =====
GMAIL_MCP_ENABLED = False  # Production'da True
GMAIL_MCP_SCOPE = "gmail.readonly"  # Sadece okuma
GMAIL_SYNC_INTERVAL_MINUTES = 30
GMAIL_ATTACHMENT_TYPES = [".xlsx", ".xls"]

# ===== LOGGING =====
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
