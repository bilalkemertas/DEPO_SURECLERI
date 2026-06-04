import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime


def run_blok_kesim(conn):

    # --- YEREL MASTER DATA YÜKLEME ---
    if 'eslesme_df' not in st.session_state:

        csv_path = "eslesme_matrisi.csv"

        if os.path.exists(csv_path):

            encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
            success = False

            for enc in encodings:
                try:
                    dfm = pd.read_csv(csv_path, dtype=str, encoding=enc)

                    dfm.columns = (
                        dfm.columns
                        .astype(str)
                        .str.replace('\ufeff', '', regex=False)
                        .str.strip()
                    )

                    st.session_state.eslesme_df = dfm
                    success = True
                    break

                except Exception:
                    continue

            if not success:
                st.error("⚠️ eslesme_matrisi.csv okunamadı")
                st.session_state.eslesme_df = pd.DataFrame()

        else:
            st.warning("⚠️ eslesme_matrisi.csv bulunamadı")
            st.session_state.eslesme_df = pd.DataFrame()

    # --- AYIKLAMA ---
    def ayikla_karakter_ve_olcu(text):

        default_return = {
            "boy": 0.0,
            "en": 0.0,
            "kalinlik": 0.0,
            "karakter": str(text) if text else ""
        }

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

            return {
                "boy": boy,
                "en": en,
                "kalinlik": kalinlik,
                "karakter": karakter
            }

        except Exception:
            return default_return

    # --- VERİM HESAP ---
    def plaka_sayisi_hesapla(plaka, blok):

        if not plaka or not blok:
            return 0

        if plaka.get('boy', 0) == 0 or plaka.get('en', 0) == 0:
            return 0

        return max(
            int(blok.get('boy', 0) // plaka['boy']) * int(blok.get('en', 0) // plaka['en']),
            int(blok.get('boy', 0) // plaka['en']) * int(blok.get('en', 0) // plaka['boy'])
        )

    def safe_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    # --- UI ---
    st.title("✂️ Blok Kesim Ekranı")

    up = st.file_uploader("Excel Dosyasını Yükleyin", type=['xlsx'])

    if up and 'main_data' not in st.session_state:

        raw_df = pd.read_excel(up, header=None)

        header_idx = 0

        for i in range(min(20, len(raw_df))):
            row_txt = " ".join(str(x).upper() for x in raw_df.iloc[i].values if pd.notna(x))
            if ("PLAKA" in row_txt or "SİPARİŞ" in row_txt) and ("ADET" in row_txt or "MIKTAR" in row_txt):
                header_idx = i
                break

        df = pd.read_excel(up, header=header_idx)

        # 🔥 KRİTİK FIX: kolon normalize
        df.columns = (
            df.columns
            .astype(str)
            .str.replace('\ufeff', '', regex=False)
            .str.replace('\t', '', regex=False)
            .str.strip()
        )

        st.session_state.main_data = df
        st.session_state.stok_data = veritabani.get_internal_data("Stok")
        st.session_state.har_data = veritabani.get_internal_data("Hareketler")

    if 'main_data' not in st.session_state:
        return

    df = st.session_state.main_data
    stok_df = st.session_state.stok_data
    eslesme_matrix = st.session_state.eslesme_df

    # --- ROBUST COL FINDER ---
    def find_col(cols, keys):
        for c in cols:
            cu = str(c).upper()
            for k in keys:
                if k in cu:
                    return c
        return None

    tanim_col = find_col(df.columns, ["PLAKA ADI", "TANIM", "ÜRÜN", "URUN"])
    miktar_col = find_col(df.columns, ["ADET", "MIKTAR"])
    kod_col = find_col(df.columns, ["PLAKA KODU", "PLAKA KOD", "SIPARIS", "KOD"])

    if not tanim_col or not miktar_col:
        st.error("Excel kolonları okunamadı → Plaka Adı / Adet eksik")
        st.write(df.columns)
        return

    vis_rows = []
    pivot_data = []

    for idx, row in df.iterrows():

        plaka_adi = str(row.get(tanim_col, '')).strip()
        plaka_kodu = str(row.get(kod_col, '')).split('.')[0].strip() if kod_col else ""
        plaka_adet = safe_float(row.get(miktar_col, 0))

        bagli_blok_kod = ""
        bagli_blok_adi = ""
        is_matched = False

        # --- MATRIS ---
        if plaka_kodu and not eslesme_matrix.empty:

            m = eslesme_matrix[
                eslesme_matrix.iloc[:, 0].astype(str).str.strip() == plaka_kodu
            ]

            if not m.empty and len(m.columns) >= 4:

                bagli_blok_kod = str(m.iloc[0, 2]).strip()
                bagli_blok_adi = str(m.iloc[0, 3]).strip()

                is_matched = True

                pivot_data.append({
                    "BAĞLI BLOK KODU": bagli_blok_kod,
                    "BAĞLI BLOK ADI": bagli_blok_adi,
                    "PLAKA ADET": plaka_adet
                })

        # --- FALLBACK ---
        if not is_matched:

            p_info = ayikla_karakter_ve_olcu(plaka_adi)

            for _, s in stok_df.iterrows():

                b_info = ayikla_karakter_ve_olcu(s.get('İsim', ''))

                if plaka_sayisi_hesapla(p_info, b_info) > 0:
                    bagli_blok_kod = s.get('Kod', '')
                    bagli_blok_adi = s.get('İsim', '')
                    break

            if not bagli_blok_kod:
                bagli_blok_kod = "UYGUN BLOK YOK"
                bagli_blok_adi = "Uygun bulunamadı"

        df.at[idx, 'Gerekli Blok Kodu'] = bagli_blok_kod
        df.at[idx, 'Gerekli Blok Adı'] = bagli_blok_adi

        vis_rows.append({
            "Plaka Kodu": plaka_kodu,
            "Plaka Adı": plaka_adi,
            "Adet": plaka_adet,
            "Blok": bagli_blok_adi
        })

    st.dataframe(pd.DataFrame(vis_rows), use_container_width=True)

    if pivot_data:
        pdf = pd.DataFrame(pivot_data)
        st.dataframe(
            pdf.groupby(["BAĞLI BLOK KODU", "BAĞLI BLOK ADI"])["PLAKA ADET"]
            .sum()
            .reset_index(),
            use_container_width=True
        )
