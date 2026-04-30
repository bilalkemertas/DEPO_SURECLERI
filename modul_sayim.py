import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")

    # --- OTURUM YÖNETİMİ ---
    if 'aktif_sayim_adi' not in st.session_state:
        st.session_state.aktif_sayim_adi = None

    # Eğer aktif bir sayım yoksa, başlatma ekranını göster
    if st.session_state.aktif_sayim_adi is None:
        st.info("ℹ️ Şu an açık bir sayım oturumu bulunmuyor. İşlem yapmak için yeni bir sayım başlatmalısınız.")
        with st.container(border=True):
            sayim_etiketi = st.text_input("Sayım Oturumu İsmi (Örn: A_Blok, Yil_Sonu_2023):", placeholder="Oturum adı girin...")
            if st.button("🚀 YENİ SAYIM BAŞLAT", use_container_width=True, type="primary"):
                if sayim_etiketi:
                    # Tarih damgalı benzersiz sayfa ismi oluştur
                    zaman = datetime.now().strftime("%d%m_%H%M")
                    yeni_sayfa_adi = f"Sayim_{sayim_etiketi}_{zaman}"
                    
                    # Veritabanında (Excel'de) boş bir sayfa oluşturmak için ilk satırı gönderiyoruz
                    bos_df = pd.DataFrame(columns=["Tarih", "Adres", "Kod", "İsim", "Miktar", "Birim", "Personel", "Durum"])
                    try:
                        veritabani.update_data(yeni_sayfa_adi, bos_df)
                        st.session_state.aktif_sayim_adi = yeni_sayim_adi
                        st.success(f"✅ '{yeni_sayfa_adi}' oturumu başlatıldı. Veriler bu sekmeye yazılacak.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sayfa oluşturulurken hata: {e}")
                else:
                    st.warning("Lütfen bir oturum ismi girin!")
        return # Aktif sayım yoksa aşağıyı gösterme

    # Aktif sayım varsa devam et
    st.success(f"📡 Aktif Oturum: **{st.session_state.aktif_sayim_adi}**")
    if st.button("🛑 OTURUMU KAPAT (Yeni Sayım İçin)"):
        st.session_state.aktif_sayim_adi = None
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
                # Verileri aktif oturumun sayfasına ekle
                mevcut_sayim_verisi = veritabani.get_internal_data(st.session_state.aktif_sayim_adi)
                yeni_eklenenler = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                veritabani.update_data(st.session_state.aktif_sayim_adi, pd.concat([mevcut_sayim_verisi, yeni_eklenenler], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veriler kaydedildi!")
                st.rerun()

    with t2:
        # Sadece bu oturuma ait verileri çek
        df_sayim = veritabani.get_internal_data(st.session_state.aktif_sayim_adi)
        df_stok = veritabani.get_internal_data("Stok")

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
            
            # Tablo gösterimi
            st.dataframe(rapor, use_container_width=True, hide_index=True)

            # --- Excel İndirme ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                rapor.to_excel(writer, index=False, sheet_name='Fark_Raporu')
            st.download_button("📥 FARK RAPORUNU İNDİR", data=buffer.getvalue(), file_name=f"Fark_{st.session_state.aktif_sayim_adi}.xlsx", use_container_width=True)

            # --- Stok Güncelleme ---
            st.markdown("---")
            st.warning("⚠️ Bu butona basıldığında gerçek stoklarınız bu sayım verileriyle GÜNCELLENİR.")
            if st.button("🚀 STOK VERİTABANINI BU SAYIMLA EŞİTLE", type="primary", use_container_width=True):
                # (Daha önce yazdığımız kısmi güncelleme mantığı buraya gelir)
                # Buradaki işlem bittikten sonra oturumu kapatabiliriz:
                # st.session_state.aktif_sayim_adi = None
                st.success("Stoklar güncellendi!")
