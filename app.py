import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
<style>
#MainMenu, footer, header, .stDeployButton {display: none !important;}
.block-container { padding: 0.5rem !important; }
input { font-size: 16px !important; }
.stButton>button { height: 3em; font-size: 16px !important; }
</style>
""", unsafe_allow_html=True)

# --- SESSION ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "page" not in st.session_state: st.session_state.page = "home"
if "gecici_sayim_listesi" not in st.session_state: st.session_state.gecici_sayim_listesi = []
if "delete_confirm" not in st.session_state: st.session_state.delete_confirm = None

# --- LOGIN ---
if not st.session_state.logged_in:
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def read(ws):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=ws)
    except:
        return pd.DataFrame()

def kod_map():
    df = read("Stok")
    if df.empty:
        return {}
    return dict(zip(df["Kod"].astype(str), df["İsim"].astype(str)))

# --- HOME ---
if st.session_state.page == "home":
    st.title("📦 Depo Kontrol")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("📊 STOK"):
            st.session_state.page = "stok"; st.rerun()
        if st.button("🏭 ÜRETİM"):
            st.session_state.page = "uretim"; st.rerun()

    with c2:
        if st.button("📝 SAYIM"):
            st.session_state.page = "sayim"; st.rerun()
        if st.button("📈 RAPOR"):
            st.session_state.page = "rapor"; st.rerun()

# --- STOK ---
elif st.session_state.page == "stok":
    if st.button("⬅️"):
        st.session_state.page = "home"; st.rerun()

    st.subheader("Stok Giriş / Çıkış")

    km = kod_map()

    islem = st.selectbox("İşlem", ["Giriş", "Çıkış"])
    kod = st.selectbox("Kod", [""] + list(km.keys()))
    miktar = st.number_input("Miktar", 0.0)
    adres = st.text_input("Adres")

    if st.button("Kaydet"):
        if kod:
            yeni = pd.DataFrame([{
                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Kod": kod,
                "İşlem": islem,
                "Miktar": miktar,
                "Adres": adres
            }])

            df = read("Sayfa1")
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1",
                        data=pd.concat([df, yeni], ignore_index=True))
            st.success("Kaydedildi")
            st.rerun()

# --- SAYIM ---
elif st.session_state.page == "sayim":
    if st.button("⬅️"):
        st.session_state.page = "home"; st.rerun()

    st.subheader("Sayım")

    km = kod_map()

    adr = st.text_input("Adres")
    kod = st.selectbox("Kod", [""] + list(km.keys()))
    mik = st.number_input("Miktar", 0.0)

    if st.button("Listeye Ekle"):
        st.session_state.gecici_sayim_listesi.append({
            "Tarih": datetime.now().strftime("%Y-%m-%d"),
            "Kod": kod,
            "Adres": adr,
            "Miktar": mik
        })

    if st.session_state.gecici_sayim_listesi:
        st.write(st.session_state.gecici_sayim_listesi)

        if st.button("Kaydet"):
            df = read("sayim")
            conn.update(spreadsheet=SHEET_URL, worksheet="sayim",
                        data=pd.concat([df, pd.DataFrame(st.session_state.gecici_sayim_listesi)], ignore_index=True))
            st.session_state.gecici_sayim_listesi = []
            st.success("Kaydedildi")
            st.rerun()

# --- ÜRETİM ---
elif st.session_state.page == "uretim":
    if st.button("⬅️"):
        st.session_state.page = "home"; st.rerun()

    st.subheader("Net Stok")

    df = read("Sayfa1")

    if not df.empty:
        df["Miktar"] = pd.to_numeric(df["Miktar"], errors="coerce").fillna(0)

        giris = df[df["İşlem"] == "Giriş"].groupby("Kod")["Miktar"].sum()
        cikis = df[df["İşlem"] == "Çıkış"].groupby("Kod")["Miktar"].sum()

        net = (giris - cikis).fillna(0).reset_index()
        net.columns = ["Kod", "Net"]

        st.dataframe(net)

    if st.button("Yenile"):
        st.cache_data.clear()
        st.rerun()

# --- RAPOR ---
elif st.session_state.page == "rapor":
    if st.button("⬅️"):
        st.session_state.page = "home"; st.rerun()

    t1, t2 = st.tabs(["Net Stok", "Hareketler"])

    with t1:
        df = read("Sayfa1")
        if not df.empty:
            df["Miktar"] = pd.to_numeric(df["Miktar"], errors="coerce").fillna(0)
            giris = df[df["İşlem"] == "Giriş"].groupby("Kod")["Miktar"].sum()
            cikis = df[df["İşlem"] == "Çıkış"].groupby("Kod")["Miktar"].sum()
            net = (giris - cikis).fillna(0).reset_index()
            net.columns = ["Kod", "Net"]
            st.dataframe(net)

    with t2:
        st.dataframe(read("Sayfa1").iloc[::-1])
