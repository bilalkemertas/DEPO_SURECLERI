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
    rt1, rt2, rt3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Raporu", "📜 Hareket Arşivi"])
    
    # --- TAB 1: MEVCUT STOK ---
    with rt1: 
        st.dataframe(veritabani.get_internal_data("Stok"), use_container_width=True, hide_index=True)
    
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
            
    # --- TAB 3: HAREKET ARŞİVİ (Filtrelerin Düzenlendiği Kısım) ---
    with rt3:
        # Not: Sayfa ismi sende 'Sayfa1' veya 'Hareketler' olabilir, veritabani.py'ye göre değişir.
        hareketler = veritabani.get_internal_data("Hareketler")
        
        if hareketler.empty:
            # Fallback: Eğer Hareketler boşsa Sayfa1'i dene
            hareketler = veritabani.get_internal_data("Sayfa1")

        if not hareketler.empty:
            # 4'lü Filtre Kolonları
            c1, c2, c3, c4 = st.columns(4)
            f_tar = c1.text_input("📅 Tarih:", placeholder="Örn: 2024-05")
            f_adr = c2.text_input("📍 Adres:", placeholder="Örn: A-01")
            f_kod = c3.text_input("📦 Ürün Kodu:", placeholder="Örn: ST-123")
            f_isi = c4.text_input("📝 Ürün Adı:", placeholder="Örn: Sünger")
            
            df_f = hareketler.copy()
            
            # Sütun İsimlerini Normalize Et (Kod mu Malzeme Kodu mu karmaşasını bitirir)
            # Verideki sütun isimlerini kontrol ederek filtre uygula
            cols = df_f.columns.tolist()
            
            # 1. Tarih Filtresi
            if f_tar:
                t_col = next((c for c in cols if "Tarih" in c), None)
                if t_col: df_f = df_f[df_f[t_col].astype(str).str.contains(f_tar)]
            
            # 2. Adres Filtresi
            if f_adr:
                a_col = next((c for c in cols if "Adres" in c), None)
                if a_col: df_f = df_f[df_f[a_col].astype(str).str.contains(f_adr, case=False, na=False)]
                
            # 3. Kod Filtresi
            if f_kod:
                k_col = next((c for c in cols if "Kod" in c), None)
                if k_col: df_f = df_f[df_f[k_col].astype(str).str.contains(f_kod, case=False, na=False)]
                
            # 4. İsim Filtresi
            if f_isi:
                i_col = next((c for c in cols if "İsim" in c or "Adı" in c), None)
                if i_col: df_f = df_f[df_f[i_col].astype(str).str.contains(f_isi, case=False, na=False)]
            
            # Sonuçları en yeni en üstte olacak şekilde göster
            st.markdown(f"**Sonuç:** {len(df_f)} kayıt bulundu.")
            st.dataframe(df_f.iloc[::-1], use_container_width=True, hide_index=True)
        else:
            st.info("Henüz kayıtlı bir hareket bulunamadı.")
