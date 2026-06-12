import streamlit as st
import pandas as pd
import math
from datetime import datetime
import veritabani
from blok_kesim.state import init_blok_kesim_state
from blok_kesim.matching import load_local_eslesme_matrisi, karakter_match
from blok_kesim.database import fetch_live_data, update_stock_and_logs
from blok_kesim.data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn):
    """Ana blok kesim işlem ekranı"""
    
    # State Başlatma
    init_blok_kesim_state()
    
    # Eşleşme Matrisini Cache'le
    if st.session_state.get('eslesme_df') is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
    
    # Veritabanı Verilerini Çek
    stok_df, har_df = fetch_live_data()
    if stok_df.empty:
        st.error("❌ Stok veri yüklenemedi", icon="🔴")
        return
    
    st.markdown("### ✂️ KESİM KONTROL PANELİ")
    
    # Sidebar Kontrolleri
    with st.sidebar:
        st.markdown("#### 📋 İş Emri")
        up = st.file_uploader("Excel dosyası seçin", type=["xlsx", "xls"], key="isemri_uploader")
        barkod = st.text_input("Blok barkodunu okutun", key="barkod_input").strip()

    if up is None:
        st.info("📋 Sol panelden Excel dosyası yükleyerek başlayın.")
        return
    
    try:
        # Excel İşleme
        df_kesim = pd.read_excel(up)
        df_kesim.columns = [str(c).strip() for c in df_kesim.columns]
        
        # Basit Sütun Tespiti
        tanim_col = [c for c in df_kesim.columns if any(k in c.upper() for k in ["TANIM", "ÜRÜN", "PLAKA"])][0]
        miktar_col = [c for c in df_kesim.columns if any(k in c.upper() for k in ["ADET", "MİKTAR"])][0]
        
        if barkod:
            barkod_col = [c for c in stok_df.columns if "barkod" in c.lower() or "kod" in c.lower()][0]
            match_blok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)]
            
            if not match_blok.empty:
                blok = match_blok.iloc[0].to_dict()
                blok_isim = blok.get('İsim', '')
                blok_kod = blok.get('Kod', '')
                blok_info = ayikla_karakter_ve_olcu(blok_isim)
                mevcut_miktar = safe_float(blok.get('Miktar', 0))
                
                # Kesim Analizi
                uygun_satirlar = []
                toplam_dusulecek_cm = 0.0
                
                for _, row in df_kesim.iterrows():
                    urun_adi = row.get(tanim_col, "")
                    plaka_info = ayikla_karakter_ve_olcu(urun_adi)
                    
                    if karakter_match(plaka_info['karakter'], blok_info['karakter']):
                        verim = plaka_sayisi_hesapla(plaka_info, blok_info)
                        if verim > 0:
                            siparis_adet = safe_float(row.get(miktar_col, 0))
                            gereken_dilim = math.ceil(siparis_adet / verim)
                            harcanacak_cm = gereken_dilim * plaka_info['kalinlik']
                            
                            uygun_satirlar.append({"🏭 Plaka": urun_adi, "🔪 Dilim": gereken_dilim, "📏 Harcanacak": harcanacak_cm})
                            toplam_dusulecek_cm += harcanacak_cm
                
                # Sonuçlar ve Onay
                if uygun_satirlar:
                    st.dataframe(pd.DataFrame(uygun_satirlar))
                    if st.button("🚀 KESİMİ ONAYLA", type="primary"):
                        stok_df.loc[match_blok.index, 'Miktar'] = mevcut_miktar - toplam_dusulecek_cm
                        update_stock_and_logs(stok_df, None)
                        st.success("🎉 KESİM TAMAMLANDI!")
                        st.rerun()
            else:
                st.error("❌ Barkod bulunamadı.")
    except Exception as e:
        st.error(f"❌ Hata: {str(e)}")
