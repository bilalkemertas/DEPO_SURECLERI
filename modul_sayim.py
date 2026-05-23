import streamlit as st
import pandas as pd
from datetime import datetime

def goster(conn):
    # --- 1. VERİTABANI BAĞLANTISI VE HAZIRLIK ---
    try:
        df_Stok_ana = conn.read(worksheet="Stok", ttl=0)
        df_Stok_ana = df_Stok_ana.dropna(subset=["Kod", "İsim"])
        df_Stok_ana["Kod"] = df_Stok_ana["Kod"].astype(str).str.strip()
        
        kod_isim_dict = pd.Series(df_Stok_ana.İsim.values, index=df_Stok_ana.Kod).to_dict()
        isim_kod_dict = pd.Series(df_Stok_ana.Kod.values, index=df_Stok_ana.İsim).to_dict()
        
        kod_listesi = sorted(list(kod_isim_dict.keys()))
        ad_listesi = sorted(list(isim_kod_dict.keys()))
        durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]
    except Exception as e:
        st.error(f"Veri yüklenemedi: {e}")
        return

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
                    st.toast(f"{st.session_state['s_Kod']} listeye eklendi.")
                else:
                    st.warning("Adres ve Kod alanları zorunludur!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Sayımlar")
            df_temp = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
            st.dataframe(df_temp, use_container_width=True)
            if st.button("📤 DRIVE'A GÖNDER VE KAYDET", type="primary", use_container_width=True):
                try:
                    df_db = conn.read(worksheet="sayim", ttl=0)
                    df_son = pd.concat([df_db, df_temp], ignore_index=True)
                    conn.update(worksheet="sayim", data=df_son)
                    st.session_state['gecici_sayim_listesi'] = []
                    st.success("Tüm veriler Drive'a kaydedildi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")

    # --- TAB 2: ANALİZ ---
    with tab2:
        st.subheader("🔍 Sayım ve Fark Analizi")
        try:
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
