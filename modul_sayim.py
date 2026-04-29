import streamlit as st
import pandas as pd
import veritabani

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres:").upper()
            katalog = veritabani.get_katalog() 
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
            s_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
            
            s_isim = sec.split(" | ")[1] if sec != "+ MANUEL" and len(sec.split(" | ")) > 1 else ""
            
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": veritabani.get_local_time(), 
                    "Adres": s_adr, 
                    "Kod": s_kod, 
                    "Miktar": s_mik,
                    "Birim": "-", 
                    "Personel": st.session_state.user, 
                    "isim": s_isim, 
                    "Durum": s_durum
                })
                st.toast("Eklendi")
        
        if st.session_state['gecici_sayim_listesi']:
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                cols = st.columns([3, 1])
                cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
                if st.session_state.delete_confirm == idx:
                    c_del, c_esc = cols[1].columns(2)
                    if c_del.button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx); st.session_state.delete_confirm = None; st.rerun()
                    if c_esc.button("❌", key=f"esc_{idx}"):
                        st.session_state.delete_confirm = None; st.rerun()
                else:
                    if cols[1].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx; st.rerun()
            
            if st.button("📤 VERİTABANINA GÖNDER", type="primary", use_container_width=True):
                eski = veritabani.get_internal_data("sayim")
                veritabani.update_data("sayim", pd.concat([eski, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.rerun()

    with t2:
        df_sayim = veritabani.get_internal_data("sayim")
        df_stok = veritabani.get_internal_data("Stok")
        
        df_urun = veritabani.get_internal_data("Urun_Listesi")
        if df_urun.empty: df_urun = veritabani.get_internal_data("ürün listesi")
        if df_urun.empty: df_urun = veritabani.get_internal_data("Ürün Listesi")

        if not df_sayim.empty:
            df_sayim['Miktar'] = pd.to_numeric(df_sayim['Miktar'], errors='coerce').fillna(0)
            if 'Durum' not in df_sayim.columns: df_sayim['Durum'] = "Belirtilmemiş"
            
            s_ozet = df_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
            s_ozet.rename(columns={'Miktar': 'Miktar_Sayilan'}, inplace=True)
            
            if not df_stok.empty:
                df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)
                st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
                st_ozet.rename(columns={'Miktar': 'Miktar_Sistem'}, inplace=True)
            else:
                st_ozet = pd.DataFrame(columns=['Adres', 'Kod', 'Miktar_Sistem'])
            
            isim_sozlugu = {}
            if not df_stok.empty and 'İsim' in df_stok.columns and 'Kod' in df_stok.columns:
                isim_sozlugu.update(df_stok.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            if 'isim' in df_sayim.columns and 'Kod' in df_sayim.columns:
                isim_sozlugu.update(df_sayim.drop_duplicates(subset=['Kod']).set_index('Kod')['isim'].to_dict())
            if not df_urun.empty and 'isim' in df_urun.columns and 'kod' in df_urun.columns:
                isim_sozlugu.update(df_urun.drop_duplicates(subset=['kod']).set_index('kod')['isim'].to_dict())
            
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
            
            rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            
            rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
            
            st.markdown("#### 🔍 Rapor Filtreleri")
            rf1, rf2, rf3 = st.columns(3)
            f_adr = rf1.text_input("📍 Adres Filtre:").upper()
            f_kod = rf2.text_input("📦 Kod Filtre:").upper()
            f_isim = rf3.text_input("📝 İsim Filtre:").upper()
            
            if f_adr: rapor = rapor[rapor['Adres'].astype(str).str.contains(f_adr)]
            if f_kod: rapor = rapor[rapor['Kod'].astype(str).str.contains(f_kod)]
            if f_isim: rapor = rapor[rapor['İsim'].astype(str).str.contains(f_isim, case=False)]
            
            m1, m2 = st.columns(2)
            m1.metric("Toplam Sayılan", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
            m2.metric("Toplam Fark", f"{rapor['FARK'].sum():,.0f}")
            
            def color_diff(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
            st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)
