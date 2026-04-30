import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- MOBİL UYUMLU BAŞLIK FONKSİYONU ---
def mobil_baslik(emoji, metin):
    st.markdown(f"""
        <div style='display: flex; align-items: center; margin-bottom: 10px;'>
            <span style='font-size: 20px; margin-right: 10px;'>{emoji}</span>
            <span style='font-size: 18px; font-weight: bold; color: #333;'>{metin}</span>
        </div>
    """, unsafe_allow_html=True)

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.sayim_page = 'menu'

def go_sayim_menu(): st.session_state.sayim_page = 'menu'
def go_oturum(): st.session_state.sayim_page = 'oturum'
def go_giris(): st.session_state.sayim_page = 'giris'
def go_rapor(): st.session_state.sayim_page = 'rapor'

def goster():
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
            if st.button("⬅️"): go_home(); st.rerun()
        with c_title:
            mobil_baslik("⚖️", "Sayım Kontrol Merkezi")
        
        st.markdown("---")
        # Butonları biraz daha küçük ve yan yana sığacak şekilde ayarladık
        st.button("📁 OTURUM YÖNETİMİ", use_container_width=True, type="primary", on_click=go_oturum)
        st.button("📝 SAYIM GİRİŞİ", use_container_width=True, type="primary", on_click=go_giris)
        st.button("📊 FARK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)
            
        st.markdown("---")
        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Aktif: {st.session_state.aktif_sayim_adi}")
        else:
            st.info("ℹ️ Açık oturum yok.")

    # ==========================================
    # 1. OTURUM YÖNETİMİ
    # ==========================================
    elif st.session_state.sayim_page == 'oturum':
        c_nav, c_title = st.columns([1, 5])
        with c_nav:
            if st.button("⬅️"): go_sayim_menu(); st.rerun()
        with c_title:
            mobil_baslik("📁", "Oturum Yönetimi")
            
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
            st.success(f"📡 Aktif: {st.session_state.aktif_sayim_adi}")
            if st.button("🛑 OTURUMU KAPAT", type="primary", use_container_width=True):
                st.session_state.aktif_sayim_adi = None
                st.session_state['gecici_sayim_listesi'] = []
                st.rerun()

    # ==========================================
    # 2. SAYIM GİRİŞİ
    # ==========================================
    elif st.session_state.sayim_page == 'giris':
        c_nav, c_title = st.columns([1, 5])
        with c_nav:
            if st.button("⬅️"): go_sayim_menu(); st.rerun()
        with c_title:
            mobil_baslik("📝", "Sayım Girişi")
            
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
                st.markdown("**Sayılan Ürünler:**")
                for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                    cols = st.columns([4, 1])
                    cols[0].write(f"📍{item['Adres']} | {item['Kod']} | {int(item['Miktar'])} Adet")
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
        c_nav, c_title = st.columns([1, 5])
        with c_nav:
            if st.button("⬅️"): go_sayim_menu(); st.rerun()
        with c_title:
            mobil_baslik("📊", "Fark Raporu")
            
        st.markdown("---")
        df_sayim_ana = veritabani.get_internal_data("sayim")
        df_stok = veritabani.get_internal_data("Stok")
        df_urun = veritabani.get_internal_data("Urun_Listesi")

        if not df_sayim_ana.empty:
            if 'Oturum_Adi' not in df_sayim_ana.columns: df_sayim_ana['Oturum_Adi'] = "ESKI_SAYIMLAR"
            
            mevcut_oturumlar = df_sayim_ana['Oturum_Adi'].dropna().unique().tolist()
            v_idx = mevcut_oturumlar.index(st.session_state.aktif_sayim_adi) if st.session_state.aktif_sayim_adi in mevcut_oturumlar else 0
            
            secilen_oturum = st.selectbox("Oturum Seç:", mevcut_oturumlar, index=v_idx, label_visibility="collapsed")
            df_sayim = df_sayim_ana[df_sayim_ana['Oturum_Adi'] == secilen_oturum].copy()
            
            if not df_sayim.empty:
                df_sayim['Miktar'] = pd.to_numeric(df_sayim['Miktar'], errors='coerce').fillna(0)
                s_ozet = df_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
                s_ozet.rename(columns={'Miktar': 'Miktar_Sayilan'}, inplace=True)
                
                st_ozet = pd.DataFrame(columns=['Adres', 'Kod', 'Miktar_Sistem'])
                if not df_stok.empty:
                    df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)
                    st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
                    st_ozet.rename(columns={'Miktar': 'Miktar_Sistem'}, inplace=True)
                
                rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
                
                isim_sozlugu = {}
                if not df_urun.empty: isim_sozlugu.update(df_urun.drop_duplicates('kod').set_index('kod')['isim'].to_dict())
                if not df_stok.empty: isim_sozlugu.update(df_stok.drop_duplicates('Kod').set_index('Kod')['İsim'].to_dict())
                if 'İsim' in df_sayim.columns: isim_sozlugu.update(df_sayim.drop_duplicates('Kod').set_index('Kod')['İsim'].to_dict())
                
                rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
                rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
                
                # --- MOBİL UYUMLU FİLTRE ALANI ---
                with st.expander("🔍 Filtreleri Aç/Kapat"):
                    f_adr = st.text_input("📍 Adres Filtre:", placeholder="Adres yazın...").upper()
                    f_kod = st.text_input("📦 Kod Filtre:", placeholder="Kod yazın...").upper()
                
                if f_adr: rapor = rapor[rapor['Adres'].str.contains(f_adr, case=False, na=False)]
                if f_kod: rapor = rapor[rapor['Kod'].str.contains(f_kod, case=False, na=False)]
                
                st.markdown("---")
                m1, m2 = st.columns(2)
                m1.metric("Sayılan", f"{int(rapor['Miktar_Sayilan'].sum())}")
                m2.metric("Fark", f"{int(rapor['FARK'].sum())}")
                
                st.dataframe(rapor.style.map(lambda x: 'color: red' if x < 0 else 'color: green' if x > 0 else '', subset=['FARK']).format({
                    'Miktar_Sayilan': '{:,.0f}', 'Miktar_Sistem': '{:,.0f}', 'FARK': '{:,.0f}'
                }), use_container_width=True, hide_index=True)

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: rapor.to_excel(wr, index=False)
                st.download_button("📥 EXCEL", buf.getvalue(), f"Fark.xlsx", use_container_width=True)

                if st.session_state.aktif_sayim_adi == secilen_oturum:
                    st.markdown("---")
                    st.warning("⚠️ STOK GÜNCELLEME")
                    if st.checkbox("Onaylıyorum") and st.button("🚀 GÜNCELLE", type="primary", use_container_width=True):
                        sayilanlar = rapor['Kod'].unique().tolist()
                        kalan = df_stok[~df_stok['Kod'].isin(sayilanlar)]
                        yeni = rapor[['Kod', 'İsim', 'Miktar_Sayilan', 'Adres', 'Durum']].rename(columns={'Miktar_Sayilan':'Miktar'})
                        veritabani.update_data("Stok", pd.concat([kalan, yeni[yeni['Miktar']>0]], ignore_index=True))
                        st.success("Bitti!"); st.cache_data.clear(); st.rerun()
