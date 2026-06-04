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

            encodings = ['utf-8-sig','utf-8','windows-1254','iso-8859-9','cp1254']
            success = False

            for enc in encodings:
                try:
                    eslesme_df = pd.read_csv(csv_path, dtype=str, encoding=enc, sep=';')

                    eslesme_df.columns = [
                        str(c).replace('\ufeff', '').strip()
                        for c in eslesme_df.columns
                    ]

                    for col in eslesme_df.columns:
                        eslesme_df[col] = (
                            eslesme_df[col]
                            .astype(str)
                            .str.replace('\ufeff', '', regex=False)
                            .str.strip()
                        )

                    st.session_state.eslesme_df = eslesme_df
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

    # --- PLAKA VERİM ---
    def plaka_sayisi_hesapla(plaka, blok):
        if not plaka or not blok:
            return 0
        if plaka.get('boy', 0) == 0 or plaka.get('en', 0) == 0:
            return 0

        adet_boy_1 = int(blok.get('boy', 0) // plaka['boy'])
        adet_en_1  = int(blok.get('en', 0) // plaka['en'])
        verim_1 = adet_boy_1 * adet_en_1

        adet_boy_2 = int(blok.get('boy', 0) // plaka['en'])
        adet_en_2  = int(blok.get('en', 0) // plaka['boy'])
        verim_2 = adet_boy_2 * adet_en_2

        return max(verim_1, verim_2)

    def safe_float(val, default=0.0):
        try:
            return float(val)
        except:
            return default

    st.title("✂️ Blok Kesim Ekranı")

    up = st.file_uploader("Excel Yükle", type=['xlsx'])

    if up and 'main_data' not in st.session_state:

        # 🔥 BAŞLIK SATIRI DÜZELTME (gerekirse 1 → 2 yap)
        df = pd.read_excel(up, header=1)

        st.session_state.main_data = df
        st.session_state.stok_data = veritabani.get_internal_data("Stok")
        st.session_state.har_data = veritabani.get_internal_data("Hareketler")

    if 'main_data' not in st.session_state:
        return

    df = st.session_state.main_data
    stok_df = st.session_state.stok_data
    eslesme_matrix = st.session_state.eslesme_df

    # 🔥 KOLONLARI NET BAĞLA
    tanim_col = "Plaka Adı"
    miktar_col = "Adet"
    kod_col = "Plaka Kodu"

    # 🔥 KONTROLLER
    if tanim_col not in df.columns:
        st.error(f"{tanim_col} kolonu bulunamadı")
        st.write(df.columns)
        return

    if stok_df is None or stok_df.empty:
        st.error("Stok verisi boş")
        return

    vis_rows = []
    pivot_data = []

    for idx, row in df.iterrows():

        plaka_adi = str(row.get(tanim_col, '')).strip()
        plaka_kodu = str(row.get(kod_col, '')).strip()
        plaka_adet = safe_float(row.get(miktar_col, 0))

        bagli_blok_kod = ""
        bagli_blok_adi = ""
        is_matched_via_matrix = False

        # --- MATRIS ---
        if plaka_kodu and eslesme_matrix is not None and not eslesme_matrix.empty:

            m_match = eslesme_matrix[
                eslesme_matrix.iloc[:,0].astype(str).str.strip() == plaka_kodu
            ]

            if not m_match.empty:
                bagli_blok_kod = str(m_match.iloc[0,2]).strip()
                bagli_blok_adi = str(m_match.iloc[0,3]).strip()

                is_matched_via_matrix = True

                pivot_data.append({
                    "BAĞLI BLOK KODU": bagli_blok_kod,
                    "BAĞLI BLOK ADI": bagli_blok_adi,
                    "PLAKA ADET": plaka_adet
                })

        # --- FALLBACK ---
        if not is_matched_via_matrix:

            p_info = ayikla_karakter_ve_olcu(plaka_adi)

            for _, s_row in stok_df.iterrows():

                b_info = ayikla_karakter_ve_olcu(s_row.get('İsim', ''))

                if plaka_sayisi_hesapla(p_info, b_info) > 0:
                    bagli_blok_kod = str(s_row.get('Kod', '')).strip()
                    bagli_blok_adi = str(s_row.get('İsim', '')).strip()
                    break

            if not bagli_blok_kod:
                bagli_blok_kod = "UYGUN BLOK YOK"
                bagli_blok_adi = "Uygun ölçü bulunamadı"

        df.at[idx, 'Gerekli Blok Kodu'] = bagli_blok_kod
        df.at[idx, 'Gerekli Blok Adı'] = bagli_blok_adi

        vis_rows.append({
            "Plaka Kodu": plaka_kodu,
            "Plaka": plaka_adi,
            "Adet": plaka_adet,
            "Blok": bagli_blok_adi
        })

    st.dataframe(pd.DataFrame(vis_rows), use_container_width=True)

    if pivot_data:
        pdf = pd.DataFrame(pivot_data)
        pivot_df = pdf.groupby(["BAĞLI BLOK KODU","BAĞLI BLOK ADI"])["PLAKA ADET"].sum().reset_index()
        st.dataframe(pivot_df, use_container_width=True)
