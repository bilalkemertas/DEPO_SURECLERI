import streamlit as st
import pandas as pd
from datetime import datetime

def run():
    st.subheader("📝 Güncel Sayım Verisi Girişi")
    
    # Veri bağlantısı (Ana uygulamadan veritabanı değişkenlerini aldığını varsayıyorum)
    # Eğer veritabani modülünü kullanıyorsan import etmen gerekebilir
    import veritabani
    df_Stok = veritabani.get_internal_data("Stok")
    
    # Veri Temizliği (Akıllı Eşleşme İçin)
    df_Stok["Kod"] = df_Stok["Kod"].astype(str).str.strip()
    df_Stok["İsim"] = df_Stok["İsim"].astype(str).str.strip()
    
    # Seçim Listeleri
    kod_list = df_Stok["Kod"].tolist()
    isim_list = df_Stok["İsim"].tolist()
    
    # Ürün eşleşme sözlükleri
    kod_to_isim = dict(zip(df_Stok["Kod"], df_Stok["İsim"]))
    isim_to_kod = dict(zip(df_Stok["İsim"], df_Stok["Kod"]))

    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        # 1. Adım: Ürün Seçimi (Akıllı Arama)
        # Personel ister koddan seçer, ister isimden
        secilen_kod = col1.selectbox("📦 Ürün Kodu Seç", [""] + kod_list, key="sayim_kod")
        secilen_isim = col2.selectbox("📝 Ürün Adı Seç", [""] + isim_list, key="sayim_isim")

        # Otomatik Doldurma Mantığı
        if secilen_kod and secilen_kod != st.session_state.get("last_kod", ""):
            st.session_state.last_kod = secilen_kod
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
                    "Kod": secilen_kod if secilen_kod else secilen_isim, # İkisinden biri dolu
                    "Ürün Adı": secilen_isim if secilen_isim else kod_to_isim.get(secilen_kod),
                    "Miktar": s_miktar,
                    "Durum": s_durum
                }
                st.session_state['gecici_sayim_listesi'].append(kayit)
                st.success("Eklendi!")
            else:
                st.warning("Eksik bilgi girdin Patron!")

    # --- LİSTE VE ONAY ---
    if 'gecici_sayim_listesi' in st.session_state and st.session_state['gecici_sayim_listesi']:
        df_gecici = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
        st.dataframe(df_gecici, use_container_width=True)
        
        if st.button("📤 DRIVE'A GÖNDER"):
            # veritabani.update_sheet("sayim", df_gecici)
            st.session_state['gecici_sayim_listesi'] = []
            st.rerun()
