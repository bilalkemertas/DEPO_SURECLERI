import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime


def go_home():
    st.session_state.page = 'home'
    st.session_state.sayim_page = 'menu'


def go_sayim_menu():
    st.session_state.sayim_page = 'menu'


def go_oturum():
    st.session_state.sayim_page = 'oturum'


def go_giris():
    st.session_state.sayim_page = 'giris'


def go_rapor():
    st.session_state.sayim_page = 'rapor'


def goster(conn=None):
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

    # ---- EKLENDİ: EKLE sonrası input temizliği için state ----
    if 'giris_form_reset' not in st.session_state:
        st.session_state['giris_form_reset'] = False

    # -----------------------------
    # HELPERS
    # -----------------------------
    def _norm_text(val):
        if pd.isna(val):
            return ""
        return str(val).strip()

    def _upper_text(val):
        return _norm_text(val).upper()

    def _to_num(series):
        return pd.to_numeric(series, errors='coerce').fillna(0)

    def _get_df(table_name):
        try:
            df = veritabani.get_internal_data(table_name)
            if df is None:
                return pd.DataFrame()
            if not isinstance(df, pd.DataFrame):
                return pd.DataFrame(df)
            return df.copy()
        except Exception:
            return pd.DataFrame()

    def _save_df(table_name, df):
        if df is None:
            df = pd.DataFrame()
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        veritabani.update_data(table_name, df)

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
        if "Tarih" not in df_stok.columns:
            df_stok["Tarih"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        return df_stok

    def _dedupe_exact(df):
        if df.empty:
            return df
        return df.drop_duplicates().reset_index(drop=True)

    # =========================
    # MENU
    # =========================
    if st.session_state.sayim_page == 'menu':
        st.subheader("⚖️ Sayım Kontrol Merkezi")

    # =========================
    # OTURUM
    # =========================
    elif st.session_state.sayim_page == 'oturum':

        df = _get_df("sayim")
        snap = _get_df("sayim_snapshot")

        oturumlar = _session_all_sessions()
        done = set(_session_completed_sessions())
        pending = [s for s in oturumlar if s not in done]

        st.subheader("Oturum Yönetimi")

        # ---------------- EKLENDİ: KAPATILACAK OTURUM SEÇ ----------------
        if oturumlar:
            kapat_sec = st.selectbox("Kapatılacak Oturum Seç", oturumlar)
            if st.button("OTURUMU KAPAT"):
                if st.session_state.aktif_sayim_adi == kapat_sec:
                    st.session_state.aktif_sayim_adi = None
                st.success("Oturum kapatıldı (aktiflik kaldırıldı).")

        # mevcut akış bozulmadı
        new = st.text_input("Yeni oturum")

        if st.button("Başlat") and new:
            st.session_state.aktif_sayim_adi = new.upper()
            st.session_state.gecici_sayim_listesi = []
            st.rerun()

        if pending:
            sec = st.selectbox("Bekleyen", pending)
            if st.button("Aktifleştir"):
                st.session_state.aktif_sayim_adi = sec
                st.rerun()

    # =========================
    # GİRİŞ
    # =========================
    elif st.session_state.sayim_page == 'giris':

        open_s = _open_sessions()
        if not open_s:
            st.warning("Açık oturum yok")
            return

        sec = st.selectbox("Oturum", open_s)

        if sec != st.session_state.aktif_sayim_adi:
            st.session_state.aktif_sayim_adi = sec
            st.session_state.gecici_sayim_listesi = []
            st.rerun()

        # ---------------- EKLENDİ: FORM STATE ----------------
        if st.session_state.get('giris_form_reset'):
            adr_default = ""
            kod_default = ""
            isim_default = ""
            st.session_state['giris_form_reset'] = False
        else:
            adr_default = ""
            kod_default = ""
            isim_default = ""

        s_adr = st.text_input("Adres", value=adr_default).upper()

        katalog = get_dinamik_katalog()
        secim = st.selectbox("Ürün", ["+ MANUEL"] + katalog)

        if secim != "+ MANUEL":
            p = secim.split(" | ", 1)
            s_kod = st.text_input("Kod", value=p[0], disabled=True)
            s_isim = st.text_input("İsim", value=p[1] if len(p) > 1 else "", disabled=True)
        else:
            s_kod = st.text_input("Kod").upper()
            s_isim = st.text_input("İsim").upper()

        s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
        s_durum = st.selectbox("Durum", ["Kullanılabilir", "Hasarlı", "İncelemede"])

        if st.button("EKLE"):
            st.session_state.gecici_sayim_listesi.append({
                "Oturum_Adi": sec,
                "Adres": s_adr,
                "Kod": s_kod,
                "İsim": s_isim,
                "Miktar": s_mik,
                "Durum": s_durum,
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            })

            # ---------------- EKLENDİ: SADECE ADRES KALSIN ----------------
            st.session_state['giris_form_reset'] = True
            st.rerun()

        if st.button("KAYDET"):
            df = _dedupe_exact(pd.DataFrame(st.session_state.gecici_sayim_listesi))
            eski = _get_df("sayim")
            _save_df("sayim", pd.concat([eski, df], ignore_index=True))
            st.session_state.gecici_sayim_listesi = []
            st.rerun()
