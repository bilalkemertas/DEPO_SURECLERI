import streamlit as st
import pandas as pd
from datetime import datetime

def run(df_Stok_ana, conn):
    """
    Ana uygulamadan (app.py) gelen stok verisi ve veritabanı bağlantısı ile çalışır.
    """
    st.subheader("📝 Güncel Sayım Verisi Girişi")
    
    # Veri Hazırlığı
    df_Stok_ana["Kod"] = df_Stok_ana["Kod"].astype(str).str.strip()
    kod_isim_dict = pd.Series(df_Stok_ana.İsim.values, index=df_Stok_ana.Kod).to_dict()
    kod_listesi = sorted(list(kod_isim_dict.keys()))
    ad_listesi = sorted(df_Stok_ana["İsim"].unique().tolist())
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    # Bellek kontrolü
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []

    # 1. GİRİŞ EKRANI
    with st.container(border=True):
        col_adr, col_kod, col_isim, col_mik, col_durum = st.columns([1, 1.2, 1.8, 0.8, 1.2])
        
        with col_adr:
            s_adres = st.text_input("📍 Adres", key="adr_box").upper()
        with col_kod:
            s_Kod = st.selectbox("📦 Ürün Kodu", [""] + kod_listesi, key="kod_box")
        with col_isim:
            current_name = kod_isim_dict.get(str(s_Kod), "")
            st.text_input("📝 Ürün Adı", value=current_name, disabled=True)
        with col_mik:
            s_miktar = st.number_input("⚖️ Miktar", min_value=0.0, step=1.0, key="mik_box")
        with col_durum:
            s_durum = st.selectbox("🛠️ Ürün Durumu", durum_opsiyonlari, key="durum_box")
        
        if st.button("➕ Listeye Ekle", use_container_width=True):
            if s_adres and s_Kod:
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": datetime.now().strftime("%d.%m.%Y"),
                    "Personel": st.session_state.get('user_name', 'Patron'),
                    "Adres": s_adres,
                    "Kod": s_Kod,
                    "Ürün Adı": current_name,
                    "Miktar": s_miktar,
                    "Durum": s_durum
                })
                st.toast(f"{s_Kod} eklendi.")
            else:
                st.warning("Adres ve Kod alanları zorunludur!")

    # 2. LİSTE VE ONAY
    if st.session_state['gecici_sayim_listesi']:
        st.write("---")
        st.markdown("### 📥 Onay Bekleyen Sayımlar")
        df_temp = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
        st.dataframe(df_temp, use_container_width=True)
        
        c_onay, c_iptal = st.columns(2)
        if c_onay.button("📤 DRIVE'A GÖNDER VE KAYDET", type="primary", use_container_width=True):
            try:
                df_db = conn.read(worksheet="sayim", ttl=0)
                df_son = pd.concat([df_db, df_temp], ignore_index=True)
                conn.update(worksheet="sayim", data=df_son)
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Tüm veriler Drive'a kaydedildi!")
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")
        
        if c_iptal.button("⚠️ Tüm Listeyi Boşalt", use_container_width=True):
            st.session_state['gecici_sayim_listesi'] = []
            st.rerun()
