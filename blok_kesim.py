import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def run_blok_kesim(conn):

    # --- 1. GELİŞMİŞ AYIKLAMA VE EŞLEŞTİRME MOTORU ---
    def ayikla_karakter_ve_olcu(text):
        if pd.isna(text) or str(text).strip() == "":
            return None

        t = str(text).upper().strip()

        # Ölçü tespiti (Boy X En)
        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)', t)
        boy = float(olcu.group(1)) if olcu else 0
        en = float(olcu.group(2)) if olcu else 0

        karakter = t
        if olcu:
            karakter = t[:olcu.start()].strip()

        return {"boy": boy, "en": en, "karakter": karakter}


    # --- YENİ: AKILLI KARAKTER EŞLEŞTİRME ---
    def karakter_match(plaka, blok):
        if not plaka or not blok:
            return False

        kritik_kelimeler = [
            "DNS", "NEWTON",
            "MAVI", "GRI", "BEYAZ",
            "SOFT", "FLEXI", "FR",
            "SERT", "YUMUSAK"
        ]

        skor = 0
        for kelime in kritik_kelimeler:
            if kelime in plaka and kelime in blok:
                skor += 1

        return skor >= 2  # minimum eşleşme


    # --- NAVİGASYON ---
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 4])

    with c_back1:
        if st.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()

    with c_back2:
        if st.button("⬅️ TEMİZLE", use_container_width=True):
            for k in ['main_data', 'stok_data', 'har_data', 'eslesme_tablosu']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    st.title("✂️ Blok & Rulo Kesim")

    # --- 2. VERİ YÜKLEME ---
    with st.container(border=True):
        uploaded_file = st.file_uploader("Kesim Listesi Yükle (Excel)", type=['xlsx'], key="bk_uploader")

        if uploaded_file and 'main_data' not in st.session_state:
            try:
                df_raw = pd.read_excel(uploaded_file, header=None)

                baslik_satiri = 0
                for i in range(min(15, len(df_raw))):
                    vals = [str(v).upper().strip() for v in df_raw.iloc[i].fillna("").values]
                    if "STOK ADI" in vals or "BLOKCM" in vals:
                        baslik_satiri = i
                        break

                df_load = pd.read_excel(uploaded_file, header=baslik_satiri)
                df_load.columns = [str(c).strip() for c in df_load.columns]

                st.session_state['main_data'] = df_load
                st.session_state['stok_data'] = veritabani.get_internal_data("Stok")
                st.session_state['har_data'] = veritabani.get_internal_data("Hareketler")
                st.session_state['eslesme_tablosu'] = veritabani.get_internal_data("Eşleşmeler")

                st.success("✅ Veri yüklendi")

            except Exception as e:
                st.error(f"Hata: {e}")

    # --- 3. OPERASYON ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']

        tanim_col = next((c for c in df.columns if "STOK ADI" in c.upper()), None)
        blok_olcu_col = next((c for c in df.columns if "BLOKCM" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MIKTAR" in c.upper()), None)

        if not tanim_col or not blok_olcu_col:
            st.error("Sütun bulunamadı")
            st.stop()

        st.divider()
        parti_barkod = st.text_input("🔍 Blok Barkod").strip()

        if parti_barkod:
            stok_df = st.session_state['stok_data']
            blok_match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == parti_barkod]

            if not blok_match.empty:
                secilen_blok = blok_match.iloc[0]
                blok_karakteristik = ayikla_karakter_ve_olcu(secilen_blok['İsim'])

                def satir_uygun_mu(row):
                    try:
                        if pd.isna(row[tanim_col]) or pd.isna(row[blok_olcu_col]):
                            return False

                        plaka_info = ayikla_karakter_ve_olcu(row[tanim_col])
                        hedef_blok = ayikla_karakter_ve_olcu(row[blok_olcu_col])

                        if not plaka_info or not hedef_blok or not blok_karakteristik:
                            return False

                        # KARAKTER MATCH (YENİ)
                        karakter_tamam = karakter_match(
                            plaka_info['karakter'],
                            blok_karakteristik['karakter']
                        )

                        # SADECE BOY KONTROL
                        olcu_tamam = abs(
                            hedef_blok['boy'] - blok_karakteristik['boy']
                        ) < 2

                        return karakter_tamam and olcu_tamam

                    except Exception as e:
                        return False

                uygun_satirlar = df[df.apply(satir_uygun_mu, axis=1)]

                if not uygun_satirlar.empty:
                    emir = uygun_satirlar.iloc[0]

                    plaka_match = re.search(r'X(\d+)$', str(emir[tanim_col]).upper())
                    kalinlik = float(plaka_match.group(1)) if plaka_match else 0

                    adet = float(emir[miktar_col]) if miktar_col else 0
                    net = adet * kalinlik

                    df_har = st.session_state['har_data']
                    daha_once = ((df_har['Kod'] == secilen_blok['Kod']) & (df_har['İşlem'] == "KESİM/SARF")).any()

                    fire = 0 if daha_once else 2
                    toplam = net + fire

                    st.success("✅ EŞLEŞME VAR")
                    st.write(emir[tanim_col])
                    st.metric("Düşülecek", toplam)

                    if st.button("KES"):
                        if secilen_blok['Miktar'] < toplam:
                            st.error("Yetersiz blok")
                            st.stop()

                        stok_df.loc[stok_df['Kod'] == secilen_blok['Kod'], 'Miktar'] -= toplam

                        yeni = pd.DataFrame([{
                            "Tarih": datetime.now(),
                            "İşlem": "KESİM/SARF",
                            "Kod": secilen_blok['Kod'],
                            "Miktar": toplam
                        }])

                        veritabani.update_data("Stok", stok_df)
                        veritabani.update_data("Hareketler", pd.concat([df_har, yeni]))

                        st.success("Kesildi")

                else:
                    st.error("❌ UYGUN EMİR YOK")

            else:
                st.error("❌ Barkod yok")

    st.markdown("---")
    st.markdown("BRN 2026")
