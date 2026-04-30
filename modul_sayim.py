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
    # 0. SAYIM ANA MENÜSÜ (Giriş Ekranı)
    # ==========================================
    if st.session_state.sayim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): 
            go_home()
            st.rerun()
        
        st.subheader("⚖️ Sayım Kontrol Merkezi")
        st.markdown("---")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("📁 OTURUM YÖNETİMİ", use_container_width=True, type="primary", on_click=go_oturum)
        with c2:
            st.button("📝 SAYIM GİRİŞİ", use_container_width=True, type="primary", on_click=go_giris)
        with c3:
            st.button("📊 FARK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)
            
        st.markdown("---")
        if st.session_state.aktif_sayim_adi:
            st.success(f"📡 Şu an aktif olan oturum: **{st.session_state.aktif_sayim_adi}**")
        else:
            st.info("ℹ️ Şu an açık bir sayım oturumu bulunmuyor. 'Oturum Yönetimi'nden yeni sayım başlatabilirsiniz.")

    # ==========================================
    # 1. OTURUM YÖNETİMİ EKRANI
    # ==========================================
    elif st.session_state.sayim_page == 'oturum':
        if st.button("⬅️ GERİ"): 
            go_sayim_menu()
            st.rerun()
            
        st.subheader("📁 Sayım Oturumu İşlemleri")
        st.markdown("---")
        
        if st.session_state.aktif_sayim_adi is None:
            st.info("ℹ️ Şu an açık bir sayım oturumu bulunmuyor. Yeni bir sayım başlatabilirsiniz.")
            with st.container(border=True):
                sayim_etiketi = st.text_input("Sayım Oturumu İsmi (Örn: A_Blok, Yil_Sonu):", placeholder="Oturum adı girin...")
                if st.button("🚀 YENİ SAYIM BAŞLAT", use_container_width=True, type="primary"):
                    if sayim_etiketi:
                        zaman = datetime.now().strftime("%d%m_%H%M")
                        st.session_state.aktif_sayim_adi = f"{sayim_etiketi}_{zaman}"
                        st.success(f"✅ '{st.session_state.aktif_sayim_adi}' oturumu başlatıldı! Artık 'Sayım Girişi' ekranından veri girebilirsiniz.")
                        st.rerun()
                    else:
                        st.warning("Lütfen bir oturum ismi girin!")
        else:
            st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
            st.info("Bu oturum açık olduğu sürece girilen tüm sayımlar bu etikete kaydedilecektir.")
            if st.button("🛑 OTURUMU KAPAT (Sayımı Tamamla)", type="primary"):
                st.session_state.aktif_sayim_adi = None
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Oturum başarıyla kapatıldı.")
                st.rerun()

    # ==========================================
    # 2. SAYIM GİRİŞİ EKRANI
    # ==========================================
    elif st.session_state.sayim_page == 'giris':
        if st.button("⬅️ GERİ"): 
            go_sayim_menu()
            st.rerun()
            
        st.subheader("📝 Sayım Girişi")
        st.markdown("---")
        
        if st.session_state.aktif_sayim_adi is None:
            st.warning("⚠️ Lütfen önce 'Oturum Yönetimi' menüsünden yeni bir sayım başlatın!")
        else:
            st.success(f"Kayıt Yapılan Oturum: {st.session_state.aktif_sayim_adi}")
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
                        "Oturum_Adi": st.session_state.aktif_sayim_adi,
                        "Tarih": veritabani.get_local_time(), 
                        "Adres": s_adr, 
                        "Kod": s_kod, 
                        "İsim": s_isim,
                        "Miktar": s_mik,
                        "Birim": "-", 
                        "Personel": st.session_state.user, 
                        "Durum": s_durum
                    })
                    st.toast("Listeye eklendi")
            
            if st.session_state['gecici_sayim_listesi']:
                st.write("---")
                for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                    cols = st.columns([3, 1])
                    cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']}")
                    
                    if st.session_state.delete_confirm == idx:
                        c_del, c_esc = cols[1].columns(2)
                        if c_del.button("✅", key=f"conf_{idx}"):
                            st.session_state['gecici_sayim_listesi'].pop(idx)
                            st.session_state.delete_confirm = None
                            st.rerun()
                        if c_esc.button("❌", key=f"esc_{idx}"):
                            st.session_state.delete_confirm = None
                            st.rerun()
                    else:
                        if cols[1].button("🗑️", key=f"del_{idx}"):
                            st.session_state.delete_confirm = idx
                            st.rerun()
                
                if st.button("📤 VERİLERİ EXCEL'E GÖNDER", type="primary", use_container_width=True):
                    mevcut_sayim_verisi = veritabani.get_internal_data("sayim")
                    yeni_eklenenler = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                    veritabani.update_data("sayim", pd.concat([mevcut_sayim_verisi, yeni_eklenenler], ignore_index=True))
                    st.session_state['gecici_sayim_listesi'] = []
                    st.success("Veriler ana sayım veritabanına kaydedildi!")
                    st.rerun()

    # ==========================================
    # 3. FARK RAPORU EKRANI
    # ==========================================
    elif st.session_state.sayim_page == 'rapor':
        if st.button("⬅️ GERİ"): 
            go_sayim_menu()
            st.rerun()
            
        st.subheader("📊 Fark Raporu")
        st.markdown("---")
        
        df_sayim_ana = veritabani.get_internal_data("sayim")
        df_stok = veritabani.get_internal_data("Stok")

        if not df_sayim_ana.empty:
            if 'Oturum_Adi' not in df_sayim_ana.columns:
                df_sayim_ana['Oturum_Adi'] = "ESKI_SAYIMLAR"
            
           mevcut_oturumlar = df_sayim_ana['Oturum_Adi'].dropna().unique().tolist()
            
            varsayilan_index = 0
            if st.session_state.aktif_sayim_adi and st.session_state.aktif_sayim_adi in mevcut_oturumlar:
                varsayilan_index = mevcut_oturumlar.index(st.session_state.aktif_sayim_adi)
            
            if mevcut_oturumlar:
                secilen_oturum = st.selectbox("Görüntülemek istediğiniz sayım oturumunu seçin:", mevcut_oturumlar, index=varsayilan_index)
                df_sayim = df_sayim_ana[df_sayim_ana['Oturum_Adi'] == secilen_oturum].copy()
            else:
                df_sayim = pd.DataFrame()
        else:
            df_sayim = pd.DataFrame()

        if not df_sayim.empty:
            df_sayim['Miktar'] = pd.to_numeric(df_sayim['Miktar'], errors='coerce').fillna(0)
            s_ozet = df_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
            s_ozet.rename(columns={'Miktar': 'Miktar_Sayilan'}, inplace=True)
            
            if not df_stok.empty:
                df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)
                st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
                st_ozet.rename(columns={'Miktar': 'Miktar_Sistem'}, inplace=True)
            else:
                st_ozet = pd.DataFrame(columns=['Adres', 'Kod', 'Miktar_Sistem'])
            
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            
            isim_sozlugu = {}
            if not df_stok.empty and 'İsim' in df_stok.columns:
                isim_sozlugu.update(df_stok.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            if 'İsim' in df_sayim.columns:
                isim_sozlugu.update(df_sayim.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            
            rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
            rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
            
            # --- YENİ EKLENEN FİLTRELER ---
            st.markdown("#### 🔍 Rapor Filtreleri")
            katalog = veritabani.get_katalog()
            f_sec = st.selectbox("🔍 Ürün Seç (Katalogdan Filtrele):", ["+ MANUEL (TÜMÜ)"] + katalog)
            
            rf1, rf2, rf3 = st.columns(3)
            f_adr = rf1.text_input("📍 Adres Filtre:").upper()
            
            oto_kod = f_sec.split(" | ")[0] if f_sec != "+ MANUEL (TÜMÜ)" else ""
            oto_isim = f_sec.split(" | ")[1] if f_sec != "+ MANUEL (TÜMÜ)" and len(f_sec.split(" | ")) > 1 else ""
            
            f_kod = rf2.text_input("📦 Kod Filtre:", value=oto_kod).upper()
            f_isim = rf3.text_input("📝 İsim Filtre:", value=oto_isim).upper()
            
            if f_adr: rapor = rapor[rapor['Adres'].astype(str).str.contains(f_adr, case=False, na=False)]
            if f_kod: rapor = rapor[rapor['Kod'].astype(str).str.contains(f_kod, case=False, na=False)]
            if f_isim: rapor = rapor[rapor['İsim'].astype(str).str.contains(f_isim, case=False, na=False)]
            
            st.markdown("---")
            m1, m2 = st.columns(2)
            m1.metric("Toplam Sayılan", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
            m2.metric("Toplam Fark", f"{rapor['FARK'].sum():,.0f}")
            # ------------------------------
            
            def color_diff(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
            st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                rapor.to_excel(writer, index=False, sheet_name='Fark_Raporu')
            st.download_button("📥 FARK RAPORUNU İNDİR", data=buffer.getvalue(), file_name=f"Fark_{secilen_oturum}.xlsx", use_container_width=True)

            st.markdown("---")
            if st.session_state.aktif_sayim_adi == secilen_oturum:
                st.warning("⚠️ Bu butona basıldığında gerçek stoklarınız bu sayım verileriyle GÜNCELLENİR.")
                onay = st.checkbox("Verilerin doğruluğunu onaylıyorum.")
                
                if st.button("🚀 STOK VERİTABANINI BU SAYIMLA EŞİTLE", disabled=not onay, type="primary", use_container_width=True):
                    try:
                        sayilan_kodlar = rapor['Kod'].unique().tolist()
                        if not df_stok.empty:
                            kalan_stok_df = df_stok[~df_stok['Kod'].isin(sayilan_kodlar)].copy()
                        else:
                            kalan_stok_df = pd.DataFrame()
                        
                        yeni_sayim_df = rapor[['Kod', 'İsim', 'Miktar_Sayilan', 'Adres', 'Durum']].copy()
                        yeni_sayim_df.rename(columns={'Miktar_Sayilan': 'Miktar'}, inplace=True)
                        yeni_sayim_df = yeni_sayim_df[yeni_sayim_df['Miktar'] > 0]
                        
                        guncel_tam_stok = pd.concat([kalan_stok_df, yeni_sayim_df], ignore_index=True)
                        veritabani.update_data("Stok", guncel_tam_stok)
                        
                        st.success("✅ Stoklar güncellendi! İşleminiz tamamlandı.")
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Güncelleme hatası: {e}")
            else:
                st.info("🔒 Şu an geçmiş bir sayım oturumunu (arşiv) görüntülüyorsunuz. Geçmiş sayımlarla stok güncellenemez. İşlem yapmak için bu oturumu aktif etmelisiniz.")
        else:
            st.info("Bu oturuma ait bir sayım verisi bulunmuyor.")
