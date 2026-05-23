import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani

def run():
    st.subheader("📝 Güncel Sayım Verisi Girişi")
    
    # 1. Veri Hazırlığı
    df_Stok = veritabani.get_internal_data("Stok")
    df_Stok["Kod"] = df_Stok["Kod"].astype(str).str.strip()
    df_Stok["İsim"] = df_Stok["İsim"].astype(str).str.strip()
    
    kod_list = sorted(df_Stok["Kod"].unique().tolist())
    isim_list = sorted(df_Stok["İsim"].unique().tolist())
    kod_to_isim = dict(zip(df_Stok["Kod"], df_Stok["İsim"]))
    isim_to_kod = dict(zip(df_Stok["İsim"], df_Stok["Kod"]))

    # 2. State Yönetimi
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []

    # 3. Arayüz
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        # Selectbox'larda key'leri session_state ile eşleştirdik
        # Kullanıcı seçim yapınca session_state güncellenir
        secilen_kod = col1.selectbox("📦 Ürün Kodu", [""] + kod_list, key="s_kod_key")
        secilen_isim = col2.selectbox("📝 Ürün Adı", [""] + isim_list, key="s_isim_key")

        # Mantık: Kod seçilirse isim dolar, isim seçilirse kod dolar
        if secilen_kod and secilen_kod != st.session_state.get("last_kod", ""):
            st.session_state.last_kod = secilen_kod
            st.session_state.s_isim_key = kod_to_isim.get(secilen_kod, "")
            st.rerun()
            
        if secilen_isim and secilen_isim != st.session_state.get("last_isim", ""):
            st.session_state.last_isim = secilen_isim
            st.session_state.s_kod_key = isim_to_kod.get(secilen_isim, "")
            st.rerun()

        col_adr, col_mik, col_dur = st.columns(3)
        s_adres = col_adr.text_input("📍 Adres", key="s_adr_key").upper()
        s_miktar = col_mik.number_input("⚖️ Miktar", min_value=0.0, step=1.0)
        s_durum = col_dur.selectbox("🛠️ Durum", ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"])

        if st.button("➕ Listeye Ekle", use_container_width=True):
            if s_adres and (secilen_kod or secilen_isim):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": datetime.now().strftime("%d.%m.%Y"),
                    "Adres": s_adres,
                    "Kod": secilen_kod if secilen_kod else isim_to_kod.get(secilen_isim),
                    "Ürün Adı": secilen_isim if secilen_isim else kod_to_isim.get(secilen_kod),
                    "Miktar": s_miktar,
                    "Durum": s_durum
                })
                st.success("Eklendi!")
                # Listeye ekledikten sonra kutuları temizle (Opsiyonel)
            else:
                st.warning("Adres ve Ürün bilgisi şart!")

    # 4. Liste
    if st.session_state['gecici_sayim_listesi']:
        st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
        if st.button("📤 DRIVE'A GÖNDER"):
            st.session_state['gecici_sayim_listesi'] = []
            st.rerun()
