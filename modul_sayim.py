import streamlit as st
import pandas as pd
import io
import time
import random
import os
import tedarikci_api
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
    # YENİ: Önce API'den çekilmiş tedarikçi barkod haritasına bak.
    # (Mal Kabul veya bu ekrandaki "Sevkiyat Çek" ile doldurulur.)
    # ──────────────────────────────────────────────────────────
    api_harita = st.session_state.get('api_sevk_haritasi', {})
    api_kayit = api_harita.get(str(barcode_scanned).strip()) or api_harita.get(parti_no)
    if api_kayit:
        st.session_state.def_s_kod = api_kayit["MalzemeKodu"]
        st.session_state.def_s_isim = api_kayit["MalzemeAdi"]
        st.session_state.def_s_mik = float(api_kayit["Miktar"] or 0)
        st.session_state.def_s_barcode = str(barcode_scanned).strip()
        st.toast(f"🌐 Tedarikçi Portalından Bulundu: {api_kayit['MalzemeAdi']}", icon="✔️")
        return
    # ──────────────────────────────────────────────────────────
    # Buradan sonrası MEVCUT yedek mantık (FORM_SUNGER.xlsx / BRN eşleşme)
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
        for i in range(15):
            try:
                df = conn.read(worksheet=table_name, ttl=0)
                if df is None:
                    return pd.DataFrame()
                return df.copy()
            except Exception:
                if i == 14:
                    return pd.DataFrame()
                time.sleep(random.uniform(0.2, 0.7))

    def _save_df(table_name, df):
        if df is None:
            df = pd.DataFrame()
        for i in range(15):
            try:
                conn.update(worksheet=table_name, data=df)
                break
            except Exception:
                if i == 14:
                    pass
                time.sleep(random.uniform(0.2, 0.7))

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
        df_tamamlanan = _get_df("sayim_tamamlanan")
        if df_tamamlanan.empty:
            return []
        oturum_col = _find_col(df_tamamlanan, ["Oturum_Adi"])
        if not oturum_col:
            return []
        return df_tamamlanan[oturum_col].dropna().astype(str).unique().tolist()

    def _session_all_sessions():
        tum = []
        df_sayim = _get_df("sayim")
        df_snapshot = _get_df("sayim_snapshot")

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

    def _normalize_count_buffer(list_items):
        if not list_items:
            return pd.DataFrame()

        df = pd.DataFrame(list_items).copy()
        needed = {
            "Oturum_Adi": "", "Tarih": "", "Adres": "", "Kod": "",
            "İsim": "", "Miktar": 0.0, "Birim": "-", "Personel": "", "Durum": "Kullanılabilir",
            "Tedarikçi_Barkodu": ""
        }
        df = _ensure_columns(df, needed)

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

        return True, "Stoklar başarıyla güncellendi ve oturum arşivlendi!"

    def _refresh_and_rerun():
        st.rerun()

    # ==============================================================================
    # UI RENDER SÜREÇLERİ
    # ==============================================================================
    if st.session_state.sayim_page == 'menu':
        st.subheader("⚖️ Sayım Kontrol Merkezi")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("📁 OTURUM YÖNETİMİ", use_container_width=True, on_click=go_oturum)
        with c2:
            st.button("📝 SAYIM GİRİŞİ", use_container_width=True, on_click=go_giris)
        with c3:
            st.button("📊 FARK RAPORU", use_container_width=True, on_click=go_rapor)

        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
        else:
            st.info("ℹ️ Açık oturum yok. İşlem için oturum başlatın veya bekleyen bir oturumu aktifleştirin.")

    elif st.session_state.sayim_page == 'oturum':
        st.subheader("📁 Oturum Yönetimi")
        if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
            go_sayim_menu()
            st.rerun()

        df_sayim_ana = _get_df("sayim")
        df_tamamlanan = _get_df("sayim_tamamlanan")
        df_snapshot_ana = _get_df("sayim_snapshot")

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

        with st.expander("🆕 Yeni Sayım Oturumu Başlat", expanded=(st.session_state.aktif_sayim_adi is None)):
            sayim_etiketi = st.text_input("Oturum İsmi:", placeholder="Örn: A_Blok")
            if st.button("🚀 SAYIMI BAŞLAT", use_container_width=True):
                if sayim_etiketi:
                    sayim_etiketi = _upper_text(sayim_etiketi).replace(" ", "_")
                    yeni_oturum_id = f"{sayim_etiketi}_{datetime.now().strftime('%d%m_%H%M')}"

                    if not _snapshot_exists_for_session(yeni_oturum_id):
                        snapshot_df = _prepare_snapshot_for_session(yeni_oturum_id)
                        if not snapshot_df.empty:
                            mevcut_snapshots = _get_df("sayim_snapshot")
                            yeni_snapshots = snapshot_df if mevcut_snapshots.empty else pd.concat([mevcut_snapshots, snapshot_df], ignore_index=True)
                            _save_df("sayim_snapshot", _dedupe_exact(yeni_snapshots))

                    st.session_state.aktif_sayim_adi = yeni_oturum_id
                    st.session_state['gecici_sayim_listesi'] = []
                    _refresh_and_rerun()

        if bekleyenler:
            with st.expander("⏳ Bekleyen (Açık) Oturumlar"):
                secilen_bekleyen = st.selectbox("Aktifleştirilecek Oturumu Seçin:", bekleyenler)
                if st.button("🔄 OTURUMU GERİ AÇ (AKTİFLEŞTİR)", use_container_width=True):
                    st.session_state.aktif_sayim_adi = secilen_bekleyen
                    _refresh_and_rerun()

        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Şuan Çalışılan Oturum: **{st.session_state.aktif_sayim_adi}**")
            if st.button("🛑 OTURUMU SADECE KAPAT", use_container_width=True):
                st.session_state.aktif_sayim_adi = None
                st.rerun()

            onay = st.checkbox("Sayım verilerinin doğruluğunu onaylıyorum.")
            if st.button("🚀 STOKLARI GÜNCELLE VE ARŞİVLE", use_container_width=True, disabled=not onay):
                basarili, mesaj = _post_session_to_stock(st.session_state.aktif_sayim_adi)
                if basarili:
                    st.session_state.aktif_sayim_adi = None
                    st.success(mesaj)
                    _refresh_and_rerun()
                else:
                    st.error(mesaj)

    elif st.session_state.sayim_page == 'giris':
        st.subheader("📝 Sayım Girişi")
        if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
            go_sayim_menu()
            st.rerun()

        # ──────────────────────────────────────────────────────────
        # Tedarikçi Portalı (TDP API) - Sevkiyat Çekme Paneli
        # ──────────────────────────────────────────────────────────
        with st.expander("🌐 Tedarikçi Portalından Sevkiyat Çek", expanded=False):
            tedarikci_api.baglanti_durumu_goster()
            st.markdown("---")
            tdp_gun = st.number_input("Kaç günlük sevkiyat?", min_value=1, max_value=15, value=5, key="tdp_gun_sayim")
            tdp_sevk_no = st.text_input("Sevkiyat Belge No:", key="tdp_sevk_no_sayim")
            if st.button("🔄 ÇEK", key="tdp_cek_sayim"):
                basarili, mesaj, adet = tedarikci_api.sevkiyat_verisini_cek_ve_kaydet(tdp_sevk_no, tdp_gun)
                if basarili:
                    st.success(mesaj)
                else:
                    st.error(mesaj)
            if st.session_state.get('api_sevk_haritasi'):
                st.caption(f"📦 Hafızada {len(st.session_state.api_sevk_haritasi)} barkod kaydı var.")

        df_sayim_ana = _get_df("sayim")
        df_tamamlanan = _get_df("sayim_tamamlanan")

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

        bekleyenler = [o for o in sorted(list(set(tum_o))) if o not in tamamlanmis]

        if st.session_state.aktif_sayim_adi and st.session_state.aktif_sayim_adi not in bekleyenler:
            bekleyenler.insert(0, st.session_state.aktif_sayim_adi)

        if not bekleyenler:
            st.warning("⚠️ Bekleyen sayım oturumu bulunamadı. Lütfen önce oturum başlatın.")
        else:
            if st.session_state.aktif_sayim_adi not in bekleyenler:
                st.session_state.aktif_sayim_adi = bekleyenler[0]

            st.selectbox("📡 Çalışılacak Oturum:", bekleyenler, index=bekleyenler.index(st.session_state.aktif_sayim_adi))

            with st.container(border=True):
                s_adr = st.text_input("📍 Adres:").upper()

                # -----------------------------
                # 1. Adım: Tedarikçi Barkod Okutma Alanı (Okuyucu Girişi)
                # -----------------------------
                st.markdown("---")
                st.markdown("#### 🔌 Tedarikçi Barkodu Okutun")
                col_bar1, col_bar2 = st.columns([3, 1])
                with col_bar1:
                    sup_barcode_input = st.text_input(
                        "Tedarikçi Barkodu:",
                        key="supplier_barcode_key",
                        placeholder="Barkodu okutun ve Enter'a basın...",
                        label_visibility="collapsed"
                    )
                with col_bar2:
                    islem_yap = st.button("🔍 Getir / Çöz", use_container_width=True)

                # Barkod değiştiğinde veya butona tıklandığında tetikleme yap
                if sup_barcode_input and (islem_yap or st.session_state.get('last_handled_barcode') != sup_barcode_input):
                    st.session_state.last_handled_barcode = sup_barcode_input
                    handle_supplier_barcode(sup_barcode_input)

                st.markdown("---")
                st.markdown("#### 📦 Malzeme Bilgileri")

                # -----------------------------
                # KRİTİK ALAN: Tedarikçi Barkod / Parti No Bilgi Gösterimi ve Manuel Müdahale Alanı
                # -----------------------------
                s_barcode_val = st.text_input(
                    "🔌 Tedarikçi Barkodu / Parti No:",
                    value=st.session_state.def_s_barcode,
                    placeholder="Okutulan barkod burada görünür, elle de yazabilirsiniz..."
                )

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
                            "Tedarikçi_Barkodu": _norm_text(s_barcode_val)  # Barkodu da kayda iliştiriyoruz
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
                            eski_df = _get_df("sayim")
                            guncel_df = yeni_veri_df if eski_df.empty else pd.concat([eski_df, yeni_veri_df], ignore_index=True)
                            _save_df("sayim", _dedupe_exact(guncel_df))
                            st.session_state['gecici_sayim_listesi'] = []
                            st.success("Tüm veriler başarıyla kaydedildi!")
                            _refresh_and_rerun()

    elif st.session_state.sayim_page == 'rapor':
        st.subheader("📊 Fark Raporu")
        if st.button("⬅️ Sayım Menüsüne Dön", use_container_width=True):
            go_sayim_menu()
            st.rerun()

        df_sayim_ana = _get_df("sayim")
        df_snapshot_ana = _get_df("sayim_snapshot")
        df_urun = _get_df("Urun_Listesi")

        if not df_sayim_ana.empty:
            mevcut_oturumlar = df_sayim_ana["Oturum_Adi"].dropna().astype(str).unique().tolist()
            secilen_oturum = st.selectbox("Raporu Gösterilecek Oturum:", mevcut_oturumlar)

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
