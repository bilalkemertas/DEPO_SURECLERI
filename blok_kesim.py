import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime

def run_blok_kesim(conn):

    # --- YEREL MASTER DATA YÜKLEME (TÜRKÇE KARAKTER ZIRHLI & CACHED) ---
    if 'eslesme_df' not in st.session_state:
        csv_path = "eslesme_matrisi.csv"
        if os.path.exists(csv_path):
            encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
            success = False
            for enc in encodings:
                try:
                    st.session_state.eslesme_df = pd.read_csv(csv_path, dtype=str, encoding=enc)
                    st.session_state.eslesme_df.columns = [c.strip() for c in st.session_state.eslesme_df.columns]
                    success = True
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            if not success:
                st.error("⚠️ 'eslesme_matrisi.csv' uygun bir Türkçe karakter formatında okunamadı!")
                st.session_state.eslesme_df = pd.DataFrame()
        else:
            st.warning("⚠️ 'eslesme_matrisi.csv' dosyası kök dizinde bulunamadı! Eski yedek algoritmaya geçiş yapılıyor.")
            st.session_state.eslesme_df = pd.DataFrame()

    # --- ZIRHLI AYIKLAMA MOTORU (Sadece istisnai Fallback durumları için saklandı) ---
    def ayikla_karakter_ve_olcu(text):
        default_return = {"boy": 0.0, "en": 0.0, "kalinlik": 0.0, "karakter": str(text) if text else ""}
        if pd.isna(text) or str(text).strip() == "":
            return default_return

        t = str(text).upper().replace(",", ".").strip()
        olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
        olcu_kisa = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)

        try:
            if olcu_uzun:
                boy = float(olcu_uzun.group(1))
                en = float(olcu_uzun.group(2))
                kalinlik = float(olcu_uzun.group(3))
                start_idx = olcu_uzun.start()
            elif olcu_kisa:
                boy = float(olcu_kisa.group(1))
                en = float(olcu_kisa.group(2))
                kalinlik = 0.0
                start_idx = olcu_kisa.start()
            else:
                return default_return

            karakter = t[:start_idx].strip()
            return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}
        except Exception:
            return default_return

    # --- PLAKA VE VERİM HESAPLAMA ---
    def plaka_sayisi_hesapla(plaka, blok):
        if not plaka or not blok: return 0
        if plaka.get('boy', 0) == 0 or plaka.get('en', 0) == 0: return 0

        adet_boy_1 = int(blok.get('boy', 0) // plaka['boy'])
        adet_en_1  = int(blok.get('en', 0) // plaka['en'])
        verim_1 = adet_boy_1 * adet_en_1

        adet_boy_2 = int(blok.get('boy', 0) // plaka['en'])
        adet_en_2  = int(blok.get('en', 0) // plaka['boy'])
        verim_2 = adet_boy_2 * adet_en_2

        return max(verim_1, verim_2)

    # --- GÜVENLİ FLOAT DÖNÜŞÜMÜ ---
    def safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    # --- NAVİGASYON ---
    c1, c2, _ = st.columns([1.5, 1.5, 4])
    if c1.button("ANA MENÜ"):
        st.session_state.page = 'home'
        st.rerun()

    if c2.button("TEMİZLE"):
        for k in ['main_data', 'stok_data', 'har_data']:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    st.title("✂️ Blok Kesim Ekranı")

    # --- EXCEL YÜKLEME ---
    up = st.file_uploader("Excel Dosyasını Yükleyin (Kesim / İş Emri Listesi)", type=['xlsx'])

    if up and 'main_data' not in st.session_state:
        try:
            raw_df = pd.read_excel(up, header=None)
            header_idx = 0
            
            for i in range(min(20, len(raw_df))):
                row_str = " ".join(str(val).upper() for val in raw_df.iloc[i].values if pd.notna(val))
                if ("TANIM" in row_str or "ÜRÜN" in row_str or "URUN" in row_str) and \
                   ("MIKTAR" in row_str or "MİKTAR" in row_str or "ADET" in row_str):
                    header_idx = i
                    break
            
            df = pd.read_excel(up, header=header_idx)
            df.columns = [str(c).strip() for c in df.columns]
            df.dropna(how='all', inplace=True)
            
            st.session_state.main_data = df
            st.session_state.stok_data = veritabani.get_internal_data("Stok")
            st.session_state.har_data = veritabani.get_internal_data("Hareketler")
        except Exception as e:
            st.error(f"❌ Veri yükleme hatası: {e}")
            st.stop()

    # --- ANA OPERASYON VE TEMİZLENMİŞ MATRİS YAPISI ---
    if 'main_data' in st.session_state:
        df = st.session_state.main_data
        eslesme_matrix = st.session_state.eslesme_df
        stok_df = st.session_state.stok_data

        # --- DİNAMİK SÜTUN BULUCU ---
        matris_kod_col = None
        matris_blok_kod_col = None
        matris_blok_adi_col = None

        if eslesme_matrix is not None and not eslesme_matrix.empty:
            eslesme_matrix.columns = [str(c).strip() for c in eslesme_matrix.columns]
            matris_kod_col = next((c for c in eslesme_matrix.columns if "HAMMADDE" in c.upper() or "PLAKA KOD" in c.upper() or (c.upper() == "KOD")), eslesme_matrix.columns[0])
            matris_blok_kod_col = next((c for c in eslesme_matrix.columns if "BAĞLI BLOK STOK KODU" in c.upper() or "BLOK KOD" in c.upper() or "BLOK_KOD" in c.upper()), None)
            matris_blok_adi_col = next((c for c in eslesme_matrix.columns if "BAĞLI BLOK STOK ADI" in c.upper() or "BLOK AD" in c.upper() or "BLOK_ADI" in c.upper()), None)

            if not matris_blok_kod_col and len(eslesme_matrix.columns) >= 4:
                matris_kod_col = eslesme_matrix.columns[0]
                matris_blok_kod_col = eslesme_matrix.columns[2]
                matris_blok_adi_col = eslesme_matrix.columns[3]

        tanim_col = next((c for c in df.columns if "TANIM" in c.upper() or "ÜRÜN" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MIKTAR" in c.upper() or "MİKTAR" in c.upper()), None)
        kod_col = next((c for c in df.columns if "KOD" in c.upper() or "STOK KODU" in c.upper()), None)

        if not tanim_col or not miktar_col:
            st.warning("⚠️ Yüklenen Excel dosyasında Ürün Tanımı veya Adet sütunları bulunamadı!")
            st.stop()

        vis_rows = []
        pivot_data = []

        # --- TABLO OLUŞTURMA DÖNGÜSÜ ---
        for _, row in df.iterrows():
            plaka_adi = str(row.get(tanim_col, ''))
            plaka_kodu = str(row.get(kod_col, '')).split('.')[0].strip() if kod_col and pd.notna(row.get(kod_col)) else ""
            plaka_adet = safe_float(row.get(miktar_col, 0))
            
            bagli_blok_kod = ""
            bagli_blok_adi = ""
            is_matched_via_matrix = False

            # 1. ADIM: Kesin Tablodan Doğrudan Çekme (MASTER DATA)
            if plaka_kodu and eslesme_matrix is not None and not eslesme_matrix.empty and matris_kod_col:
                eslesme_matrix[matris_kod_col] = eslesme_matrix[matris_kod_col].astype(str).str.split('.').str[0].str.strip()
                m_match = eslesme_matrix[eslesme_matrix[matris_kod_col] == plaka_kodu]
                
                if not m_match.empty and matris_blok_kod_col and matris_blok_adi_col:
                    ilk_eslesme = m_match.dropna(subset=[matris_blok_kod_col]).iloc[0]
                    bagli_blok_kod = str(ilk_eslesme[matris_blok_kod_col]).strip()
                    bagli_blok_adi = str(ilk_eslesme[matris_blok_adi_col]).strip()
                    is_matched_via_matrix = True
                    
                    pivot_data.append({
                        "BAĞLI BLOK KODU": bagli_blok_kod, 
                        "BAĞLI BLOK ADI": bagli_blok_adi, 
                        "PLAKA ADET": plaka_adet
                    })

            # 2. ADIM: Sadece ve Sadece Yeni Kod Gelirse Fallback Çalışsın
            if not is_matched_via_matrix and not stok_df.empty:
                p_info = ayikla_karakter_ve_olcu(plaka_adi)
                text = str(p_info['karakter']).upper()
                p_dns = re.search(r'(\d{2,3})\s*(?:DNS)?', text).group(1) if re.search(r'(\d{2,3})\s*(?:DNS)?', text) else None
                p_words = set(re.findall(r'[A-Z]+', re.sub(r'\d+', '', text).replace('DNS', '').strip()))

                secilen_kod = None
                secilen_isim = None

                for _, s_row in stok_df.iterrows():
                    b_info = ayikla_karakter_ve_olcu(s_row.get('İsim', ''))
                    b_text = str(b_info['karakter']).upper()
                    b_dns = re.search(r'(\d{2,3})\s*(?:DNS)?', b_text).group(1) if re.search(r'(\d{2,3})\s*(?:DNS)?', b_text) else None
                    b_words = set(re.findall(r'[A-Z]+', re.sub(r'\d+', '', b_text).replace('DNS', '').strip()))

                    if p_dns and b_dns and p_dns != b_dns: continue
                    if len(p_words) > 0 and len(b_words) > 0 and len(p_words.intersection(b_words)) == 0: continue
                    
                    if plaka_sayisi_hesapla(p_info, b_info) > 0:
                        secilen_kod = str(s_row.get('Kod', '')).strip()
                        secilen_isim = str(s_row.get('İsim', '')).strip()
                        break 

                if secilen_kod:
                    bagli_blok_kod = secilen_kod
                    bagli_blok_adi = secilen_isim
                    pivot_data.append({
                        "BAĞLI BLOK KODU": secilen_kod, 
                        "BAĞLI BLOK ADI": secilen_isim, 
                        "PLAKA ADET": plaka_adet
                    })
                else:
                    bagli_blok_kod = "UYGUN BLOK MATRİSTE/STOKTA YOK"
                    bagli_blok_adi = "Eşleşen Blok Bilgisi Bulunamadı"

            vis_rows.append({
                "Plaka Kodu": plaka_kodu,
                "Plaka Adı/Tanımı": plaka_adi,
                "Talep Adet": plaka_adet,
                "Gerekli Blok Kodu": bagli_blok_kod,
                "Gerekli Blok Adı": bagli_blok_adi
            })

        vis_df = pd.DataFrame(vis_rows)

        # --- 1. BÖLÜM: TOPLAM GEREKLİ BLOK İHTİYAÇ RAPORU (PIVOT) ---
        with st.expander("📊 İŞ EMRİ TOPLAM GEREKLİ BLOK İHTİYAÇ RAPORU (ÖZET)", expanded=True):
            if pivot_data:
                pdf = pd.DataFrame(pivot_data)
                pivot_df = pdf.groupby(["BAĞLI BLOK KODU", "BAĞLI BLOK ADI"])["PLAKA ADET"].sum().reset_index()
                pivot_df.rename(columns={"PLAKA ADET": "Toplam Üretilecek Plaka (Adet)"}, inplace=True)
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ İş emri plakalarına ait gerekli blok stok özeti çıkarılamadı.")

        # --- 2. BÖLÜM: PLAKA VE BAĞLI BLOK DETAY TABLOSU ---
        st.subheader("📋 İş Emri Üretim Planı Kalemleri")
        st.dataframe(vis_df, use_container_width=True, hide_index=True)

        # --- 3. BÖLÜM: BARKOD OKUTMA VE AKSİYON ALANI ---
        st.markdown("---")
        st.subheader("⚙️ Blok Seçimi")
        barkod = st.text_input("🔍 KESİLECEK BLOK BARKODUNU OKUTUNUZ / PARTİ NO")

        if barkod:
            match = stok_df[stok_df['Tedarikçi Barkod'].astype(str).str.strip() == str(barkod).strip()]

            if not match.empty:
                blok = match.iloc[0]
                blok_kod = str(blok.get('Kod', '')).strip()
                blok_info = ayikla_karakter_ve_olcu(blok.get('İsim', ''))
                mevcut_miktar = safe_float(blok.get('Miktar', 0))

                def uygun_mu(row):
                    try:
                        if kod_col and eslesme_matrix is not None and not eslesme_matrix.empty and matris_kod_col:
                            pk = str(row.get(kod_col, '')).split('.')[0].strip()
                            matris_match = eslesme_matrix[eslesme_matrix[matris_kod_col] == pk]
                            if not matris_match.empty and matris_blok_kod_col:
                                if blok_kod in matris_match[matris_blok_kod_col].astype(str).str.strip().tolist():
                                    return plaka_sayisi_hesapla(ayikla_karakter_ve_olcu(row.get(tanim_col, "")), blok_info) > 0
                                return False

                        p_info = ayikla_karakter_ve_olcu(row.get(tanim_col, ""))
                        text = str(p_info['karakter']).upper()
                        b_text = str(blok_info['karakter']).upper()
                        p_dns = re.search(r'(\d{2,3})\s*(?:DNS)?', text).group(1) if re.search(r'(\d{2,3})\s*(?:DNS)?', text) else None
                        b_dns = re.search(r'(\d{2,3})\s*(?:DNS)?', b_text).group(1) if re.search(r'(\d{2,3})\s*(?:DNS)?', b_text) else None
                        
                        if p_dns and b_dns and p_dns != b_dns: return False
                        if len(set(re.findall(r'[A-Z]+', text)).intersection(set(re.findall(r'[A-Z]+', b_text)))) == 0: return False
                        return plaka_sayisi_hesapla(p_info, blok_info) > 0
                    except Exception:
                        return False

                uygunlar = df[df.apply(uygun_mu, axis=1)].copy()

                if not uygunlar.empty:
                    uygunlar['tek_kat_verim'] = uygunlar.apply(
                        lambda r: plaka_sayisi_hesapla(ayikla_karakter_ve_olcu(r.get(tanim_col, "")), blok_info), axis=1
                    )
                    emir = uygunlar.sort_values(by="tek_kat_verim", ascending=False).iloc[0]
                    
                    plaka_detay = ayikla_karakter_ve_olcu(emir[tanim_col])
                    kalinlik = plaka_detay['kalinlik']
                    adet = safe_float(emir[miktar_col])
                    
                    tek_katta_cikan_plaka = safe_float(emir['tek_kat_verim'])
                    gereken_dilim_sayisi = math.ceil(adet / tek_katta_cikan_plaka) if tek_katta_cikan_plaka > 0 else 0
                    net = gereken_dilim_sayisi * kalinlik

                    har = st.session_state.har_data
                    once = False
                    if not har.empty and 'Kod' in har.columns:
                        once = ((har['Kod'].astype(str).str.strip() == blok_kod) & (har['İşlem'] == "KESİM/SARF")).any()

                    fire = 0 if once else 2
                    toplam = net + fire

                    with st.container(border=True):
                        st.success(f"🎯 OKUTULAN BLOK UYUMLU: {blok.get('İsim', '')}")
                        st.write(f"**Eşleşen Plaka:** {emir[tanim_col]}")
                        st.write(f"**Kesim Planı:** Tek Katta Çıkan: {tek_katta_cikan_plaka} Plaka | Gerekli Bıçak Hareketi: {gereken_dilim_sayisi} Kez")
                        
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Blok Boyu / Kalan Stok (cm)", f"{mevcut_miktar:.2f}")
                        c_m2.metric("Toplam Düşecek Sarfiyat (cm)", f"{toplam:.2f}", delta=f"Fire: {fire} cm")

                    if st.button("✂️ KESİM HAREKETİNİ ONAYLA VE STOKTAN DÜŞ", type="primary", use_container_width=True):
                        if mevcut_miktar < toplam:
                            st.error(f"❌ Yetersiz Stok! Blokta {mevcut_miktar:.2f} cm var, {toplam:.2f} cm gerekiyor.")
                        else:
                            try:
                                 hedef_index = stok_df[stok_df['Kod'].astype(str).str.strip() == blok_kod].index
                                 if not hedef_index.empty:
                                     stok_df.loc[hedef_index, 'Miktar'] -= toplam

                                 yeni = pd.DataFrame([{
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "İşlem": "KESİM/SARF",
                                    "Kod": blok.get('Kod', ''),
                                    "Miktar": toplam
                                 }])

                                 veritabani.update_data("Stok", stok_df)
                                 veritabani.update_data("Hareketler", pd.concat([har, yeni], ignore_index=True))
                                
                                 st.balloons()
                                 st.success("🎉 Kesim işlemi başarıyla veritabanına işlendi, stok güncellendi!")
                                 st.rerun()
                            except Exception as e:
                                 st.error(f"❌ Veritabanı kaydı hatası: {e}")
                else:
                    st.error("❌ Okuttuğunuz blok kod/kalitesi, yüklenen iş emrindeki açık plakaların hiçbirinin hammadde gereksinimiyle (Matris bazında) eşleşmiyor!")
            else:
                st.error("❌ Okutulan Blok Barkodu stok listesinde bulunamadı!")

    st.markdown("---")
    st.caption("Bilal KEMERTAŞ | BRN 2026")
