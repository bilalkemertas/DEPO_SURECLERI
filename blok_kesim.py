import streamlit as st
import pandas as pd
import veritabani
import re
from datetime import datetime

def run_blok_kesim(conn):

    # --- GELİŞMİŞ AYIKLAMA ---
    def ayikla_karakter_ve_olcu(text):
        if pd.isna(text) or str(text).strip() == "":
            return None

        t = str(text).upper().replace(",", ".").strip()

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

        karakter = t[:start_idx].strip()
        return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}

    # --- TEMİZLEME ---
    def temizle_karakter(text):
        if not text:
            return ""
        t = text.upper()
        gereksizler = ["SUNGER", "PU", "PLAKA", "DUZ", "LEVHA", "RULO", "YATAK", "FRMYTK"]
        for g in gereksizler:
            t = t.replace(g, "")
        t = t.replace("DNS", "")
        t = re.sub(r'[\(\)\-\+\:]', ' ', t)
        return re.sub(r'\s+', ' ', t).strip()

    # --- KARAKTER MATCH (GELİŞTİRİLDİ) ---
    def karakter_match(plaka, blok):
        if not plaka or not blok:
            return False

        def parse(text):
            dns = re.search(r'(\d+)\s*DNS', text)
            dns_val = int(dns.group(1)) if dns else None
            kelimeler = set(re.findall(r'[A-Z]+', text))
            return dns_val, kelimeler

        p_dns, p_words = parse(plaka)
        b_dns, b_words = parse(blok)

        if p_dns and b_dns and p_dns != b_dns:
            return False

        ortak = p_words.intersection(b_words)
        return len(ortak) >= 1

    # --- ÜRETİM HESABI ---
    def plaka_sayisi(plaka, blok):
        if plaka['boy'] == 0 or plaka['en'] == 0:
            return 0

        adet_boy = int(blok['boy'] // plaka['boy'])
        adet_en  = int(blok['en'] // plaka['en'])

        return adet_boy * adet_en

    # --- NAV ---
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

    # --- ANA ---
    if 'main_data' in st.session_state:

        df = st.session_state.main_data

        tanim_col = next((c for c in df.columns if "STOK" in c.upper() or "TANIM" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MİKTAR" in c.upper()), None)

        barkod = st.text_input("🔍 OKUTULAN BARKOD / PARTİ NO")

        if barkod:

            stok_df = st.session_state.stok_data
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

                        karakter_ok = karakter_match(plaka_clean, blok_clean)

                        uretim = plaka_sayisi(plaka, blok_info)
                        olcu_ok = uretim > 0

                        return karakter_ok and olcu_ok
                    except:
                        return False

                uygunlar = df[df.apply(uygun_mu, axis=1)]

                if not uygunlar.empty:

                    # --- EN İYİ SEÇİM ---
                    def skor(row):
                        pl = ayikla_karakter_ve_olcu(row[tanim_col])
                        return plaka_sayisi(pl, blok_info)

                    uygunlar['SKOR'] = uygunlar.apply(skor, axis=1)
                    emir = uygunlar.sort_values(by="SKOR", ascending=False).iloc[0]

                    plaka_detay = ayikla_karakter_ve_olcu(emir[tanim_col])

                    kalinlik = plaka_detay['kalinlik'] if plaka_detay else 0
                    adet = float(emir[miktar_col]) if miktar_col else 0

                    uretilebilir = plaka_sayisi(plaka_detay, blok_info)

                    if uretilebilir == 0:
                        st.error("Bu bloktan üretim yapılamaz")
                        st.stop()

                    net = adet * kalinlik

                    har = st.session_state.har_data
                    once = False
                    if not har.empty and 'Kod' in har.columns:
                        once = ((har['Kod'] == blok['Kod']) & (har['İşlem'] == "KESİM/SARF")).any()

                    fire = 0 if once else 2
                    toplam = net + fire

                    with st.container(border=True):
                        st.success("✅ REÇETE VE EŞLEŞME BULUNDU")
                        st.write(f"**Eşleşen Ürün:** {emir[tanim_col]}")
                        st.write(f"**Üretilebilir Plaka:** {uretilebilir} adet")
                        st.write(f"**Kalınlık:** {kalinlik} cm | **Sipariş:** {adet} adet")

                        c_m1, c_m2 = st.columns(2)
                        c_m1.metric("Mevcut Stok", f"{blok['Miktar']:.2f}")
                        c_m2.metric("Toplam Sarfiyat", f"{toplam:.2f}", delta=f"Fire: {fire}")

                    if st.button("✂️ KESİM HAREKETİNİ ONAYLA", type="primary"):
                        if blok['Miktar'] < toplam:
                            st.error("❌ YETERSİZ STOK")
                        else:
                            stok_df.loc[stok_df['Kod'] == blok['Kod'], 'Miktar'] -= toplam

                            yeni = pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İşlem": "KESİM/SARF",
                                "Kod": blok['Kod'],
                                "Miktar": toplam
                            }])

                            veritabani.update_data("Stok", stok_df)
                            veritabani.update_data("Hareketler", pd.concat([har, yeni], ignore_index=True))

                            st.success("🎉 KESİM KAYDEDİLDİ")
                            st.rerun()

                else:
                    st.error("❌ EŞLEŞME YOK")

            else:
                st.error("❌ BARKOD BULUNAMADI")

    st.markdown("---")
    st.caption("Bilal KEMERTAŞ | BRN 2026")
