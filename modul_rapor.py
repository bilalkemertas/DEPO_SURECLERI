import streamlit as st
import veritabani

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Stok Hareketleri")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        katalog = veritabani.get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog)
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            s_lot = st.text_input("🔢 Parti/Lot No:").upper()
        with c2:
            s_adr = st.text_input("📍 Adres:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
        s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            st.success("Kayıt Başarılı!")
