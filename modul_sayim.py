import streamlit as st
import pandas as pd
import veritabani
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
    ss.setdefault('katalog_hafiza', [])
    ss.setdefault('sayim_df_cache', {})
    ss.setdefault('sayim_cache_initialized', False)

    # ---------- HELPERS ----------
    def _norm(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        return str(x).strip()

    def _upper(x):
        return _norm(x).upper()

    def _df(name):
        cache = ss['sayim_df_cache']
        if name in cache:
            return cache[name]
        try:
            df = veritabani.get_internal_data(name)
            df = pd.DataFrame() if df is None else (df if isinstance(df, pd.DataFrame) else pd.DataFrame(df))
        except:
            df = pd.DataFrame()
        cache[name] = df
        return df

    def _save(name, df):
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

    # ---------- KATALOG ----------
    def get_katalog():
        if ss['katalog_hafiza']:
            return ss['katalog_hafiza']

        df = _df("Urun_Listesi")
        k = _col(df, ["kod"])
        i = _col(df, ["isim", "ad"])

        if df.empty or not k or not i:
            return []

        out = (df[k].astype(str).str.strip() + " | " + df[i].astype(str).str.strip()).drop_duplicates().tolist()
        ss['katalog_hafiza'] = out
        return out

    # ---------- SESSION ----------
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
    # OTURUM (KAPAT EKLENDİ)
    # =========================
    elif ss.sayim_page == 'oturum':

        df = _df("sayim")

        col = _col(df, ["Oturum_Adi"])
        sessions = sorted(df[col].dropna().astype(str).unique().tolist()) if col else []

        st.subheader("Oturum Yönetimi")

        sec = st.selectbox("Oturum Seç", sessions)

        # ---- KAPAT OTURUM EKLENDİ ----
        if st.button("🛑 OTURUMU KAPAT"):
            if sec:
                done_df = _df("sayim_tamamlanan")

                new_row = pd.DataFrame([{
                    "Oturum_Adi": sec,
                    "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "Durum": "KAPATILDI"
                }])

                merged = pd.concat([done_df, new_row], ignore_index=True)
                merged = _dedupe(merged)

                _save("sayim_tamamlanan", merged)

                st.success("Oturum kapatıldı")
                st.rerun()

    # =========================
    # GİRİŞ (INPUT RESET EKLENDİ)
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

        # ---- KEY TANIMI (RESET İÇİN) ----
        addr_key = "addr"
        kod_key = "kod"
        isim_key = "isim"

        st.text_input("Adres", key=addr_key)

        katalog = get_katalog()
        urun = st.selectbox("Ürün", ["MANUEL"] + katalog)

        if st.button("EKLE"):

            ss.gecici_sayim_listesi.append({
                "Oturum_Adi": sec,
                "Adres": ss.get(addr_key, ""),
                "Miktar": 1
            })

            # ---- SADECE ADRES KALSIN DİĞERLERİ SİL ----
            ss[kod_key] = ""
            ss[isim_key] = ""

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

        sayim["Kod"] = sayim.get("Kod", "").astype(str).str.upper()
        sayim["Adres"] = sayim.get("Adres", "").astype(str).str.upper()

        s = sayim.groupby(["Adres", "Kod"], as_index=False)["Miktar"].sum()
        st_ = stok.groupby(["Adres", "Kod"], as_index=False)["Miktar"].sum()

        r = s.merge(st_, on=["Adres", "Kod"], how="outer", suffixes=("_SAYIM", "_STOK")).fillna(0)
        r["FARK"] = r["Miktar_SAYIM"] - r["Miktar_STOK"]

        st.dataframe(r, use_container_width=True)
