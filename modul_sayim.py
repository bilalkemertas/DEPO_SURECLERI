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
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'aktif_sayim_adi' not in st.session_state:
        st.session_state.aktif_sayim_adi = None
    if 'sayim_page' not in st.session_state:
        st.session_state.sayim_page = 'menu'
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None

    # --- 0. MENÜ ---
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

    # --- 1. OTURUM YÖNETİMİ (GÜNCELLEME BURAYA TAŞINDI) ---
    elif st.session_state.sayim_page == 'oturum':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        with c_title:
            st.subheader("📁 Oturum Yönetimi")
        st.markdown("---")
        
        if st.session_state.aktif_sayim_adi is None:
            with st.container(border=True):
                st.info("Yeni bir sayım oturumu başlatın.")
                sayim_etiketi = st.text_input("Oturum İsmi:", placeholder="Örn: A_Blok")
                if st.button("🚀 SAYIMI BAŞLAT", use_container_width=True, type="primary"):
                    if sayim_etiketi:
                        zaman = datetime.now().strftime("%d%m_%H%M")
                        st.session_state.aktif_sayim_adi = f"{sayim_etiketi}_{zaman}"
                        st.rerun()
        else:
            st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
            
            # --- STOK GÜNCELLEME VE KAPATMA ALANI ---
            with st.container(border=True):
                st.warning("⚠️ DİKKAT: Bu işlem sayılan ürünlerin stoklarını günceller ve oturumu arşivler.")
                onay = st.checkbox("Sayım verilerinin doğruluğunu ve stokların ezilmesini onaylıyorum.")
                
                if st.button("🚀 STOKLARI GÜNCELLE VE OTURUMU KAPAT", type="primary", use_container_width=True, disabled=not onay):
                    # Verileri Çek
                    df_sayim_ana = veritabani.get_internal_data("sayim")
                    df_stok = veritabani.get_internal_data("Stok")
                    df_urun = veritabani.get_internal_data("Urun_Listesi")
                    df_tamamlanan = veritabani.get_internal_data("sayim_tamamlanan")
                    
                    aktif = st.session_state.aktif_sayim_adi
                    df_bu_sayim = df_sayim_ana[df_sayim_ana['Oturum_Adi'] == aktif].copy()
                    
                    if not df_bu_sayim.empty:
                        # 1. Sayım verilerini işle (Miktar Topla)
                        df_bu_sayim['Miktar'] = pd.to_numeric(df_bu_sayim['Miktar'], errors='coerce').fillna(0)
                        s_ozet = df_bu_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
                        
                        # 2. İsim eşleme için sözlük
                        isim_sozlugu = {}
                        if not df_urun.empty: isim_sozlugu.update(df_urun.drop_duplicates('kod').set_index('kod')['isim'].to_dict())
                        if not df_stok.empty: isim_sozlugu.update(df_stok.drop_duplicates('Kod').set_index('Kod')['İsim'].to_dict())
                        
                        # 3. ZIRHLI KISMİ EZME MANTIĞI
                        sayilan_kodlar = s_ozet['Kod'].unique().tolist()
                        # Sayılmayanlar kalsın
                        stok_kalan = df_stok[~df_stok['Kod'].isin(sayilan_kodlar)]
                        # Yeni sayılanlar eklensin
                        yeni_stok_verisi = s_ozet[['Kod', 'Miktar', 'Adres', 'Durum']].copy()
                        yeni_stok_verisi['İsim'] = yeni_stok_verisi['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
                        
                        # Stok Güncelle
                        veritabani.update_data("Stok", pd.concat([stok_kalan, yeni_stok_verisi[yeni_stok_verisi['Miktar']>0]], ignore_index=True))
                        
                        # 4. Oturumu Arşive Ekle (Mükerrerlik Önleme)
                        log_yeni = pd.DataFrame([{"Oturum_Adi": aktif, "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M")}])
                        veritabani.update_data("sayim_tamamlanan", pd.concat([df_tamamlanan, log_yeni], ignore_index=True))
                        
                        # 5. Oturumu Kapat ve Temizle
                        st.session_state.aktif_sayim_adi = None
                        st.session_state['gecici_sayim_listesi'] = []
                        st.success("Stoklar güncellendi ve oturum başarıyla kapatıldı!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Bu oturuma ait henüz bir sayım girişi yapılmamış! Boş oturum güncellenemez.")

            if st.button("🛑 SADECE OTURUMU KAPAT (GÜNCELLEMEDEN)", use_container_width=True):
                st.session_state.aktif_sayim_adi = None
                st.session_state['gecici_sayim_listesi'] = []
                st.rerun()

    # --- 2. SAYIM GİRİŞİ ---
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
                    cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {int(item['Miktar'])}")
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

    # --- 3. FARK RAPORU (BUTON BURADAN KALDIRILDI) ---
    elif st.session_state.sayim_page == 'rapor':
        c_nav, c_title = st.columns([1, 4])
        with c_nav:
            if st.button("⬅️ GERİ"): go_sayim_menu(); st.rerun()
        with c_title:
            st.subheader("📊 Fark Raporu")
        st.markdown("---")
        
        df_sayim_ana = veritabani.get_internal_data("sayim")
        df_tamamlanan = veritabani.get_internal_data("sayim_tamamlanan")
        df_stok = veritabani.get_internal_data("Stok")
        df_urun = veritabani.get_internal_data("Urun_Listesi")

        if not df_sayim_ana.empty:
            if 'Oturum_Adi' not in df_sayim_ana.columns: df_sayim_ana['Oturum_Adi'] = "ESKI_SAYIMLAR"
            
            tamamlanan_liste = []
            if not df_tamamlanan.empty and 'Oturum_Adi' in df_tamamlanan.columns:
                tamamlanan_liste = df_tamamlanan['Oturum_Adi'].dropna().unique().tolist()
            
            # Sadece aktarılmamışları göster
            mevcut_oturumlar = [o for o in df_sayim_ana['Oturum_Adi'].dropna().unique().tolist() if o not in tamamlanan_liste]
            
            if mevcut_oturumlar:
                v_idx = mevcut_oturumlar.index(st.session_state.aktif_sayim_adi) if st.session_state.aktif_sayim_adi in mevcut_oturumlar else 0
                secilen_oturum = st.selectbox("Raporlanacak Oturumu Seç:", mevcut_oturumlar, index=v_idx)
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
                    
                    rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
                    rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
                    
                    st.dataframe(rapor, use_container_width=True, hide_index=True)

                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: rapor.to_excel(wr, index=False)
                    st.download_button("📥 EXCEL İNDİR", buf.getvalue(), f"Fark_{secilen_oturum}.xlsx", use_container_width=True)
            else:
                st.info("İşlem bekleyen (aktarılmamış) sayım oturumu bulunamadı.")
