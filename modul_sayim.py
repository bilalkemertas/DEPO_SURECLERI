import streamlit as st
import pandas as pd
from datetime import datetime

def goster(conn):
    # --- 1. TEK SEFERLİK VERİ YÜKLEME (CACHE) ---
    if 'stok_df' not in st.session_state:
        with st.spinner("Veritabanı senkronize ediliyor..."):
            df_temp = conn.read(worksheet="Stok", ttl=0)
            df_temp = df_temp.dropna(subset=["Kod", "İsim"])
            df_temp["Kod"] = df_temp["Kod"].astype(str).str.strip()
            
            st.session_state['stok_df'] = df_temp
            st.session_state['kod_isim_dict'] = pd.Series(df_temp.İsim.values, index=df_temp.Kod).to_dict()
            st.session_state['isim_kod_dict'] = pd.Series(df_temp.Kod.values, index=df_temp.İsim).to_dict()
            st.session_state['kod_listesi'] = sorted(list(st.session_state['kod_isim_dict'].keys()))
            st.session_state['ad_listesi'] = sorted(list(st.session_state['isim_kod_dict'].keys()))

    if 'sayim_db' not in st.session_state:
        st.session_state['sayim_db'] = conn.read(worksheet="sayim", ttl=0)

    # --- 2. DEĞİŞKENLER ---
    df_Stok_ana = st.session_state['stok_df']
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    # --- 3. ARAYÜZ ---
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    
    # Session state'de tutulan seçimler
    if 's_Kod' not in st.session_state: st.session_state['s_Kod'] = None
    if 's_Isim' not in st.session_state: st.session_state['s_Isim'] = None

    st.title("🚀 Sayım ve Durum Takibi")
    tab1, tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])

    with tab1:
        with st.container(border=True):
            col_adr, col_kod, col_isim, col_mik, col_durum = st.columns([1, 1.2, 1.8, 0.8, 1.2])
            
            s_adres = col_adr.text_input("📍 Adres", key="adr_box").upper()
            
            # --- AKILLI ARAMA: SELECTBOX ---
            # Kullanıcı burada yazmaya başladığı an filtreleme başlar
            new_kod = col_kod.selectbox("📦 Ürün Kodu", [""] + st.session_state['kod_listesi'], key="kod_sel")
            new_isim = col_isim.selectbox("📝 Ürün Adı", [""] + st.session_state['ad_listesi'], key="isim_sel")

            # Kod değiştiyse isim otomatik güncellenir
            if new_kod and new_kod != st.session_state['s_Kod']:
                st.session_state['s_Kod'] = new_kod
                st.session_state['s_Isim'] = st.session_state['kod_isim_dict'].get(new_kod)
                st.rerun()
            
            # İsim değiştiyse kod otomatik güncellenir
            if new_isim and new_isim != st.session_state['s_Isim']:
                st.session_state['s_Isim'] = new_isim
                st.session_state['s_Kod'] = st.session_state['isim_kod_dict'].get(new_isim)
                st.rerun()

            s_miktar = col_mik.number_input("⚖️ Miktar", min_value=0.0, step=1.0, key="mik_box")
            s_durum = col_durum.selectbox("🛠️ Ürün Durumu", durum_opsiyonlari, key="durum_box")
            
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
                    st.rerun()

        # Liste Görüntüleme
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 DRIVE'A GÖNDER"):
                df_son = pd.concat([st.session_state['sayim_db'], pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True)
                conn.update(worksheet="sayim", data=df_son)
                st.session_state['sayim_db'] = df_son
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veriler Drive'a aktarıldı!")
                st.rerun()

    with tab2:
        # Analiz kısmı (Sadece ilk yüklemede veya manuel yenilemede çalışır)
        if not st.session_state['sayim_db'].empty:
            sistem = df_Stok_ana[['Adres', 'Kod', 'İsim', 'Miktar']].copy()
            sistem.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]
            s_ozet = st.session_state['sayim_db'].groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            s_ozet.columns = ["Adres", "Kod", "Sayılan_Miktar"]
            final_df = pd.merge(sistem, s_ozet, on=['Adres', 'Kod'], how='outer').fillna(0)
            final_df['FARK'] = final_df['Sayılan_Miktar'] - final_df['Sistem_Miktarı']
            st.dataframe(final_df, use_container_width=True)
