import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def run_blok_kesim(conn):

    # --- AYIKLAMA ---
    def ayikla_karakter_ve_olcu(text):
        if pd.isna(text) or str(text).strip() == "":
            return None

        t = str(text).upper().strip()

        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)', t)
        boy = float(olcu.group(1)) if olcu else 0
        en = float(olcu.group(2)) if olcu else 0

        karakter = t
        if olcu:
            karakter = t[:olcu.start()].strip()

        return {"boy": boy, "en": en, "karakter": karakter}


    # --- BLOKCM AYRI AYIKLAMA ---
    def ayikla_blokcm(text):
        if pd.isna(text):
            return None

        t = str(text).upper()

        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)', t)

        return {
            "boy": float(olcu.group(1)) if olcu else 0,
            "en": float(olcu.group(2)) if olcu else 0,
            "full": t
        }


    # --- TEMİZLEME (KRİTİK DÜZELTME) ---
    def temizle_karakter(text):
        if not text:
            return ""

        t = text.upper()

        gereksizler = ["SUNGER", "PU", "PLAKA", "DUZ", "LEVHA"]

        for g in gereksizler:
            t = t.replace(g, "")

        return re.sub(r'\s+', ' ', t).strip()


    # --- MATCH (DÜZELTİLDİ) ---
    def karakter_match(plaka, blok):
        if not plaka or not blok:
            return False

        # artık direkt string içerik karşılaştırıyoruz
        plaka_words = set(plaka.split())
        blok_words = set(blok.split())

        ortak = plaka_words.intersection(blok_words)

        # en az 2 güçlü teknik eşleşme
        return len(ortak) >= 2


    # --- NAV ---
    c1, c2, _ = st.columns([1.5,1.5,4])

    if c1.button("ANA MENÜ"):
        st.session_state.page = 'home'
        st.rerun()

    if c2.button("TEMİZLE"):
        for k in ['main_data','stok_data','har_data']:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    st.title("BLOK KESİM")

    # --- YÜKLE ---
    up = st.file_uploader("Excel", type=['xlsx'])

    if up and 'main_data' not in st.session_state:
        df = pd.read_excel(up)
        df.columns = [str(c).strip() for c in df.columns]

        st.session_state.main_data = df
        st.session_state.stok_data = veritabani.get_internal_data("Stok")
        st.session_state.har_data = veritabani.get_internal_data("Hareketler")

    # --- ANA ---
    if 'main_data' in st.session_state:

        df = st.session_state.main_data

        tanim_col = next((c for c in df.columns if "STOK ADI" in c.upper()), None)
        blok_col = next((c for c in df.columns if "BLOKCM" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper()), None)

        barkod = st.text_input("BARKOD")

        if barkod:

            stok_df = st.session_state.stok_data
            match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == barkod]

            if not match.empty:

                blok = match.iloc[0]
                blok_info = ayikla_karakter_ve_olcu(blok['İsim'])

                def uygun_mu(row):
                    try:
                        plaka = ayikla_karakter_ve_olcu(row[tanim_col])
                        hedef = ayikla_blokcm(row[blok_col])

                        if not plaka or not hedef or not blok_info:
                            return False

                        plaka_clean = temizle_karakter(plaka['karakter'])
                        blok_clean = temizle_karakter(blok_info['karakter'])

                        karakter_ok = karakter_match(plaka_clean, blok_clean)

                        # 🔥 KRİTİK DÜZELTME: SADECE BOY DEĞİL EN DE KONTROL
                        olcu_ok = (
                            abs(hedef['boy'] - blok_info['boy']) < 3 and
                            abs(hedef['en'] - blok_info['en']) < 3
                        )

                        return karakter_ok and olcu_ok

                    except:
                        return False

                uygunlar = df[df.apply(uygun_mu, axis=1)]

                if not uygunlar.empty:

                    emir = uygunlar.iloc[0]

                    kalinlik_match = re.search(r'X(\d+)$', str(emir[tanim_col]).upper())
                    kalinlik = float(kalinlik_match.group(1)) if kalinlik_match else 0

                    adet = float(emir[miktar_col]) if miktar_col else 0
                    net = adet * kalinlik

                    har = st.session_state.har_data
                    once = ((har['Kod']==blok['Kod']) & (har['İşlem']=="KESİM/SARF")).any()

                    fire = 0 if once else 2
                    toplam = net + fire

                    st.success("EŞLEŞME VAR")
                    st.write(emir[tanim_col])
                    st.metric("DÜŞÜLECEK", toplam)

                    if st.button("KES"):
                        if blok['Miktar'] < toplam:
                            st.error("YETERSİZ")
                            st.stop()

                        stok_df.loc[stok_df['Kod']==blok['Kod'],'Miktar'] -= toplam

                        yeni = pd.DataFrame([{
                            "Tarih": datetime.now(),
                            "İşlem": "KESİM/SARF",
                            "Kod": blok['Kod'],
                            "Miktar": toplam
                        }])

                        veritabani.update_data("Stok", stok_df)
                        veritabani.update_data("Hareketler", pd.concat([har,yeni]))

                        st.success("OK")

                else:
                    st.error("EŞLEŞME YOK")

            else:
                st.error("BARKOD YOK")

    st.markdown("---")
    st.markdown("Bilal KEMERTAŞ | BRN 2026")
