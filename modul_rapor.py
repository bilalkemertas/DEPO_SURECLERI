import streamlit as st
import veritabani
import pandas as pd

def go_home(): 
    st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📈 Raporlar ve Arşiv")
    rt1, rt2, rt3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazirlik Raporu", "📜 Hareket Arşivi"])
    
    # --- TAB 1: MEVCUT STOK (Filtreler ve Adres Maskeleme) ---
    with rt1: 
        df_stok = veritabani.get_internal_data("Stok").copy()
        
        if not df_stok.empty:
            # 3'lü Filtre Kolonları
            sc1, sc2, sc3 = st.columns(3)
            f_kod_s = sc1.text_input("📦 Ürün Kodu Filtrele:", placeholder="Örn: ST-123", key="stok_kod_filtre")
            f_isi_s = sc2.text_input("📝 Ürün Adı Filtrele:", placeholder="Örn: Sünger", key="stok_isim_filtre")
            f_adr_s = sc3.text_input("📍 Adres Filtrele:", placeholder="Örn: A-01", key="stok_adres_filtre")
            
            # Filtreleme Mantığı
            cols_s = df_stok.columns.tolist()
            
            if f_kod_s:
                k_col = next((c for c in cols_s if "Kod" in c), None)
                if k_col: df_stok = df_stok[df_stok[k_col].astype(str).str.contains(f_kod_s, case=False, na=False)]
                
            if f_isi_s:
                i_col = next((c for c in cols_s if "İsim" in c or "Adı" in c), None)
                if i_col: df_stok = df_stok[df_stok[i_col].astype(str).str.contains(f_isi_s, case=False, na=False)]
                
            if f_adr_s:
                a_col = next((c for c in cols_s if "Adres" in c), None)
                if a_col: df_stok = df_stok[df_stok[a_col].astype(str).str.contains(f_adr_s, case=False, na=False)]

            # --- SIFIR MİKTAR VE ADRES KONTROLÜ ---
            m_col = next((c for c in cols_s if "Miktar" in c), None)
            a_col = next((c for c in cols_s if "Adres" in c), None)

            if m_col:
                # Önce miktar kontrolü
                mask = (df_stok[m_col] == 0) | (df_stok[m_col] == "0")
                
                # Adres sütununu maskele
                if a_col:
                    df_stok.loc[mask, a_col] = "STOK YOK"
                
                # Miktar sütununu maskele
                df_stok[m_col] = df_stok[m_col].apply(lambda x: "STOK YOK" if x == 0 or x == "0" else x)

            st.markdown(f"**Güncel Stok Listesi:** {len(df_stok)} kalem ürün listeleniyor.")
            st.dataframe(df_stok, use_container_width=True, hide_index=True)
        else:
            st.info("Stok verisi bulunamadı.")
    
    # --- TAB 2: HAZIRLIK RAPORU ---
    with rt2:
        df_h = veritabani.get_internal_data("Is_Emirleri").copy()
        if not df_h.empty:
            r_emir_list = sorted(df_h["İş Emri"].astype(str).unique().tolist())
            r_emir = st.multiselect("📋 İş Emri Filtrele:", r_emir_list, key="r_emir")
            r_df = df_h.copy()
            if r_emir: 
                r_df = r_df[r_df["İş Emri"].astype(str).isin(r_emir)]
            st.dataframe(r_df, use_container_width=True, hide_index=True)
            
    # --- TAB 3: HAREKET ARŞİVİ ---
    with rt3:
        hareketler = veritabani.get_internal_data("Hareketler")
        if hareketler.empty:
            hareketler = veritabani.get_internal_data("Sayfa1")

        if not hareketler.empty:
            c1, c2, c3, c4 = st.columns(4)
            f_tar = c1.text_input("📅 Tarih:", placeholder="Örn: 2024-05", key="har_tar_filtre")
            f_adr = c2.text_input("📍 Adres:", placeholder="Örn: A-01", key="har_adr_filtre")
            f_kod = c3.text_input("📦 Ürün Kodu:", placeholder="Örn: ST-123", key="har_kod_filtre")
            f_isi = c4.text_input("📝 Ürün Adı:", placeholder="Örn: Sünger", key="har_isim_filtre")
            
            df_f = hareketler.copy()
            cols = df_f.columns.tolist()
            
            if f_tar:
                t_col = next((c for c in cols if "Tarih" in c), None)
                if t_col: df_f = df_f[df_f[t_col].astype(str).str.contains(f_tar)]
            
            if f_adr:
                a_col = next((c for c in cols if "Adres" in c), None)
                if a_col: df_f = df_f[df_f[a_col].astype(str).str.contains(f_adr, case=False, na=False)]
                
            if f_kod:
                k_col = next((c for c in cols if "Kod" in c), None)
                if k_col: df_f = df_f[df_f[k_col].astype(str).str.contains(f_kod, case=False, na=False)]
                
            if f_isi:
                i_col = next((c for c in cols if "İsim" in c or "Adı" in c), None)
                if i_col: df_f = df_f[df_f[i_col].astype(str).str.contains(f_isi, case=False, na=False)]
            
            st.markdown(f"**Sonuç:** {len(df_f)} kayıt bulundu.")
            st.dataframe(df_f.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Henüz kayıtlı bir hareket bulunamadı.")
