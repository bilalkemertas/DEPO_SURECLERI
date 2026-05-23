import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani

def run(): # Fonksiyon adını 'run' olarak tuttum, app.py'da bunu çağır
    st.subheader("📝 Güncel Sayım Verisi Girişi")
    
    # Veri bağlantısı
    df_Stok = veritabani.get_internal_data("Stok")
    
    # Bellek kontrolü
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    
    # Sözlükleri oluştur (Seçim kutuları için)
    kod_list = sorted(df_Stok["Kod"].astype(str).unique().tolist())
    isim_list = sorted(df_Stok["İsim"].astype(str).unique().tolist())
    kod_to_isim = dict(zip(df_Stok["Kod"].astype(str), df_Stok["İsim"]))
    isim_to_kod = dict(zip(df_Stok["İsim"], df_Stok["Kod"].astype(str)))

    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        # 1. Adım: Ürün Seçimi (Key'ler session_state ile uyumlu)
        secilen_kod = col1.selectbox("📦 Ürün Kodu", [""] + kod_list, key="sayim_kod")
        secilen_isim = col2.selectbox("📝 Ürün Adı", [""] + isim_list, key="sayim_isim")

        # Otomatik Doldurma Mantığı (Keyler session_state'deki isimlerle aynı)
        if secilen_kod and secilen_kod != st.session_state.get("last_kod", ""):
            st.session_state.last_kod = secilen_kod
            # Selectbox değerini session_state üzerinden güncellemek için
            st.session_state.sayim_isim = kod_to_isim.get(secilen_kod, "")
            st.rerun()
            
        if secilen_isim and secilen_isim != st.session_state.get("last_isim", ""):
            st.session_state.last_isim = secilen_isim
            st.session_state.sayim_kod = isim_to_kod.get(secilen_isim, "")
            st.rerun()

        # Adres, Miktar ve Durum
        col_adr, col_mik, col_dur = st.columns(3)
        s_adres = col_adr.text_input("📍 Adres", key="s_adres").upper()
        s_miktar = col_mik.number_input("⚖️ Miktar", min_value=0.0, step=1.0)
        s_durum = col_dur.selectbox("🛠️ Durum", ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"])

        if st.button("➕ Listeye Ekle", use_container_width=True):
            if s_adres and (secilen_kod or secilen_isim):
                kayit = {
                    "Tarih": datetime.now().strftime("%d.%m.%Y"),
                    "Adres": s_adres,
                    "Kod": secilen_kod if secilen_kod else secilen_isim,
                    "Ürün Adı": secilen_isim if secilen_isim else kod_to_isim.get(secilen_kod),
                    "Miktar": s_miktar,
                    "Durum": s_durum
                }
                st.session_state['gecici_sayim_listesi'].append(kayit)
                st.success("Eklendi!")
            else:
                st.warning("Eksik bilgi girdin Patron!")

    # --- LİSTE VE ONAY ---
    if st.session_state['gecici_sayim_listesi']:
        df_gecici = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
        st.dataframe(df_gecici, use_container_width=True)
        
        if st.button("📤 DRIVE'A GÖNDER"):
            # veritabani.update_sheet("sayim", df_gecici)
            st.session_state['gecici_sayim_listesi'] = []
            st.rerun()
