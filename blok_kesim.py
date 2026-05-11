import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def run_blok_kesim(conn):
    # --- 1. AYIKLAMA MOTORU (Regex - Geliştirilmiş) ---
    def ayikla_malzeme_detay(tanim):
        if pd.isna(tanim): return None
        text = str(tanim).upper()
        # 188X158X1 veya 188X158 formatını yakala
        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)(?:\s*[Xx]\s*(\d+))?', text)
        
        if not olcu: return None

        boy, en, yuk = olcu.groups()
        return {
            "boy": float(boy),
            "en": float(en),
            "kalinlik": float(yuk) if yuk else None, # Kalınlık yoksa None (hata için)
            "ozellik": text[:olcu.start()].strip()
        }

    # --- NAVİGASYON ---
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 4])
    with c_back1:
        if st.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.page = 'home'; st.rerun()
    with c_back2:
        if st.session_state.get('main_data') is not None:
            if st.button("⬅️ TEMİZLE", use_container_width=True):
                for k in ['main_data', 'stok_data']: 
                    if k in st.session_state: del st.session_state[k]
                st.rerun()

    st.title("✂️ Blok & Rulo Kesim Operasyonu")

    # --- 2. VERİ YÜKLEME ---
    with st.container(border=True):
        uploaded_file = st.file_uploader("Kesim Listesi Yükle (Excel)", type=['xlsx'], key="bk_uploader")
        if uploaded_file and 'main_data' not in st.session_state:
            try:
                st.session_state['main_data'] = pd.read_excel(uploaded_file)
                st.session_state['stok_data'] = veritabani.get_internal_data("Stok")
                st.success("✅ Kesim listesi ve güncel stok yüklendi.")
            except Exception as e: st.error(f"Hata: {e}")

    # --- 3. OPERASYON EKRANI ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        df.columns = [str(c).strip() for c in df.columns]
        
        st.divider()
        parti_no = st.text_input("🔍 Kesilecek Parti No Okutun:").strip()

        if parti_no:
            match = df[df['Parti No'].astype(str) == parti_no]
            
            if not match.empty:
                item = match.iloc[0]
                detay = ayikla_malzeme_detay(item['Malzeme Tanımı'])
                
                # KRİTİK KALINLIK KONTROLÜ
                if not detay or detay['kalinlik'] is None:
                    st.error("❌ Hata: Malzeme adında kalınlık bilgisi bulunamadı! (Örn: 188X158X1 olmalı)"); st.stop()

                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info(f"**Üretilecek:** {detay['ozellik']}\n\n**Ölçü:** {detay['boy']}x{detay['en']} cm | **Kalınlık:** {detay['kalinlik']} cm")
                    with c2:
                        adet = float(item.get('Miktar', 0))
                        net_tuketim = adet * detay['kalinlik']
                        st.warning(f"**Net Kesim:** {net_tuketim} cm\n\n**Planlanan Blok:** {item.get('Kullanılacak BlokCM', 'Belirtilmemiş')}")

                    st.divider()
                    st.write("📍 **Gerçek Stoktan Blok Seçimi**")
                    
                    # STOKTAN UYGUN BLOKLARI BUL (Boy ve En eşleşen, Miktarı (Yüksekliği) olanlar)
                    stok_df = st.session_state['stok_data']
                    # Stoktaki blokların ölçülerini ayıkla ve filtrele
                    stok_df['detay'] = stok_df['İsim'].apply(ayikla_malzeme_detay)
                    
                    def uygun_mu(s_detay):
                        if not s_detay: return False
                        return s_detay['boy'] == detay['boy'] and s_detay['en'] == detay['en']

                    uygun_bloklar = stok_df[stok_df['detay'].apply(uygun_mu) & (stok_df['Miktar'] > 0)]

                    if not uygun_bloklar.empty:
                        # Blok seçimi için liste hazırla
                        blok_options = [f"{row['Kod']} | {row['İsim']} | Kalan: {row['Miktar']} cm" for _, row in uygun_bloklar.iterrows()]
                        secilen_blok_str = st.selectbox("Kesilecek Bloğu Seçin:", blok_options)
                        
                        secilen_kod = secilen_blok_str.split(" | ")[0]
                        secilen_row = uygun_bloklar[uygun_bloklar['Kod'] == secilen_kod].iloc[0]
                        
                        # FIRE MANTIĞI: Blok daha önce kesildi mi?
                        # Hareketler tablosuna bakarak bu blok kodunun daha önce "GİRİŞ" harici bir işlemi var mı kontrol edilebilir.
                        # Şimdilik kullanıcıya soralım veya ilk kesim olup olmadığını miktarından tahmin edelim.
                        is_first_cut = st.toggle("🚨 Blok İlk Kez mi Kesiliyor? (2 cm Kapak Firesi Eklensin mi?)", value=False)
                        fire = 2.0 if is_first_cut else 0.0
                        toplam_dusulecek = net_tuketim + fire

                        st.metric("Bloktan Düşecek Toplam", f"{toplam_dusulecek} cm", delta=f"Fire: {fire} cm", delta_color="inverse")

                        if st.button("🔥 KESİMİ ONAYLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                            if secilen_row['Miktar'] < toplam_dusulecek:
                                st.error("❌ Hata: Blok yüksekliği yetersiz!"); st.stop()
                            
                            # 1. Stok Güncelle (Yükseklik Düş)
                            stok_df.loc[stok_df['Kod'] == secilen_kod, 'Miktar'] -= toplam_dusulecek
                            
                            # 2. Hareket Kaydı At
                            df_har = veritabani.get_internal_data("Hareketler")
                            yeni_har = pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "İşlem": "KESİM/SARF",
                                "İş Emri": parti_no,
                                "Kod": secilen_kod,
                                "İsim": secilen_row['İsim'],
                                "Miktar": toplam_dusulecek,
                                "Personel": "Bilal",
                                "Lot": "-", "Adres": secilen_row['Adres'], "Durum": "Kullanıldı"
                            }])
                            df_har = pd.concat([df_hr, yeni_har] if 'df_hr' in locals() else [df_har, yeni_har], ignore_index=True)

                            # Veritabanını Güncelle
                            veritabani.update_data("Stok", stok_df.drop(columns=['detay']))
                            veritabani.update_data("Hareketler", df_har)
                            
                            st.balloons(); st.success(f"✅ {parti_no} kaydedildi. Blok kalan: {secilen_row['Miktar'] - toplam_dusulecek} cm")
                            del st.session_state['stok_data']; st.rerun()
                    else:
                        st.error("❌ Stokta uygun ölçülerde (Boy x En) blok bulunamadı!")
            else: st.error("Parti No bulunamadı.")

    st.markdown("---")
    st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
