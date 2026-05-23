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

    ss = st.session_state

    ss.setdefault('gecici_sayim_listesi', [])
    ss.setdefault('aktif_sayim_adi', None)
    ss.setdefault('sayim_page', 'menu')
    ss.setdefault('delete_confirm', None)
    ss.setdefault('katalog_hafiza', [])
    ss.setdefault('sayim_df_cache', {})
    ss.setdefault('sayim_cache_initialized', False)

    # input reset state (NEW)
    ss.setdefault('ui_adres', "")
    ss.setdefault('ui_urun', "MANUEL")

    # ---------- HELPERS ----------
    def _norm(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        return str(x).strip()

    def _upper(x):
        return _norm(x).upper()

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
        st.subheader("⚖️ Sayım Kontrol Merkezi")

        st.button("📁 OTURUM YÖNETİMİ", on_click=go_oturum)
        st.button("📝 SAYIM GİRİŞİ", on_click=go_giris)
        st.button("📊 FARK RAPORU", on_click=go_rapor)

    # =========================
    # OTURUM (UPDATED - CLOSE SESSION ADDED)
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

        # ---------------- NEW: CLOSE SESSION ----------------
        st.markdown("---")
        close_candidates = [s for s in sessions if s not in done]

        if close_candidates:
            kapat_sec = st.selectbox("Kapatılacak Oturum", close_candidates)

            if st.button("OTURUMU KAPAT"):
                df_done = _df("sayim_tamamlanan")

                new_row = pd.DataFrame([{
                    "Oturum_Adi": kapat_sec,
                    "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "Durum": "KAPATILDI"
                }])

                df_done = pd.concat([df_done, new_row], ignore_index=True)
                df_done = _dedupe(df_done)

                _save("sayim_tamamlanan", df_done)

                if ss.aktif_sayim_adi == kapat_sec:
                    ss.aktif_sayim_adi = None

                st.success("Oturum kapatıldı")
                st.rerun()

    # =========================
    # GİRİŞ (UPDATED - RESET AFTER ADD)
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

        # -------- INPUTS (CONTROLLED STATE) --------
        ss.ui_adres = st.text_input("Adres", value=ss.ui_adres)
        katalog = ["MANUEL"]  # simplified
        ss.ui_urun = st.selectbox("Ürün", katalog, index=0)

        if st.button("EKLE"):
            ss.gecici_sayim_listesi.append({
                "Oturum_Adi": sec,
                "Adres": ss.ui_adres,
                "Urun": ss.ui_urun,
                "Miktar": 1
            })

            # ---------------- NEW: CLEAR INPUTS AFTER ADD ----------------
            ss.ui_adres = ""
            ss.ui_urun = "MANUEL"

            st.rerun()

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
    # RAPOR
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

        r = s.merge(st_, on=["Adres", "Kod"], how="outer").fillna(0)
        r["FARK"] = r["Miktar_x"] - r["Miktar_y"]

        st.dataframe(r, use_container_width=True)
