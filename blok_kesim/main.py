import streamlit as st
import pandas as pd
import math
from datetime import datetime

from blok_kesim.state import init_blok_kesim_state
from blok_kesim.matching import load_local_eslesme_matrisi, karakter_match
from blok_kesim.database import fetch_live_data, update_stock_and_logs
from blok_kesim.data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

def run_blok_kesim(conn):
    # ============ SAYFA AYARLARI ============
    st.set_page_config(page_title="🧱 Blok Kesim Otomasyonu", layout="wide", initial_sidebar_state="expanded")
    
    # ============ SIDEBAR KONTROL PANELİ ============
    with st.sidebar:
        st.markdown("### 🎛️ KONTROL PANELİ")
        st.divider()
        
        # State Başlatma
        init_blok_kesim_state()
        
        # Eşleşme Matrisini Yükle
        if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
            st.session_state.eslesme_df = load_local_eslesme_matrisi()
        
        # Veritabanı Verilerini Çek
        stok_df, har_df = fetch_live_data()
        
        if stok_df.empty:
            st.error("❌ Stok veri yüklenemedi", icon="🔴")
            return
        
        # İş Emri Dosyası Yükleme
        st.markdown("#### 📋 İş Emri Yükleme")
        up = st.file_uploader("Excel dosyası seçin", type=["xlsx", "xls"], label_visibility="collapsed")
        
        # Barkod Giriş Alanı
        st.markdown("#### 📦 Hammadde Seçimi")
        barkod = st.text_input(
            "Blok barkodunu okutun",
            placeholder="Barkod veya kod...",
            label_visibility="collapsed"
        ).strip()
        
        st.divider()
        
        # Veritabanı Durum İstatistikleri
        st.markdown("#### 📊 DEPO STATİSTİKLERİ")
        c1, c2 = st.columns(2)
        c1.metric("📦 Toplam Blok", len(stok_df))
        c2.metric("📋 İş Emri", "Yüklemeyi Bekliyor" if up is None else "✅ Yüklendi")
        
        # Stok Durumu (Compact)
        if not stok_df.empty:
            total_qty = safe_float(stok_df['Miktar'].sum())
            st.metric("📏 Toplam Stok (cm)", f"{total_qty:,.0f}", delta=f"{len(stok_df)} Blok")
    
    # ============ ANA İÇERİK ALANI ============
    st.markdown("### 🧱 KESİM KONTROL PANELİ")
    
    if up is None:
        st.info("📋 Sol panelden Excel dosyası yükleyerek başlayın", icon="ℹ️")
        return
    
    try:
        # ========== EXCEL İŞLEME ==========
        raw_df = pd.read_excel(up, header=None)
        header_idx = 0
        tanim_col = None
        miktar_col = None
        
        for i in range(min(20, len(raw_df))):
            row_vals = [str(x).upper().strip() for x in raw_df.iloc[i].dropna().values]
            row_str = " ".join(row_vals)
            
            has_tanim = any(k in row_str for k in ["TANIM", "ÜRÜN", "URUN", "MALZEME", "PLAKA"])
            has_miktar = any(k in row_str for k in ["ADET", "MİKTAR", "MIKTAR", "PLAN", "ADEDİ", "ADEDI"])
            
            if has_tanim and has_miktar:
                header_idx = i
                break
        
        df_kesim = pd.read_excel(up, header=header_idx)
        df_kesim.columns = [str(c).strip() for c in df_kesim.columns]
        
        for col in df_kesim.columns:
            c_upper = col.upper()
            if any(k in c_upper for k in ["TANIM", "ÜRÜN", "URUN", "MALZEME", "PLAKA"]):
                tanim_col = col
            if any(k in c_upper for k in ["ADET", "MİKTAR", "MIKTAR", "PLAN", "ADEDİ", "ADEDI", "TOPLAM"]):
                miktar_col = col
        
        if not tanim_col or not miktar_col:
            col1, col2 = st.columns(2)
            tanim_col = col1.selectbox("Ürün Tanımı Sütunu:", df_kesim.columns)
            miktar_col = col2.selectbox("Adet/Miktar Sütunu:", df_kesim.columns)
        
        # ========== BARKOD İŞLEME ==========
        if barkod:
            barkod_col = None
            for c in stok_df.columns:
                if "barkod" in c.lower() or "kod" in c.lower():
                    barkod_col = c
                    break
            
            if not barkod_col:
                st.error("❌ Stok tablosunda barkod sütunu yok", icon="🔴")
                return
            
            match_blok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)]
            
            if not match_blok.empty:
                blok = match_blok.iloc[0].to_dict()
                blok_isim = blok.get('İsim', blok.get('Stok Adı', ''))
                blok_kod = blok.get('Kod', blok.get('Stok Kodu', ''))
                blok_info = ayikla_karakter_ve_olcu(blok_isim)
                mevcut_miktar = safe_float(blok.get('Miktar', 0))
                
                # ============ BLOK BİLGİ PANELI (COMPACT) ============
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📦 Blok Adı", blok_isim[:20], delta=blok_kod)
                col2.metric("📐 Boy", f"{blok_info['boy']:.1f}mm")
                col3.metric("📏 En", f"{blok_info['en']:.1f}mm")
                col4.metric("📊 Stok", f"{mevcut_miktar:,.0f}cm", delta=f"{blok_info['kalinlik']:.1f}mm kal.")
                
                # ============ KESİM ANALİZİ ==========
                uygun_satirlar = []
                toplam_dusulecek_cm = 0.0
                
                for idx, row in df_kesim.iterrows():
                    urun_adi = row.get(tanim_col, "")
                    if pd.isna(urun_adi) or str(urun_adi).strip() == "":
                        continue
                    
                    plaka_info = ayikla_karakter_ve_olcu(urun_adi)
                    karakter_ok = karakter_match(plaka_info['karakter'], blok_info['karakter'])
                    
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
                            gereken_dilim = math.ceil(siparis_adet / verim)
                            kalinlik = plaka_info['kalinlik']
                            harcanacak_cm = gereken_dilim * kalinlik
                            
                            uygun_satirlar.append({
                                "🏭 Plaka": urun_adi[:25],
                                "📊 Sipariş": int(siparis_adet),
                                "✂️ Çıkan": verim,
                                "🔪 Dilim": gereken_dilim,
                                "📏 Harcanacak": f"{harcanacak_cm:.0f}cm"
                            })
                            toplam_dusulecek_cm += harcanacak_cm
                
                if uygun_satirlar:
                    # KESİM TABLOSU
                    st.markdown("#### ✂️ KESİM PLANI")
                    tab_table, tab_summary = st.tabs(["📋 Detay", "📊 Özet"])
                    
                    with tab_table:
                        st.dataframe(
                            pd.DataFrame(uygun_satirlar),
                            use_container_width=True,
                            hide_index=True,
                            height=250
                        )
                    
                    with tab_summary:
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("📍 Toplam Plaka", len(uygun_satirlar))
                        col2.metric("✂️ Toplam Dilim", sum(int(x["🔪 Dilim"]) for x in uygun_satirlar))
                        col3.metric("📉 Harcanacak", f"{toplam_dusulecek_cm:,.0f}cm")
                        col4.metric("📦 Mevcut", f"{mevcut_miktar:,.0f}cm")
                        
                        # Verimlilik hesabı
                        if toplam_dusulecek_cm > 0:
                            verimlilik = (toplam_dusulecek_cm / mevcut_miktar * 100) if mevcut_miktar > 0 else 0
                            col5.metric("⚡ Verimlilik", f"%{verimlilik:.1f}", 
                                       delta="✅ Yeterli" if mevcut_miktar >= toplam_dusulecek_cm else "❌ YETERSİZ")
                    
                    # KESİM DURUMU VE ONAY
                    st.divider()
                    
                    if mevcut_miktar < toplam_dusulecek_cm:
                        st.error(
                            f"❌ **STOK YETERSİZ**\n\n"
                            f"Gerekli: {toplam_dusulecek_cm:,.0f}cm | Mevcut: {mevcut_miktar:,.0f}cm | "
                            f"Eksik: {toplam_dusulecek_cm - mevcut_miktar:,.0f}cm",
                            icon="🚫"
                        )
                    else:
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.success(
                                f"✅ **KESİM HAZIR**\n\n"
                                f"Harcanacak: {toplam_dusulecek_cm:,.0f}cm | Kalan: {mevcut_miktar - toplam_dusulecek_cm:,.0f}cm",
                                icon="✅"
                            )
                        
                        with c2:
                            if st.button("🚀 KESİMİ ONAYLA", type="primary", use_container_width=True):
                                idx_stok = stok_df[stok_df[barkod_col].astype(str).str.strip() == str(barkod)].index
                                stok_df.loc[idx_stok, 'Miktar'] = mevcut_miktar - toplam_dusulecek_cm
                                
                                yeni_log = pd.DataFrame([{
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "Barkod": barkod,
                                    "Stok Kodu": blok_kod,
                                    "Stok Adı": blok_isim,
                                    "İşlem": "KESİM/SARF",
                                    "Miktar": toplam_dusulecek_cm,
                                    "Personel": st.session_state.get('kullanici_adi', 'Otomasyon'),
                                    "Durum": "Tamamlandı"
                                }])
                                
                                success = update_stock_and_logs(stok_df, yeni_log)
                                if success:
                                    st.balloons()
                                    st.success("🎉 **KESIM TAMAMLANDI** - Stoklar güncellendi!")
                                    st.rerun()
                else:
                    st.warning("⚠️ Bu blok, iş emri listesiyle eşleşen plaka bulunamadı!", icon="⚠️")
            else:
                st.error("❌ Okutulan barkod stokta bulunamadı!", icon="🔴")
    
    except Exception as e:
        st.error(f"❌ Hata: {e}", icon="🔴")
