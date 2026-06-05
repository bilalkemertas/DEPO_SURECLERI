import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime

def run_blok_kesim(conn):
    # --- MASTER DATA YÜKLEME (TÜRKÇE KARAKTER ZIRHLI & CACHED) ---
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
                except:
                    continue
            if not success:
                st.session_state.eslesme_df = pd.DataFrame()
        else:
            st.warning("⚠️ 'eslesme_matrisi.csv' dosyası kök dizinde bulunamadı! Eşleştirme matrisi devre dışı.")
            st.session_state.eslesme_df = pd.DataFrame()

    # --- ZIRHLI AYIKLAMA MOTORU (ASLA NONE DÖNMEZ) ---
    def ayikla_karakter_ve_olcu(text):
        default_return = {"boy": 0.0, "en": 0.0, "kalinlik": 0.0, "karakter": str(text) if text else ""}
        if pd.isna(text) or str(text).strip() == "":
            return default_return
        
        t = str(text).upper().replace(",", ".").strip()
        olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
        if olcu_uzun:
            try:
                boy = float(olcu_uzun.group(1))
                en = float(olcu_uzun.group(2))
                kalinlik = float(olcu_uzun.group(3))
                start_idx = olcu_uzun.start()
                karakter = t[:start_idx].strip()
                karakter = re.sub(r'[^A-Z0-9\sĞÜŞİÖÇ]+$', '', karakter).strip()
                return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}
            except:
                pass
        return default_return

    # --- VERİTABANINDAN CANLI VERİLERİ ALALIM ---
    try:
        stok_df = veritabani.get_internal_data("Stok")
        har_df = veritabani.get_internal_data("Hareketler")
    except AttributeError:
        stok_df = veritabani.get_data("Stok", conn)
        har_df = veritabani.get_data("Hareketler", conn)

    if stok_df is None or stok_df.empty:
        stok_df = pd.DataFrame()

    if har_df is None:
        har_df = pd.DataFrame()

    # --- SÜTUN STANDARDİZASYONU (KEYERROR ÖNLEME KALKANI) ---
    if not stok_df.empty:
        stok_df.columns = [str(c).strip() for c in stok_df.columns]
        renames = {}
        for col in stok_df.columns:
            col_upper = col.upper()
            if col_upper in ['KOD', 'STOK KODU', 'STOK_KODU', 'MALZEME KODU', 'URUN KODU', 'ÜRÜN KODU']:
                renames[col] = 'Kod'
            elif col_upper in ['MİKTAR', 'MIKTAR', 'ADET', 'STOK ADET', 'STOK_MİKTARI']:
                renames[col] = 'Miktar'
            elif col_upper in ['ADRES', 'STOK ADRES', 'YER', 'DEPO_ADRES']:
                renames[col] = 'Adres'
            elif col_upper in ['MALZEME ADI', 'MALZEME_ADI', 'STOK ADI', 'STOK_ADI', 'İSİM', 'ISIM', 'ÜRÜN ADI', 'URUN_ADI']:
                renames[col] = 'Malzeme_Adi'
        if renames:
            stok_df = stok_df.rename(columns=renames)

    # --- DİNAMİK BARKOD SÜTUNU TESPİTİ ---
    stok_barkod_col = None
    olasi_barkod_sutunlari = ['Barkod', 'BARKOD', 'Barkod No', 'Stok Barkodu', 'Tedarikçi Barkodu', 'Tedarikçi_Barkodu']
    for c in olasi_barkod_sutunlari:
        if c in stok_df.columns:
            stok_barkod_col = c
            break
    if stok_barkod_col is None:
        for c in stok_df.columns:
            if 'barkod' in str(c).lower() or 'barcode' in str(c).lower():
                stok_barkod_col = c
                break
    if stok_barkod_col is None and not stok_df.empty:
        stok_barkod_col = stok_df.columns[0]

    # --- DİNAMİK ESLESME MATRİSİ SÜTUN TESPİTİ ---
    eslesme = st.session_state.eslesme_df
    plaka_kod_col = None
    bagli_blok_kod_col = None
    bagli_blok_adi_col = None

    if not eslesme.empty:
        for c in eslesme.columns:
            c_upper = c.upper()
            if 'BAĞLI' in c_upper and ('KOD' in c_upper or 'CODE' in c_upper):
                bagli_blok_kod_col = c
            elif 'BAĞLI' in c_upper and ('ADI' in c_upper or 'NAME' in c_upper):
                bagli_blok_adi_col = c
            elif ('HAM' in c_upper or 'YARI' in c_upper or 'PLAKA' in c_upper) and ('KOD' in c_upper or 'CODE' in c_upper):
                plaka_kod_col = c
        
        if not plaka_kod_col:
            plaka_kod_col = eslesme.columns[0]
        if not bagli_blok_kod_col and len(eslesme.columns) > 2:
            bagli_blok_kod_col = eslesme.columns[2]
        if not bagli_blok_adi_col and len(eslesme.columns) > 3:
            bagli_blok_adi_col = eslesme.columns[3]

    # --- BAĞIMSIZ PENCERE YÖNETİM SİSTEMİ (STATE TABANLI) ---
    if 'blok_kesim_page' not in st.session_state:
        st.session_state.blok_kesim_page = 'menu'  # İlk giriş ana menü/dashboard

    # =========================================================================
    # 0. BAĞIMSIZ ALT MENÜ / DASHBOARD EKRANI
    # =========================================================================
    if st.session_state.blok_kesim_page == 'menu':
        st.title("🧱 Blok ve Rulo Sünger Kesim Otomasyonu")
        st.write("Yönetmek istediğiniz bağımsız kesim ekranını seçiniz:")
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("📋 **Planlama Penceresi**")
            st.write("Kesim planı yükle, sipariş plaka listesini ve gerekli toplam hammadde ihtiyaç raporunu gör.")
            if st.button("📋 PLAN & İŞ EMRİ YÜKLE", use_container_width=True):
                st.session_state.blok_kesim_page = 'plan'
                st.rerun()

        with col2:
            st.success("🧱 **Operatör Kesim Terminali**")
            st.write("Okutulan hammadde barkoduyla açık siparişleri eşle, kesim yap ve stoktan otomatik düş.")
            if st.button("🧱 KESİM OPERASYONU", use_container_width=True, type="primary"):
                st.session_state.blok_kesim_page = 'kesim'
                st.rerun()

        with col3:
            st.warning("📊 **Kesim Analiz Raporu**")
            st.write("Süreç boyunca yapılan tüm kesim, sarfiyat ve üretim giriş hareketlerini detaylıca izle.")
            if st.button("📊 KESİM RAPORLARI", use_container_width=True):
                st.session_state.blok_kesim_page = 'rapor'
                st.rerun()

    # =========================================================================
    # EKRAN 1: PLAN & İŞ EMRİ YÜKLEME (BAĞIMSIZ PENCERE)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'plan':
        # Geri Dönüş Başlığı
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_plan"):
                st.session_state.blok_kesim_page = 'menu'
                st.rerun()
        with c_nav2:
            st.subheader("📋 Kesim Planı ve İş Emri Yükleme")
        
        st.markdown("---")
        is_emri_file = st.file_uploader("Sipariş/Kesim Planı Excel Dosyasını Sürükleyin ve Bırakın", type=['xlsx', 'xls'])

        if is_emri_file is not None:
            try:
                excel_sheets = pd.ExcelFile(is_emri_file)
                sheet_name = None
                for s in excel_sheets.sheet_names:
                    if any(x in s.upper() for x in ["HAZIRLIK", "SHEET4", "PLAN", "KESIM", "KESİM", "Sayfa1"]):
                        sheet_name = s
                        break
                if sheet_name is None:
                    sheet_name = excel_sheets.sheet_names[0]
                
                df_is_emri = pd.read_excel(is_emri_file, sheet_name=sheet_name)
                df_is_emri.columns = [str(c).strip() for c in df_is_emri.columns]
                st.session_state.df_is_emri = df_is_emri
                st.success(f"✅ '{sheet_name}' sekmesi başarıyla yüklendi! ({len(df_is_emri)} satır bulundu)")
            except Exception as e:
                st.error(f"❌ Excel dosyası okunurken hata oluştu: {e}")

        # Yüklü Plan Varsa Pivot İhtiyaç Özeti ve Detayları Gösterelim
        if 'df_is_emri' in st.session_state and not st.session_state.df_is_emri.empty:
            is_emri = st.session_state.df_is_emri
            
            # Dinamik Excel Sütun Analizi
            is_emri_stok_col = None
            is_emri_stok_adi_col = None
            is_emri_miktar_col = None
            is_emri_sip_no_col = None

            for c in is_emri.columns:
                c_upper = c.upper()
                if any(x in c_upper for x in ['STOK KOD', 'ÜRÜN KOD', 'URUN KOD', 'MALZEME KOD', 'KOD']):
                    is_emri_stok_col = c
                elif any(x in c_upper for x in ['STOK AD', 'MALZEME AD', 'ÜRÜN AD', 'URUN AD', 'ADI']):
                    is_emri_stok_adi_col = c
                elif any(x in c_upper for x in ['MİKTAR', 'MIKTAR', 'ADET', 'SİPARİŞ MİKTARI', 'SIPARIS MIKTARI']):
                    is_emri_miktar_col = c
                elif any(x in c_upper for x in ['SİPARİŞ NO', 'SIPARIS NO', 'SİPARİŞ_NO', 'SIPARIS_NO']):
                    is_emri_sip_no_col = c

            if not is_emri_stok_col: is_emri_stok_col = is_emri.columns[0]
            if not is_emri_stok_adi_col and len(is_emri.columns) > 1: is_emri_stok_adi_col = is_emri.columns[1]
            if not is_emri_miktar_col:
                for c in is_emri.columns:
                    if 'MİK' in c.upper() or 'MIK' in c.upper() or 'ADET' in c.upper() or 'QTY' in c.upper():
                        is_emri_miktar_col = c
                        break
                if not is_emri_miktar_col and len(is_emri.columns) > 2:
                    is_emri_miktar_col = is_emri.columns[2]

            vis_rows = []
            pivot_data = []

            eslesme_dict = {}
            if not eslesme.empty and plaka_kod_col and bagli_blok_kod_col:
                for _, r in eslesme.iterrows():
                    p_kod = str(r.get(plaka_kod_col, '')).strip()
                    b_kod = str(r.get(bagli_blok_kod_col, '')).strip()
                    b_adi = str(r.get(bagli_blok_adi_col, '')) if bagli_blok_adi_col else ""
                    eslesme_dict[p_kod] = {"blok_kod": b_kod, "blok_adi": b_adi}

            for _, row in is_emri.iterrows():
                plaka_kodu = str(row.get(is_emri_stok_col, '')).strip()
                plaka_adi = str(row.get(is_emri_stok_adi_col, '')) if is_emri_stok_adi_col else ""
                
                try:
                    plaka_adet = float(row.get(is_emri_miktar_col, 0.0))
                except:
                    plaka_adet = 0.0
                    
                sip_no = str(row.get(is_emri_sip_no_col, 'Belirtilmemiş')).strip() if is_emri_sip_no_col else 'Belirtilmemiş'
                
                match_info = eslesme_dict.get(plaka_kodu)
                if match_info:
                    bagli_blok_kod = match_info["blok_kod"]
                    bagli_blok_adi = match_info["blok_adi"]
                    pivot_data.append({
                        "BAĞLI BLOK KODU": bagli_blok_kod,
                        "BAĞLI BLOK ADI": bagli_blok_adi,
                        "PLAKA ADET": plaka_adet
                    })
                else:
                    bagli_blok_kod = "UYGUN BLOK YOK"
                    bagli_blok_adi = "Matris Dışı / Uygun Ölçüde Stok Bulunamadı"

                vis_rows.append({
                    "Sipariş No": sip_no,
                    "Plaka Kodu": plaka_kodu,
                    "Plaka Adı/Tanımı": plaka_adi,
                    "Talep Adet": plaka_adet,
                    "Gerekli Blok Kodu": bagli_blok_kod,
                    "Gerekli Blok Adı": bagli_blok_adi
                })

            vis_df = pd.DataFrame(vis_rows)

            # --- TOPLAM GEREKLİ BLOK İHTİYAÇ ÖZETİ ---
            st.markdown("---")
            st.subheader("📊 İş Emri Toplam Gerekli Blok/Rulo Stok İhtiyacı (Özet)")
            if pivot_data:
                pdf = pd.DataFrame(pivot_data)
                pivot_df = pdf.groupby(["BAĞLI BLOK KODU", "BAĞLI BLOK ADI"])["PLAKA ADET"].sum().reset_index()
                pivot_df.rename(columns={"PLAKA ADET": "Toplam Üretilecek Plaka (Adet)"}, inplace=True)
                pivot_df = pivot_df.sort_values(by="Toplam Üretilecek Plaka (Adet)", ascending=False)
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ İş emri plakalarına ait gerekli blok stok özeti çıkarılamadı.")

            # --- İŞ EMRİ DETAY TABLOSU ---
            st.markdown("---")
            st.subheader("📋 İş Emri Üretim Planı Kalem Detayları")
            st.dataframe(vis_df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Henüz bir kesim planı yüklenmedi. Lütfen yukarıdan bir Excel dosyası sürükleyip bırakın.")

    # =========================================================================
    # EKRAN 2: OPERATÖR KESİM TERMİNALİ (BAĞIMSIZ PENCERE)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'kesim':
        # Geri Dönüş Başlığı
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_kesim"):
                st.session_state.blok_kesim_page = 'menu'
                st.rerun()
        with c_nav2:
            st.subheader("🧱 Operatör Kesim ve Hammadde Eşleme")

        st.markdown("---")

        # İş Emri Kontrolü
        if 'df_is_emri' not in st.session_state or st.session_state.df_is_emri.empty:
            st.warning("⚠️ Kesim yapabilmek için lütfen önce 'PLAN & İŞ EMRİ YÜKLE' ekranından kesim planınızı yükleyin.")
        else:
            barkod_giris = st.text_input("🔍 KESİLECEK BLOK VEYA RULO BARKODUNU OKUTUNUZ / GİRİNİZ:", key="kesim_barkod_input")

            if barkod_giris:
                barkod = str(barkod_giris).strip()

                if stok_barkod_col is not None and not stok_df.empty:
                    match_stok = stok_df[stok_df[stok_barkod_col].astype(str).str.strip() == barkod]
                else:
                    match_stok = pd.DataFrame()

                if not match_stok.empty:
                    stok_satir = match_stok.iloc[0]
                    blok_kod = str(stok_satir.get('Kod', '')).strip()
                    blok_adi = str(stok_satir.get('Malzeme_Adi', stok_satir.get('Malzeme Adı', stok_satir.get('Ad', '')))).strip()
                    
                    try:
                        blok_miktar = float(stok_satir.get('Miktar', 0.0))
                    except:
                        blok_miktar = 0.0
                        
                    blok_adres = str(stok_satir.get('Adres', 'Bilinmeyen Adres')).strip()

                    # Şık Hammadde kartı gösterimi
                    st.info(f"📍 **Bulunan Hammadde:** {blok_adi} ({blok_kod}) | **Mevcut Stok:** {blok_miktar} Adet | **Adres:** {blok_adres}")

                    ham_olcu = ayikla_karakter_ve_olcu(blok_adi)
                    is_emri = st.session_state.df_is_emri

                    # Sütun isimlerini esnek belirleyelim
                    is_emri_stok_col = None
                    for c in is_emri.columns:
                        if any(x in c.upper() for x in ['STOK KOD', 'ÜRÜN KOD', 'URUN KOD', 'MALZEME KOD', 'KOD']):
                            is_emri_stok_col = c
                            break
                    if not is_emri_stok_col: is_emri_stok_col = is_emri.columns[0]

                    # Matristen okutulan blok koduna uygun plaka kodlarını çekelim
                    uygun_plakalar = []
                    if not eslesme.empty:
                        bagli_col = next((c for c in eslesme.columns if 'BAĞLI' in c or 'BLOK' in c), eslesme.columns[2])
                        ham_col = next((c for c in eslesme.columns if 'HAM' in c or 'KODU' in c or 'Sipariş' in c or 'PLAKA' in c), eslesme.columns[0])

                        matris_match = eslesme[eslesme[bagli_col].astype(str).str.strip() == blok_kod]
                        if not matris_match.empty:
                            uygun_kodlar = matris_match[ham_col].astype(str).str.strip().tolist()
                            uygun_plakalar = is_emri[is_emri[is_emri_stok_col].astype(str).str.strip().isin(uygun_kodlar)].copy()

                    if len(uygun_plakalar) > 0:
                        st.success(f"🎯 Bu bloktan kesilebilecek {len(uygun_plakalar)} adet açık sipariş kalemi eşleşti!")

                        plaka_gosterim = []
                        for idx, row in uygun_plakalar.iterrows():
                            plaka_gosterim.append({
                                "Sipariş No": row.get('Sipariş No', 'Belirtilmemiş'),
                                "Yarı Mamul Kodu": row.get(is_emri_stok_col, ''),
                                "Yarı Mamul Adı": row.get('Stok Adı', row.get('Malzeme Adı', '')),
                                "Sipariş Miktarı": row.get('Sipariş Miktarı', 0),
                                "Gelen Miktar": row.get('Gelen Miktar', 0),
                                "Birim": row.get('Birim', 'AD')
                            })
                        
                        df_secim = pd.DataFrame(plaka_gosterim)
                        st.dataframe(df_secim, hide_index=True)

                        # Seçim Alanı
                        secilen_plaka_idx = st.selectbox(
                            "Kesim Yapılacak Sipariş Satırını Seçin:", 
                            options=range(len(df_secim)),
                            format_func=lambda i: f"Sip:{df_secim.iloc[i]['Sipariş No']} - {df_secim.iloc[i]['Yarı Mamul Adı']}"
                        )

                        secilen_plaka = df_secim.iloc[secilen_plaka_idx]
                        plaka_adi = secilen_plaka["Yarı Mamul Adı"]
                        plaka_kodu = secilen_plaka["Yarı Mamul Kodu"]
                        plaka_olcu = ayikla_karakter_ve_olcu(plaka_adi)

                        st.write("---")
                        st.subheader("📐 Ölçü ve Fire Hesaplama")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Hammadde Ölçüsü:** {ham_olcu['boy']}x{ham_olcu['en']}x{ham_olcu['kalinlik']} cm ({ham_olcu['karakter']})")
                        with col2:
                            st.markdown(f"**Mamul Ölçüsü:** {plaka_olcu['boy']}x{plaka_olcu['en']}x{plaka_olcu['kalinlik']} cm ({plaka_olcu['karakter']})")

                        # Matematiksel maksimum kesim hesabı
                        if plaka_olcu['boy'] > 0 and plaka_olcu['en'] > 0 and plaka_olcu['kalinlik'] > 0:
                            en_kat = math.floor(ham_olcu['en'] / plaka_olcu['en'])
                            boy_kat = math.floor(ham_olcu['boy'] / plaka_olcu['boy'])
                            kat_basina_plaka = en_kat * boy_kat if (en_kat > 0 and boy_kat > 0) else 1
                            
                            max_plaka = math.floor(ham_olcu['kalinlik'] / plaka_olcu['kalinlik']) * kat_basina_plaka
                            st.info(f"💡 **Teorik Hesaplama:** 1 adet bloktan maksimum **{max_plaka} adet** plaka üretilebilir.")

                            kesim_adedi = st.number_input(
                                "Kesilecek Plaka Miktarını Girin (Adet):", 
                                min_value=1, 
                                max_value=10000, 
                                value=int(max_plaka) if max_plaka > 0 else 1
                            )
                            
                            blok_sarf_adedi = st.number_input(
                                "Tüketilecek Blok/Hammadde Miktarı (Adet):",
                                min_value=1.0,
                                max_value=float(blok_miktar) if blok_miktar > 0 else 1.0,
                                value=1.0,
                                step=1.0
                            )

                            if st.button("🔥 KESİMİ GERÇEKLEŞTİR VE STOKLARI GÜNCELLE"):
                                try:
                                    stok_index = match_stok.index[0]
                                    kalan_hammadde_miktari = blok_miktar - blok_sarf_adedi
                                    
                                    if kalan_hammadde_miktari <= 0:
                                        stok_df = stok_df.drop(stok_index)
                                    else:
                                        stok_df.at[stok_index, 'Miktar'] = kalan_hammadde_miktari

                                    plaka_stok_match = stok_df[
                                        (stok_df['Kod'].astype(str).str.strip() == str(plaka_kodu).strip()) & 
                                        (stok_df['Adres'].astype(str).str.strip() == str(blok_adres).strip())
                                    ]
                                    
                                    if not plaka_stok_match.empty:
                                        p_idx = plaka_stok_match.index[0]
                                        mevcut_p_mik = float(stok_df.at[p_idx, 'Miktar'])
                                        stok_df.at[p_idx, 'Miktar'] = mevcut_p_mik + kesim_adedi
                                    else:
                                        yeni_plaka_satir = {
                                            "Adres": blok_adres,
                                            "Kod": plaka_kodu,
                                            "Malzeme_Adi": plaka_adi,
                                            "Miktar": kesim_adedi,
                                            "Birim": "AD"
                                        }
                                        for col in stok_df.columns:
                                            if col not in yeni_plaka_satir:
                                                yeni_plaka_satir[col] = ""
                                        stok_df = pd.concat([stok_df, pd.DataFrame([yeni_plaka_satir])], ignore_index=True)

                                    # Hareket Günlüğü Kayıtları
                                    t_tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    har_sarf = {
                                        "Tarih": t_tarih,
                                        "İşlem": "KESİM/SARF",
                                        "Adres": blok_adres,
                                        "Kod": blok_kod,
                                        "Malzeme_Adi": blok_adi,
                                        "Miktar": -blok_sarf_adedi,
                                        "Birim": "AD"
                                    }
                                    har_uret = {
                                        "Tarih": t_tarih,
                                        "İşlem": "ÜRETİM/GİRİŞ",
                                        "Adres": blok_adres,
                                        "Kod": plaka_kodu,
                                        "Malzeme_Adi": plaka_adi,
                                        "Miktar": kesim_adedi,
                                        "Birim": "AD"
                                    }

                                    for col in har_df.columns:
                                        if col not in har_sarf: har_sarf[col] = ""
                                        if col not in har_uret: har_uret[col] = ""

                                    har_df = pd.concat([har_df, pd.DataFrame([har_sarf, har_uret])], ignore_index=True)

                                    try:
                                        veritabani.update_data("Stok", stok_df)
                                        veritabani.update_data("Hareketler", har_df)
                                        st.balloons()
                                        st.success(f"🎉 Kesim işlemi tamamlandı! Stoktan {blok_sarf_adedi} adet blok düşüldü, hanenize {kesim_adedi} adet plaka eklendi!")
                                        st.rerun()
                                    except Exception as db_err:
                                        st.error(f"❌ Veritabanı yazma hatası: {db_err}")
                                except Exception as ex:
                                    st.error(f"❌ Kesim sırasında hata oluştu: {ex}")
                        else:
                            st.warning("⚠️ Mamul ölçü bilgisi eksik olduğu için otomatik fire/kesim hesabı yapılamıyor.")
                    else:
                        st.error("❌ Okuttuğunuz blok kodu, yüklenen kesim planındaki hiçbir plakanın hammaddesiyle eşleşmiyor!")
                else:
                    st.error(f"❌ '{barkod}' barkodlu hammadde stokta bulunamadı! Lütfen kontrol edin.")

    # =========================================================================
    # EKRAN 3: KESİM RAPORLARI (BAĞIMSIZ PENCERE)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'rapor':
        # Geri Dönüş Başlığı
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_rapor"):
                st.session_state.blok_kesim_page = 'menu'
                st.rerun()
        with c_nav2:
            st.subheader("📊 Blok ve Rulo Kesim Raporları")

        st.markdown("---")
        
        if not har_df.empty:
            har_df.columns = [str(c).strip() for c in har_df.columns]
            
            # Sadece Kesim/Sarf ve Üretim/Giriş işlemlerini listeleyelim
            kesim_hareketleri = har_df[har_df['İşlem'].isin(['KESİM/SARF', 'ÜRETİM/GİRİŞ'])]
            
            if not kesim_hareketleri.empty:
                # Kolaylık için en son hareketi en üstte gösterelim
                kesim_hareketleri = kesim_hareketleri.iloc[::-1]
                
                # İstatistiksel Özetler
                total_sarf = abs(kesim_hareketleri[kesim_hareketleri['İşlem'] == 'KESİM/SARF']['Miktar'].astype(float).sum())
                total_giris = kesim_hareketleri[kesim_hareketleri['İşlem'] == 'ÜRETİM/GİRİŞ']['Miktar'].astype(float).sum()
                
                sum_col1, sum_col2 = st.columns(2)
                with sum_col1:
                    st.metric("🧱 Tüketilen Toplam Hammadde", f"{total_sarf:.1f} Adet")
                with sum_col2:
                    st.metric("🎯 Üretilen Toplam Plaka (Yarı Mamul)", f"{total_giris:.1f} Adet")
                
                st.markdown("---")
                st.write("📋 **Son Kesim İşlemleri Günlüğü:**")
                st.dataframe(kesim_hareketleri, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Sistemde kayıtlı herhangi bir blok kesim hareketi bulunmamaktadır.")
        else:
            st.info("ℹ️ Stok hareket geçmişi boş.")

if __name__ == "__main__":
    st.warning("Bu modül doğrudan çalıştırılamaz. Lütfen app.py üzerinden erişin.")
