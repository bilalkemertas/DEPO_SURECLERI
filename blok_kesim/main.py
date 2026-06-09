import streamlit as st
import pandas as pd
from datetime import datetime

# Alt modüllerden importlar
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi, karakter_match
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn):
    st.subheader("🧱 Blok & Rulo Sünger Kesim Otomasyonu")
    
    # 1. State Başlatma
    init_blok_kesim_state()
    
    # Local Eşleşme Matrisini Cache'e Al veya Yükle
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
        
    # 2. Veritabanından Canlı Veri Çekimi
    stok_df, har_df = fetch_live_data()
    if stok_df.empty:
        st.warning("Stok verisi yüklenemedi veya boş.")
        return

    # 3. Dosya Yükleme Alanı (İş Emri Kesim Listesi)
    up = st.file_uploader("📋 Kesim Listesi Excel Dosyasını Yükleyin", type=["xlsx", "xls"])
    
    if up is not None:
        try:
            # Akıllı Başlık Satırı Avcısı (Dynamic Header Row Finder)
            raw_df = pd.read_excel(up, header=None)
            header_idx = 0
            tanim_col = None
            miktar_col = None
            
            # İlk 20 satırı tarayarak başlıkları bul
            for i in range(min(20, len(raw_df))):
                row_vals = [str(x).lower() for x in raw_df.iloc[i].dropna()]
                if any(k in row_vals for k in ["ürün", "tanım", "malzeme", "plaka", "adet", "miktar"]):
                    header_idx = i
                    break
                    
            df_kesim = pd.read_excel(up, header=header_idx)
            df_kesim.columns = [str(c).strip() for c in df_kesim.columns]
            
            # Kolon Yakalama
            for col in df_kesim.columns:
                c_low = col.lower()
                if "tanım" in c_low or "ürün" in c_low or "malzeme" in c_low:
                    tanim_col = col
                if "adet" in c_low or "miktar" in c_low or "plan" in c_low:
                    miktar_col = col
                    
            if not tanim_col or not miktar_col:
                st.error("Excel sütunlarında 'Ürün Tanımı' veya 'Miktar/Adet' alanları tespit edilemedi!")
                return
                
            st.success("✅ Kesim Listesi Başarıyla Çözümlendi!")
            
            # 4. Barkod Girişi ve Blok Seçim Alanı
            st.markdown("### 🔍 Kesilecek Hammadde / Blok Seçimi")
            barkod = st.text_input("🎯 Blok Barkodunu Okutun veya Kod Girin:", key="blok_barkod_input").strip()
            
            if barkod:
                # Stok Kartı Filtreleme (Zırhlı Arama)
                barkod_col = None
                for c in stok_df.columns:
                    if "barkod" in c.lower() or "kod" in c.lower():
                        barkod_col = c
                        break
                        
                if not barkod_col:
                    st.error("Stok veritabanında barkod/kod sütunu bulunamadı.")
                    return
                    
                match_blok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)]
                
                if not match_blok.empty:
                    blok = match_blok.iloc[0].to_dict()
                    blok_isim = blok.get('İsim', blok.get('Stok Adı', ''))
                    blok_kod = blok.get('Kod', blok.get('Stok Kodu', ''))
                    
                    st.info(f"📦 **Bulunan Blok:** {blok_isim} | **Mevcut Miktar:** {blok.get('Miktar', 0)} cm/Mt")
                    
                    # Blok Ölçülerini Ayıkla
                    blok_info = ayikla_karakter_ve_olcu(blok_isim)
                    mevcut_miktar = safe_float(blok.get('Miktar', 0))
                    
                    # İş Emri Eşleşme Hesaplamaları
                    uygun_satirlar = []
                    toplam_dusulecek_cm = 0.0
                    
                    for idx, row in df_kesim.iterrows():
                        urun_adi = row.get(tanim_col, "")
                        if pd.isna(urun_adi) or str(urun_adi).strip() == "":
                            continue
                            
                        plaka_info = ayikla_karakter_ve_olcu(urun_adi)
                        
                        # Karakter, Kalite ve Verim Kontrolü
                        karakter_ok = karakter_match(plaka_info['karakter'], blok_info['karakter'])
                        
                        # Matris üzerinden kod sorgulama (Yedek zırh)
                        matris_ok = False
                        if not st.session_state.eslesme_df.empty:
                            m_match = st.session_state.eslesme_df[
                                st.session_state.eslesme_df['BAĞLI BLOK STOK KODU'].astype(str).str.strip() == str(blok_kod)
                            ]
                            if not m_match.empty:
                                matris_ok = True
                        
                        if karakter_ok or matris_ok:
                            verim = plaka_sayisi_hesapla(plaka_info, blok_info)
                            if verim > 0:
                                siparis_adet = safe_float(row.get(miktar_col, 0))
                                gereken_dilim = math.ceil(siparis_adet / verim) if verim else 0
                                kalinlik = plaka_info['kalinlik']
                                harcanacak_cm = gereken_dilim * kalinlik
                                
                                uygun_satirlar.append({
                                    "Plaka Adı": urun_adi,
                                    "Sipariş Adet": siparis_adet,
                                    "Bloktan Çıkan": verim,
                                    "Gereken Dilim": gereken_dilim,
                                    "Harcanacak (cm)": harcanacak_cm
                                })
                                toplam_dusulecek_cm += harcanacak_cm
                                
                    if uygun_satirlar:
                        st.markdown("#### 📊 Eşleşen ve Kesilebilecek Plaka Detayları")
                        st.table(pd.DataFrame(uygun_satirlar))
                        
                        # Metrik Paneli
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Mevcut Stok (cm)", f"{mevcut_miktar:.2f}")
                        c_m2.metric("Düşülecek Toplam (cm)", f"{toplam_dusulecek_cm:.2f}")
                        
                        if mevcut_miktar < toplam_dusulecek_cm:
                            st.error("❌ Stok yetersiz! Seçilen bloktan bu siparişlerin tamamı kesilemez.")
                        else:
                            # 5. KESİM ONAY BUTONU VE TRANSACTION MANTIĞI
                            if st.button("🚀 KESİMİ ONAYLA VE STOKTAN DÜŞ", type="primary"):
                                # Stok Güncelleme
                                idx_stok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)].index
                                stok_df.loc[idx_stok, 'Miktar'] = mevcut_miktar - toplam_dusulecek_cm
                                
                                # Hareket Kaydı Logu Oluşturma
                                yeni_log = pd.DataFrame([{
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Barkod": barkod,
                                    "Stok Kodu": blok_kod,
                                    "Stok Adı": blok_isim,
                                    "İşlem": "KESİM/SARF",
                                    "Miktar": toplam_dusulecek_cm,
                                    "Personel": st.session_state.get('kullanici_adi', 'Otomasyon Sorumlusu'),
                                    "Durum": "Tamamlandı"
                                }])
                                
                                # Veritabanına Yazma
                                success = update_stock_and_logs(stok_df, yeni_log)
                                if success:
                                    st.balloons()
                                    st.success("🎉 Kesim işlemi başarıyla tamamlandı ve veritabanı güncellendi!")
                                    st.rerun()
                    else:
                        st.error("❌ Okutulan blok kalitesi veya ölçüsü, yüklenen listedeki hiçbir ürünle matris bazında eşleşmedi!")
                else:
                    st.error("❌ Okutulan barkoda ait hammadde/blok stokta bulunamadı!")
                    
        except Exception as e:
            st.error(f"Dosya okuma esnasında kritik hata oluştu: {e}")
            
    st.markdown("---")
    st.markdown("🚀 Bilal Kemertaş BRN 2026", unsafe_allow_html=True)
