import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- AYAR ---
st.set_page_config(page_title="Depo Pro", layout="wide")

# --- SESSION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "page" not in st.session_state:
    st.session_state.page = "home"
if "sayim_list" not in st.session_state:
    st.session_state.sayim_list = []
if "uretim_list" not in st.session_state:
    st.session_state.uretim_list = []

# --- LOGIN ---
if not st.session_state.logged_in:
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            users = st.secrets["users"]
            if u.lower() in users and users[u.lower()] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# --- BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_ID = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=5)
def read_data(sheet):
    try:
        return conn.read(spreadsheet=SHEET_ID, worksheet=sheet)
    except Exception as e:
        st.error(f"{sheet} okunamadı: {e}")
        return pd.DataFrame()

# --- NET STOK ---
def hesapla_net_stok():
    df = read_data("Sayfa1")
    if df.empty:
        return pd.DataFrame()

    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)

    giris = df[df['Tip'] == 'Giriş'].groupby('Kod')['Miktar'].sum()
    cikis = df[df['Tip'] == 'Çıkış'].groupby('Kod')['Miktar'].sum()

    net = (giris - cikis).fillna(0).reset_index()
    net.columns = ['Kod', 'Net Stok']
    return net

# --- ANA MENÜ ---
if st.session_state.page == "home":
    st.title("📦 Depo Paneli")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("📊 Stok"):
            st.session_state.page = "stok"
            st.rerun()

        if st.button("📝 Sayım"):
            st.session_state.page = "sayim"
            st.rerun()

    with c2:
        if st.button("🏭 Üretim Hazırlık"):
            st.session_state.page = "uretim"
            st.rerun()

        if st.button("📈 Rapor"):
            st.session_state.page = "rapor"
            st.rerun()

# --- STOK ---
elif st.session_state.page == "stok":
    if st.button("⬅️ Menü"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("📦 Net Stok")

    if st.button("🔄 Yenile"):
        st.cache_data.clear()
        st.rerun()

    df = hesapla_net_stok()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Veri yok")

# --- SAYIM ---
elif st.session_state.page == "sayim":
    if st.button("⬅️ Menü"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("📝 Sayım")

    kod = st.text_input("Kod")
    miktar = st.number_input("Miktar", min_value=0.0)
    adres = st.text_input("Adres")

    if st.button("➕ Ekle"):
        if kod and adres:
            st.session_state.sayim_list.append({
                "Tarih": datetime.now().strftime("%Y-%m-%d"),
                "Kod": kod,
                "Miktar": miktar,
                "Adres": adres,
                "Personel": st.session_state.user
            })
            st.success("Eklendi")

    if st.session_state.sayim_list:
        st.dataframe(pd.DataFrame(st.session_state.sayim_list))

        if st.button("📤 Kaydet"):
            df_old = read_data("sayim")
            new_df = pd.concat([df_old, pd.DataFrame(st.session_state.sayim_list)], ignore_index=True)

            conn.update(spreadsheet=SHEET_ID, worksheet="sayim", data=new_df)
            st.session_state.sayim_list = []
            st.success("Kaydedildi")
            st.rerun()

# --- ÜRETİM HAZIRLIK ---
elif st.session_state.page == "uretim":
    if st.button("⬅️ Menü"):
        st.session_state.page = "home"
        st.rerun()

    st.subheader("🏭 Üretim Hazırlık")

    net_stok = hesapla_net_stok()

    kod = st.text_input("Ürün Kodu")
    miktar = st.number_input("Kullanılacak Miktar", min_value=0.0)

    mevcut = 0
    if not net_stok.empty and kod in net_stok['Kod'].values:
        mevcut = net_stok[net_stok['Kod'] == kod]['Net Stok'].values[0]

    st.info(f"Mevcut Stok: {mevcut}")

    if st.button("➕ Listeye Ekle"):
        if miktar > mevcut:
            st.error("Yetersiz stok!")
        else:
            st.session_state.uretim_list.append({
                "Kod": kod,
                "Miktar": miktar,
                "Tarih": datetime.now().strftime("%Y-%m-%d")
            })
            st.success("Eklendi")

    if st.session_state.uretim_list:
        st.write("### Hazırlık Listesi")
        st.dataframe(pd.DataFrame(st.session_state.uretim_list))

        if st.button("🚀 Üretime Gönder"):
            df_old = read_data("Sayfa1")

            cikislar = pd.DataFrame(st.session_state.uretim_list)
            cikislar["Tip"] = "Çıkış"

            new_df = pd.concat([df_old, cikislar], ignore_index=True)

            conn.update(spreadsheet=SHEET_ID, worksheet="Sayfa1", data=new_df)

            st.session_state.uretim_list = []
            st.success("Üretim düşüldü (stoktan çıktı)")
            st.rerun()

# --- RAPOR ---
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
st.markdown("<hr><center>Depo Sistemi</center>", unsafe_allow_html=True)
