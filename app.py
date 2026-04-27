import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
<style>
#MainMenu, footer, header {display:none;}
.block-container { padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "home"

# --- 3. LOGIN ---
if not st.session_state.logged_in:
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            users = st.secrets["users"]
            if u.lower() in users and users[u.lower()] == p:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# --- 4. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 5. DATA OKUMA ---
@st.cache_data(ttl=5)
def read_data(sheet):
    try:
        return conn.read(spreadsheet=SHEET_ID, worksheet=sheet)
    except Exception as e:
        st.error(f"{sheet} okunamadı: {e}")
        return pd.DataFrame()

# --- 6. NET STOK HESAPLA ---
def hesapla_net_stok():
    df = read_data("Sayfa1")  # hareket tablosu

    if df.empty:
        return pd.DataFrame()

    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)

    giris = df[df['Tip'] == 'Giriş'].groupby('Kod')['Miktar'].sum()
    cikis = df[df['Tip'] == 'Çıkış'].groupby('Kod')['Miktar'].sum()

    net = (giris - cikis).fillna(0).reset_index()
    net.columns = ['Kod', 'Net Stok']

    return net.sort_values(by="Net Stok", ascending=False)

# --- 7. NAV ---
if st.session_state.page == "home":
    st.title("📦 Depo Paneli")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("📊 Stok", use_container_width=True):
            st.session_state.page = "stok"
            st.rerun()

    with c2:
        if st.button("📈 Rapor", use_container_width=True):
            st.session_state.page = "rapor"
            st.rerun()

# --- 8. STOK SAYFASI ---
elif st.session_state.page == "stok":
    if st.button("⬅️ Menü"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("📦 Net Stok Listesi")

    if st.button("🔄 Hesapla / Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    net_df = hesapla_net_stok()

    if not net_df.empty:
        st.dataframe(net_df, use_container_width=True)
    else:
        st.warning("Veri yok")

# --- 9. RAPOR ---
elif st.session_state.page == "rapor":
    if st.button("⬅️ Menü"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("📈 Hareketler")

    df = read_data("Sayfa1")

    if not df.empty:
        st.dataframe(df.iloc[::-1], use_container_width=True)
    else:
        st.warning("Veri yok")

# --- FOOTER ---
st.markdown("<hr><center>BRN Depo Sistemi</center>", unsafe_allow_html=True)
