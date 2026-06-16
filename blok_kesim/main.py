"""Blok & Rulo Sünger Kesim Otomasyonu - Ana Modül

App.py'den çağrılacak şekilde tasarlandı. Kendi set_page_config çağırmıyor
(app.py'de zaten yapılmış) Sidebar kontrollerini üst seviyeye sağlıyor. """

import streamlit as st
import pandas as pd
import re
import math
from datetime import datetime

# Clean Architecture - Modüller Arası Göreli (Relative) İçe Aktarımlar
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi, karakter_match
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn=None):
    """
    Ana blok kesim ekranı
    App.py'den çağrılır - set_page_config yoktur
    """
    # 1. State Başlatma (Hafıza Zırhı)
    init_blok_kesim_state()
    
    # 2. Eşleşme Matrisini Yükle (Yerel Master Data Yükleme)
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
        
    st.title("✂️ Akıllı Blok Kesim Komuta Ekranı")
    st.markdown("---")
    
    # ==========================================
    # ADIM 1: İŞ EMRİ (EXCEL) YÜKLEME EKRANI
    # ==========================================
    st.header("📂 1. İş Emri Yükleme")
    up = st.file_uploader("Kesim Listesi / Excel Dosyasını Yükleyin (DataGrid)", type=['xlsx', 'xls'])
    
    if up:
        # Dosya değiştiyse veya ilk kez yükleniyorsa oku
        if 'main_data' not in st.session_state or st.session_state.get('uploaded_file_name') != up.name:
            try:
                # Akıllı Başlık Bulucu (Header Finder) Zırhı
                raw_df = pd.read_excel(up, header=None)
                header_idx = 0
                # Üstteki ilk 20 satırı tarayıp başlıkların hangi satırda olduğunu bul
                for i in range(min(20, len(raw_df))):
                    row_vals = [str(x).upper() for x in raw_df.iloc[i].dropna().tolist()]
                    if any("TANIM" in v or "KOD" in v or "MİKTAR" in v or "ADET" in v for v in row_vals):
                        header_idx = i
                        break
                
                df = pd.read_excel(up, header=header_idx)
                st.session_state.main_data = df
                st.session_state.uploaded_file_name = up.name
                st.success("✅ İş emri başarıyla yüklendi ve başlıklar otomatik bulundu!")
            except Exception as e:
                st.error(f"Dosya okuma hatası: {e}")
                
        df = st.session_state.get('main_data')
        
        if df is not None and not df.empty:
            st.dataframe(df.head(), use_container_width=True)
            
            # Dinamik Sütun Tespiti 
            tanim_col = next((c for c in df.columns if "TANIM" in str(c).upper() or "ÜRÜN" in str(c).upper()), None)
            miktar_col = next((c for c in df.columns if "ADET" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
            kod_col = next((c for c in df.columns if "KOD" in str(c).upper() or "STOK KODU" in str(c).upper()), None)
            
            if not tanim_col or not miktar_col:
                st.warning("⚠️ Yüklenen Excel dosyasında Ürün Tanımı veya Adet sütunları bulunamadı!")
                return
            
            # ==========================================
            # ADIM 2: PLAKA SEÇİMİ VE EŞLEŞTİRME TABLOSU
            # ==========================================
            st.markdown("---")
            st.header("🔗 2. Plaka Eşleştirme ve Seçim")
            
            # Yüklenen listedeki ürünleri (plakaları) çıkar ve operatöre sun
            plaka_listesi = df[tanim_col].dropna().unique().tolist()
            secilen_plaka = st.selectbox("📌 Kesilecek Yarı Mamulü (Plakayı) Seçin", ["Seçiniz..."] + plaka_listesi)
            
            if secilen_plaka != "Seçiniz...":
                st.session_state.secilen_hedef_plaka = secilen_plaka
                
                # Matris Eşleştirmesi
                eslesme_matrix = st.session_state.get('eslesme_df')
                if eslesme_matrix is not None and not eslesme_matrix.empty:
                    # Matris sütunlarını dinamik bul
                    matris_plaka_col = eslesme_matrix.columns[0]
                    matris_blok_kod_col = eslesme_matrix.columns[2] if len(eslesme_matrix.columns) > 2 else None
                    matris_blok_adi_col = eslesme_matrix.columns[3] if len(eslesme_matrix.columns) > 3 else None
                    
                    # Regex ile kaçış karakterlerini koruyarak eşleşme ara
                    m_match = eslesme_matrix[eslesme_matrix[matris_plaka_col].astype(str).str.contains(re.escape(str(secilen_plaka).strip()), case=False, na=False)]
                    
                    if not m_match.empty and matris_blok_kod_col and matris_blok_adi_col:
                        st.success(f"✅ Matris Eşleşmesi Bulundu! '{secilen_plaka}' için kullanılabilecek bloklar:")
                        st.dataframe(m_match[[matris_plaka_col, matris_blok_kod_col, matris_blok_adi_col]], use_container_width=True)
                    else:
                        st.warning("⚠️ Bu plaka eşleştirme matrisinde bulunamadı! Akıllı eşleşme / serbest seçim yapabilirsiniz.")
                else:
                    st.error("❌ Eşleşme matrisi (eslesme_matrisi.csv) bulunamadı veya okunamadı!")

                # ==========================================
                # ADIM 3: MAKİNEYE YÜKLENECEK BLOK BARKODU VE KESİM ONAYI
                # ==========================================
                st.markdown("---")
                st.header("✂️ 3. Makineye Yüklenecek Blok ve Kesim Onayı")
                
                # Depo canlı stok verisini çek (Session'da yoksa)
                if st.session_state.get('stok_data') is None:
                    with st.spinner("Canlı Depo Verileri Çekiliyor..."):
                        # Veritabanı modülündeki çağrı parametreleri
                        try:
                            stok_df, har_df = fetch_live_data()
                        except TypeError:
                            stok_df, har_df = fetch_live_data(conn)
                        st.session_state.stok_data = stok_df
                        st.session_state.har_data = har_df
                
                stok_df = st.session_state.get('stok_data')
                
                # BARKOD GİRİŞİ 
                barkod = st.text_input("🎯 Makineye Yüklenen Blok Barkodunu Okutun veya Kod Girin:", key="blok_barkod_input").strip()
                
                # BARKOD İŞLEME VE DİNAMİK SÜTUN DEDEKTÖRÜ
                if barkod:
                    if stok_df is not None and not stok_df.empty:
                        barkod_col = None
                        for c in stok_df.columns:
                            if "barkod" in str(c).lower() or "kod" in str(c).lower() or "tedarikçi" in str(c).lower():
                                barkod_col = c
                                break
                                
                        if barkod_col:
                            match = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod).strip()]
                            
                            if match.empty:
                                st.error(f"❌ '{barkod}' barkodlu stok depoda bulunamadı!")
                            else:
                                st.success("✅ Blok Stokta Bulundu!")
                                blok_row = match.iloc[0]
                                st.dataframe(pd.DataFrame([blok_row]), use_container_width=True)
                                
                                # Miktar düşüm mantığı için stok kolonunu bul
                                olcu_col = None
                                for c in ['Gelen Miktar', 'Miktar', 'Bakiye', 'Boy', 'Kalan']:
                                    if c in stok_df.columns: 
                                        olcu_col = c
                                        break
                                        
                                mevcut_miktar = safe_float(blok_row.get(olcu_col, 0)) if olcu_col else 0.0
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("📦 Mevcut Blok Miktarı", f"{mevcut_miktar:.2f}")
                                
                                sarfiyat = st.number_input("📉 Kesilen / Sarf Edilen Miktar", min_value=0.0, max_value=float(mevcut_miktar), step=1.0)
                                fire = st.number_input("🗑️ Fire Miktarı (Varsa)", min_value=0.0, step=1.0)
                                
                                if st.button("🚀 KESİM HAREKETİNİ ONAYLA VE STOKTAN DÜŞ", type="primary"):
                                    if sarfiyat <= 0:
                                        st.warning("⚠️ Lütfen sıfırdan büyük bir sarfiyat miktarı girin.")
                                    elif sarfiyat > mevcut_miktar:
                                        st.error("❌ Stok yetersiz! Sarfiyat mevcut miktardan fazla olamaz.")
                                    else:
                                        # 1. Stok Düşümü (DataFrame Güncellemesi)
                                        index_val = match.index[0]
                                        stok_df.at[index_val, olcu_col] = mevcut_miktar - sarfiyat
                                        
                                        # 2. Hareket Kaydı Hazırlama
                                        aciklama_metni = f"Hedef Plaka: {secilen_plaka} | Fire: {fire}"
                                        
                                        yeni_har = pd.DataFrame([{
                                            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "İşlem": "KESİM/SARF",
                                            "Kod": blok_row.get('Stok Kodu', blok_row.get('Kod', barkod)),
                                            "Miktar": sarfiyat,
                                            "Açıklama": aciklama_metni
                                        }])
                                        
                                        with st.spinner("Sisteme İşleniyor ve Veritabanı Güncelleniyor..."):
                                            basarili = update_stock_and_logs(stok_df, st.session_state.har_data, yeni_har)
                                        
                                        if basarili:
                                            st.balloons()
                                            st.success("🎉 Kesim işlemi başarıyla veritabanına işlendi ve Stok güncellendi!")
                                            
                                            # Cache güncellemesi
                                            st.session_state.stok_data = stok_df 
                                            
                                            if st.button("🔄 Yeni Kesime Geç"):
                                                st.rerun()
                        else:
                            st.error("❌ Stok tablosunda uygun bir 'Barkod' sütunu bulunamadı!")
                    else:
                        st.error("❌ Veritabanından stok verisi çekilemedi veya tablo boş.")
