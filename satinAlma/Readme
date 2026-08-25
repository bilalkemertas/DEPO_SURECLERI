# Satın Alma - Gmail Modülü

**BRN WMS** için Safaş tedarikçisinden gelen mail Excel dosyalarını otomatik olarak parse edip SAS (Satın Alma Siparişi) oluşturan Python modülü.

---

## 🎯 Özellikler

✓ **Gmail'den otomatik Excel okuma** (read-only MCP)  
✓ **Safaş Excel dosyası parse** (hacim hesapla, boyut okuma)  
✓ **Eşleşmeler sheet'den Stok Kodu lookup**  
✓ **Otomatik SAS No oluşturma** (SAS-0000001, SAS-0000002...)  
✓ **Multi-birim stok takibi** (m³ + Adet + Parti)  
✓ **Barcode duplicate kontrol** (teslim alma ekranında)  
✓ **SAS durumu otomatik hesaplama** (Açık → Kısmi → Tamamlandı)

---

## 📦 Klasör Yapısı

```
satinAlma_GmailModulu/
├── __init__.py              # Paket başlatıcı
├── config.py                # Yapılandırma ve sabitler
├── gmail_agent.py           # Gmail okuma (read-only MCP)
├── excel_parser.py          # Excel parse + Lookup
├── sas_creator.py           # SAS No oluşturucu
├── barcode_kontrol.py       # Barcode doğrulaması
└── README.md                # Bu dosya
```

---

## ⚙️ Kurulum

### 1. Python Bağımlılıkları

```bash
pip install openpyxl streamlit gspread google-auth
```

### 2. Modülü Streamlit Uygulamasına Entegre Et

```bash
# Modülü app dizinine kopyala
cp -r satinAlma_GmailModulu /path/to/streamlit/app/
```

### 3. Google Workspace Ayarları

#### Gmail MCP (İsteğe Bağlı - Production için)

1. **Google Workspace Admin** → **Güvenlik** → **API Kontrolü**
2. **Gmail kapsamı** seç: `gmail.readonly` (sadece okuma)
3. **Yetkili uygulamalar** → Streamlit Cloud IP'sini ekle
4. **Servis hesabı JSON** oluştur ve `.streamlit/secrets.toml`'ye ekle:

```toml
[gmail_config]
enabled = true
sender = "safas@safas.com.tr"
scope = "gmail.readonly"

[connections.gsheets]
spreadsheet = "YOUR_SPREADSHEET_ID"
```

---

## 📖 Kullanım

### 1. Excel Parser - Safaş Dosyası Ayrıştırma

```python
from satinAlma_GmailModulu.excel_parser import ExcelAyrıştırıcı

ayristics = ExcelAyrıştırıcı()

# Excel dosyasını oku
with open('safas_sevkiyat.xlsx', 'rb') as f:
    excel_bytes = f.read()

# Ayrıştır
satırlar, meta_veri = ayristics.safas_excel_ayristic(excel_bytes)
print(f"✓ {meta_veri['satir_sayisi']} satır ayrıştırıldı")

# Eşleşmeler sheet'den lookup yap
eslesmeler = [
    {'Ürün Kodu': 'D023190570STD000', 'BRN Kodu': '12050566', 'BRN Ürün Adı': 'D 23 FLEX MAVİ'}
]
satırlar = ayristics.satırları_zenginleştir(satırlar, eslesmeler)

# Doğrula
gecerli_satırlar, hata_satırları = ayristics.satırları_doğrula(satırlar)
```

### 2. SAS Oluşturucu - Satın Alma Siparişi Oluştur

```python
from satinAlma_GmailModulu.sas_creator import SasOlusturucu

olustrucu = SasOlusturucu()

# Son SAS No'yu bul
satin_alma_verisi = [...]  # Google Sheets'ten çek
son_numara = olustrucu.son_sas_no_bul(satin_alma_verisi)

# Sonraki SAS No'yu oluştur
yeni_sas_no = olustrucu.sonraki_sas_no_olustur(son_numara)
# Sonuç: "SAS-0000001" veya "SAS-0000002"...

# Satin_Alma satırları oluştur
satin_alma_satirlari = olustrucu.satin_alma_satirlari_olustur(
    gecerli_satırlar,
    yeni_sas_no
)

# Google Sheets'e yazacak format hazırla
sayfa_verisi = olustrucu.sayfaya_yazacak_veriyi_hazirla(satin_alma_satirlari)

# Satin_Alma sheet'e ekle (gspread append_rows)
gc = gspread.service_account_from_dict(credentials_dict)
sh = gc.open_by_key("SPREADSHEET_ID")
ws = sh.worksheet("Satin_Alma")
ws.append_rows(sayfa_verisi)

# SAS özeti
ozet = olustrucu.sas_ozeti_olustur(satin_alma_satirlari)
print(f"✓ SAS {ozet['sas_no']} oluşturuldu | {ozet['toplam_m3']} m³")
```

### 3. Barcode Kontrol - Teslim Alma Ekranında

```python
from satinAlma_GmailModulu.barcode_kontrol import BarcodeKontrol

# Barcode normalize et
barcode = "0006858500"
barcode = BarcodeKontrol.barcode_normalizasyon_yap(barcode)

# Duplicate kontrol
is_duplicate, mesaj = BarcodeKontrol.barcode_duplicate_kontrol(
    barcode,
    satin_alma_verisi,
    hareketler_verisi
)

if is_duplicate:
    print(f"⚠️ {mesaj}")  # Uyarı
else:
    # Barcode'dan SAS satırını bul
    sas_satiri = BarcodeKontrol.barcode_ile_sas_satiri_bul(
        barcode,
        satin_alma_verisi
    )
    
    if sas_satiri:
        print(f"✓ SAS: {sas_satiri['sas_no']} | Ürün: {sas_satiri['stok_adi']}")
        
        # Gelen miktar doğrula
        gecerli, uyarilar = BarcodeKontrol.teslim_alinacak_miktar_dogrula(
            sas_satiri,
            gelen_m3=1.25,
            gelen_adet=2,
            gelen_parti=1
        )
        
        # SAS durumunu hesapla
        yeni_durum = BarcodeKontrol.sas_durumu_hesapla(
            sas_satiri['siparisi_m3'],
            sas_satiri['siparisi_adet'],
            gelen_toplam_m3=1.25,
            gelen_toplam_adet=2
        )
        print(f"SAS Durumu: {yeni_durum}")
```

### 4. Streamlit UI Entegrasyonu

`teslim_alma.py`'nin `'olustur'` page state'ine ekle:

```python
import streamlit as st
from satinAlma_GmailModulu import (
    ExcelAyrıştırıcı,
    SasOlusturucu,
    BarcodeKontrol,
)

# SAS oluşturma butonu
if st.button("📧 Gmail'den SAS Oluştur"):
    # 1. Gmail'den Excel indir
    # 2. Parse et
    # 3. SAS oluştur
    # 4. Sheets'e yaz
    st.success("✅ SAS başarıyla oluşturuldu!")
```

---

## 📊 Veri Akışı

```
┌─────────────────┐
│ Safaş Mail      │
│ (Excel dosyası) │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│ ExcelAyrıştırıcı            │
│ - Parse et                  │
│ - Hacim hesapla             │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Eşleşmeler Lookup           │
│ Ürün Kodu → Stok Kodu       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ SasOlusturucu               │
│ - SAS No generate           │
│ - Satin_Alma formatı        │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Google Sheets               │
│ Satin_Alma sheet            │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ teslim_alma.py              │
│ - Barcode tarat             │
│ - Duplicate kontrol         │
│ - Mal kabul yap             │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ Stok / Hareketler Sheet     │
│ Güncelleme                  │
└─────────────────────────────┘
```

---

## ⚙️ Yapılandırma (config.py)

Temel ayarlar:

```python
# Tedarikçi
TEDARIKCI_AD = "SAFAS"
TEDARIKCI_MAIL = "safas@safas.com.tr"

# Google Sheets
SATIN_ALMA_SHEET_NAME = "Satin_Alma"
ESLESMELER_SHEET_NAME = "Eşleşmeler"

# SAS Statüsü
SAS_STATUS_ACIK = "Açık"
SAS_STATUS_KISMI = "Kısmi Tamamlandı"
SAS_STATUS_TAMAMLANDI = "Tamamlandı"

# Tolerans
MIKTAR_TOLERANSI_YUZDE = 5  # %5 eksik uyarısı
TAMAMLANMA_EŞIK_YUZDE = 98  # %98 = tamamlandı

# Hacim formülü
HACIM_BOLENI = 1_000_000  # (En×Boy×Yükseklik) / 1,000,000 = m³
```

---

## 🔍 Hacim Hesaplama

```
Safaş Excel'den:
├─ En: 188 cm
├─ Boy: 158 cm
├─ Yükseklik: 21 cm

Formula:
Hacim = (188 × 158 × 21) / 1,000,000
      = 621,504 / 1,000,000
      = 0.621 m³

Stok'a kayıt:
├─ Birim: METRE (m³)
├─ Adet: 2 (Parti İçi)
├─ Parti: 1 (Bir paket)
```

---

## 🚀 Önemli Notlar

1. **Duplicate Kontrol**: Taranan barcode daha önce teslim alındıysa uyarı verir
2. **Multi-birim**: m³ (ana birim) + Adet + Parti takip edilir
3. **SAS Statüsü**: Otomatik hesaplanır (Açık → Kısmi → Tamamlandı)
4. **Gmail Read-Only**: Sadece okuma yetkisi (gönderme yapılmaz)
5. **Logging**: Tüm işlemler `logging` ile izlenebilir

---

## 📝 Hata Ayıklama

```python
import logging

# Logging etkinleştir
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Modülü çalıştır
from satinAlma_GmailModulu.excel_parser import ExcelAyrıştırıcı
ayristics = ExcelAyrıştırıcı()
# ... logging çıktısı göreceksin
```

---

## 📞 Destek

**Modül**: `satinAlma_Modulu`  
**Versiyon**: 1.0.0  
**Geliştirici**: Bilal KEMERTAŞ

---

**Son Güncelleme**: 25 Ağustos 2026
