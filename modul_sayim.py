import streamlit as st
import pandas as pd
from datetime import datetime

def goster(conn):
    # --- 1. SESSION STATE İLE VERİ KİLİTLEME ---
    # Stok verisini bir kez çek, session_state'de tut.
    if 'cached_stok_df' not in st.session_state:
        try:
            with st.spinner("Veritabanı senkronize ediliyor..."):
                df_temp = conn.read(worksheet="Stok", ttl=0)
                df_temp = df_temp.dropna(subset=["Kod", "İsim"])
                df_temp["Kod"] = df_temp["Kod"].astype(str).str.strip()
                st.session_state['cached_stok_df'] = df_temp
                
                # Arama ve sözlükleri de bir kez oluştur
                st.session_state['kod_isim_dict'] = pd.Series(df_temp.İsim.values, index=df_temp.Kod).to_dict()
                st.session_state['isim_kod_dict'] = pd.Series(df_temp.Kod.values, index=df_temp.İsim).to_dict()
                st.session_state['kod_listesi'] = sorted(list(st.session_state['kod_isim_dict'].keys()))
                st.session_state['ad_listesi'] = sorted(list(st.session_state['isim_kod_dict'].keys()))
        except Exception as e:
            st.error(f"Veri yüklenemedi: {e}")
            return

    # Kısayollar
    df_Stok_ana = st.session_state['cached_stok_df']
    kod_isim_dict = st.session_state['kod_isim_dict']
    isim_kod_dict = st.session_state['isim_kod_dict']
    kod_listesi = st.session_state['kod_listesi']
    ad_listesi = st.session_state['ad_listesi']
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    # --- 2. GİRİŞ VE BELLEK SİSTEMİ ---
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 's_Kod' not in st.session_state: st.session_state['s_Kod'] = ""
    if 's_Isim' not in st.session_state: st.session_state['s_Isim'] = ""

    st.title("🚀 Sayım ve Durum Takibi")
    tab1, tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])

    # --- TAB 1: SAYIM GİRİŞ EKRANI ---
    with tab1:
        st.subheader("📍 Yeni Veri Girişi")
        with st.container(border=True):
            col_adr, col_kod, col_isim, col_mik, col_durum = st.columns([1, 1.2, 1.8, 0.8, 1.2])
            
            with col_adr:
                s_adres = st.text_input("📍 Adres", key="adr_box").upper()
            with col_kod:
                new_kod = st.selectbox("📦 Ürün Kodu", [""] + kod_listesi, key="kod_sel")
                if new_kod != st.session_state['s_Kod']:
                    st.session_state['s_Kod'] = new_kod
                    st.session_state['s_Isim'] = kod_isim_dict.get(new_kod, "")
                    st.rerun()
            with col_isim:
                new_isim = st.selectbox("📝 Ürün Adı", [""] + ad_listesi, key="isim_sel")
                if new_isim != st.session_state['s_Isim']:
                    st.session_state['s_Isim'] = new_isim
                    st.session_state['s_Kod'] = isim_kod_dict.get(new_isim, "")
                    st.rerun()
            with col_mik:
                s_miktar = st.number_input("⚖️ Miktar", min_value=0.0, step=1.0, key="mik_box")
            with col_durum:
                s_durum = st.selectbox("🛠️ Ürün Durumu", durum_opsiyonlari, key="durum_box")
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adres and st.session_state['s_Kod']:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%d.%m.%Y"),
                        "Personel": st.session_state.get('kullanici_adi', 'Patron'),
                        "Adres": s_adres,
                        "Kod": st.session_state['s_Kod'],
                        "Ürün Adı": st.session_state['s_Isim'],
                        "Miktar": s_miktar,
                        "Durum": s_durum
                    })
                    st.toast(f"{st.session_state['s_Kod']} eklendi.")
                else:
                    st.warning("Adres ve Ürün bilgisi zorunludur!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Sayımlar")
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 DRIVE'A GÖNDER VE KAYDET", type="primary"):
                df_db = conn.read(worksheet="sayim", ttl=0)
                df_son = pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True)
                conn.update(worksheet="sayim", data=df_son)
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veriler kaydedildi!")
                st.rerun()

    # --- TAB 2: ANALİZ ---
    with tab2:
        st.subheader("🔍 Sayım ve Fark Analizi")
        try:
            # Raporlama için bir kez okuma yeterli
            df_sayim_db = conn.read(worksheet="sayim", ttl=0)
            if not df_sayim_db.empty:
                sistem = df_Stok_ana[['Adres', 'Kod', 'İsim', 'Miktar']].copy()
                sistem.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]
                s_ozet = df_sayim_db.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                s_ozet.columns = ["Adres", "Kod", "Sayılan_Miktar"]
                final_df = pd.merge(sistem, s_ozet, on=['Adres', 'Kod'], how='outer').fillna(0)
                final_df['FARK'] = final_df['Sayılan_Miktar'] - final_df['Sistem_Miktarı']
                st.dataframe(final_df, use_container_width=True)
        except:
            st.info("Henüz sayım verisi bulunmuyor.")
