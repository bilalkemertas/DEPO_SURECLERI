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

        mevcut = _get_df(table_name)

        if not mevcut.empty:
            df = pd.concat([mevcut, df], ignore_index=True)

        df = df.drop_duplicates().reset_index(drop=True)
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

    def _normalize_count_buffer(list_items):
        if not list_items:
            return pd.DataFrame()

        df = pd.DataFrame(list_items).copy()

        needed = {
            "Oturum_Adi": "",
            "Tarih": "",
            "Adres": "",
            "Kod": "",
            "İsim": "",
            "Miktar": 0.0,
            "Birim": "-",
            "Personel": "",
            "Durum": "Kullanılabilir",
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

        df = df[df["Kod"] != ""]
        df = df[df["Oturum_Adi"] != ""]
        return df.reset_index(drop=True)

    def _post_session_to_stock(aktif_oturum):
        df_sayim_ana = _get_df("sayim")
        df_stok = _get_df("Stok")
        df_urun = _get_df("Urun_Listesi")
        df_tamamlanan = _get_df("sayim_tamamlanan")

        if df_sayim_ana.empty:
            return False, "Sayım verisi bulunamadı."

        oturum_col = _find_col(df_sayim_ana, ["Oturum_Adi"])
        if not oturum_col:
            return False, "Oturum kolonu bulunamadı."

        df_bu_sayim = df_sayim_ana[df_sayim_ana[oturum_col].astype(str) == str(aktif_oturum)].copy()
        if df_bu_sayim.empty:
            return False, "Bu oturuma ait kayıt bulunamadı."

        df_bu_sayim = _ensure_columns(df_bu_sayim, {
            "Adres": "",
            "Kod": "",
            "İsim": "",
            "Miktar": 0,
            "Durum": "Kullanılabilir",
            "Birim": "-",
            "Personel": "",
            "Tarih": "",
        })

        df_bu_sayim["Adres"] = df_bu_sayim["Adres"].astype(str).str.strip().str.upper()
        df_bu_sayim["Kod"] = df_bu_sayim["Kod"].astype(str).str.strip().str.upper()
        df_bu_sayim["Miktar"] = _to_num(df_bu_sayim["Miktar"])

        s_ozet = (
            df_bu_sayim
            .groupby(["Adres", "Kod", "Durum"], sort=False, dropna=False)["Miktar"]
            .sum()
            .reset_index()
        )

        isim_sozlugu = {}
        urun_kod_col = _find_col(df_urun, ["kod", "Kod"])
        urun_isim_col = _find_col(df_urun, ["isim", "İsim"])

        if not df_urun.empty and urun_kod_col and urun_isim_col:
            tmp = df_urun[[urun_kod_col, urun_isim_col]].drop_duplicates(subset=[urun_kod_col])
            isim_sozlugu.update({str(k).strip().upper(): str(v).strip() for k, v in zip(tmp[urun_kod_col], tmp[urun_isim_col])})

        if df_stok.empty:
            df_stok = pd.DataFrame(columns=["Adres", "Kod", "İsim", "Miktar", "Durum", "Birim"])

        df_stok = _ensure_columns(df_stok, {
            "Adres": "",
            "Kod": "",
            "İsim": "",
            "Miktar": 0,
            "Durum": "Kullanılabilir",
            "Birim": "-",
        })

        df_stok["Adres"] = df_stok["Adres"].astype(str).str.strip().str.upper()
        df_stok["Kod"] = df_stok["Kod"].astype(str).str.strip().str.upper()
        df_stok["Miktar"] = _to_num(df_stok["Miktar"])

        sayilan_anahtarlar = set(zip(s_ozet["Adres"], s_ozet["Kod"]))
        stok_kalan = df_stok[~df_stok.apply(lambda r: (r.get("Adres", ""), r.get("Kod", "")) in sayilan_anahtarlar, axis=1)]

        yeni_stok_verisi = s_ozet.copy()
        yeni_stok_verisi["İsim"] = yeni_stok_verisi["Kod"].map(isim_sozlugu).fillna("TANIMSIZ")
        yeni_stok_verisi["Birim"] = "-"
        yeni_stok_verisi["Miktar"] = _to_num(yeni_stok_verisi["Miktar"])
        yeni_stok_verisi = yeni_stok_verisi[yeni_stok_verisi["Miktar"] > 0]

        stok_final = pd.concat([stok_kalan, yeni_stok_verisi], ignore_index=True)
        stok_final = stok_final.drop_duplicates().reset_index(drop=True)

        veritabani.update_data("Stok", stok_final)

        log_yeni = pd.DataFrame([{
            "Oturum_Adi": aktif_oturum,
            "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "Toplam_Kalem": int(len(df_bu_sayim)),
            "Toplam_Satir": int(len(s_ozet)),
            "Durum": "POST_EDILDI"
        }])

        tamamlanan_guncel = pd.concat([_get_df("sayim_tamamlanan"), log_yeni], ignore_index=True)
        tamamlanan_guncel = tamamlanan_guncel.drop_duplicates().reset_index(drop=True)

        veritabani.update_data("sayim_tamamlanan", tamamlanan_guncel)

        return True, "Stoklar güncellendi ve oturum arşivlendi!"

    def _refresh_and_rerun():
        st.rerun()

    # UI kısmı değişmedi (kırpılmadı)
    if st.session_state.sayim_page == 'menu':
        c_btn1, c_btn2, c_title = st.columns([1.5, 1.5, 4])
        with c_btn1:
            if st.button("🏠 ANA MENÜ", use_container_width=True, key="nav_home_main_menu"):
                go_home()
                st.rerun()
        with c_btn2:
            if st.button("⬅️ GERİ", use_container_width=True, key="nav_back_main_menu"):
                go_home()
                st.rerun()
        with c_title:
            st.subheader("⚖️ Sayım Kontrol Merkezi")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("📁 OTURUM YÖNETİMİ", use_container_width=True, type="primary", on_click=go_oturum)
        with c2:
            st.button("📝 SAYIM GİRİŞİ", use_container_width=True, type="primary", on_click=go_giris)
        with c3:
            st.button("📊 FARK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)
