import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")

    # Geçici listeyi güvenceye alalım
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []

    # --- OTURUM YÖNETİMİ ---
    if 'aktif_sayim_adi' not in st.session_state:
        st.session_state.aktif_sayim_adi = None

    if st.session_state.aktif_sayim_adi is None:
        st.info("ℹ️ Şu an açık bir sayım oturumu bulunmuyor. İşlem yapmak için yeni bir sayım başlatmalısınız.")
        with st.container(border=True):
            sayim_etiketi = st.text_input("Sayım Oturumu İsmi (Örn: A_Blok, Yil_Sonu):", placeholder="Oturum adı girin...")
            if st.button("🚀 YENİ SAYIM BAŞLAT", use_container_width=True, type="primary"):
                if sayim_etiketi:
                    zaman = datetime.now().strftime("%d%m_%H%M")
                    # İsmi oluştur ama yeni sekme açma, bunu etiket olarak kullanacağız
                    st.session_state.aktif_sayim_adi = f"{sayim_etiketi}_{zaman}"
                    st.success(f"✅ '{st.session_state.aktif_sayim_adi}' oturumu başlatıldı! Veriler ana sayım listesine bu etiketle yazılacak.")
                    st.rerun()
                else:
                    st.warning("Lütfen bir oturum ismi girin!")
        return

    st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
    if st.button("🛑 OTURUMU KAPAT (Yeni Sayım İçin)"):
        st.session_state.aktif_sayim_adi = None
        st.session_state['gecici_sayim_listesi'] = []
        st.rerun()

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
                    "Oturum_Adi": st.session_state.aktif_sayim_adi, # YENİ: Oturum etiketi veritabanına gidiyor!
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
                if cols[1].button("🗑️", key=f"del_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.rerun()
            
            if st.button("📤 VERİLERİ EXCEL'E GÖNDER", type="primary", use_container_width=True):
                # Her şeyi mevcut 'sayim' sekmesine gönderiyoruz
                mevcut_sayim_verisi = veritabani.get_internal_data("sayim")
                yeni_eklenenler = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                veritabani.update_data("sayim", pd.concat([mevcut_sayim_verisi, yeni_eklenenler], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veriler ana sayım veritabanına kaydedildi!")
                st.rerun()

   with t2:
        df_sayim_ana = veritabani.get_internal_data("sayim")
        df_stok = veritabani.get_internal_data("Stok")

        if not df_sayim_ana.empty:
            # Geçmiş uyumluluğu korumak için, eski verilerde Oturum_Adi yoksa "ESKI_SAYIMLAR" yap
            if 'Oturum_Adi' not in df_sayim_ana.columns:
                df_sayim_ana['Oturum_Adi'] = "ESKI_SAYIMLAR"
            
            # --- YENİ: GEÇMİŞ OTURUMLARI GÖRÜNTÜLEME MENÜSÜ ---
            st.markdown("#### 🗂️ Sayım Oturumu Seçimi")
            mevcut_oturumlar = df_sayim_ana['Oturum_Adi'].dropna().unique().tolist()
            
            # Eğer aktif bir sayım varsa, açılır menüde otomatik olarak onu seçili getir
            varsayilan_index = 0
            if st.session_state.aktif_sayim_adi and st.session_state.aktif_sayim_adi in mevcut_oturumlar:
                varsayilan_index = mevcut_oturumlar.index(st.session_state.aktif_sayim_adi)
            
            # Kullanıcı hangi raporu görmek istiyorsa seçsin
            if mevcut_oturumlar:
                secilen_oturum = st.selectbox("Görüntülemek istediğiniz sayım oturumunu (arşivi) seçin:", mevcut_oturumlar, index=varsayilan_index)
                # Tabloyu sadece seçilen oturuma göre filtrele
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
            
            # İsimleri doldurma mekanizması
            isim_sozlugu = {}
            if not df_stok.empty and 'İsim' in df_stok.columns:
                isim_sozlugu.update(df_stok.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            if 'İsim' in df_sayim.columns:
                isim_sozlugu.update(df_sayim.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            
            rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
            rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
            
            # Tablo gösterimi
            def color_diff(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
            st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)

            # --- Excel İndirme ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                rapor.to_excel(writer, index=False, sheet_name='Fark_Raporu')
            st.download_button("📥 FARK RAPORUNU İNDİR", data=buffer.getvalue(), file_name=f"Fark_{secilen_oturum}.xlsx", use_container_width=True)

            # --- Stok Güncelleme ---
            st.markdown("---")
            # GÜVENLİK KONTROLÜ: Sadece AKTİF oturum görüntülendiğinde güncellemeye izin ver
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
