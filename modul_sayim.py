import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.sayim_page = 'menu'

def go_sayim_menu(): st.session_state.sayim_page = 'menu'
def go_oturum(): st.session_state.sayim_page = 'oturum'
def go_giris(): st.session_state.sayim_page = 'giris'
def go_rapor(): st.session_state.sayim_page = 'rapor'

def goster():
    # Session state tanımlamaları
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'aktif_sayim_adi' not in st.session_state:
        st.session_state.aktif_sayim_adi = None
    if 'sayim_page' not in st.session_state:
        st.session_state.sayim_page = 'menu'
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None

    # ==========================================
    # 0. SAYIM ANA MENÜSÜ
    # ==========================================
    if st.session_state.sayim_page == 'menu':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_home(); st.rerun()
        with c_title:
            st.subheader("⚖️ Sayım Kontrol Merkezi")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1: st.button("📁 OTURUM YÖNETİMİ", use_container_width=True, type="primary", on_click=go_oturum)
        with c2: st.button("📝 SAYIM GİRİŞİ", use_container_width=True, type="primary", on_click=go_giris)
        with c3: st.button("📊 FARK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)
            
        st.markdown("---")
        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
        else:
            st.info("ℹ️ Açık oturum yok. İşlem için oturum başlatın.")

    # ==========================================
    # 1. OTURUM YÖNETİMİ
    # ==========================================
    elif st.session_state.sayim_page == 'oturum':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        with c_title:
            st.subheader("📁 Oturum Yönetimi")
            
        st.markdown("---")
        if st.session_state.aktif_sayim_adi is None:
            with st.container(border=True):
                sayim_etiketi = st.text_input("Oturum İsmi:", placeholder="Örn: A_Blok")
                if st.button("🚀 BAŞLAT", use_container_width=True, type="primary"):
                    if sayim_etiketi:
                        zaman = datetime.now().strftime("%d%m_%H%M")
                        st.session_state.aktif_sayim_adi = f"{sayim_etiketi}_{zaman}"
                        st.rerun()
        else:
            st.success(f"📡 Aktif: **{st.session_state.aktif_sayim_adi}**")
            if st.button("🛑 OTURUMU KAPAT", type="primary", use_container_width=True):
                st.session_state.aktif_sayim_adi = None
                st.session_state['gecici_sayim_listesi'] = []
                st.rerun()

    # ==========================================
    # 2. SAYIM GİRİŞİ
    # ==========================================
    elif st.session_state.sayim_page == 'giris':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        with c_title:
            st.subheader("📝 Sayım Girişi")
            
        st.markdown("---")
        if st.session_state.aktif_sayim_adi is None:
            st.warning("⚠️ Önce oturum başlatın!")
        else:
            with st.container(border=True):
                s_adr = st.text_input("📍 Adres:").upper()
                katalog = veritabani.get_katalog() 
                sec = st.selectbox("🔍 Ürün:", ["+ MANUEL"] + katalog)
                s_kod = st.text_input("📦 Kod:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
                s_isim = sec.split(" | ")[1] if sec != "+ MANUEL" and len(sec.split(" | ")) > 1 else ""
                s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0)
                s_durum = st.selectbox("🛠️ Durum:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
                
                if st.button("➕ EKLE", use_container_width=True):
                    st.session_state['gecici_sayim_listesi'].append({
                        "Oturum_Adi": st.session_state.aktif_sayim_adi,
                        "Tarih": veritabani.get_local_time(), "Adres": s_adr, "Kod": s_kod, 
                        "İsim": s_isim, "Miktar": s_mik, "Birim": "-", 
                        "Personel": st.session_state.user, "Durum": s_durum
                    })
                    st.toast("Eklendi")
            
            if st.session_state['gecici_sayim_listesi']:
                for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                    cols = st.columns([3, 1])
                    cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']}")
                    if st.session_state.delete_confirm == idx:
                        c_del, c_esc = cols[1].columns(2)
                        if c_del.button("✅", key=f"c_{idx}"): st.session_state['gecici_sayim_listesi'].pop(idx); st.session_state.delete_confirm = None; st.rerun()
                        if c_esc.button("❌", key=f"e_{idx}"): st.session_state.delete_confirm = None; st.rerun()
                    else:
                        if cols[1].button("🗑️", key=f"d_{idx}"): st.session_state.delete_confirm = idx; st.rerun()
                
                if st.button("📤 KAYDET", type="primary", use_container_width=True):
                    eski = veritabani.get_internal_data("sayim")
                    veritabani.update_data("sayim", pd.concat([eski, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                    st.session_state['gecici_sayim_listesi'] = []; st.success("Kaydedildi!"); st.rerun()

    # ==========================================
    # 3. FARK RAPORU
    # ==========================================
    elif st.session_state.sayim_page == 'rapor':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        with c_title:
            st.subheader("📊 Fark Raporu")
            
        st.markdown("---")
        df_sayim_ana = veritabani.get_internal_data("sayim")
        df_stok = veritabani.get_internal_data("Stok")

        if not df_sayim_ana.empty:
            if 'Oturum_Adi' not in df_sayim_ana.columns: df_sayim_ana['Oturum_Adi'] = "ESKI_SAYIMLAR"
            
            # Başlık kaldırıldı, direkt selectbox
            mevcut_oturumlar = df_sayim_ana['Oturum_Adi'].dropna().unique().tolist()
            v_idx = mevcut_oturumlar.index(st.session_state.aktif_sayim_adi) if st.session_state.aktif_sayim_adi in mevcut_oturumlar else 0
            
            secilen_oturum = st.selectbox("Oturum Seç:", mevcut_oturumlar, index=v_idx, label_visibility="collapsed")
            df_sayim = df_sayim_ana[df_sayim_ana['Oturum_Adi'] == secilen_oturum].copy()
            
            if not df_sayim.empty:
                df_sayim['Miktar'] = pd.to_numeric(df_sayim['Miktar'], errors='coerce').fillna(0)
                s_ozet = df_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
                s_ozet.rename(columns={'Miktar': 'Miktar_Sayilan'}, inplace=True)
                
                df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)
                st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
                st_ozet.rename(columns={'Miktar': 'Miktar_Sistem'}, inplace=True)
                
                rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
                
                # İsim eşleme
                isimler = df_stok.drop_duplicates('Kod').set_index('Kod')['İsim'].to_dict()
                rapor['İsim'] = rapor['Kod'].map(isimler).fillna("TANIMSIZ")
                rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
                
                # Filtre başlığı kaldırıldı, direkt girişler
                katalog = veritabani.get_katalog()
                f_sec = st.selectbox("Ürün Seç:", ["+ TÜMÜ"] + katalog, label_visibility="collapsed")
                
                rf1, rf2, rf3 = st.columns(3)
                f_adr = rf1.text_input("📍 Adres:", placeholder="📍 Adres")
                o_kod = f_sec.split(" | ")[0] if f_sec != "+ TÜMÜ" else ""
                o_isi = f_sec.split(" | ")[1] if f_sec != "+ TÜMÜ" and len(f_sec.split(" | ")) > 1 else ""
                f_kod = rf2.text_input("📦 Kod:", value=o_kod, placeholder="📦 Kod")
                f_isi = rf3.text_input("📝 İsim:", value=o_isi, placeholder="📝 İsim")
                
                if f_adr: rapor = rapor[rapor['Adres'].str.contains(f_adr, case=False, na=False)]
                if f_kod: rapor = rapor[rapor['Kod'].str.contains(f_kod, case=False, na=False)]
                if f_isi: rapor = rapor[rapor['İsim'].str.contains(f_isi, case=False, na=False)]
                
                st.markdown("---")
                m1, m2 = st.columns(2)
                m1.metric("Toplam Sayılan", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
                m2.metric("Toplam Fark", f"{rapor['FARK'].sum():,.0f}")
                
                st.dataframe(rapor.style.applymap(lambda x: 'color: red' if x < 0 else 'color: green' if x > 0 else '', subset=['FARK']), use_container_width=True, hide_index=True)

                # Excel Butonu
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: rapor.to_excel(wr, index=False)
                st.download_button("📥 EXCEL İNDİR", buf.getvalue(), f"Fark_{secilen_oturum}.xlsx", use_container_width=True)

                if st.session_state.aktif_sayim_adi == secilen_oturum:
                    st.markdown("---")
                    st.warning("⚠️ STOK GÜNCELLEME")
                    if st.checkbox("Onaylıyorum") and st.button("🚀 GÜNCELLE", type="primary", use_container_width=True):
                        # Güncelleme mantığı (kısmi sayım)
                        sayilanlar = rapor['Kod'].unique().tolist()
                        kalan = df_stok[~df_stok['Kod'].isin(sayilanlar)]
                        yeni = rapor[['Kod', 'İsim', 'Miktar_Sayilan', 'Adres', 'Durum']].rename(columns={'Miktar_Sayilan':'Miktar'})
                        veritabani.update_data("Stok", pd.concat([kalan, yeni[yeni['Miktar']>0]], ignore_index=True))
                        st.success("Güncellendi!"); st.cache_data.clear(); st.rerun()
