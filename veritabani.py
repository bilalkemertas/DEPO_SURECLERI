import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ════════════════════════════════════════════════════════════════════
# 🔗 GOOGLE SHEETS BAĞLANTISI
# ════════════════════════════════════════════════════════════════════

def get_gsheets_connection():
    """Google Sheets bağlantısı oluştur"""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn
    except Exception as e:
        st.error(f"❌ Google Sheets bağlantı hatası: {e}")
        return None


def get_internal_data(sheet_name):
    """
    Google Sheets'ten veri oku
    Args:
        sheet_name: Çalışma sayfası adı (Is_Emirleri, Stok, Hareketler, vb.)
    Returns:
        pandas DataFrame veya None
    """
    try:
        conn = get_gsheets_connection()
        if conn is None:
            return None

        # Boş veri işleme
        try:
            df = conn.read(worksheet=sheet_name)
            if df is None or df.empty:
                return pd.DataFrame()
            return df
        except Exception as sheet_error:
            st.warning(f"⚠️ '{sheet_name}' sayfası okunamadı: {sheet_error}")
            return pd.DataFrame()
    except Exception as error:
        st.error(f"❌ Veri okuma hatası ({sheet_name}): {error}")
        return pd.DataFrame()


def update_data(sheet_name, dataframe):
    """
    Google Sheets'e veri yaz
    Args:
        sheet_name: Çalışma sayfası adı
        dataframe: Yazılacak pandas DataFrame
    Returns:
        bool: Başarılı/başarısız
    """
    try:
        if dataframe is None or dataframe.empty:
            st.warning(f"⚠️ '{sheet_name}' için boş DataFrame gönderildi. İşlem atlanıyor.")
            return False

        conn = get_gsheets_connection()
        if conn is None:
            return False

        # Veri temizliği
        df_clean = dataframe.copy()
        df_clean = df_clean.fillna("")  # NaN değerleri boş string'e çevir

        # Google Sheets'e yaz
        conn.update(
            worksheet=sheet_name,
            data=df_clean
        )
        return True
    except Exception as error:
        st.error(f"❌ Veri yazma hatası ({sheet_name}): {error}")
        return False


def delete_sheet_content(sheet_name):
    """
    Çalışma sayfasının içeriğini temizle
    Args:
        sheet_name: Çalışma sayfası adı
    Returns:
        bool: Başarılı/başarısız
    """
    try:
        conn = get_gsheets_connection()
        if conn is None:
            return False

        empty_df = pd.DataFrame()
        conn.update(worksheet=sheet_name, data=empty_df)
        return True
    except Exception as error:
        st.error(f"❌ Sayfayı temizle hatası ({sheet_name}): {error}")
        return False


def append_data(sheet_name, dataframe):
    """
    Google Sheets'e veri ekle (sonuna yazma)
    Args:
        sheet_name: Çalışma sayfası adı
        dataframe: Eklenecek pandas DataFrame
    Returns:
        bool: Başarılı/başarısız
    """
    try:
        if dataframe is None or dataframe.empty:
            st.warning(f"⚠️ '{sheet_name}' için boş DataFrame gönderildi.")
            return False

        # Mevcut verileri oku
        existing_df = get_internal_data(sheet_name)

        if existing_df is None or existing_df.empty:
            # Hiç veri yoksa direkt yaz
            return update_data(sheet_name, dataframe)
        else:
            # Verileri birleştir
            combined_df = pd.concat([existing_df, dataframe], ignore_index=True)
            return update_data(sheet_name, combined_df)
    except Exception as error:
        st.error(f"❌ Veri ekleme hatası ({sheet_name}): {error}")
        return False


def get_sheet_stats(sheet_name):
    """
    Çalışma sayfasının istatistiklerini al
    Args:
        sheet_name: Çalışma sayfası adı
    Returns:
        dict: Satır sayısı, sütun sayısı, vb.
    """
    try:
        df = get_internal_data(sheet_name)
        if df is None or df.empty:
            return {"rows": 0, "columns": 0, "status": "empty"}
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "status": "success",
            "column_names": df.columns.tolist()
        }
    except Exception as error:
        return {"status": "error", "message": str(error)}


def validate_required_sheets():
    """
    Gerekli çalışma sayfalarının varlığını kontrol et
    Returns:
        dict: Kontrol sonuçları
    """
    required_sheets = ["Is_Emirleri", "Stok", "Hareketler"]
    results = {}
    for sheet in required_sheets:
        stats = get_sheet_stats(sheet)
        results[sheet] = stats
    return results


# ════════════════════════════════════════════════════════════════════
# 📍 DEPO ADRES LİSTESİ (öneri/autocomplete için) - YENİ
# ════════════════════════════════════════════════════════════════════
# Bu, Google Sheets'ten değil, repo köküne konan Depo_Adresler.xlsx
# dosyasından (GitHub) okunur - adres listesi sık değişmediği için
# Google Sheets'e taşımaya gerek yok, statik dosya + önbellek yeterli.
# modul_sayim.py, teslim_alma.py, modul_stok.py hepsi bu fonksiyonu
# kullanır - tek kaynak, tek bakım noktası.

@st.cache_data(ttl=3600, show_spinner=False)
def _adres_dosyasi_oku(dosya_yolu):
    try:
        return pd.read_excel(dosya_yolu)
    except Exception:
        return pd.DataFrame()


def get_adres_listesi(dosya_yolu="Depo_Adresler.xlsx"):
    """
    Depo_Adresler.xlsx dosyasından adres kodlarını okuyup session_state'te
    önbelleğe alır (süre sınırı yok, sadece uygulama yeniden başladığında
    veya önbellek elle temizlendiğinde yenilenir). Personel adres kutusuna
    yazmaya başlayınca bu liste üzerinden öneri/arama yapılır.
    """
    if st.session_state.get('adres_hafiza'):
        return st.session_state['adres_hafiza']

    adres_listesi = []
    df = _adres_dosyasi_oku(dosya_yolu)
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]
        kod_col = "Kod" if "Kod" in df.columns else ("Raf Kodu" if "Raf Kodu" in df.columns else df.columns[0])
        kodlar = df[kod_col].astype(str).str.strip()
        adres_listesi = sorted(list(set([k.upper() for k in kodlar if k and k.lower() != "nan"])))

    st.session_state['adres_hafiza'] = adres_listesi
    return adres_listesi
