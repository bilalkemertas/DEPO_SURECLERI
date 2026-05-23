import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime


# =========================
# NAV HELPERS
# =========================
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


# =========================
# MAIN
# =========================
def goster(conn=None):

    # ---------- SESSION INIT (FAST ACCESS) ----------
    ss = st.session_state

    ss.setdefault('gecici_sayim_listesi', [])
    ss.setdefault('aktif_sayim_adi', None)
    ss.setdefault('sayim_page', 'menu')
    ss.setdefault('delete_confirm', None)
    ss.setdefault('katalog_hafiza', [])
    ss.setdefault('sayim_df_cache', {})
    ss.setdefault('sayim_cache_initialized', False)

    # ---------- HELPERS (OPTIMIZED) ----------
    def _norm(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        return str(x).strip()

    def _upper(x):
        return _norm(x).upper()

    def _num(s):
        return pd.to_numeric(s, errors='coerce').fillna(0)

    def _df(name, force=False):
        cache = ss['sayim_df_cache']
        if not force and name in cache:
            return cache[name]

        try:
            df = veritabani.get_internal_data(name)
            df = pd.DataFrame() if df is None else (df if isinstance(df, pd.DataFrame) else pd.DataFrame(df))
        except Exception:
            df = pd.DataFrame()

        cache[name] = df
        return df

    def _save(name, df):
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        veritabani.update_data(name, df)
        ss['sayim_df_cache'][name] = df

    def _col(df, candidates):
        if df is None or df.empty:
            return None
        mp = {c.lower(): c for c in df.columns}
        for c in candidates:
            if c.lower() in mp:
                return mp[c.lower()]
        return None

    def _dedupe(df):
        return df.drop_duplicates().reset_index(drop=True) if not df.empty else df

    def _warm():
        if ss['sayim_cache_initialized']:
            return
        for t in ("sayim", "sayim_snapshot", "sayim_tamamlanan", "Stok", "Urun_Listesi"):
            _df(t)
        ss['sayim_cache_initialized'] = True

    _warm()

    # ---------- KATALOG (OPTIMIZED) ----------
    def get_katalog():
        if ss['katalog_hafiza']:
            return ss['katalog_hafiza']

        df = _df("Urun_Listesi")
        kod = _col(df, ["kod"])
        isim = _col(df, ["isim", "ad"])

        if df.empty or not kod or not isim:
            return []

        tmp = df[[kod, isim]].dropna().drop_duplicates()
        out = (tmp[kod].astype(str).str.strip() + " | " + tmp[isim].astype(str).str.strip()).tolist()

        ss['katalog_hafiza'] = out
        return out

    # ---------- SESSION HELPERS ----------
    def done_sessions():
        df = _df("sayim_tamamlanan")
        c = _col(df, ["Oturum_Adi"])
        return df[c].dropna().astype(str).unique().tolist() if c else []

    def all_sessions():
        out = []
        for t in ("sayim", "sayim_snapshot"):
            df = _df(t)
            c = _col(df, ["Oturum_Adi"])
            if c:
                out.extend(df[c].dropna().astype(str).tolist())
        return sorted(set(out))

    def open_sessions():
        done = set(done_sessions())
        return [x for x in all_sessions() if x not in done]

    # =========================
    # MENU
    # =========================
    if ss.sayim_page == 'menu':
        c1, c2, c3 = st.columns([1.5, 1.5, 4])

        with c1:
            if st.button("🏠 ANA MENÜ"):
                go_home()
                st.rerun()

        with c2:
            if st.button("⬅️ GERİ"):
                go_home()
                st.rerun()

        with c3:
            st.subheader("⚖️ Sayım Kontrol Merkezi")

        st.markdown("---")

        st.button("📁 OTURUM YÖNETİMİ", on_click=go_oturum)
        st.button("📝 SAYIM GİRİŞİ", on_click=go_giris)
        st.button("📊 FARK RAPORU", on_click=go_rapor)

        if ss.aktif_sayim_adi:
            st.success(f"Aktif: {ss.aktif_sayim_adi}")
        else:
            st.info("Açık oturum yok")

    # =========================
    # OTURUM
    # =========================
    elif ss.sayim_page == 'oturum':

        df = _df("sayim")
        snap = _df("sayim_snapshot")

        ot = _col(df, ["Oturum_Adi"])
        sp = _col(snap, ["Oturum_Adi"])

        sessions = set()
        if ot: sessions.update(df[ot].dropna().astype(str))
        if sp: sessions.update(snap[sp].dropna().astype(str))

        sessions = sorted(sessions)
        done = set(done_sessions())
        pending = [s for s in sessions if s not in done]

        st.subheader("Oturum Yönetimi")

        new = st.text_input("Yeni oturum")

        if st.button("Başlat") and new:
            ss.aktif_sayim_adi = new.upper()
            ss.gecici_sayim_listesi = []
            st.rerun()

        if pending:
            sec = st.selectbox("Bekleyen", pending)
            if st.button("Aktifleştir"):
                ss.aktif_sayim_adi = sec
                st.rerun()

    # =========================
    # GİRİŞ (FAST BUFFER LOGIC)
    # =========================
    elif ss.sayim_page == 'giris':

        open_s = open_sessions()
        if not open_s:
            st.warning("Açık oturum yok")
            return

        sec = st.selectbox("Oturum", open_s)

        if sec != ss.aktif_sayim_adi:
            ss.aktif_sayim_adi = sec
            ss.gecici_sayim_listesi = []
            st.rerun()

        st.text_input("Adres")

        katalog = get_katalog()
        urun = st.selectbox("Ürün", ["MANUEL"] + katalog)

        if st.button("EKLE"):
            ss.gecici_sayim_listesi.append({
                "Oturum_Adi": sec,
                "Miktar": 1
            })

        if st.button("KAYDET"):
            new = pd.DataFrame(ss.gecici_sayim_listesi)
            old = _df("sayim")

            merged = pd.concat([old, new], ignore_index=True)
            merged = _dedupe(merged)

            _save("sayim", merged)
            ss.gecici_sayim_listesi = []
            st.success("Kaydedildi")
            st.rerun()

    # =========================
    # RAPOR (OPTIMIZED GROUPBY)
    # =========================
    elif ss.sayim_page == 'rapor':

        sayim = _df("sayim")
        stok = _df("Stok")

        if sayim.empty:
            st.info("Veri yok")
            return

        sayim["Kod"] = sayim["Kod"].astype(str).str.upper()
        sayim["Adres"] = sayim["Adres"].astype(str).str.upper()

        s = sayim.groupby(["Adres", "Kod"], as_index=False)["Miktar"].sum()

        stok["Kod"] = stok["Kod"].astype(str).str.upper()
        stok["Adres"] = stok["Adres"].astype(str).str.upper()

        st_ = stok.groupby(["Adres", "Kod"], as_index=False)["Miktar"].sum()

        r = s.merge(st_, on=["Adres", "Kod"], how="outer", suffixes=("_SAYIM", "_STOK")).fillna(0)
        r["FARK"] = r["Miktar_SAYIM"] - r["Miktar_STOK"]

        st.dataframe(r, use_container_width=True)
