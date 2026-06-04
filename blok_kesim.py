import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime

def run_blok_kesim(conn):

    # --- YEREL MASTER DATA YÜKLEME (PERFORMANS İÇİN CACHED / SESSION STATE) ---
    if 'eslesme_df' not in st.session_state:
        csv_path = "eslesme_matrisi.csv"
        if os.path.exists(csv_path):
            try:
                # CSV dosyasını güvenli şekilde oku ve stringe zorla
                st.session_state.eslesme_df = pd.read_csv(csv_path, dtype=str)
                # Sütun isimlerindeki olası boşlukları temizle
                st.session_state.eslesme_df.columns = [c.strip() for c in st.session_state.eslesme_df.columns]
            except Exception as e:
                st.error(f"⚠️ 'eslesme_matrisi.csv' okuma hatası: {e}")
                st.session_state.eslesme_df = pd.DataFrame()
        else:
            st.warning("⚠️ 'eslesme_matrisi.csv' dosyası kök dizinde bulunamadı! Eski algoritmaya geçiş yapılıyor.")
            st.session_state.eslesme_df = pd.DataFrame()

    # --- ZIRHLI AYIKLAMA MOTORU (ASLA NONE DÖNMEZ) ---
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

    # --- PLAKA VE VERİM HESAPLAMA (GÜVENLİ) ---
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

    st.title("✂️ Akıllı Blok Kesim Komuta Ekranı")

    # --- YÜKLE ---
    up = st.file_uploader("Excel Dosyasını Yükleyin (DataGrid)", type=['xlsx'])

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

    # --- ANA OPERASYON ---
    if 'main_data' in st.session_state:
        df = st.session_state.main_data
        eslesme_matrix = st.session_state.eslesme_df

        tanim_col = next((c for c in df.columns if "TANIM" in c.upper() or "ÜRÜN" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MIKTAR" in c.upper() or "MİKTAR" in c.upper()), None)
        kod_col = next((c for c in df.columns if "KOD" in c.upper() or "STOK KODU" in c.upper()), None) # Plaka/Yarı mamul kod sütununu bul

        if not tanim_col or not miktar_col:
            st.warning("⚠️ Yüklenen Excel dosyasında Ürün Tanımı ('Ürün'/'Tanım') veya Adet ('Adet'/'Miktar') sütunları bulunamadı!")
            st.stop()

        barkod = st.text_input("🔍 OKUTULAN BARKOD / PARTİ NO")

        if barkod:
            stok_df = st.session_state.stok_data
            match = stok_df[stok_df['Tedarikçi Barkod'].astype(str).str.strip() == str(barkod).strip()]

            if not match.empty:
                blok = match.iloc[0]
                blok_kod = str(blok.get('Kod', '')).strip() # Okutulan bloğun gerçek stok kodu
                blok_info = ayikla_karakter_ve_olcu(blok.get('İsim', ''))
                mevcut_miktar = safe_float(blok.get('Miktar', 0))

                # --- SİHİRLİ EŞLEŞTİRME FONKSİYONU ---
                def uygun_mu(row):
                    try:
                        # Eğer yüklenen kesim listesinde kod sütunu varsa ve CSV yüklendiyse öncelikli MASTER DATA sorgula
                        if kod_col and not eslesme_matrix.empty:
                            plaka_kodu = str(row.get(kod_col, '')).strip()
                            
                            # CSV matrisinden plakanın hammadde/stok kodunu filtrele
                            matris_match = eslesme_matrix[eslesme_matrix['hammadde kodu'] == plaka_kodu]
                            
                            if not matris_match.empty:
                                # Bu plakanın bağlı olduğu onaylı blok kodlarının listesini al
                                onayli_blok_kodlari = matris_match['BAĞLI BLOK STOK KODU'].astype(str).str.strip().tolist()
                                
                                # Okutulan blok kodu, bu plakanın üretebileceği blok listesinde var mı?
                                if blok_kod in onayli_blok_kodlari:
                                    # Kod eşleştiyse sadece ölçü kurtarıyor mu (verim var mı) ona bak, karakteri sorma bile!
                                    urun_adi = row.get(tanim_col, "")
                                    plaka_olculeri = ayikla_karakter_ve_olcu(urun_adi)
                                    verim = plaka_sayisi_hesapla(plaka_olculeri, blok_info)
                                    return verim > 0
                                else:
                                    return False # Onaylı blok listesinde yoksa elenir

                        # --- FALLBACK: Eğer kod sütunu bulunamazsa eski Akıllı Regex Algoritması devreye girer ---
                        urun_adi = row.get(tanim_col, "")
                        if pd.isna(urun_adi): return False
                        
                        plaka = ayikla_karakter_ve_olcu(urun_adi)
                        
                        # Eski Karakter parse/DNS kelime eşleştirme motoru
                        text = str(plaka['karakter']).upper().replace(",", ".") if plaka['karakter'] else ""
                        p_dns = int(re.search(r'(\d{2,3})\s*(?:DNS)?', text).group(1)) if re.search(r'(\d{2,3})\s*(?:DNS)?', text) else None
                        p_words = set(re.findall(r'[A-Z]+', re.sub(r'\d+', '', text).replace('DNS', '').strip()))

                        b_text = str(blok_info['karakter']).upper().replace(",", ".") if blok_info['karakter'] else ""
                        b_dns = int(re.search(r'(\d{2,3})\s*(?:DNS)?', b_text).group(1)) if re.search(r'(\d{2,3})\s*(?:DNS)?', b_text) else None
                        b_words = set(re.findall(r'[A-Z]+', re.sub(r'\d+', '', b_text).replace('DNS', '').strip()))

                        if p_dns is not None and b_dns is not None and p_dns != b_dns: return False
                        if len(p_words) > 0 and len(b_words) > 0 and len(p_words.intersection(b_words)) == 0: return False
                        
                        verim = plaka_sayisi_hesapla(plaka, blok_info)
                        return verim > 0
                    except Exception:
                        return False

                # Hızlı filtreleme
                uygunlar = df[df.apply(uygun_mu, axis=1)].copy()

                if not uygunlar.empty:
                    # En iyi eşleşmeyi seç
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

                    # --- GÜVENLİ FİRE GEÇMİŞİ KONTROLÜ ---
                    har = st.session_state.har_data
                    once = False
                    if not har.empty and 'Kod' in har.columns:
                        har_kod_str = har['Kod'].astype(str).str.strip()
                        once = ((har_kod_str == blok_kod) & (har['İşlem'] == "KESİM/SARF")).any()

                    fire = 0 if once else 2
                    toplam = net + fire

                    with st.container(border=True):
                        st.success("✅ REÇETE VE MASTER DATA EŞLEŞMESİ BULUNDU")
                        st.write(f"**Eşleşen Ürün:** {emir[tanim_col]}")
                        if kod_col and not eslesme_matrix.empty and str(emir.get(kod_col, '')).strip() in eslesme_matrix['hammadde kodu'].values:
                            st.caption("🎯 Bilgi: Eşleşme 2258 Satırlık 'Blok-Plaka Matrisi' üzerinden tam doğrulukla yapılmıştır.")
                        st.write(f"**Kesim Detayı:** Tek Katta Çıkan Plaka: {tek_katta_cikan_plaka} | Bıçak Hareketi: {gereken_dilim_sayisi} Kez")
                        st.write(f"**Sipariş Adeti:** {adet} Adet")
                        
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Mevcut Stok (cm/Mt)", f"{mevcut_miktar:.2f}")
                        c_m2.metric("Düşülecek Toplam Sarfiyat", f"{toplam:.2f}", delta=f"Fire: {fire}")

                    # Buton ve Kayıt
                    if st.button("✂️ KESİM HAREKETİNİ ONAYLA", type="primary"):
                        if mevcut_miktar < toplam:
                            st.error(f"❌ Yetersiz Stok! Bu işlem için {toplam:.2f} cm gerekli, blokta {mevcut_miktar:.2f} cm var.")
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
                                st.success("🎉 Kesim işlemi başarıyla kaydedildi! Stok güncellendi.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Veritabanı kaydı sırasında hata oluştu: {e}")
                else:
                    st.error("❌ Bu Barkodun Sünger Kalitesi veya Ölçüsü, Yüklenen Sipariş Listesiyle Eşleşmiyor!")
            else:
                st.error("❌ Okutulan Barkod Sistem Stoklarında Kayıtlı Değil!")

    st.markdown("---")
    st.caption("Bilal KEMERTAŞ | BRN 2026")
