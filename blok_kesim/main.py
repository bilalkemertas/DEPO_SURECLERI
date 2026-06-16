"""Blok & Rulo Sünger Kesim Otomasyonu - Ana Modül

Bu modül, yüklenen iş emrindeki veya seçilen plakaya ait doğru bloğu 
eslesme_matrisi.csv üzerinden tespit eder, ekrana yazar ve kesim doğrulamasını yapar.
"""

import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

# Clean Architecture - Göreli İçe Aktarımlar
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn=None):
    """Ana Blok Kesim Ekranı Kontrol Merkezi"""
    
    # 1. Hafıza Yapısını Başlat
    init_blok_kesim_state()
    
    # 2. Eşleşme Matrisini Yükle
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
        
    st.title("✂️ Akıllı Blok Kesim ve Eşleştirme Otomasyonu")
    st.markdown("---")
    
    # Sivilceler ve sekmeler (3 Adımlı Sihirbaz)
    tab1, tab2, tab3 = st.tabs(["📂 1. İş Emri / Kesim Listesi Yükle", "🎯 2. Blok Tespit Merkezi", "🪚 3. Barkod Doğrulama ve Kesim"])
    
    # ==========================================
    # SEKME 1: İŞ EMRİ / KESİM LİSTESİ YÜKLEME
    # ==========================================
    with tab1:
        st.header("Excel Kesim Listesi Girişi")
        up_file = st.file_uploader("Lütfen Güncel İş Emri / Kesim Listesini Seçin:", type=['xlsx', 'xls'])
        
        if up_file:
            if 'main_data' not in st.session_state or st.session_state.get('uploaded_file_name') != up_file.name:
                try:
                    # Akıllı Başlık Avcısı (Header Finder)
                    raw_df = pd.read_excel(up_file, header=None)
                    header_idx = 0
                    for i in range(min(20, len(raw_df))):
                        row_vals = [str(x).upper() for x in raw_df.iloc[i].dropna().tolist()]
                        if any("TANIM" in v or "KOD" in v or "MİKTAR" in v or "ADET" in v for v in row_vals):
                            header_idx = i
                            break
                    
                    df = pd.read_excel(up_file, header=header_idx)
                    st.session_state.main_data = df
                    st.session_state.uploaded_file_name = up_file.name
                    st.success("✅ İş emri listesi başarıyla yüklendi!")
                except Exception as e:
                    st.error(f"Dosya okunurken hata oluştu: {e}")
            
            df = st.session_state.get('main_data')
            if df is not None and not df.empty:
                st.dataframe(df.head(10), use_container_width=True)
                st.info("➡️ İş emri yüklendi. Şimdi lütfen 2. Sekmeye geçerek bloğu tespit edin.")

    # ==========================================
    # SEKME 2: BLOK TESPİT MERKEZİ (PLAKA -> BLOK)
    # ==========================================
    with tab2:
        st.header("Eşleşme Matrisinden Blok Tespiti")
        
        # Eğer iş emri yüklendiyse sütun bul, yüklenmediyse serbest seçim yaptır
        df = st.session_state.get('main_data')
        matris_df = st.session_state.eslesme_df
        
        plaka_secenekleri = []
        if df is not None and not df.empty:
            tanim_col = next((c for c in df.columns if "TANIM" in str(c).upper() or "ÜRÜN" in str(c).upper() or "AD" in str(c).upper()), None)
            if tanim_col:
                plaka_secenekleri = df[tanim_col].dropna().unique().tolist()
        
        # Eğer iş emri yoksa matrisin kendi listesini getir (Serbest mod için)
        if not plaka_secenekleri and matris_df is not None and not matris_df.empty:
            matris_tanim_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper() or "MAMÜL" in str(c).upper()), matris_df.columns[1])
            plaka_secenekleri = matris_df[matris_tanim_col].dropna().unique().tolist()
            
        secilen_plaka = st.selectbox("📌 Kesilecek Yarı Mamulü (Plakayı) Seçin:", ["Seçiniz..."] + plaka_secenekleri)
        
        if secilen_plaka != "Seçiniz...":
            st.session_state.secilen_hedef_plaka = secilen_plaka
            
            if matris_df is not None and not matris_df.empty:
                # Sütun isim zırhları
                m_plaka_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper()), matris_df.columns[1])
                m_blok_kod_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK KODU" in str(c).upper()), matris_df.columns[2])
                m_blok_adi_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK ADI" in str(c).upper()), matris_df.columns[3])
                
                # Matriste arama yap
                eslesme_row = matris_df[matris_df[m_plaka_col].astype(str).str.strip() == str(secilen_plaka).strip()]
                
                if not eslesme_row.empty:
                    tespit_kod = eslesme_row.iloc[0][m_blok_kod_col]
                    tespit_ad = eslesme_row.iloc[0][m_blok_adi_col]
                    
                    # Bulunan kodları hafızaya yaz (3. adımda doğrulamak için)
                    st.session_state.hedef_blok_kodu = str(tespit_kod).strip()
                    st.session_state.hedef_blok_adi = str(tespit_ad).strip()
                    
                    # BÜYÜKÇE EKRANA YAZMA ALANI (Kullanıcı İsteği)
                    st.markdown("---")
                    with st.container(border=True):
                        st.markdown("### 📋 TESPİT EDİLEN KULLANILACAK BLOK")
                        st.subheader(f"🧱 Blok Kodu: `{st.session_state.hedef_blok_kodu}`")
                        st.subheader(f"🏷️ Blok Adı: *{st.session_state.hedef_blok_adi}*")
                    st.success("🎯 Hedef blok başarıyla kilitlendi! Şimdi 3. Sekmeye geçip makineye atılan bloğu okutabilirsiniz.")
                else:
                    st.error("❌ Bu plaka eşleşme matrisinde bulunamadı! Lütfen matris dosyasını kontrol edin.")
            else:
                st.error("❌ Eşleşme matrisi veri tabanı yüklenemedi!")

    # ==========================================
    # SEKME 3: BARKOD DOĞRULAMA VE KESİM
    # ==========================================
    with tab3:
        st.header("Operatör Doğrulama ve Sarf Girişi")
        
        # Hafızadaki hedef kilitleri kontrol et
        h_plaka = st.session_state.get('secilen_hedef_plaka')
        h_blok_kod = st.session_state.get('hedef_blok_kodu')
        h_blok_ad = st.session_state.get('hedef_blok_adi')
        
        if not h_blok_kod:
            st.warning("⚠️ Lütfen önce 2. Sekmeden kesilecek plakayı seçip hedef bloğu tespit ettirin!")
        else:
            # Operatöre hangi bloğu getirmesi gerektiğini hatırlat
            st.info(f"🎯 **İŞLEM EMİR:** `{h_plaka}` üretimi için depodan gelmesi gereken blok: **{h_blok_kod} - {h_blok_ad}**")
            
            # Canlı stok verisi çekimi
            if st.session_state.stok_data is None:
                with st.spinner("Canlı Depo Verileri Çekiliyor..."):
                    try:
                        stok_df, har_df = fetch_live_data()
                    except TypeError:
                        stok_df, har_df = fetch_live_data(conn)
                    st.session_state.stok_data = stok_df
                    st.session_state.har_data = har_df
            
            stok_df = st.session_state.stok_data
            
            # OPERATÖR BARKODU OKUTUR
            barkod_input = st.text_input("📦 Makineye Koyduğunuz Blok Barkodunu Okutun:", key="operator_kesim_barkod").strip()
            
            if barkod_input:
                if stok_df is not None and not stok_df.empty:
                    # Akıllı Barkod ve Stok Kodu Sütun Bulucuları
                    s_barkod_col = next((c for c in stok_df.columns if "BARKOD" in str(c).upper() or "TEDARİKÇİ BARKODU" in str(c).upper()), stok_df.columns[2])
                    s_kod_col = next((c for c in stok_df.columns if "STOK KODU" in str(c).upper() or "KOD" in str(c).upper()), stok_df.columns[0])
                    s_miktar_col = next((c for c in stok_df.columns if any(m in str(c).upper() for m in ['BAKİYE', 'MİKTAR', 'BOY', 'KALAN', 'GELEN MİKTAR'])), stok_df.columns[4])
                    
                    # Stoğu tara
                    stok_match = stok_df[stok_df[s_barkod_col].astype(str).str.strip() == str(barkod_input).strip()]
                    
                    if stok_match.empty:
                        st.error(f"❌ Okutulan '{barkod_input}' barkodlu blok sistem stoklarında bulunamadı!")
                    else:
                        blok_row = stok_match.iloc[0]
                        okutulan_blok_kodu = str(blok_row.get(s_kod_col, "")).strip()
                        
                        # VERİ DOĞRULAMA / UYUMLULUK ZIRHI
                        if okutulan_blok_kodu != h_blok_kod:
                            st.error(f"🚨 HATA! Yanlış Blok Getirildi! Matrisin istediği blok: `{h_blok_kod}` fakat makineye konulan blok: `{okutulan_blok_kodu}`")
                            st.warning("⚠️ Lütfen doğru bloğu getirin veya seçimi kontrol edin!")
                        else:
                            st.success(f"🎯 OKUTULAN BLOK UYUMLU VE DOĞRU: {blok_row.get('Stok Adı', blok_row.get('İsim', ''))}")
                            st.dataframe(pd.DataFrame([blok_row]), use_container_width=True)
                            
                            st.markdown("---")
                            # Miktar İşlemleri ve Fire Algoritması Hesaplaması
                            mevcut_miktar = safe_float(blok_row.get(s_miktar_col, 0))
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                st.metric("📏 Mevcut Blok Boyu / Miktarı", f"{mevcut_miktar:.2f}")
                            
                            # Akıllı Fire Hesaplama Silsilesi (Daha önce kesildi mi?)
                            har_df = st.session_state.har_data
                            daha_once_kesildi_mi = False
                            if har_df is not None and not har_df.empty and 'Kod' in har_df.columns:
                                daha_once_kesildi_mi = ((har_df['Kod'].astype(str).str.strip() == okutulan_blok_kodu) & (har_df['İşlem'] == "KESİM/SARF")).any()
                            
                            otomatik_fire = 0 if daha_once_kesildi_mi else 2
                            if otomatik_fire > 0:
                                st.caption(f"💡 Bu blok ilk defa kesiliyor, sisteme otomatik +{otomatik_fire} cm kabuk/baş fire payı önerildi.")
                                
                            sarf_miktari = st.number_input("📉 Kesilen / Tüketilen Miktar (cm)", min_value=0.0, max_value=float(mevcut_miktar), step=1.0)
                            ek_fire = st.number_input("🗑️ Varsa Ekstra Fire Miktarı (cm)", min_value=0.0, step=1.0)
                            
                            total_dusulecek = sarf_miktari + ek_fire + otomatik_fire
                            
                            if st.button("🚀 KESİM HAREKETİNİ ONAYLA VE STOKTAN DÜŞ", type="primary"):
                                if sarf_miktari <= 0:
                                    st.warning("⚠️ Sarfiyat miktarı sıfır olamaz!")
                                elif total_dusulecek > mevcut_miktar:
                                    st.error("❌ Girilen sarfiyat ve fire miktarı mevcut stok boyunu aşıyor!")
                                else:
                                    # Stoğu Güncelle
                                    idx_val = stok_match.index[0]
                                    stok_df.at[idx_val, s_miktar_col] = mevcut_miktar - total_dusulecek
                                    
                                    # Log / Hareket Geçmişi Yazma
                                    aciklama = f"Plaka: {h_plaka} | Net Sarf: {sarf_miktari} | Baş Fire: {otomatik_fire} | Ek Fire: {ek_fire}"
                                    yeni_log = pd.DataFrame([{
                                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "İşlem": "KESİM/SARF",
                                        "Kod": okutulan_blok_kodu,
                                        "Miktar": total_dusulecek,
                                        "Açıklama": aciklama
                                    }])
                                    
                                    with st.spinner("Veritabanı güncelleniyor..."):
                                        durum = update_stock_and_logs(stok_df, st.session_state.har_data, yeni_log)
                                        
                                    if durum:
                                        st.balloons()
                                        st.success("🎉 Kesim kaydı başarıyla işlendi ve hedef blok stoktan düşüldü!")
                                        st.session_state.stok_data = stok_df
                                        
                                        # Formu sıfırlama butonu
                                        if st.button("🔄 Sıradaki Kesim İşlemine Geç"):
                                            st.session_state.secilen_hedef_plaka = None
                                            st.session_state.hedef_blok_kodu = None
                                            st.session_state.hedef_blok_adi = None
                                            st.rerun()
