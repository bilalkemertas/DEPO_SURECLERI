import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime

def run_blok_kesim(conn):
    st.title("🧱 Blok ve Rulo Sünger Kesim Otomasyonu")
    st.write("Kesim planı yükleyerek ve hammadde barkodu okutarak akıllı kesim ve stok düşüm işlemlerini yönetin.")

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
        # 3'lü kombinasyon araması (Örn: 188x88x18.5)
        olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
        if olcu_uzun:
            try:
                boy = float(olcu_uzun.group(1))
                en = float(olcu_uzun.group(2))
                kalinlik = float(olcu_uzun.group(3))
                start_idx = olcu_uzun.start()
                karakter = t[:start_idx].strip()
                # Karakter sonundaki özel işaretleri temizle
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
        # Eğer kurumsal bağlantı tipi farklıysa güvenli fallback
        stok_df = veritabani.get_data("Stok", conn)
        har_df = veritabani.get_data("Hareketler", conn)

    if stok_df is None or stok_df.empty:
        st.warning("⚠️ Stok veritabanı boş veya yüklenemedi!")
        stok_df = pd.DataFrame()

    if har_df is None:
        har_df = pd.DataFrame()

    # --- ADIM 1: İŞ EMRİ LİSTESİ YÜKLEME ---
    st.subheader("📋 1. İş Emri Listesi Yükle")
    is_emri_file = st.file_uploader("Kesim Planı Excel Dosyasını Yükleyin", type=['xlsx', 'xls'])

    if is_emri_file is not None:
        try:
            excel_sheets = pd.ExcelFile(is_emri_file)
            sheet_name = None
            for s in excel_sheets.sheet_names:
                if any(x in s.upper() for x in ["HAZIRLIK", "SHEET4", "PLAN", "KESIM", "KESİM"]):
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

    # --- ADIM 2: BARKOD OKUTMA VE SORGULAMA ---
    st.subheader("🔍 2. Hammadde Barkodu Okut")
    barkod_giris = st.text_input("Blok veya Rulo Barkodunu Okutun / Girin:", key="kesim_barkod_input")

    if barkod_giris:
        barkod = str(barkod_giris).strip()
        
        # --- 1. ADIM: STOK VERİTABANINDAKİ BARKOD SÜTUNUNU DİNAMİK OLARAK BULALIM ---
        stok_barkod_col = None
        olasi_barkod_sutunlari = ['Barkod', 'BARKOD', 'Barkod No', 'Stok Barkodu', 'Tedarikçi Barkodu', 'Tedarikçi_Barkodu']
        
        # 1. Aşama: Tam eşleşen sütun var mı kontrol edelim
        for c in olasi_barkod_sutunlari:
            if c in stok_df.columns:
                stok_barkod_col = c
                break

        # 2. Aşama: Eğer tam eşleşme yoksa, içinde "barkod" veya "barcode" geçen ilk sütunu bulalım
        if stok_barkod_col is None:
            for c in stok_df.columns:
                if 'barkod' in str(c).lower() or 'barcode' in str(c).lower():
                    stok_barkod_col = c
                    break

        # 3. Aşama: Hala bulunamadıysa, kullanıcıya çöktürmeden temiz bir Streamlit uyarısı gösterelim
        if stok_barkod_col is None:
            st.error(f"⚠️ Depo Stok tablosunda barkod sütunu tespit edilemedi! Mevcut sütunlar: {list(stok_df.columns)}")
            stok_barkod_col = stok_df.columns[0] if not stok_df.empty else None

        # --- DİNAMİK BARKOD SÜTUNU ÜZERİNDEN GÜVENLİ SORGULAMA ---
        if stok_barkod_col is not None and not stok_df.empty:
            match_stok = stok_df[stok_df[stok_barkod_col].astype(str).str.strip() == barkod]
        else:
            match_stok = pd.DataFrame()

        if not match_stok.empty:
            stok_satir = match_stok.iloc[0]
            blok_kod = str(stok_satir.get('Kod', '')).strip()
            blok_adi = str(stok_satir.get('Malzeme_Adi', stok_satir.get('Malzeme Adı', stok_satir.get('Ad', '')))).strip()
            blok_miktar = float(stok_satir.get('Miktar', 0.0))
            blok_adres = str(stok_satir.get('Adres', 'Bilinmeyen Adres')).strip()

            st.info(f"📍 **Hammadde Bulundu:** {blok_adi} ({blok_kod}) | **Miktar:** {blok_miktar} Adet | **Adres:** {blok_adres}")

            # Hammaddenin ölçü ve karakter çözümlemesini yapalım
            ham_olcu = ayikla_karakter_ve_olcu(blok_adi)
            
            # --- EŞLEŞEN PLAKALARI BULMA VE KESİM HESAPLAMA ---
            if 'df_is_emri' in st.session_state and not st.session_state.df_is_emri.empty:
                is_emri = st.session_state.df_is_emri
                eslesme = st.session_state.eslesme_df
                
                # Matrise göre eşleşen yarı mamulleri tespit etme
                uygun_plakalar = []
                if not eslesme.empty:
                    # 'BAĞLI BLOK STOK KODU' sütun ismini esnek bulalım
                    bagli_col = next((c for c in eslesme.columns if 'BAĞLI' in c or 'BLOK' in c), eslesme.columns[2])
                    ham_col = next((c for c in eslesme.columns if 'HAM' in c or 'KODU' in c or 'Sipariş' in c), eslesme.columns[0])
                    
                    # Blok koduna bağlı plaka kodlarını matristen filtrele
                    matris_match = eslesme[eslesme[bagli_col].astype(str).str.strip() == blok_kod]
                    if not matris_match.empty:
                        uygun_kodlar = matris_match[ham_col].astype(str).str.strip().tolist()
                        
                        # İş emrindeki sipariş kalemlerinden bu plaka kodlarına uyanları çek
                        is_emri_stok_col = next((c for c in is_emri.columns if 'Stok' in c or 'Kod' in c), is_emri.columns[0])
                        uygun_plakalar = is_emri[is_emri[is_emri_stok_col].astype(str).str.strip().isin(uygun_kodlar)].copy()

                if len(uygun_plakalar) > 0:
                    st.success(f"🎯 Bu bloktan kesilebilecek {len(uygun_plakalar)} adet açık sipariş kalemi eşleşti!")
                    
                    # Seçim tablosu oluşturalım
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
                    st.dataframe(df_secim)

                    # Kullanıcıya kesmek istediği plakayı seçtirelim
                    secilen_plaka_idx = st.selectbox(
                        "Kesim Yapılacak Sipariş Satırını Seçin:", 
                        options=range(len(df_secim)),
                        format_func=lambda i: f"Sip:{df_secim.iloc[i]['Sipariş No']} - {df_secim.iloc[i]['Yarı Mamul Adı']}"
                    )
                    
                    secilen_plaka = df_secim.iloc[secilen_plaka_idx]
                    plaka_adi = secilen_plaka["Yarı Mamul Adı"]
                    plaka_kodu = secilen_plaka["Yarı Mamul Kodu"]
                    
                    plaka_olcu = ayikla_karakter_ve_olcu(plaka_adi)
                    
                    # Ölçüsel Matematik ve Verimlilik Analizi
                    st.write("---")
                    st.subheader("📐 Ölçü ve Fire Hesaplama")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Hammadde Ölçüsü:** {ham_olcu['boy']}x{ham_olcu['en']}x{ham_olcu['kalinlik']} cm ({ham_olcu['karakter']})")
                    with col2:
                        st.markdown(f"**Mamul Ölçüsü:** {plaka_olcu['boy']}x{plaka_olcu['en']}x{plaka_olcu['kalinlik']} cm ({plaka_olcu['karakter']})")

                    # Matematiksel maksimum kesim hesabı (Boy ve En bazında kaç adet çıkar?)
                    if plaka_olcu['boy'] > 0 and plaka_olcu['en'] > 0 and plaka_olcu['kalinlik'] > 0:
                        en_kat = math.floor(ham_olcu['en'] / plaka_olcu['en'])
                        boy_kat = math.floor(ham_olcu['boy'] / plaka_olcu['boy'])
                        kat_basina_plaka = en_kat * boy_kat if (en_kat > 0 and boy_kat > 0) else 1
                        
                        # 1 Bloktan çıkabilecek teorik plaka miktarı
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
                            max_value=float(blok_miktar),
                            value=1.0,
                            step=1.0
                        )

                        if st.button("🔥 KESİMİ GERÇEKLEŞTİR VE STOKLARI GÜNCELLE"):
                            try:
                                # 1. Adım: Hammaddeyi Stoktan Düş veya Güncelle
                                stok_index = match_stok.index[0]
                                kalan_hammadde_miktari = blok_miktar - blok_sarf_adedi
                                
                                if kalan_hammadde_miktari <= 0:
                                    stok_df = stok_df.drop(stok_index)
                                else:
                                    stok_df.at[stok_index, 'Miktar'] = kalan_hammadde_miktari

                                # 2. Adım: Yeni Plakayı Stoklara Ekle / Güncelle
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
                                    # Eksik sütunları da tanımlayalım
                                    for col in stok_df.columns:
                                        if col not in yeni_plaka_satir:
                                            yeni_plaka_satir[col] = ""
                                    stok_df = pd.concat([stok_df, pd.DataFrame([yeni_plaka_satir])], ignore_index=True)

                                # 3. Adım: Hareket Log Kayıtlarını Hazırla
                                t_tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Sarf Kaydı
                                har_sarf = {
                                    "Tarih": t_tarih,
                                    "İşlem": "KESİM/SARF",
                                    "Adres": blok_adres,
                                    "Kod": blok_kod,
                                    "Malzeme_Adi": blok_adi,
                                    "Miktar": -blok_sarf_adedi,
                                    "Birim": "AD"
                                }
                                # Üretim Giriş Kaydı
                                har_uret = {
                                    "Tarih": t_tarih,
                                    "İşlem": "ÜRETİM/GİRİŞ",
                                    "Adres": blok_adres,
                                    "Kod": plaka_kodu,
                                    "Malzeme_Adi": plaka_adi,
                                    "Miktar": kesim_adedi,
                                    "Birim": "AD"
                                }

                                # Log sütunlarını eşle
                                for col in har_df.columns:
                                    if col not in har_sarf: har_sarf[col] = ""
                                    if col not in har_uret: har_uret[col] = ""

                                har_df = pd.concat([har_df, pd.DataFrame([har_sarf, har_uret])], ignore_index=True)

                                # 4. Adım: Veritabanına Yazma
                                try:
                                    veritabani.update_data("Stok", stok_df)
                                    veritabani.update_data("Hareketler", har_df)
                                    st.balloons()
                                    st.success(f"🎉 Kesim işlemi başarıyla tamamlandı! Stoktan {blok_sarf_adedi} adet blok düşüldü, hanenize {kesim_adedi} adet plaka eklendi!")
                                    st.rerun()
                                except Exception as db_err:
                                    st.error(f"❌ Veritabanı güncelleme hatası: {db_err}")
                            except Exception as ex:
                                st.error(f"❌ Kesim işlemi uygulanırken hata oluştu: {ex}")
                    else:
                        st.warning("⚠️ Mamul ölçü bilgisi tespit edilemediğinden otomatik fire hesabı yapılamıyor.")
                else:
                    st.error("❌ Okuttuğunuz blok kod/kalitesi, yüklenen iş emrindeki açık plakaların hiçbirinin hammadde gereksinimiyle (Matris bazında) eşleşmiyor!")
            else:
                st.warning("⚠️ Lütfen kesim işlemlerine başlamadan önce Adım 1'den güncel bir iş emri planı yükleyin.")
        else:
            st.error(f"❌ '{barkod}' barkodlu hammadde stokta bulunamadı! Lütfen barkodu kontrol edin.")

# Bu dosya bağımsız çalıştırıldığında test edilmesini sağlar
if __name__ == "__main__":
    st.warning("Bu modül doğrudan çalıştırılamaz. Lütfen app.py üzerinden erişin.")
