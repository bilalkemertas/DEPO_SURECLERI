import streamlit as st
import veritabani

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Raporlar ve Arşiv")
    rt1, rt2, rt3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Raporu", "📜 Hareket Arşivi"])
    
    with rt1: st.dataframe(veritabani.get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = veritabani.get_internal_data("Is_Emirleri").copy()
        if not df_h.empty:
            r_emir_list = sorted(df_h["İş Emri"].astype(str).unique().tolist())
            r_emir = st.multiselect("📋 İş Emri Filtrele:", r_emir_list, key="r_emir")
            r_df = df_h.copy()
            if r_emir: r_df = r_df[r_df["İş Emri"].astype(str).isin(r_emir)]
            st.dataframe(r_df, use_container_width=True, hide_index=True)
            
    with rt3:
        hareketler = veritabani.get_internal_data("Sayfa1")
        if not hareketler.empty:
            f1, f2, f3 = st.columns(3)
            f_tar, f_kod, f_isi = f1.text_input("📅 Tarih:"), f2.text_input("📦 Kod:"), f3.text_input("📝 İsim:")
            df_f = hareketler.copy()
            if f_tar: df_f = df_f[df_f['Tarih'].astype(str).str.contains(f_tar)]
            if f_kod: df_f = df_f[df_f['Malzeme Kodu'].astype(str).str.contains(f_kod, case=False)]
            if f_isi: df_f = df_f[df_f['Malzeme Adı'].astype(str).str.contains(f_isi, case=False)]
            st.dataframe(df_f.iloc[::-1], use_container_width=True, hide_index=True)
