import streamlit as st
import pandas as pd
import math
from datetime import datetime

# Paket içi alt modüllerden işlevsel fonksiyonları çağırıyoruz
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi, karakter_match
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn):
    st.subheader("🧱 Blok & Rulo Sünger Kesim Otomasyonu")
    
    # 1. State Yönetim Mekanizmasını Başlat
    init_blok_kesim_state()
    
    # Yerel Eşleşme Matrisini Belleğe Al (Cache Koruma)
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
        
    # 2. Veritabanından Stok ve Hareketler Verilerini Çek
    stok_df, har_df = fetch_live_data()
    if stok_df.empty:
        st.warning("⚠️ Stok verisi veritabanından yüklenemedi veya tablo boş.")
        return

    # 3. Dosya Yükleme Alanı (Kesim / İş Emri Listesi)
    up = st.file_uploader("📋 Kesim Listesi Excel Dosyasını Yükleyin", type=["xlsx", "xls"])
    
    if up is not None:
        try:
            # Akıllı Başlık Satırı Avcısı (Zırhlı Versiyon)
            raw_df = pd.read_excel(up, header=None)
            header_idx = 0
            tanim_col = None
            miktar_col = None
            
            # İlk 20 satırı agresif şekilde tarayarak başlık satırını bulur
            for i in range(min(20, len(raw_df))):
                row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].dropna().values]
                row_str = " ".join(row_vals)
                
                # Sütunları yakalamak için esnek anahtar kelime varyasyonları
                has_tanim = any(k in row_str for k in ["TANIM", "ÜRÜN", "URUN", "MALZEME", "PLAKA", "Plaka Adı"])
                has_miktar = any(k in row_str for k in ["Adet", "MİKTAR", "MIKTAR", "PLAN", "ADEDİ", "ADEDI"])
                
                if has_tanim and has_miktar:
                    header_idx = i
                    break
                    
            # Belirlenen doğru satırdan itibaren Excel'i oku
            df_kesim = pd.read_excel(up, header=header_idx)
            # Sütun başlıklarındaki sağ-sol görünmez boşlukları temizle
            df_kesim.columns = [str(c).strip() for c in df_kesim.columns]
            
            # Kolon Yakalama Motoru (Regex ve İçerik Bazlı)
            for col in df_kesim.columns:
                c_upper = col.upper()
                
                # Ürün Tanımı / Plaka Sütunu Yakalayıcı
                if any(k in c_upper for k in ["TANIM", "ÜRÜN", "URUN", "MALZEME", "PLAKA"]):
                    tanim_col = col
                
                # Miktar / Adet Sütunu Yakalayıcı
                if any(k in c_upper for k in ["ADET", "MİKTAR", "MIKTAR", "PLAN", "ADEDİ", "ADEDI", "TOPLAM"]):
                    miktar_col = col
                    
            # ZIRH SİGORTASI: Eğer otomatik algılanamadıysa arayüzden personele seçtir (Fallback Modu)
            if not tanim_col or not miktar_col:
                st.error("⚠️ Sütunlar Otomatik Tespit Edilemedi!")
                st.info(f"💡 Excel'inizdeki Sütunlar: {list(df_kesim.columns)}")
                
                c_sel1, c_sel2 = st.columns(2)
                tanim_col = c_sel1.selectbox("🎯 Ürün Tanımı / Plaka Sütununu Seçin:", df_kesim.columns, index=0)
                miktar_col = c_sel2.selectbox("🔢 Adet / Miktar Sütununu Seçin:", df_kesim.columns, index=min(1, len(df_kesim.columns)-1))
            
            st.success(f"✅ Eşleşme Başarılı! (Eşleşenler -> Ürün: '{tanim_col}', Miktar: '{miktar_col}')")
            
            # 4. Barkod Okutma ve Blok Seçim Katmanı
            st.markdown("### 🔍 Kesilecek Hammadde / Blok Seçimi")
            barkod = st.text_input("🎯 Blok Barkodunu Okutun veya Kod Girin:", key="blok_barkod_input").strip()
            
            if barkod:
                # Stok Tablosunda Barkod Sütununu Bul (Dinamik Sütun Dedektörü)
                barkod_col = None
                for c in stok_df.columns:
                    if "barkod" in c.lower() or "kod" in c.lower():
                        barkod_col = c
                        break
                        
                if not barkod_col:
                    st.error("❌ Stok veritabanında barkod/kod sütunu bulunamadı.")
                    return
                    
                match_blok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)]
                
                if not match_blok.empty:
                    blok = match_blok.iloc[0].to_dict()
                    blok_isim = blok.get('İsim', blok.get('Stok Adı', ''))
                    blok_kod = blok.get('Kod', blok.get('Stok Kodu', ''))
                    
                    st.info(f"📦 **Bulunan Blok:** {blok_isim} | **Mevcut Miktar:** {blok.get('Miktar', 0)} cm/Mt")
                    
                    # Blok Ölçülerini ve Kalitesini regex ile çöz
                    blok_info = ayikla_karakter_ve_olcu(blok_isim)
                    mevcut_miktar = safe_float(blok.get('Miktar', 0))
                    
                    # İş Emri Listesindeki Ürünlerin Blok ile Uyumluluğunu Hesapla
                    uygun_satirlar = []
                    toplam_dusulecek_cm = 0.0
                    
                    for idx, row in df_kesim.iterrows():
                        urun_adi = row.get(tanim_col, "")
                        if pd.isna(urun_adi) or str(urun_adi).strip() == "":
                            continue
                            
                        plaka_info = ayikla_karakter_ve_olcu(urun_adi)
                        
                        # Kalite, Yoğunluk (DNS) ve Karakter Eşleşme Doğrulaması
                        karakter_ok = karakter_match(plaka_info['karakter'], blok_info['karakter'])
                        
                        # Eşleşme matrisi üzerinden kod kontrolü (Yedek Zırh)
                        matris_ok = False
                        if not st.session_state.eslesme_df.empty:
                            m_match = st.session_state.eslesme_df[
                                st.session_state.eslesme_df['BAĞLI BLOK STOK KODU'].astype(str).str.strip() == str(blok_kod)
                            ]
                            if not m_match.empty:
                                matris_ok = True
                        
                        if karakter_ok or matris_ok:
                            # Blok Verimliliğini (En-Boy Kombinasyon) Hesapla
                            verim = plaka_sayisi_hesapla(plaka_info, blok_info)
                            if verim > 0:
                                siparis_adet = safe_float(row.get(miktar_col, 0))
                                gereken_dilim = math.ceil(siparis_adet / verim) if verim
