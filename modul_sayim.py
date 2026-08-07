import streamlit as st
import pandas as pd
import io
import time
import random
import os
import uuid
import veri_onbellek as vo
import veritabani
from datetime import datetime

# Navigation Helpers
def go_home():
    st.session_state.page = 'main'
    st.session_state.sayim_page = 'menu'


def go_sayim_menu():
    st.session_state.sayim_page = 'menu'


def go_oturum():
    st.session_state.sayim_page = 'oturum'


def go_giris():
    st.session_state.sayim_page = 'giris'


def go_rapor():
    st.session_state.sayim_page = 'rapor'


def go_el_terminal():
    st.session_state.sayim_page = 'el_terminali'


# ==============================================================================
# Gelişmiş GitHub / Yerel Veri Yükleme Motoru
# ==============================================================================
@st.cache_data(ttl=60)
def load_github_xlsx(url_or_path):
    """
    Excel dosyasını belirtilen URL veya yerel dosya yolundan yükler.
    Hata durumunda korumalı bir şekilde hata mesajı döner.
    """
    try:
        if str(url_or_path).startswith("http://") or str(url_or_path).startswith("https://"):
            return pd.read_excel(url_or_path)
        else:
            if os.path.exists(url_or_path):
                return pd.read_excel(url_or_path)
            else:
                return None
    except Exception as e:
        st.sidebar.error(f"⚠️ Excel yükleme hatası ({url_or_path}): {str(e)}")
        return None


@st.cache_data(ttl=60)
def load_github_csv(url_or_path):
    """
    CSV dosyasını Türkçe karakter korumalı ve otomatik kodlama denemeli yükler.
    """
    try:
        if str(url_or_path).startswith("http://") or str(url_or_path).startswith("https://"):
            return pd.read_csv(url_or_path, dtype=str)
        else:
            if os.path.exists(url_or_path):
                encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
                for enc in encodings:
                    try:
                        return pd.read_csv(url_or_path, dtype=str, encoding=enc)
                    except:
                        continue
                return None
    except Exception as e:
        st.sidebar.error(f"⚠️ CSV yükleme hatası ({url_or_path}): {str(e)}")
        return None


# ==============================================================================
# Tedarikçi Barkod İşleme Motoru
# ==============================================================================
def handle_supplier_barcode(barcode_scanned):
    """
    Tedarikçi barkodunu okuyup son 10 karakteri ayıklar.
    Önce API'den (Tedarikçi Portalı) çekilmiş canlı barkod haritasına bakar;
    bulunamazsa FORM_SUNGER.xlsx ve BRN-FORM EŞLEŞME.xlsx dosyalarından
    malzeme bilgisi ile teslimat miktarını çeker (mevcut yedek mantık).
    """
    if not barcode_scanned:
        return

    # 1. Son 10 karakteri Parti No olarak al
    parti_no = str(barcode_scanned).strip()[-10:]

    st.toast(f"🔍 Barkod Çözümlendi! Parti No: {parti_no} aranıyor...", icon="⏳")

    # ──────────────────────────────────────────────────────────
    # YENİ: Önce "Satin_Alma" (Satın Alma Sipariş) sekmesinde ara.
    # Bu, Mal Kabul modülünün de kullandığı aynı kaynak - buradaki
    # eşleşme, eski Excel dosyalarından (FORM_SUNGER/BRN eşleşme)
    # daha güncel ve güvenilir kabul edilir, o yüzden önce buraya
    # bakılır. Bulunursa Stok Kodu/Adı/Sipariş Miktarı otomatik
    # dolduruluyor ve barkod (parti/seri no) Tedarikçi_Barkodu
    # alanına taşınarak stoğa kaydediliyor.
    # ──────────────────────────────────────────────────────────
    df_sas = veritabani.get_internal_data("Satin_Alma")
    if df_sas is not None and not df_sas.empty and "Tedarikçi Barkodu" in df_sas.columns:
        df_sas_temp = df_sas.copy()

        # DÜZELTME: Google Sheets'te barkod sütunu sayısal olarak
        # saklanmışsa (örn. "2608041845"), Python'a okunurken
        # "2608041845.0" gibi ondalıklı bir değere dönüşebiliyor. Bu
        # yüzden birebir metin karşılaştırması tutmuyordu - veri Sheets'te
        # GERÇEKTEN var olsa bile "bulunamadı" hatası veriyordu. Aynı
        # temizleme mantığı bu projede clean_code() adıyla zaten var
        # (teslim_alma.py) - burada da uyguluyoruz.
        def _barkod_temizle(val):
            s = str(val).strip()
            if s.endswith(".0"):
                s = s[:-2]
            return s

        df_sas_temp["Temiz_Barkod"] = df_sas_temp["Tedarikçi Barkodu"].apply(_barkod_temizle)
        barkod_aranan = _barkod_temizle(barcode_scanned)
        parti_aranan = _barkod_temizle(parti_no)

        found_sas = df_sas_temp[df_sas_temp["Temiz_Barkod"] == barkod_aranan]
        if found_sas.empty:
            found_sas = df_sas_temp[df_sas_temp["Temiz_Barkod"] == parti_aranan]

        if not found_sas.empty:
            sas_row = found_sas.iloc[0]
            st.session_state.def_s_kod = str(sas_row.get("Stok Kodu", "")).strip()
            st.session_state.def_s_isim = str(sas_row.get("Stok Adı", "")).strip()
            try:
                st.session_state.def_s_mik = float(sas_row.get("Sipariş Miktarı", 0) or 0)
            except (ValueError, TypeError):
                st.session_state.def_s_mik = 0.0
            st.session_state.def_s_barcode = str(barcode_scanned).strip()
            st.toast(f"✅ Satın Alma'da bulundu: {sas_row.get('Stok Adı', '')}", icon="✔️")
            return
        else:
            # DÜZELTME: Bulunamama durumu artık görünür - Satin_Alma'nın
            # gerçekten kontrol edildiği ama eşleşme çıkmadığı belli oluyor.
            st.toast(f"ℹ️ '{parti_no}' Satın Alma'da bulunamadı, FORM_SUNGER.xlsx kontrol ediliyor...", icon="🔎")
    elif df_sas is not None and not df_sas.empty:
        st.toast("⚠️ Satın Alma sekmesinde 'Tedarikçi Barkodu' sütunu bulunamadı, atlanıyor.", icon="⚠️")
    else:
        st.toast("ℹ️ Satın Alma sekmesi boş/erişilemedi, FORM_SUNGER.xlsx kontrol ediliyor...", icon="🔎")

    # ──────────────────────────────────────────────────────────
    # Satın Alma'da bulunamazsa: FORM_SUNGER.xlsx / BRN-FORM
    # EŞLEŞME.xlsx dosyalarıyla (yerel/GitHub Excel) devam et.
    # ──────────────────────────────────────────────────────────

    # 2. FORM_SUNGER.xlsx Dosyasını Yükle
    df_sunger = load_github_xlsx(st.session_state.github_form_sunger_url)
    if df_sunger is None or df_sunger.empty:
        st.error("❌ 'FORM_SUNGER.xlsx' dosyası okunamadı! Lütfen dosya yolunu veya URL ayarlarını kontrol edin.")
        return

    # Sütun isimlerini standartlaştır
    df_sunger.columns = [str(c).strip() for c in df_sunger.columns]

    # Dinamik sütun eşleştirme
    parti_col = next((c for c in df_sunger.columns if "parti" in c.lower() or "lot" in c.lower() or ("no" in c.lower() and "parti" in c.lower())), None)
    malzeme_col = next((c for c in df_sunger.columns if "malzeme" in c.lower() or "kod" in c.lower()), None)

    # KESİN MİKTAR/HACİM TESPİTİ (Teslimat No'yu almasını engeller)
    miktar_col = None
    for c in df_sunger.columns:
        if c.lower() == "toplam m3" or c.lower() == "toplam_m3":
            miktar_col = c
            break
    if not miktar_col:
        for c in df_sunger.columns:
            if ("m3" in c.lower() or "hacim" in c.lower()) and "teslimat" not in c.lower() and "no" not in c.lower():
                miktar_col = c
                break

    # Bulunamazsa varsayılan veya indeks bazlı atama yap
    if not parti_col:
        parti_col = "Parti No" if "Parti No" in df_sunger.columns else df_sunger.columns[0]
    if not malzeme_col:
        malzeme_col = "Malzeme Kodu" if "Malzeme Kodu" in df_sunger.columns else (df_sunger.columns[1] if len(df_sunger.columns) > 1 else df_sunger.columns[0])
    if not miktar_col:
        miktar_col = "Toplam M3"  # Sadece Toplam M3'ü kullan, son sütunu rastgele alma!

    # Parti No verilerini karşılaştırmaya hazırla
    df_sunger[parti_col] = df_sunger[parti_col].astype(str).str.strip()
    match_sunger = df_sunger[df_sunger[parti_col] == parti_no]

    # Kısmi eşleşme araması (fallback)
    if match_sunger.empty:
        match_sunger = df_sunger[df_sunger[parti_col].str.contains(parti_no, na=False)]

    if match_sunger.empty:
        st.error(f"❌ '{parti_no}' Parti No, 'FORM_SUNGER.xlsx' içerisinde bulunamadı!")
        return

    row_sunger = match_sunger.iloc[0]
    malzeme_kodu = str(row_sunger.get(malzeme_col, '')).strip()

    # Teslimat miktarını güvenli bir şekilde sayıya dönüştür
    try:
        raw_qty = str(row_sunger.get(miktar_col, '0')).replace(',', '.')
        teslimat_miktari = float(raw_qty)
    except:
        teslimat_miktari = 0.0

    st.toast(f"✅ Parti No Eşleşti! Malzeme Kodu: {malzeme_kodu} | Hacim: {teslimat_miktari}", icon="✔️")

    # 3. BRN-FORM EŞLEŞME.xlsx Excel Dosyasını Yükle ve Kendi Kodumuzu/Stok Adımızı Bul
    df_eslesme = load_github_xlsx(st.session_state.github_brn_form_url)
    our_code = malzeme_kodu
    our_name = f"Tedarikçi Kodu: {malzeme_kodu}"

    if df_eslesme is not None and not df_eslesme.empty:
        df_eslesme.columns = [str(c).strip() for c in df_eslesme.columns]

        # Sütunları dinamik ve zırhlı tespit et (FORM KODU ve BRN KODU / BRN ÜRÜN ADI için)
        form_col = next((c for c in df_eslesme.columns if "form" in c.lower() and "kod" in c.lower()), None)
        brn_cod_col = next((c for c in df_eslesme.columns if "brn" in c.lower() and "kod" in c.lower()), None)
        brn_nam_col = next((c for c in df_eslesme.columns if "brn" in c.lower() and ("ad" in c.lower() or "ürün" in c.lower() or "urun" in c.lower())), None)

        # Fallback sütun tespitleri (eğer spesifik kelimeler bulunamazsa varsayılan sütun indisleri atanır)
        if not form_col:
            form_col = df_eslesme.columns[0]
        if not brn_cod_col:
            brn_cod_col = df_eslesme.columns[1] if len(df_eslesme.columns) > 1 else df_eslesme.columns[0]
        if not brn_nam_col:
            brn_nam_col = df_eslesme.columns[2] if len(df_eslesme.columns) > 2 else brn_cod_col

        # Karşılaştırma için kodları temizleme fonksiyonu (.0 uzantılarını, boşlukları siler, büyük harf yapar)
        def clean_code(val):
            if pd.isna(val):
                return ""
            s = str(val).strip().upper()
            if s.endswith(".0"):
                s = s[:-2]
            return s

        df_eslesme[form_col] = df_eslesme[form_col].apply(clean_code)
        target_code = clean_code(malzeme_kodu)
        match_eslesme = df_eslesme[df_eslesme[form_col] == target_code]

        if not match_eslesme.empty:
            row_eslesme = match_eslesme.iloc[0]
            our_code = str(row_eslesme.get(brn_cod_col, malzeme_kodu)).strip()
            our_name = str(row_eslesme.get(brn_nam_col, 'TANIMSIZ')).strip()
            st.success(f"🎯 BRN Kod Eşleşti: {our_code} | Stok: {our_name}")
        else:
            # Kısmi eşleşme kontrolü (Fallback)
            match_eslesme_partial = df_eslesme[df_eslesme[form_col].str.contains(target_code, na=False)]
            if not match_eslesme_partial.empty:
                row_eslesme = match_eslesme_partial.iloc[0]
                our_code = str(row_eslesme.get(brn_cod_col, malzeme_kodu)).strip()
                our_name = str(row_eslesme.get(brn_nam_col, 'TANIMSIZ')).strip()
                st.success(f"🎯 BRN Kod Eşleşti (Kısmi): {our_code} | Stok: {our_name}")
            else:
                st.warning(f"⚠️ '{malzeme_kodu}' kodu BRN-FORM eşleşme tablosunda bulunamadı. Orijinal kod kullanılacak.")
                # Eğer katalogda varsa ismi oradan almayı dene
                catalog = get_dinamik_katalog_local()
                for cat_item in catalog:
                    if cat_item.startswith(malzeme_kodu):
                        parts = cat_item.split(" | ", 1)
                        our_name = parts[1].strip() if len(parts) > 1 else our_name
                        break
    else:
        st.warning("⚠️ 'BRN-FORM EŞLEŞME.xlsx' bulunamadığından eşleşme kontrolü yapılamadı.")

    # 4. Session State Değerlerini Güncelleyerek Formu Doldur
    st.session_state.def_s_kod = our_code
    st.session_state.def_s_isim = our_name
    st.session_state.def_s_mik = teslimat_miktari
    st.session_state.def_s_barcode = str(barcode_scanned).strip()  # Okutulan barkodu da forma taşı


def get_dinamik_katalog_local():
    """handle_supplier_barcode içerisinden katalog hafızasına erişim için bağımsız fonksiyon"""
    return st.session_state.get('katalog_hafiza', [])


# ==============================================================================
# Ana Sayım Modülü Ekranı
# ==============================================================================
def goster(conn=None):
    if conn is None:
        st.error("Google Sheets bağlantısı (conn) modüle sağlanamadı!")
        return

    # -----------------------------
    # AKTİF KULLANICI BELİRLEME
    # -----------------------------
    aktif_kullanici = st.session_state.get('user') or \
        st.session_state.get('kullanici_adi') or \
        "Tanımsız"

    if 'user' not in st.session_state:
        st.session_state['user'] = aktif_kullanici

    # -----------------------------
    # SESSION STATE INIT
    # -----------------------------
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'aktif_sayim_adi' not in st.session_state:
        st.session_state.aktif_sayim_adi = None
    if 'sayim_page' not in st.session_state:
        st.session_state.sayim_page = 'menu'

    # -----------------------------
    # 🆕 OTOMATİK CİHAZ ALGILAMA (Buton YOK - Sistem kendisi karar verir)
    # Tarayıcının User-Agent bilgisine bakarak el terminali / mobil / Android
    # tabanlı bir cihaz olup olmadığını anlar ve sadece oturumun İLK yüklenişinde
    # otomatik olarak "El Terminali Modu"na geçirir. Kullanıcı sonrasında
    # menüden istediği ekrana serbestçe geçebilir (otomatik geçiş tekrar etmez).
    # -----------------------------
    if 'oto_mod_kontrol_edildi' not in st.session_state:
        st.session_state.oto_mod_kontrol_edildi = True
        ua_lower = ""
        try:
            headers = st.context.headers
            ua_lower = (headers.get("User-Agent", "") or headers.get("user-agent", "")).lower()
        except Exception:
            ua_lower = ""

        el_terminali_anahtar_kelimeler = [
            "android", "iphone", "ipad", "mobile", "windows ce", "windows phone",
            "zebra", "honeywell", "datalogic", "cipherlab", "urovo",
            "point mobile", "newland", "m3 mobile", "chainway"
        ]

        if ua_lower and any(k in ua_lower for k in el_terminali_anahtar_kelimeler):
            st.session_state.sayim_page = 'el_terminali'
            st.session_state.oto_algilanan_cihaz = "📱 El Terminali / Mobil Cihaz"
        else:
            st.session_state.oto_algilanan_cihaz = "🖥️ Masaüstü / PC"

    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None
    if 'katalog_hafiza' not in st.session_state:
        st.session_state['katalog_hafiza'] = []

    # Barkod Değerlerini Hafızada Tutmak İçin State Kontrolleri
    if 'def_s_kod' not in st.session_state:
        st.session_state.def_s_kod = ""
    if 'def_s_isim' not in st.session_state:
        st.session_state.def_s_isim = ""
    if 'def_s_mik' not in st.session_state:
        st.session_state.def_s_mik = 0.0
    if 'def_s_barcode' not in st.session_state:
        st.session_state.def_s_barcode = ""

    # --- 🟢 KRİTİK: FORM SIFIRLAMA (WIDGETLAR OLUŞMADAN ÖNCE YAPILMALI) ---
    if st.session_state.get('clear_sayim_form'):
        st.session_state.def_s_kod = ""
        st.session_state.def_s_isim = ""
        st.session_state.def_s_mik = 0.0
        st.session_state.def_s_barcode = ""
        if 'supplier_barcode_key' in st.session_state:
            st.session_state.supplier_barcode_key = ""
        st.session_state.clear_sayim_form = False

    # GitHub Dosya Yolları / URL Ayarları (Varsayılan Yereldir, Ayarlardan Değişebilir)
    if 'github_form_sunger_url' not in st.session_state:
        st.session_state.github_form_sunger_url = "FORM_SUNGER.xlsx"
    if 'github_brn_form_url' not in st.session_state:
        st.session_state.github_brn_form_url = "BRN-FORM EŞLEŞME.xlsx"
    if 'github_depo_adresler_url' not in st.session_state:
        st.session_state.github_depo_adresler_url = "Depo_Adresler.xlsx"

    # -----------------------------
    # Gelişmiş GitHub Bağlantı Paneli (Sidebar)
    # -----------------------------
    with st.sidebar.expander("⚙️ Entegrasyon ve GitHub Ayarları", expanded=False):
        st.markdown("### 🔌 Dosya Kaynakları")
        st.session_state.github_form_sunger_url = st.text_input(
            "FORM_SUNGER.xlsx Yolu/URL:",
            value=st.session_state.github_form_sunger_url,
            help="Yerel dosya adını ya da GitHub Raw URL'sini girebilirsiniz."
        )
        st.session_state.github_brn_form_url = st.text_input(
            "BRN-FORM EŞLEŞME.xlsx Yolu/URL:",
            value=st.session_state.github_brn_form_url,
            help="Yerel dosya adını ya da GitHub Raw URL'sini girebilirsiniz."
        )
        st.session_state.github_depo_adresler_url = st.text_input(
            "Depo_Adresler.xlsx Yolu/URL:",
            value=st.session_state.github_depo_adresler_url,
            help="Adres öneri listesi. Yerel dosya adını ya da GitHub Raw URL'sini girebilirsiniz."
        )
        if st.button("Önbelleği Temizle"):
            load_github_xlsx.clear()
            load_github_csv.clear()
            st.toast("Önbellek temizlendi!", icon="🧹")

    # NOT: Tedarikçi Portalı (TDP) sevkiyat çekme paneli artık burada değil,
    # "Sayım Girişi" ekranının başında (ana içerik alanında) gösteriliyor -
    # bu uygulamada sidebar varsayılan kapalı ve açma oku CSS ile gizli
    # olduğu için sidebar'daki alanlara erişilemiyordu.

    # -----------------------------
    # HELPERS (GSheets Uyumlu)
    # -----------------------------
    def _norm_text(val):
        if pd.isna(val):
            return ""
        return str(val).strip()

    def _upper_text(val):
        return _norm_text(val).upper()

    def _to_num(series):
        if series.dtype == object:
            series = series.astype(str).str.replace(",", ".", regex=False)
        return pd.to_numeric(series, errors='coerce').fillna(0.0).astype(float)

    def _get_df(table_name):
        # NOT: Burada artık süre bazlı (TTL) önbellek YOK. Ne zaman taze
        # veri okunacağı, aşağıdaki _sayim_ortak_verileri_yukle() tarafından
        # olay bazlı (sayfaya ilk giriş / kayıt sonrası / elle "Yenile")
        # kontrol ediliyor. Bu fonksiyon sadece ham okuma + 3 deneme yapar.
        son_hata = None
        for i in range(3):
            try:
                df = conn.read(worksheet=table_name, ttl=0)
                if df is None:
                    return pd.DataFrame()
                return df.copy()
            except Exception as e:
                son_hata = e
                if i == 2:
                    st.error(f"❌ '{table_name}' sekmesi okunamadı! Hata: {son_hata}")
                    st.warning(
                        f"Kontrol et: Google Sheets dosyanda '{table_name}' adında bir sekme "
                        "gerçekten var mı? Sekme adı büyük/küçük harf dahil BİREBİR aynı olmalı."
                    )
                    return pd.DataFrame()
                time.sleep(random.uniform(0.2, 0.5))

    def _save_df(table_name, df):
        if df is None:
            df = pd.DataFrame()
        son_hata = None
        for i in range(15):
            try:
                conn.update(worksheet=table_name, data=df)
                return True
            except Exception as e:
                son_hata = e
                if i == 14:
                    st.error(f"❌ '{table_name}' sekmesine yazılamadı! Hata: {son_hata}")
                    st.warning(
                        f"Kontrol et: Google Sheets dosyanda '{table_name}' adında bir sekme (worksheet) "
                        "gerçekten var mı? Sekme adı büyük/küçük harf dahil BİREBİR aynı olmalı."
                    )
                    return False
                time.sleep(random.uniform(0.2, 0.7))
        return False

    # ──────────────────────────────────────────────────────────
    # YENİ: Gerçek (native) EKLEME. _save_df'in aksine sekmenin tamamını
    # OKUMAZ/ÜZERİNE YAZMAZ - Google'ın "spreadsheets.values.append"
    # API'sini kullanarak SADECE yeni satırları sona ekler. Mevcut
    # binlerce satır hiç etkilenmez, bu yüzden hem çok daha hızlıdır
    # hem de "tüm sekme tek satırla değişti" tarzı veri kaybı riski
    # taşımaz. Sütun sırasını sekmedeki GERÇEK başlık satırından okur.
    # ──────────────────────────────────────────────────────────
    def _guvenli_satirlar_ekle(worksheet_adi, satirlar_df):
        if satirlar_df is None or satirlar_df.empty:
            return True
        try:
            ws = conn.client._open_spreadsheet().worksheet(worksheet_adi)
            basliklar = ws.row_values(1)
            if not basliklar:
                basliklar = list(satirlar_df.columns)
                ws.append_row(basliklar, value_input_option="USER_ENTERED")
            # Sekmede olup dataframe'de olmayan sütunlar için boş değer,
            # dataframe'de olup sekmede olmayan sütunlar yoksayılır.
            eklenecek = []
            for _, satir in satirlar_df.iterrows():
                eklenecek.append([str(satir.get(b, "")) for b in basliklar])
            ws.append_rows(eklenecek, value_input_option="USER_ENTERED")
            return True
        except Exception as e:
            st.error(f"❌ '{worksheet_adi}' sekmesine satır eklenemedi: {e}")
            st.warning("Bu, native ekleme API'sinde bir sorun olduğunu gösterir - eski yönteme (tam sekme yazma) dönmek için tekrar dene.")
            return False

    def _find_col(df, candidates):
        if df is None or df.empty:
            return None
        lower_map = {c.lower(): c for c in df.columns}
        for cand in candidates:
            if cand.lower() in lower_map:
                return lower_map[cand.lower()]
        return None

    def _ensure_columns(df, cols_with_defaults):
        df = df.copy()
        for col, default in cols_with_defaults.items():
            if col not in df.columns:
                df[col] = default
        return df

    def _standardize_catalog_source(df, kod_col, isim_col):
        katalog_listesi = []
        if df.empty or kod_col is None or isim_col is None:
            return katalog_listesi

        temp = df[[kod_col, isim_col]].copy()
        temp[kod_col] = temp[kod_col].astype(str).str.strip()
        temp[isim_col] = temp[isim_col].astype(str).str.strip()
        temp = temp[(temp[kod_col] != "") & (temp[kod_col].str.lower() != "nan")]
        temp = temp.drop_duplicates(subset=[kod_col])

        for _, row in temp.iterrows():
            katalog_listesi.append(f"{_norm_text(row[kod_col])} | {_norm_text(row[isim_col])}")

        return katalog_listesi

    def get_dinamik_adres_listesi():
        """
        Depo_Adresler.xlsx dosyasından (GitHub/yerel) adres kodlarını okuyup
        session_state'te önbelleğe alır - ürün kataloğu ile birebir aynı
        desen. Personel adres kutusuna yazmaya başlayınca bu liste üzerinden
        arama/öneri yapılır (Streamlit selectbox zaten yazdıkça filtreler).
        """
        if st.session_state.get('adres_hafiza'):
            return st.session_state['adres_hafiza']

        adres_listesi = []
        df_adres = load_github_xlsx(st.session_state.github_depo_adresler_url)
        if df_adres is not None and not df_adres.empty:
            df_adres.columns = [str(c).strip() for c in df_adres.columns]
            kod_col = _find_col(df_adres, ["Kod", "Raf Kodu", "Adres"])
            if kod_col:
                kodlar = df_adres[kod_col].astype(str).str.strip()
                adres_listesi = sorted(list(set([k.upper() for k in kodlar if k and k.lower() != "nan"])))

        st.session_state['adres_hafiza'] = adres_listesi
        return adres_listesi

    def get_dinamik_katalog():
        if st.session_state.get('katalog_hafiza'):
            return st.session_state['katalog_hafiza']

        katalog_listesi = []
        df_urun = _get_df("Urun_Listesi")
        kod_col = _find_col(df_urun, ["kod", "Kod"])
        isim_col = _find_col(df_urun, ["isim", "İsim", "ad", "Ad"])

        if not df_urun.empty and kod_col and isim_col:
            katalog_listesi = _standardize_catalog_source(df_urun, kod_col, isim_col)

        if not katalog_listesi:
            df_stok = _get_df("Stok")
            kod_col = _find_col(df_stok, ["Kod", "kod"])
            isim_col = _find_col(df_stok, ["İsim", "isim"])
            if not df_stok.empty and kod_col and isim_col:
                katalog_listesi = _standardize_catalog_source(df_stok, kod_col, isim_col)

        katalog_listesi = sorted(list(set([x for x in katalog_listesi if x and x != " | "])))
        st.session_state['katalog_hafiza'] = katalog_listesi
        return katalog_listesi

    def _session_completed_sessions():
        # DÜZELTME: Artık doğrudan _get_df (ağa gider) yerine, zaten
        # önbelleğe alınmış ortak veriden okunuyor. Bu fonksiyon
        # _open_sessions() üzerinden HER SAYFA YENİLEMESİNDE çağrıldığı
        # için, önbellek olmadan adres seçmek gibi ufak etkileşimlerde
        # bile Google Sheets'e gidiyordu.
        _veri_ortak = _sayim_ortak_verileri_yukle()
        df_tamamlanan = _veri_ortak["sayim_tamamlanan"]
        if df_tamamlanan.empty:
            return []
        oturum_col = _find_col(df_tamamlanan, ["Oturum_Adi"])
        if not oturum_col:
            return []
        return df_tamamlanan[oturum_col].dropna().astype(str).unique().tolist()

    def _session_all_sessions():
        # DÜZELTME: Aynı sebeple önbellekten okunuyor (yukarıdaki nota bak).
        tum = []
        _veri_ortak = _sayim_ortak_verileri_yukle()
        df_sayim = _veri_ortak["sayim"]
        df_snapshot = _veri_ortak["sayim_snapshot"]

        oturum_col = _find_col(df_sayim, ["Oturum_Adi"])
        if not df_sayim.empty and oturum_col:
            tum.extend(df_sayim[oturum_col].dropna().astype(str).unique().tolist())

        oturum_col = _find_col(df_snapshot, ["Oturum_Adi"])
        if not df_snapshot.empty and oturum_col:
            tum.extend(df_snapshot[oturum_col].dropna().astype(str).unique().tolist())

        return sorted(list(set(tum)))

    def _open_sessions():
        tamamlanan = set(_session_completed_sessions())
        return [o for o in _session_all_sessions() if o not in tamamlanan]

    # ──────────────────────────────────────────────────────────
    # YENİ: Oturum meta bilgisi (açan kişi / atanan personel / durum)
    # "sayim_oturumlari" adında YENİ bir Google Sheets sekmesi kullanır.
    # Bu sekmeyi Google Sheet dosyanda önceden oluşturman gerekiyor,
    # sütun başlıkları önemli değil - kod otomatik oluşturuyor.
    # ──────────────────────────────────────────────────────────
    def _get_oturum_meta():
        df = _get_df("sayim_oturumlari")
        if df.empty:
            return pd.DataFrame(columns=["Oturum_Adi", "Acan_Kisi", "Acilis_Tarihi", "Atanan_Personel", "Durum"])
        df = _ensure_columns(df, {"Oturum_Adi": "", "Acan_Kisi": "", "Acilis_Tarihi": "", "Atanan_Personel": "", "Durum": "Açık"})
        df["Oturum_Adi"] = df["Oturum_Adi"].astype(str).str.strip()
        return df

    def _oturum_meta_satiri(oturum_adi):
        df = _get_oturum_meta()
        if df.empty:
            return None
        eslesme = df[df["Oturum_Adi"] == str(oturum_adi)]
        if eslesme.empty:
            return None
        return eslesme.iloc[-1]

    def _oturum_ilerleme(oturum_adi):
        """(sayılan_kalem, toplam_kalem) döner - 'sayim' ve 'sayim_snapshot' sekmelerinden hesaplar"""
        df_sayim = _get_df("sayim")
        df_snap = _get_df("sayim_snapshot")

        sayilan = 0
        if not df_sayim.empty and "Oturum_Adi" in df_sayim.columns:
            alt = df_sayim[df_sayim["Oturum_Adi"].astype(str) == str(oturum_adi)]
            if not alt.empty and "Adres" in alt.columns and "Kod" in alt.columns:
                sayilan = alt.drop_duplicates(subset=["Adres", "Kod"]).shape[0]
            else:
                sayilan = len(alt)

        toplam = 0
        if not df_snap.empty and "Oturum_Adi" in df_snap.columns:
            alt2 = df_snap[df_snap["Oturum_Adi"].astype(str) == str(oturum_adi)]
            if not alt2.empty and "Adres" in alt2.columns and "Kod" in alt2.columns:
                toplam = alt2.drop_duplicates(subset=["Adres", "Kod"]).shape[0]
            else:
                toplam = len(alt2)

        return sayilan, toplam

    # ──────────────────────────────────────────────────────────
    # DÜZELTME (N+1 sorgu hatası): Yukarıdaki _oturum_ilerleme ve
    # _oturum_meta_satiri, her çağrıldığında Google Sheets'e YENİDEN
    # bağlanıyor. "Bekleyen Oturumlar" listesinde HER oturum için bu
    # fonksiyonlar ayrı ayrı çağrılınca (5 oturum = 15 ekstra okuma),
    # Google Sheets'in dakikalık kota limiti hızla aşılıyor ve sayfa
    # "Running GSheetsServiceAccountClient.read..." mesajında asılı
    # kalıyor. Bu iki fonksiyon, sekmeleri TEK SEFER okuyup listeyi
    # bellekte (ağa gitmeden) hesaplamak için kullanılır.
    # ──────────────────────────────────────────────────────────
    def _oturum_meta_satiri_bellekten(meta_df, oturum_adi):
        if meta_df is None or meta_df.empty or "Oturum_Adi" not in meta_df.columns:
            return None
        eslesme = meta_df[meta_df["Oturum_Adi"].astype(str) == str(oturum_adi)]
        if eslesme.empty:
            return None
        return eslesme.iloc[-1]

    def _oturum_ilerleme_bellekten(df_sayim, df_snap, oturum_adi):
        sayilan = 0
        if df_sayim is not None and not df_sayim.empty and "Oturum_Adi" in df_sayim.columns:
            alt = df_sayim[df_sayim["Oturum_Adi"].astype(str) == str(oturum_adi)]
            if not alt.empty and "Adres" in alt.columns and "Kod" in alt.columns:
                sayilan = alt.drop_duplicates(subset=["Adres", "Kod"]).shape[0]
            else:
                sayilan = len(alt)

        toplam = 0
        if df_snap is not None and not df_snap.empty and "Oturum_Adi" in df_snap.columns:
            alt2 = df_snap[df_snap["Oturum_Adi"].astype(str) == str(oturum_adi)]
            if not alt2.empty and "Adres" in alt2.columns and "Kod" in alt2.columns:
                toplam = alt2.drop_duplicates(subset=["Adres", "Kod"]).shape[0]
            else:
                toplam = len(alt2)

        return sayilan, toplam

    def _snapshot_exists_for_session(oturum_adi):
        df_snapshot = _get_df("sayim_snapshot")
        if df_snapshot.empty:
            return False
        oc = _find_col(df_snapshot, ["Oturum_Adi"])
        if not oc:
            return False
        return (df_snapshot[oc].astype(str) == str(oturum_adi)).any()

    def _prepare_snapshot_for_session(oturum_adi):
        df_stok = _get_df("Stok")
        if df_stok.empty:
            return pd.DataFrame()
        df_stok = df_stok.copy()
        df_stok["Oturum_Adi"] = oturum_adi
        df_stok["Personel"] = aktif_kullanici
        if "Tarih" not in df_stok.columns:
            df_stok["Tarih"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        return df_stok

    def _dedupe_exact(df):
        if df.empty:
            return df
        return df.drop_duplicates().reset_index(drop=True)

    # ──────────────────────────────────────────────────────────
    # YENİ: Süre sınırı OLMAYAN, olay bazlı ortak veri önbelleği.
    # "sayim", "sayim_tamamlanan", "sayim_snapshot", "sayim_oturumlari"
    # sekmeleri session_state'te tutulur. Adres/miktar gibi alanlara
    # yazmak sayfayı yeniden çalıştırsa bile bu veriler TEKRAR OKUNMAZ -
    # sadece şu durumlarda yenilenir:
    #   1) Bu tarayıcı oturumunda ilk kez "Oturum Yönetimi" veya
    #      "Sayım Girişi" ekranına girildiğinde,
    #   2) Kendi kaydımızı yaptıktan hemen sonra (zorla=True),
    #   3) Kullanıcı elle "🔄 Listeyi Yenile" butonuna bastığında.
    # Böylece arama/miktar girme ne kadar sürerse sürsün Google Sheets'e
    # gereksiz bağlanma olmaz.
    # ──────────────────────────────────────────────────────────
    def _sayim_ortak_verileri_yukle(zorla=False):
        # DÜZELTME: Eskiden burada "sayim", "sayim_tamamlanan",
        # "sayim_snapshot", "sayim_oturumlari" SIRAYLA (biri bitmeden
        # diğeri başlamadan) okunuyordu - 4 ayrı bekleme demekti. Artık
        # veri_onbellek.py üzerinden PARALEL okunuyor (aynı anda 4 istek),
        # toplam bekleme süresi en yavaş tekil okuma kadar oluyor. Süre
        # sınırı hâlâ yok - sadece ilk giriş / kayıt sonrası / elle
        # "Yenile" ile yenileniyor (bkz. veri_onbellek.py).
        return vo.modul_verisi_yukle(
            conn, "sayim",
            ["sayim", "sayim_tamamlanan", "sayim_snapshot", "sayim_oturumlari"],
            zorla=zorla
        )

    def _normalize_count_buffer(list_items):
        if not list_items:
            return pd.DataFrame()

        df = pd.DataFrame(list_items).copy()
        needed = {
            "Kayit_ID": "", "Oturum_Adi": "", "Tarih": "", "Adres": "", "Kod": "",
            "İsim": "", "Miktar": 0.0, "Birim": "-", "Personel": "", "Durum": "Kullanılabilir",
            "Tedarikçi_Barkodu": ""
        }
        df = _ensure_columns(df, needed)

        df["Kayit_ID"] = df["Kayit_ID"].astype(str).str.strip()
        df.loc[df["Kayit_ID"] == "", "Kayit_ID"] = [uuid.uuid4().hex for _ in range((df["Kayit_ID"] == "").sum())]
        df["Oturum_Adi"] = df["Oturum_Adi"].astype(str).str.strip()
        df["Tarih"] = df["Tarih"].astype(str).str.strip()
        df["Adres"] = df["Adres"].astype(str).str.strip().str.upper()
        df["Kod"] = df["Kod"].astype(str).str.strip().str.upper()
        df["İsim"] = df["İsim"].astype(str).str.strip()
        df["Miktar"] = _to_num(df["Miktar"])
        df["Birim"] = df["Birim"].astype(str).str.strip()
        df["Personel"] = df["Personel"].astype(str).str.strip()
        df["Durum"] = df["Durum"].astype(str).str.strip()
        df["Tedarikçi_Barkodu"] = df["Tedarikçi_Barkodu"].astype(str).str.strip()

        df = df[df["Kod"] != ""]
        df = df[df["Oturum_Adi"] != ""]

        return df.reset_index(drop=True)

    def _post_session_to_stock(aktif_oturum):
        df_sayim_ana = _get_df("sayim")
        df_stok = _get_df("Stok")
        df_urun = _get_df("Urun_Listesi")
        df_tamamlanan = _get_df("sayim_tamamlanan")

        if df_sayim_ana.empty:
            return False, "Veritabanında hiçbir sayım verisi bulunamadı."

        oturum_col = _find_col(df_sayim_ana, ["Oturum_Adi"])
        if not oturum_col:
            return False, "Oturum kolonu bulunamadı."

        df_bu_sayim = df_sayim_ana[df_sayim_ana[oturum_col].astype(str) == str(aktif_oturum)].copy()
        if df_bu_sayim.empty:
            return False, f"Bu oturuma ({aktif_oturum}) ait herhangi bir kayıt veritabanında bulunamadı!"

        df_bu_sayim = _ensure_columns(df_bu_sayim, {
            "Adres": "", "Kod": "", "İsim": "", "Miktar": 0.0,
            "Durum": "Kullanılabilir", "Birim": "-", "Personel": "", "Tarih": "",
            "Tedarikçi_Barkodu": ""
        })

        df_bu_sayim["Adres"] = df_bu_sayim["Adres"].astype(str).str.strip().str.upper()
        df_bu_sayim["Kod"] = df_bu_sayim["Kod"].astype(str).str.strip().str.upper()
        df_bu_sayim["Miktar"] = _to_num(df_bu_sayim["Miktar"])

        s_ozet = df_bu_sayim.groupby(["Adres", "Kod", "Durum"], sort=False, dropna=False)["Miktar"].sum().reset_index()

        isim_sozlugu = {}
        urun_kod_col = _find_col(df_urun, ["kod", "Kod"])
        urun_isim_col = _find_col(df_urun, ["isim", "İsim"])
        stok_kod_col = _find_col(df_stok, ["Kod", "kod"])
        stok_isim_col = _find_col(df_stok, ["İsim", "isim"])

        if not df_urun.empty and urun_kod_col and urun_isim_col:
            tmp = df_urun[[urun_kod_col, urun_isim_col]].drop_duplicates(subset=[urun_kod_col])
            isim_sozlugu.update({
                str(k).strip().upper(): str(v).strip()
                for k, v in zip(tmp[urun_kod_col], tmp[urun_isim_col]) if str(k).strip() != ""
            })

        if df_stok.empty:
            df_stok = pd.DataFrame(columns=["Adres", "Kod", "İsim", "Miktar", "Durum", "Birim"])

        df_stok = _ensure_columns(df_stok, {"Adres": "", "Kod": "", "İsim": "", "Miktar": 0.0, "Durum": "Kullanılabilir", "Birim": "-"})
        df_stok["Adres"] = df_stok["Adres"].astype(str).str.strip().str.upper()
        df_stok["Kod"] = df_stok["Kod"].astype(str).str.strip().str.upper()
        df_stok["Miktar"] = _to_num(df_stok["Miktar"])

        sayilan_anahtarlar = set(zip(s_ozet["Adres"], s_ozet["Kod"]))
        mask_untouched = ~df_stok.apply(lambda r: (r.get("Adres", ""), r.get("Kod", "")) in sayilan_anahtarlar, axis=1)
        stok_kalan = df_stok[mask_untouched].copy()

        yeni_stok_verisi = s_ozet.copy()
        yeni_stok_verisi["İsim"] = yeni_stok_verisi["Kod"].map(isim_sozlugu).fillna("TANIMSIZ")
        yeni_stok_verisi["Birim"] = "-"
        yeni_stok_verisi = yeni_stok_verisi[yeni_stok_verisi["Miktar"] > 0].copy()

        stok_final = pd.concat([stok_kalan, yeni_stok_verisi], ignore_index=True)
        stok_final = stok_final[stok_final["Kod"] != ""].reset_index(drop=True)

        _save_df("Stok", stok_final)

        tamamlanmis_sayimlar = set()
        if not df_tamamlanan.empty:
            tamamlanan_oturum_col = _find_col(df_tamamlanan, ["Oturum_Adi"])
            if tamamlanan_oturum_col:
                tamamlanmis_sayimlar = set(df_tamamlanan[tamamlanan_oturum_col].astype(str).tolist())

        if aktif_oturum not in tamamlanmis_sayimlar:
            log_yeni = pd.DataFrame([{
                "Oturum_Adi": aktif_oturum,
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                "Personel": aktif_kullanici,
                "Toplam_Kalem": int(len(df_bu_sayim)),
                "Toplam_Satir": int(len(s_ozet)),
                "Durum": "POST_EDILDI"
            }])
            tamamlanan_guncel = log_yeni if df_tamamlanan.empty else pd.concat([df_tamamlanan, log_yeni], ignore_index=True)
            _save_df("sayim_tamamlanan", _dedupe_exact(tamamlanan_guncel))

        # YENİ: sayim_oturumlari sekmesinde de durumu güncelle (varsa)
        meta_df = _get_df("sayim_oturumlari")
        if not meta_df.empty and "Oturum_Adi" in meta_df.columns:
            meta_df.loc[meta_df["Oturum_Adi"].astype(str) == str(aktif_oturum), "Durum"] = "Tamamlandı"
            _save_df("sayim_oturumlari", meta_df)

        return True, "Stoklar başarıyla güncellendi ve oturum arşivlendi!"

    def _refresh_and_rerun():
        st.rerun()

    # ──────────────────────────────────────────────────────────
    # YENİ: CİHAZ BAĞIMSIZ AKTİF BELGE MANTIĞI
    # Eskiden "aktif belge" her cihazın kendi session_state'inde ayrı ayrı
    # tutuluyordu - masaüstünde aktifleştirilen bir belge el terminalinde
    # görünmüyordu, çünkü ikisi tamamen ayrı tarayıcı oturumları.
    # Kural netleşti: "Bir belge varsa ve açıksa, herkese her ekranda
    # açıktır. Kapalıysa herkese kapatılır." Bu yüzden aktif belge artık
    # cihazda saklanmıyor - HER SAYFA YÜKLENİŞİNDE paylaşımlı veriden
    # (sayim_oturumlari / sayim_snapshot / sayim) YENİDEN hesaplanıyor:
    #   - Açık belge yoksa  -> aktif belge yok (herkese kapalı)
    #   - Açık belge 1 taneyse -> o belge otomatik aktif (herkese açık)
    #   - Açık belge birden fazlaysa -> otomatik seçim yapılamaz (hangisi
    #     olduğu belirsiz), kullanıcı listeden kendi seçer; ama seçimi
    #     yine bu cihaza özeldir (paralel sayım senaryosunda kaçınılmaz).
    # ──────────────────────────────────────────────────────────
    _acik_belgeler_genel = _open_sessions()
    if len(_acik_belgeler_genel) == 0:
        st.session_state.aktif_sayim_adi = None
    elif len(_acik_belgeler_genel) == 1:
        st.session_state.aktif_sayim_adi = _acik_belgeler_genel[0]
    elif st.session_state.aktif_sayim_adi not in _acik_belgeler_genel:
        st.session_state.aktif_sayim_adi = None

    # ==============================================================================
    # UI RENDER SÜREÇLERİ
    # ==============================================================================
    if st.session_state.sayim_page == 'menu':
        st.subheader("⚖️ Sayım Kontrol Merkezi")
        if st.session_state.get('oto_algilanan_cihaz'):
            st.caption(f"Algılanan cihaz: {st.session_state.oto_algilanan_cihaz}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.button("📁 SAYIM BELGESİ YÖNETİMİ", use_container_width=True, on_click=go_oturum)
        with c2:
            st.button("📝 SAYIM GİRİŞİ", use_container_width=True, on_click=go_giris)
        with c3:
            st.button("📊 FARK RAPORU", use_container_width=True, on_click=go_rapor)
        with c4:
            st.button("📱 EL TERMİNALİ MODU", use_container_width=True, on_click=go_el_terminal)

        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Aktif Sayım Belgesi: **{st.session_state.aktif_sayim_adi}**")
        else:
            st.info("ℹ️ Açık sayım belgesi yok. İşlem için belge oluşturun veya bekleyen bir belgeyi aktifleştirin.")

    elif st.session_state.sayim_page == 'oturum':
        st.subheader("📁 Sayım Belgesi Yönetimi")
        c_geri, c_yenile = st.columns([3, 1])
        with c_geri:
            if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
                go_sayim_menu()
                st.rerun()
        with c_yenile:
            if st.button("🔄 Yenile", use_container_width=True):
                _sayim_ortak_verileri_yukle(zorla=True)
                st.rerun()

        _veri = _sayim_ortak_verileri_yukle()
        df_sayim_ana = _veri["sayim"]
        df_tamamlanan = _veri["sayim_tamamlanan"]
        df_snapshot_ana = _veri["sayim_snapshot"]

        tamamlanmis_oturumlar = []
        if not df_tamamlanan.empty:
            oc = _find_col(df_tamamlanan, ["Oturum_Adi"])
            if oc:
                tamamlanmis_oturumlar = df_tamamlanan[oc].dropna().astype(str).unique().tolist()

        tum_oturumlar = []
        if not df_sayim_ana.empty:
            oc = _find_col(df_sayim_ana, ["Oturum_Adi"])
            if oc:
                tum_oturumlar.extend(df_sayim_ana[oc].dropna().astype(str).unique().tolist())
        if not df_snapshot_ana.empty:
            oc = _find_col(df_snapshot_ana, ["Oturum_Adi"])
            if oc:
                tum_oturumlar.extend(df_snapshot_ana[oc].dropna().astype(str).unique().tolist())

        bekleyenler = [o for o in sorted(list(set(tum_oturumlar))) if o not in tamamlanmis_oturumlar]

        with st.expander("🆕 Yeni Sayım Belgesi Oluştur", expanded=(st.session_state.aktif_sayim_adi is None)):
            sayim_etiketi = st.text_input("Sayım Belgesi Adı:", placeholder="Örn: A_Blok")
            atanan_personel = st.text_input(
                "👥 Atanan Personel (opsiyonel):",
                placeholder="Örn: Ahmet, Mehmet — boş bırakırsan herkes çalışabilir"
            )
            if st.button("🚀 SAYIMI BAŞLAT", use_container_width=True):
                if sayim_etiketi:
                    sayim_etiketi = _upper_text(sayim_etiketi).replace(" ", "_")
                    yeni_oturum_id = f"{sayim_etiketi}_{datetime.now().strftime('%d%m_%H%M')}"

                    # DÜZELTME: sayim_snapshot artık ortak önbellekten okunuyor
                    # (ayrı bir ağ çağrısı yapılmıyor).
                    mevcut_snapshots = _veri["sayim_snapshot"]
                    oc_snap = _find_col(mevcut_snapshots, ["Oturum_Adi"])
                    snapshot_zaten_var = (
                        oc_snap is not None and not mevcut_snapshots.empty and
                        (mevcut_snapshots[oc_snap].astype(str) == str(yeni_oturum_id)).any()
                    )
                    if not snapshot_zaten_var:
                        snapshot_df = _prepare_snapshot_for_session(yeni_oturum_id)
                        if not snapshot_df.empty:
                            yeni_snapshots = snapshot_df if mevcut_snapshots.empty else pd.concat([mevcut_snapshots, snapshot_df], ignore_index=True)
                            _save_df("sayim_snapshot", _dedupe_exact(yeni_snapshots))

                    # YENİ: Oturum meta bilgisini (açan kişi, atanan personel) kaydet
                    meta_satiri = pd.DataFrame([{
                        "Oturum_Adi": yeni_oturum_id,
                        "Acan_Kisi": _norm_text(aktif_kullanici),
                        "Acilis_Tarihi": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                        "Atanan_Personel": _norm_text(atanan_personel),
                        "Durum": "Açık"
                    }])
                    mevcut_meta = _veri["sayim_oturumlari"]
                    yeni_meta = meta_satiri if mevcut_meta.empty else pd.concat([mevcut_meta, meta_satiri], ignore_index=True)
                    _save_df("sayim_oturumlari", _dedupe_exact(yeni_meta))

                    # DÜZELTME: Yeni oturum hemen listede görünsün diye
                    # ortak önbelleği zorla yeniliyoruz.
                    _sayim_ortak_verileri_yukle(zorla=True)

                    st.session_state['gecici_sayim_listesi'] = []
                    st.session_state.aktif_sayim_adi = yeni_oturum_id
                    _refresh_and_rerun()

        if bekleyenler:
            with st.expander("⏳ Bekleyen (Açık) Sayım Belgeleri", expanded=True):
                df_oturum_meta_all = _veri["sayim_oturumlari"]

                satirlar = []
                for o in bekleyenler:
                    meta_satiri = _oturum_meta_satiri_bellekten(df_oturum_meta_all, o)
                    acan = meta_satiri["Acan_Kisi"] if meta_satiri is not None else "-"
                    atanan = _norm_text(meta_satiri["Atanan_Personel"]) if meta_satiri is not None else ""
                    sayilan, toplam = _oturum_ilerleme_bellekten(df_sayim_ana, df_snapshot_ana, o)
                    satirlar.append({
                        "Sayım Belgesi": o,
                        "Açan": acan,
                        "Atanan Personel": atanan if atanan else "Herkes",
                        "İlerleme": f"{sayilan} / {toplam}" if toplam else f"{sayilan} kalem sayıldı"
                    })
                if satirlar:
                    st.dataframe(pd.DataFrame(satirlar), use_container_width=True, hide_index=True)

                # Not: Sadece birden fazla belge açıkken bu seçim anlamlı -
                # tek belge açıkken zaten otomatik aktif oluyor (yukarıdaki
                # cihaz bağımsız mantık).
                secilen_bekleyen = st.selectbox("Aktifleştirilecek Sayım Belgesini Seçin:", bekleyenler)
                if st.button("🔄 BELGEYİ GERİ AÇ (AKTİFLEŞTİR)", use_container_width=True):
                    st.session_state.aktif_sayim_adi = secilen_bekleyen
                    _refresh_and_rerun()

        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Şuan Çalışılan Sayım Belgesi: **{st.session_state.aktif_sayim_adi}**")
            # NOT: "Sadece Kapat" butonu kaldırıldı - artık aktif belge
            # cihazda saklanmıyor, paylaşımlı veriden hesaplanıyor. Belge
            # açık kaldıkça (post edilmedikçe) TÜM cihazlarda otomatik
            # aktif görünmeye devam eder - bu, "açıksa herkese açık,
            # kapalıysa herkese kapalı" kuralının ta kendisi. Belgeyi
            # gerçekten kapatmanın tek yolu aşağıdaki POST işlemi.

            onay = st.checkbox("Sayım verilerinin doğruluğunu onaylıyorum.")
            if st.button("🚀 STOKLARI GÜNCELLE VE ARŞİVLE", use_container_width=True, disabled=not onay):
                basarili, mesaj = _post_session_to_stock(st.session_state.aktif_sayim_adi)
                if basarili:
                    _sayim_ortak_verileri_yukle(zorla=True)
                    st.session_state.aktif_sayim_adi = None
                    st.success(mesaj)
                    _refresh_and_rerun()
                else:
                    st.error(mesaj)


    elif st.session_state.sayim_page == 'giris':
        st.subheader("📝 Sayım Girişi")
        c_geri, c_yenile = st.columns([3, 1])
        with c_geri:
            if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
                go_sayim_menu()
                st.rerun()
        with c_yenile:
            if st.button("🔄 Yenile", use_container_width=True):
                _sayim_ortak_verileri_yukle(zorla=True)
                st.rerun()

        # DÜZELTME: Eskiden burada df_sayim_ana/df_tamamlanan okunuyor,
        # SONRA _open_sessions() aynı sekmeleri (+ sayim_snapshot) YENİDEN
        # okuyordu, SONRA aşağıda ilerleme/atanan gösterimi için üçüncü kez
        # okunuyordu. Bu ekran her barkod okutmada/tuşlamada yeniden
        # çalıştığı için (on_change), aynı sekmelere saniyede defalarca
        # bağlanılıyor ve Google Sheets kota limitine takılıp sayfa
        # "Running GSheetsServiceAccountClient.read..." durumunda asılı
        # kalıyordu. Artık her sekme sayfa başına SADECE 1 KEZ okunuyor.
        _veri = _sayim_ortak_verileri_yukle()
        df_sayim_ana = _veri["sayim"]
        df_tamamlanan = _veri["sayim_tamamlanan"]
        df_snapshot_ana = _veri["sayim_snapshot"]
        df_oturum_meta_all = _veri["sayim_oturumlari"]

        tamamlanmis = []
        if not df_tamamlanan.empty:
            oc = _find_col(df_tamamlanan, ["Oturum_Adi"])
            if oc:
                tamamlanmis = df_tamamlanan[oc].dropna().astype(str).unique().tolist()

        tum_o = []
        if not df_sayim_ana.empty:
            oc = _find_col(df_sayim_ana, ["Oturum_Adi"])
            if oc:
                tum_o.extend(df_sayim_ana[oc].dropna().astype(str).unique().tolist())
        if not df_snapshot_ana.empty:
            oc = _find_col(df_snapshot_ana, ["Oturum_Adi"])
            if oc:
                tum_o.extend(df_snapshot_ana[oc].dropna().astype(str).unique().tolist())

        bekleyenler = [o for o in sorted(list(set(tum_o))) if o not in tamamlanmis]

        if st.session_state.aktif_sayim_adi and st.session_state.aktif_sayim_adi not in bekleyenler:
            bekleyenler.insert(0, st.session_state.aktif_sayim_adi)

        if not bekleyenler:
            st.warning("⚠️ Bekleyen sayım belgesi bulunamadı. Lütfen önce belge oluşturun.")
        else:
            # YENİ: Ekrana her girişte TÜM post edilmemiş (açık) belgeler
            # bir tabloda görünür - Açan/Atanan/İlerleme bilgisiyle birlikte.
            # Otomatik hiçbir belgeye girilmiyor, seçim tamamen kullanıcıda.
            st.markdown("#### 📋 Post Edilmemiş Tüm Sayım Belgeleri")
            satirlar = []
            for o in bekleyenler:
                meta_satiri = _oturum_meta_satiri_bellekten(df_oturum_meta_all, o)
                acan = meta_satiri["Acan_Kisi"] if meta_satiri is not None else "-"
                atanan = _norm_text(meta_satiri["Atanan_Personel"]) if meta_satiri is not None else ""
                sayilan, toplam = _oturum_ilerleme_bellekten(df_sayim_ana, df_snapshot_ana, o)
                satirlar.append({
                    "Sayım Belgesi": o,
                    "Açan": acan,
                    "Atanan Personel": atanan if atanan else "Herkes",
                    "İlerleme": f"{sayilan} / {toplam}" if toplam else f"{sayilan} kalem sayıldı"
                })
            st.dataframe(pd.DataFrame(satirlar), use_container_width=True, hide_index=True)

            if st.session_state.aktif_sayim_adi not in bekleyenler:
                st.session_state.aktif_sayim_adi = bekleyenler[0]

            # DÜZELTME: Seçim artık gerçekten işleniyor - eskiden selectbox
            # sonucu hiçbir değişkene atanmıyordu, dropdown'dan farklı bir
            # belge seçmek görünürde çalışıyor ama hiçbir etkisi olmuyordu.
            secilen_oturum = st.selectbox(
                "📡 Çalışılacak Sayım Belgesi:",
                bekleyenler,
                index=bekleyenler.index(st.session_state.aktif_sayim_adi)
            )
            if secilen_oturum != st.session_state.aktif_sayim_adi:
                st.session_state.aktif_sayim_adi = secilen_oturum
                st.rerun()

            # DÜZELTME: Artık yukarıda zaten okunmuş df_oturum_meta_all,
            # df_sayim_ana, df_snapshot_ana kullanılıyor - tekrar Google
            # Sheets'e bağlanmıyor.
            _meta_satiri = _oturum_meta_satiri_bellekten(df_oturum_meta_all, st.session_state.aktif_sayim_adi)
            _acan_metni = _meta_satiri["Acan_Kisi"] if _meta_satiri is not None else "-"
            _atanan_metni = _norm_text(_meta_satiri["Atanan_Personel"]) if _meta_satiri is not None else ""
            _sayilan, _toplam = _oturum_ilerleme_bellekten(df_sayim_ana, df_snapshot_ana, st.session_state.aktif_sayim_adi)
            st.caption(
                f"👤 Açan: {_acan_metni} | 👥 Atanan: {_atanan_metni if _atanan_metni else 'Herkes çalışabilir'} | "
                f"📊 İlerleme: {_sayilan} / {_toplam}" if _toplam else
                f"👤 Açan: {_acan_metni} | 👥 Atanan: {_atanan_metni if _atanan_metni else 'Herkes çalışabilir'} | "
                f"📊 İlerleme: {_sayilan} kalem sayıldı"
            )

            with st.container(border=True):
                adres_listesi = get_dinamik_adres_listesi()
                sec_adres = st.selectbox(
                    "📍 Adres:",
                    ["+ MANUEL"] + adres_listesi,
                    help="Yazmaya başlayınca listede arama yapabilirsin. Listede yoksa '+ MANUEL' seçip elle yaz."
                )
                if sec_adres != "+ MANUEL":
                    s_adr = sec_adres
                else:
                    s_adr = st.text_input("📍 Adres (elle):").upper()

                # -----------------------------
                # 1. Adım: Tedarikçi Barkod Okutma Alanı (Okuyucu Girişi)
                # OTOMATİK ENTER: on_change ile barkod okutulunca otomatik işlenir,
                # işlendikten sonra alan otomatik temizlenir (yeni okutmaya hazır).
                # -----------------------------
                def _sup_barcode_auto_submit():
                    barkod = st.session_state.get("supplier_barcode_key", "").strip()
                    if barkod:
                        handle_supplier_barcode(barkod)
                        st.session_state.last_handled_barcode = barkod
                        st.session_state.supplier_barcode_key = ""

                st.markdown("---")
                st.markdown("#### 🔌 Tedarikçi Barkodu Okutun")
                col_bar1, col_bar2 = st.columns([3, 1])
                with col_bar1:
                    sup_barcode_input = st.text_input(
                        "Tedarikçi Barkodu:",
                        key="supplier_barcode_key",
                        placeholder="Barkodu okutun, otomatik işlenir...",
                        label_visibility="collapsed",
                        on_change=_sup_barcode_auto_submit
                    )
                with col_bar2:
                    islem_yap = st.button("🔍 Getir / Çöz", use_container_width=True)

                # Manuel buton ile de tetikleme (yedek / fallback)
                if islem_yap and sup_barcode_input:
                    st.session_state.last_handled_barcode = sup_barcode_input
                    handle_supplier_barcode(sup_barcode_input)

                st.markdown("---")
                st.markdown("#### 📦 Malzeme Bilgileri")

                # DÜZELTME: Eskiden burada İKİNCİ bir "Tedarikçi Barkodu / Parti
                # No" giriş kutusu vardı - yukarıdaki okuma alanıyla aynı işi
                # yapıyor, kafa karıştırıyordu. Artık tek barkod alanı var
                # (yukarıdaki, otomatik enter yapan). Okutulan/girilen barkod
                # değeri session_state'te tutuluyor, burada sadece bilgi
                # amaçlı salt-okunur gösteriliyor.
                if st.session_state.def_s_barcode:
                    st.caption(f"🔌 Kayıtlı Barkod / Parti No: **{st.session_state.def_s_barcode}**")

                katalog = get_dinamik_katalog()

                # Barkod ile eşleşen kodu katalog içinde bulmaya çalış
                default_index = 0
                if st.session_state.def_s_kod:
                    for idx, cat_item in enumerate(katalog):
                        if cat_item.upper().startswith(st.session_state.def_s_kod.upper() + " |"):
                            default_index = idx + 1  # "+ MANUEL" seçeneği 0. sırada olduğu için
                            break

                sec = st.selectbox("🔍 Ürün / Malzeme Kataloğu:", ["+ MANUEL"] + katalog, index=default_index)

                if sec != "+ MANUEL":
                    sec_parcalar = sec.split(" | ", 1)
                    s_kod = st.text_input("📦 Kod:", value=sec_parcalar[0].strip(), disabled=True)
                    s_isim = st.text_input("📝 İsim:", value=sec_parcalar[1].strip() if len(sec_parcalar) > 1 else "", disabled=True)
                else:
                    # Barkod okutulmuşsa verileri otomatik doldur, yoksa boş veya manuel giriş
                    s_kod = st.text_input("📦 Kod:", value=st.session_state.def_s_kod).upper()
                    s_isim = st.text_input("📝 İsim:", value=st.session_state.def_s_isim).upper()

                # Barkoddan çekilen miktar otomatik doldurulur
                s_mik = st.number_input("Miktar:", min_value=0.0, step=0.01, value=st.session_state.def_s_mik)
                s_dur = st.selectbox("🛠️ Durum:", ["Kullanılabilir", "Hasarlı", "İncelemede"])

                # Temizle butonu ile formu boşaltma imkanı sağla
                if st.button("🧹 Girişleri Temizle", use_container_width=True):
                    st.session_state.clear_sayim_form = True
                    st.rerun()

                if st.button("➕ EKLE", use_container_width=True):
                    if not _norm_text(s_kod):
                        st.error("Ürün kodu boş bırakılamamaktadır.")
                    else:
                        yeni_satir = {
                            "Oturum_Adi": st.session_state.aktif_sayim_adi,
                            "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                            "Adres": _upper_text(s_adr),
                            "Kod": _upper_text(s_kod),
                            "İsim": _norm_text(s_isim),
                            "Miktar": float(s_mik),
                            "Birim": "-",
                            "Personel": _norm_text(aktif_kullanici),
                            "Durum": _norm_text(s_dur),
                            "Tedarikçi_Barkodu": _norm_text(st.session_state.def_s_barcode)  # Barkodu da kayda iliştiriyoruz
                        }
                        mevcut = st.session_state['gecici_sayim_listesi']
                        mevcut.append(yeni_satir)
                        st.session_state['gecici_sayim_listesi'] = mevcut
                        st.toast("Listeye Eklendi", icon="📥")

                        # Ekleme yapıldıktan sonra geçici barkod hafızasını sıfırla
                        st.session_state.clear_sayim_form = True
                        st.rerun()

                if st.session_state['gecici_sayim_listesi']:
                    st.markdown("### 📋 Geçici Sayım Listesi")
                    for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                        cols = st.columns([3, 1])
                        # Ekranda okutulan Tedarikçi Barkodu bilgisini de gösterelim
                        barkod_metni = f" | 🔌 Barkod: {item['Tedarikçi_Barkodu']}" if item.get('Tedarikçi_Barkodu') else ""
                        cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {float(item['Miktar']):.3f} | 🛠️ {item['Durum']}{barkod_metni}")
                        if cols[1].button("🗑️", key=f"d_{idx}"):
                            st.session_state['gecici_sayim_listesi'].pop(idx)
                            st.rerun()

                    if st.button("📤 BULUTA KAYDET", use_container_width=True):
                        yeni_veri_df = _normalize_count_buffer(st.session_state['gecici_sayim_listesi'])
                        if not yeni_veri_df.empty:
                            # DÜZELTME: Artık "oku + tüm sekmeyi üzerine yaz"
                            # yerine native EKLEME kullanılıyor - mevcut
                            # binlerce satıra dokunulmuyor.
                            basarili = _guvenli_satirlar_ekle("sayim", yeni_veri_df)
                            if basarili:
                                _sayim_ortak_verileri_yukle(zorla=True)
                                st.session_state['gecici_sayim_listesi'] = []
                                st.success("Tüm veriler başarıyla kaydedildi!")
                                _refresh_and_rerun()

    elif st.session_state.sayim_page == 'rapor':
        st.subheader("📊 Fark Raporu")
        if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
            go_sayim_menu()
            st.rerun()

        # DÜZELTME: Burada da doğrudan _get_df yerine önbellekten okunuyor -
        # aynı sebep, selectbox değiştikçe tekrar tekrar ağa gitmesin diye.
        _veri_rapor = _sayim_ortak_verileri_yukle()
        df_sayim_ana = _veri_rapor["sayim"]
        df_snapshot_ana = _veri_rapor["sayim_snapshot"]

        if not df_sayim_ana.empty:
            mevcut_oturumlar = df_sayim_ana["Oturum_Adi"].dropna().astype(str).unique().tolist()
            secilen_oturum = st.selectbox("Raporu Gösterilecek Sayım Belgesi:", mevcut_oturumlar)

            df_sayim = df_sayim_ana[df_sayim_ana["Oturum_Adi"].astype(str) == str(secilen_oturum)].copy()

            if not df_sayim.empty:
                df_sayim["Miktar"] = _to_num(df_sayim["Miktar"])
                s_ozet = df_sayim.groupby(["Adres", "Kod", "Durum"], sort=False)["Miktar"].sum().reset_index().rename(columns={"Miktar": "Miktar_Sayilan"})

                df_snapshot_oturum = df_snapshot_ana[df_snapshot_ana["Oturum_Adi"].astype(str) == str(secilen_oturum)].copy() if not df_snapshot_ana.empty else pd.DataFrame()

                if not df_snapshot_oturum.empty:
                    df_snapshot_oturum["Miktar"] = _to_num(df_snapshot_oturum["Miktar"])
                    st_ozet = df_snapshot_oturum.groupby(["Adres", "Kod"], sort=False)["Miktar"].sum().reset_index().rename(columns={"Miktar": "Miktar_Sistem"})
                else:
                    st_ozet = pd.DataFrame(columns=["Adres", "Kod", "Miktar_Sistem"])

                rapor = pd.merge(s_ozet, st_ozet, on=["Adres", "Kod"], how="outer")
                rapor["Miktar_Sayilan"] = _to_num(rapor.get("Miktar_Sayilan", 0.0))
                rapor["Miktar_Sistem"] = _to_num(rapor.get("Miktar_Sistem", 0.0))
                rapor["FARK"] = rapor["Miktar_Sayilan"] - rapor["Miktar_Sistem"]

                st.dataframe(rapor, use_container_width=True, hide_index=True)

    # ==============================================================================
    # YENİ: EL TERMİNALİ MODU (El terminali / dokunmatik cihazlar için sade ekran)
    # ==============================================================================
    elif st.session_state.sayim_page == 'el_terminali':
        # Büyük yazı tipi ve büyük dokunma alanları için CSS
        st.markdown("""
            <style>
            div[data-testid="stTextInput"] input,
            div[data-testid="stNumberInput"] input {
                font-size: 26px !important;
                min-height: 58px !important;
                height: auto !important;
                padding: 8px 12px !important;
            }
            div[data-testid="stSelectbox"] div[data-baseweb="select"] {
                font-size: 22px !important;
                min-height: 55px !important;
            }
            div.stButton > button {
                font-size: 22px !important;
                min-height: 62px !important;
                height: auto !important;
                white-space: normal !important;
                line-height: 1.3 !important;
                padding: 10px 12px !important;
                font-weight: 700 !important;
            }
            div[data-testid="stMarkdownContainer"] h4 {
                font-size: 20px !important;
                margin-top: 6px !important;
                margin-bottom: 2px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        st.subheader("📱 El Terminali Modu")
        if st.button("⬅️ GERİ", use_container_width=True):
            go_sayim_menu()
            st.rerun()

        if not st.session_state.aktif_sayim_adi:
            st.warning("⚠️ Aktif sayım belgesi yok. Önce 'Sayım Belgesi Yönetimi' ekranından bir belge oluşturun veya aktifleştirin.")
        else:
            st.success(f"📡 Sayım Belgesi: **{st.session_state.aktif_sayim_adi}**")

            def _el_barkod_auto_submit():
                barkod = st.session_state.get("el_barkod_key", "").strip()
                if barkod:
                    handle_supplier_barcode(barkod)
                    st.session_state.el_barkod_key = ""

            with st.container(border=True):
                st.markdown("#### 1️⃣ Adres")
                adres_listesi_el = get_dinamik_adres_listesi()
                sec_adres_el = st.selectbox(
                    "Adres:",
                    ["+ MANUEL"] + adres_listesi_el,
                    label_visibility="collapsed",
                    key="el_adres_secim_key"
                )
                if sec_adres_el != "+ MANUEL":
                    el_adr = sec_adres_el
                else:
                    el_adr = st.text_input(
                        "Adres (elle):",
                        key="el_adres_key",
                        label_visibility="collapsed",
                        placeholder="ADRES"
                    ).upper()

                st.markdown("#### 2️⃣ Barkod (Okutunca Otomatik İşlenir)")
                st.text_input(
                    "Barkod:",
                    key="el_barkod_key",
                    label_visibility="collapsed",
                    placeholder="Barkodu okutun...",
                    on_change=_el_barkod_auto_submit
                )

                st.markdown("#### 📦 Malzeme")
                st.text_input("Kod:", value=st.session_state.def_s_kod, disabled=True, key="el_kod_goster")
                st.text_input("İsim:", value=st.session_state.def_s_isim, disabled=True, key="el_isim_goster")

                st.markdown("#### 3️⃣ Miktar")
                el_mik = st.number_input(
                    "Miktar:",
                    min_value=0.0,
                    step=0.01,
                    value=st.session_state.def_s_mik,
                    key="el_mik_key",
                    label_visibility="collapsed"
                )

                el_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "İncelemede"], key="el_durum_key")

                if st.button("✅ LİSTEYE EKLE", use_container_width=True):
                    if not _norm_text(st.session_state.def_s_kod):
                        st.error("Önce barkod okutun veya Kod alanını doldurun.")
                    else:
                        yeni_satir = {
                            "Oturum_Adi": st.session_state.aktif_sayim_adi,
                            "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                            "Adres": _upper_text(el_adr),
                            "Kod": _upper_text(st.session_state.def_s_kod),
                            "İsim": _norm_text(st.session_state.def_s_isim),
                            "Miktar": float(el_mik),
                            "Birim": "-",
                            "Personel": _norm_text(aktif_kullanici),
                            "Durum": _norm_text(el_dur),
                            "Tedarikçi_Barkodu": _norm_text(st.session_state.def_s_barcode)
                        }
                        st.session_state['gecici_sayim_listesi'].append(yeni_satir)
                        st.session_state.def_s_kod = ""
                        st.session_state.def_s_isim = ""
                        st.session_state.def_s_mik = 0.0
                        st.session_state.def_s_barcode = ""
                        st.toast("✅ Eklendi!", icon="📥")
                        st.rerun()

                st.markdown(f"**📋 Bu Sayım Belgesinde Bekleyen Kayıt: {len(st.session_state['gecici_sayim_listesi'])}**")

                if st.session_state['gecici_sayim_listesi']:
                    son_kayit = st.session_state['gecici_sayim_listesi'][-1]
                    st.info(f"Son: 📍{son_kayit['Adres']} | 📦{son_kayit['Kod']} | 🔢{son_kayit['Miktar']}")

                    if st.button("📤 BULUTA KAYDET", use_container_width=True, key="el_kaydet"):
                        yeni_veri_df = _normalize_count_buffer(st.session_state['gecici_sayim_listesi'])
                        if not yeni_veri_df.empty:
                            basarili = _guvenli_satirlar_ekle("sayim", yeni_veri_df)
                            if basarili:
                                _sayim_ortak_verileri_yukle(zorla=True)
                                st.session_state['gecici_sayim_listesi'] = []
                                st.success("Kaydedildi!")
                                st.rerun()
