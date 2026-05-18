import streamlit as st
import pandas as pd
import veritabani
import re
import math
from datetime import datetime

def run_blok_kesim(conn):

    # --- GELİŞMİŞ AYIKLAMA (3'LÜ ÖLÇÜ VE VİRGÜL DESTEKLİ) ---
    def ayikla_karakter_ve_olcu(text):
        if pd.isna(text) or str(text).strip() == "":
            return None

        t = str(text).upper().replace(",", ".").strip() # Virgülleri noktaya çevir (18.5 için)
        
        # 3'lü veya 2'li ölçü kalıbını bulur (Örn: 188X88X18.5 veya 200X100)
        olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
        olcu_kisa = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)

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
            return {"boy": 0, "en": 0, "kalinlik": 0, "karakter": t}

        # Ölçüden öncesini ürünün karakteri/kalitesi olarak alıyoruz
        karakter = t[:start_idx].strip()
        return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}

    # --- TEMİZLEME ---
    def temizle_karakter(text):
        if not text:
            return ""
        t = text.upper()
        # Kelimelerin tam eşleşmesi için temizlik yapıyoruz
        gereksizler = ["SUNGER", "PU", "PLAKA", "DUZ", "LEVHA", "RULO", "YATAK", "FRMYTK"]
        for g in gereksizler:
            t = t.replace(g, "")
        # Parantezleri ve özel karakterleri temizle
        t = re.sub(r'[\(\)\-\+\:]', ' ', t)
        return re.sub(r'\s+', ' ', t).strip()

    # --- YENİ: DNS VE KALİTE PARSİNG ---
    def parse_ozellik(text):
        text = str(text).upper().replace(",", ".")
        dns_match = re.search(r'(\d{2,3})\s*(?:DNS)?', text)
        text_harfler = re.sub(r'\d+', '', text).replace('DNS', '').strip()
        kalite_kelimeleri = set(re.findall(r'[A-Z]+', text_harfler))
        return {
            "dns": int(dns_match.group(1)) if dns_match else None,
            "kelimeler": kalite_kelimeleri
        }

    # --- YENİ: KELİME BAZLI EŞLEŞTİRME (DNS ZIRHLI) ---
    def karakter_match(plaka, blok):
        if not plaka or not blok:
            return False
            
        p = parse_ozellik(plaka)
        b = parse_ozellik(blok)

        # DNS birebir olmalı
        if p["dns"] is not None and b["dns"] is not None:
            if p["dns"] != b["dns"]:
                return False

        # Kalite kelimeleri kesişmeli
        ortak = p["kelimeler"].intersection(b["kelimeler"])
        if len(p["kelimeler"]) > 0 and len(b["kelimeler"]) > 0 and len(ortak) == 0:
            return False

        return True

    # --- YENİ: PLAKA SAYISI (VERİM) HESAPLAMA ---
    def plaka_sayisi_hesapla(plaka, blok):
        if plaka.get('boy', 0) == 0 or plaka.get('en', 0) == 0:
            return 0

        # Düz Kesim
        adet_boy_1 = int(blok['boy'] // plaka['boy'])
        adet_en_1  = int(blok['en'] // plaka['en'])
        verim_1 = adet_boy_1 * adet_en_1

        # 90 Derece Döndürülerek Kesim
        adet_boy_2 = int(blok['boy'] // plaka['en'])
        adet_en_2  = int(blok['en'] // plaka['boy'])
        verim_2 = adet_boy_2 * adet_en_2

        return max(verim_1, verim_2)

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
        df = pd.read_excel(up)
        df.columns = [str(c).strip() for c in df.columns]
        st.session_state.main_data = df
        st.session_state.stok_data = veritabani.get_internal_data("Stok")
        st.session_state.har_data = veritabani.get_internal_data("Hareketler")

    # --- ANA OPERASYON ---
    if 'main_data' in st.session_state:
        df = st.session_state.main_data

        # Dinamik Sütun Yakalama
        tanim_col = next((c for c in df.columns if "STOK" in c.upper() or "TANIM" in c.upper()), None)
        blok_col = next((c for c in df.columns if "BLOKCM" in c.upper() or "KODU" in c.upper() or "KOD" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MİKTAR" in c.upper()), None)

        barkod = st.text_input("🔍 OKUTULAN BARKOD / PARTİ NO")

        if barkod:
            stok_df = st.session_state.stok_data
            
            # Master veri ve hareket listesindeki barkodları stringe çevirerek tam eşleştirme yapıyoruz
            match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == str(barkod)]

            if not match.empty:
                blok = match.iloc[0]
                blok_info = ayikla_karakter_ve_olcu(blok['İsim'])

                def uygun_mu(row):
                    try:
                        plaka = ayikla_karakter_ve_olcu(row[tanim_col])
                        if not plaka or not blok_info:
                            return False

                        plaka_clean = temizle_karakter(plaka['karakter'])
                        blok_clean = temizle_karakter(blok_info['karakter'])

                        # 1. Aşama: Sünger Kalite/Dansite Uyumu Kontrolü (YENİ MODEL)
                        karakter_ok = karakter_match(plaka_clean, blok_clean)

                        # 2. Aşama: Ölçü Esnekliği ve Kesim Verimi Kontrolü (YENİ MODEL)
                        verim = plaka_sayisi_hesapla(plaka, blok_info)
                        olcu_ok = verim > 0

                        return karakter_ok and olcu_ok
                    except:
                        return False

                # Uygun siparişleri bul
                uygunlar = df[df.apply(uygun_mu, axis=1)].copy()

                if not uygunlar.empty:
                    # YENİ: EN İYİ EŞLEŞMEYİ SEÇME (Verim Puanlaması)
                    uygunlar['tek_kat_verim'] = uygunlar.apply(
                        lambda r: plaka_sayisi_hesapla(ayikla_karakter_ve_olcu(r[tanim_col]), blok_info), axis=1
                    )
                    
                    # Verimi en yüksek olan siparişi seç
                    emir = uygunlar.sort_values(by="tek_kat_verim", ascending=False).iloc[0]
                    
                    plaka_detay = ayikla_karakter_ve_olcu(emir[tanim_col])
                    kalinlik = plaka_detay['kalinlik'] if plaka_detay else 0
                    adet = float(emir[miktar_col]) if miktar_col else 0
                    
                    # YENİ: GERÇEK KALINLIK DİLİMLEME MATEMATİĞİ
                    tek_katta_cikan_plaka = emir['tek_kat_verim']
                    # Bu siparişi karşılamak için makine kaç dilim kesecek?
                    gereken_dilim_sayisi = math.ceil(adet / tek_katta_cikan_plaka) if tek_katta_cikan_plaka > 0 else 0
                    # Tüketilecek net blok kalınlığı
                    net = gereken_dilim_sayisi * kalinlik

                    # Rapor Geçmişi ve Fire Hesabı (SENİN MANTIĞIN KORUNDU)
                    har = st.session_state.har_data
                    once = False
                    if not har.empty and 'Kod' in har.columns:
                        once = ((har['Kod'] == blok['Kod']) & (har['İşlem'] == "KESİM/SARF")).any()

                    fire = 0 if once else 2
                    toplam = net + fire

                    # Bilgilendirme Kartı
                    with st.container(border=True):
                        st.success("✅ REÇETE VE EŞLEŞME BULUNDU")
                        st.write(f"**Eşleşen Ürün:** {emir[tanim_col]}")
                        st.write(f"**Kesim Detayı:** Tek Katta Çıkan Plaka: {tek_katta_cikan_plaka} | Bıçak Hareketi: {gereken_dilim_sayisi} Kez")
                        st.write(f"**Sipariş Adeti:** {adet} Adet")
                        
                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Mevcut Stok (cm/Mt)", f"{blok['Miktar']:.2f}")
                        c_m2.metric("Düşülecek Toplam Sarfiyat", f"{toplam:.2f}", delta=f"Fire: {fire}")

                    # --- BUTON DURUM YÖNETİMİ VE KAYIT ---
                    if st.button("✂️ KESİM HAREKETİNİ ONAYLA", type="primary"):
                        if blok['Miktar'] < toplam:
                            st.error("❌ Depodaki bu blok miktarı, kesilmek istenen miktardan az! (Yetersiz Stok)")
                        else:
                            # Bellekteki Stok Miktarını Güncelle
                            stok_df.loc[stok_df['Kod'] == blok['Kod'], 'Miktar'] -= toplam

                            # Yeni Hareket Satırı Oluştur
                            yeni = pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İşlem": "KESİM/SARF",
                                "Kod": blok['Kod'],
                                "Miktar": toplam
                            }])

                            # Veritabanına/Sheets'e gönder
                            veritabani.update_data("Stok", stok_df)
                            veritabani.update_data("Hareketler", pd.concat([har, yeni], ignore_index=True))
                            
                            st.balloons()
                            st.success("🎉 Kesim işlemi başarıyla kaydedildi! Stok güncellendi.")
                            st.rerun()
                else:
                    st.error("❌ Bu Barkodun Sünger Kalitesi veya Ölçüsü, Yüklenen Sipariş Listesiyle Eşleşmiyor!")
            else:
                st.error("❌ Okutulan Barkod Sistem Stoklarında Kayıtlı Değil!")

    st.markdown("---")
    st.caption("Bilal KEMERTAŞ | BRN 2026")
