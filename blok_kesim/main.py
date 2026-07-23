"""
Akıllı Blok Kesim ve Otomasyon Masası - Kalıcı Hafızalı & Gelişmiş Eşleştirmeli
"""
import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime

import tedarikci_api  # YENİ: Tedarikçi Portalı (TDP) API entegrasyonu

# --- GÜVENLİ İTHALAT (Circular Import ve Yol Hatalarını Önleme) ---
try:
    from .state import init_blok_kesim_state
    from .matching import load_local_eslesme_matrisi, karakter_match
    from .database import fetch_live_data, update_stock_and_logs
    from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float
except ImportError:
    try:
        from blok_kesim.state import init_blok_kesim_state
        from blok_kesim.matching import load_local_eslesme_matrisi, karakter_match
        from blok_kesim.database import fetch_live_data, update_stock_and_logs
        from blok_kesim.data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float
    except ImportError:
        # Streamlit test ortamı veya izole çalıştırma için yedek fonksiyon tanımları
        def init_blok_kesim_state(): pass
        def load_local_eslesme_matrisi(): return pd.DataFrame()
        def karakter_match(p, b): return True
        def fetch_live_data(conn=None): return pd.DataFrame(), pd.DataFrame()
        def update_stock_and_logs(s, h, l): return True
        def ayikla_karakter_ve_olcu(t): return {"boy": 0.0, "en": 0.0, "kalinlik": 0.0, "karakter": str(t)}
        def plaka_sayisi_hesapla(p, b): return 1
        def safe_float(v, d=0.0):
            try: return float(v)
            except: return d

# --- ZIRHLI METİN TEMİZLEME VE EŞLEŞTİRME MOTORU ---
def clean_str(val):
    """
    Karakter, boşluk, Türkçe harf ve ekleri temizleyerek
    sağlıklı eşleşme stringi üretir.
    """
    if pd.isna(val) or not val:
        return ""
    s = str(val).strip().upper()
    # Türkçe Karakter Dönüşümü
    s = s.replace("İ", "I").replace("Ş", "S").replace("Ğ", "G").replace("Ü", "U").replace("Ö", "O").replace("Ç", "C")
    # İşaretlerin standardizasyonu ve boşlukları yok etme
    s = s.replace("*", "X").replace(" ", "").replace("-", "").replace(".", "")
    # Sık kullanılan ek ve tanımlayıcı kelimeleri kaldır
    s = s.replace("PLAKA", "").replace("PLAKASI", "").replace("SUNGER", "").replace("SÜNGER", "")
    return s


def find_best_match(plaka_name, matris, plaka_col, blok_kod_col, blok_adi_col):
    """
    İş emrindeki plaka adını, matris tablosundaki Yarı Mamul Adı ile 4 katmanlı akıllı eşleştirir.
    """
    if pd.isna(plaka_name) or not plaka_name or matris is None or matris.empty:
        return None

    p_clean = clean_str(plaka_name)

    # Adım 1: Tam ve temizlenmiş string eşleşmesi (Boşluksuz, Türkçe karaktersiz)
    matris_temp = matris.copy()
    matris_temp['clean_col'] = matris_temp[plaka_col].apply(clean_str)

    exact_match = matris_temp[matris_temp['clean_col'] == p_clean]
    if not exact_match.empty:
        row = exact_match.iloc[0]
        return {
            "blok_kodu": str(row[blok_kod_col]).strip(),
            "blok_adi": str(row[blok_adi_col]).strip()
        }

    # Adım 2: İçerme (Substring) Kontrolü (İç içe geçmiş isimler)
    contains_match = matris_temp[matris_temp['clean_col'].str.contains(p_clean, regex=False) | matris_temp['clean_col'].apply(lambda x: x in p_clean)]
    if not contains_match.empty:
        row = contains_match.iloc[0]
        return {
            "blok_kodu": str(row[blok_kod_col]).strip(),
            "blok_adi": str(row[blok_adi_col]).strip()
        }

    # Adım 3: Ölçü ve Kalite Eşleşmesi (Fallback)
    try:
        p_info = ayikla_karakter_ve_olcu(plaka_name)
        if p_info and p_info.get('boy', 0) > 0:
            for idx, m_row in matris.iterrows():
                m_val = str(m_row[plaka_col])
                m_info = ayikla_karakter_ve_olcu(m_val)
                if m_info and m_info.get('boy', 0) > 0:
                    # Boyutlar ±2 cm toleransla uyuyor mu ve sünger yoğunluk sınıfı eşleşiyor mu?
                    if (abs(p_info['boy'] - m_info['boy']) <= 2 and
                        abs(p_info['en'] - m_info['en']) <= 2 and
                        abs(p_info['kalinlik'] - m_info['kalinlik']) <= 1.5 and
                        karakter_match(p_info['karakter'], m_info['karakter'])):
                        return {
                            "blok_kodu": str(m_row[blok_kod_col]).strip(),
                            "blok_adi": str(m_row[blok_adi_col]).strip()
                        }
    except Exception:
        pass

    return None


# --- DOSYA VE PERSISTENCE (KALICI VERİTABANI YAZMA/OKUMA) YARDIMCILARI ---
def safe_save_is_emri(df):
    """İş Emrini hem RAM'e hem de yerel kalıcı dosyaya kaydeder"""
    st.session_state.main_data = df
    os.makedirs("data", exist_ok=True)
    try:
        df.to_csv("data/is_emri_aktif.csv", index=False)
        # Eğer varsa sisteme de kaydetmeyi dene
        import veritabani
        if hasattr(veritabani, 'update_data'):
            veritabani.update_data("Sunger_Kesim", df)
    except Exception as e:
        pass


def safe_load_is_emri():
    """Kayıtlı aktif iş emrini yerel depodan veya veritabanından yükler"""
    if 'main_data' not in st.session_state or st.session_state.main_data is None:
        # Önce yerel yedek dosyayı kontrol et
        if os.path.exists("data/is_emri_aktif.csv"):
            try:
                df = pd.read_csv("data/is_emri_aktif.csv")
                st.session_state.main_data = df
                return df
            except:
                pass
        # Veritabanı sorgula
        try:
            import veritabani
            if hasattr(veritabani, 'get_internal_data'):
                df = veritabani.get_internal_data("Sunger_Kesim")
                if df is not None and not df.empty:
                    st.session_state.main_data = df
                    return df
        except:
            pass
    return st.session_state.get('main_data')


def safe_save_operator_list(df):
    """Operatör sepetini yedekler"""
    st.session_state.operator_kesim_listesi = df
    os.makedirs("data", exist_ok=True)
    try:
        df.to_csv("data/operator_list_aktif.csv", index=False)
    except:
        pass


def safe_load_operator_list():
    """Uygulama açılışında kayıtlı sepeti yükler"""
    if 'operator_kesim_listesi' not in st.session_state or st.session_state.operator_kesim_listesi is None or st.session_state.operator_kesim_listesi.empty:
        if os.path.exists("data/operator_list_aktif.csv"):
            try:
                df = pd.read_csv("data/operator_list_aktif.csv")
                st.session_state.operator_kesim_listesi = df
                return df
            except:
                pass
        st.session_state.operator_kesim_listesi = pd.DataFrame(columns=["Plaka", "Gerekli Blok Kodu", "Gerekli Blok Adı"])
    return st.session_state.operator_kesim_listesi


# ==========================================
# ANA KONTROL MERKEZİ (RUN FUNCTION)
# ==========================================
def run_blok_kesim(conn=None):
    """Ana Blok Kesim Ekranı Kontrol Merkezi"""

    # --- 1. HAFIZA VE DURUM BAŞLATMA (STATE INIT) ---
    init_blok_kesim_state()

    # YENİ: Tedarikçi Portalı (TDP) login formu - sidebar'da, idempotent
    tedarikci_api.render_login_sidebar()

    # Kritik anahtarların sıfırlanmasını engelleyen zırhlı koruma
    if 'stok_data' not in st.session_state:
        st.session_state.stok_data = None
    if 'har_data' not in st.session_state:
        st.session_state.har_data = None
    if 'eslesme_df' not in st.session_state:
        st.session_state.eslesme_df = None
    if 'bk_page' not in st.session_state:
        st.session_state.bk_page = 'menu'
    if 'gerceklesen_kesimler' not in st.session_state:
        st.session_state.gerceklesen_kesimler = []

    # Sepet ve İş Emri verilerini diskten kalıcı olarak yükleme tetikleyicisi
    st.session_state.main_data = safe_load_is_emri()
    st.session_state.operator_kesim_listesi = safe_load_operator_list()

    # Eşleşme Matrisini Yükle
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()

    # Ortak Canlı Veri Çekimi
    def load_live_stock():
        if st.session_state.stok_data is None:
            with st.spinner("Canlı Depo Verileri Çekiliyor..."):
                try:
                    s_df, h_df = fetch_live_data()
                except TypeError:
                    s_df, h_df = fetch_live_data(conn)
                st.session_state.stok_data = s_df
                st.session_state.har_data = h_df
        return st.session_state.stok_data, st.session_state.har_data

    def go_menu():
        st.session_state.bk_page = 'menu'

    # ==========================================
    # 0. ANA MENÜ EKRANI
    # ==========================================
    if st.session_state.bk_page == 'menu':
        st.title("✂️ Akıllı Blok Kesim ve Otomasyon Merkezi")
        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("📂 1. İŞ EMRİ YÜKLE", use_container_width=True, type="primary",
                      on_click=lambda: setattr(st.session_state, 'bk_page', 'is_emri'))
            st.info("Üretimden gelen excel kesim listelerini sisteme tanıtın ve kalıcı kaydedin.")

        with c2:
            st.button("🎯 2. KESİM LİSTESİ & BARKOD", use_container_width=True, type="primary",
                      on_click=lambda: setattr(st.session_state, 'bk_page', 'kesim_ekrani'))
            st.warning("Operatörlerin listesini oluşturup barkod okutacağı kalıcı çalışma alanı.")

        with c3:
            st.button("📈 3. ÜRETİM VE STOK RAPORU", use_container_width=True, type="primary",
                      on_click=lambda: setattr(st.session_state, 'bk_page', 'rapor_ekrani'))
            st.success("Kesilen plakalar, kalanlar ve blok stok ihtiyaç analizleri.")

    # ==========================================
    # 1. EKRAN: İŞ EMRİ YÜKLEME VE KAYDETME
    # ==========================================
    elif st.session_state.bk_page == 'is_emri':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            go_menu()
            st.rerun()

        st.header("📂 Excel İş Emri / Kesim Listesi Yükleme")
        st.markdown("---")

        # Aktif iş emri bilgisi
        df_emir_aktif = st.session_state.get('main_data')
        if df_emir_aktif is not None and not df_emir_aktif.empty:
            st.success("📡 Sistemde Kayıtlı Aktif İş Emri Bulunmaktadır.")
            with st.expander("Aktif İş Emri Önizleme"):
                st.dataframe(df_emir_aktif.head(5), use_container_width=True)

        up_file = st.file_uploader("Lütfen Güncel İş Emri / Kesim Listesini Seçin (Excel):", type=['xlsx', 'xls'])

        if up_file:
            if st.session_state.get('uploaded_file_name') != up_file.name:
                try:
                    raw_df = pd.read_excel(up_file, header=None)
                    header_idx = 0
                    for i in range(min(20, len(raw_df))):
                        row_vals = [str(x).upper() for x in raw_df.iloc[i].dropna().tolist()]
                        if any("TANIM" in v or "KOD" in v or "MİKTAR" in v or "ADET" in v for v in row_vals):
                            header_idx = i
                            break

                    df = pd.read_excel(up_file, header=header_idx)
                    st.session_state.gecici_is_emri = df
                    st.session_state.uploaded_file_name = up_file.name
                    st.info("📊 Excel dosyası okundu. Aşağıdaki tablodan kontrol edip 'Veritabanına Kaydet' butonuna basınız.")
                except Exception as e:
                    st.error(f"Dosya okunurken hata oluştu: {e}")

            # Geçici yüklenen iş emrini göster ve kaydetme butonu çıkar
            df_gecici = st.session_state.get('gecici_is_emri')
            if df_gecici is not None and not df_gecici.empty:
                st.subheader("Yüklenen Dosya Önizleme")
                st.dataframe(df_gecici.head(10), use_container_width=True)

                # 🛠️ Geliştirilen Kalıcı Kaydet Butonu
                if st.button("💾 İŞ EMRİNİ VERİTABANINA VE HAFIZAYA KAYDET", type="primary", use_container_width=True):
                    safe_save_is_emri(df_gecici)
                    st.balloons()
                    st.success("🎉 İş Emri sisteme ve kalıcı veritabanına başarıyla kilitlendi! Artık Kesim Masasına geçebilirsiniz.")

    # ==========================================
    # 2. EKRAN: OPERATÖR SEÇİM VE BARKOD KESİM
    # ==========================================
    elif st.session_state.bk_page == 'kesim_ekrani':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            go_menu()
            st.rerun()

        st.header("🎯 Operatör Kesim Masası")

        # ────────────────────────────────────────────────────────────
        # YENİ: Tedarikçi Portalından (TDP API) Sevkiyat Çekme Paneli
        # ────────────────────────────────────────────────────────────
        with st.expander("🌐 Tedarikçi Portalından Sevkiyat Çek", expanded=False):
            c_g1, c_g2 = st.columns([1, 2])
            tdp_gun = c_g1.number_input("Kaç günlük sevkiyat?", min_value=1, max_value=15, value=5, key="tdp_gun_bk")
            tdp_sevk_no = c_g2.text_input("Sevkiyat Belge No:", key="tdp_sevk_no_bk")
            if st.button("🔄 ÇEK", key="tdp_cek_bk"):
                basarili, mesaj, adet = tedarikci_api.sevkiyat_verisini_cek_ve_kaydet(tdp_sevk_no, tdp_gun)
                if basarili:
                    st.success(f"✅ {mesaj}")
                else:
                    st.error(f"❌ {mesaj}")
            if st.session_state.get('api_sevk_haritasi'):
                st.caption(f"📦 Hafızada {len(st.session_state.api_sevk_haritasi)} barkod kaydı var.")

        st.markdown("---")

        df_emir = st.session_state.get('main_data')
        matris_df = st.session_state.eslesme_df
        stok_df, har_df = load_live_stock()

        if df_emir is None or df_emir.empty:
            st.error("⚠️ Henüz bir İş Emri yüklenmedi! Lütfen önce 1. Ekrandan Excel yükleyip kaydedin.")
            st.stop()

        if matris_df is None or matris_df.empty:
            st.error("⚠️ Eşleşme matrisi (eslesme_matrisi.csv) bulunamadı!")
            st.stop()

        # Sütunları dinamik ve zırhlı tespit et
        tanim_col = next((c for c in df_emir.columns if any(x in str(c).upper() for x in ["TANIM", "URUN", "ÜRÜN", "AD", "YARI MAMUL"])), None)
        m_plaka_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper()), matris_df.columns[1])
        m_blok_kod_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK KODU" in str(c).upper()), matris_df.columns[2])
        m_blok_adi_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK ADI" in str(c).upper()), matris_df.columns[3])

        s_kod_col = next((c for c in stok_df.columns if any(x in str(c).upper() for x in ["STOK KODU", "KOD", "MALZEME KOD"])), stok_df.columns[0])
        s_miktar_col = next((c for c in stok_df.columns if any(m in str(c).upper() for m in ['BAKİYE', 'MİKTAR', 'BOY', 'KALAN'])), stok_df.columns[4])
        s_barkod_col = next((c for c in stok_df.columns if any(b in str(c).upper() for b in ["BARKOD", "STOK BARKODU", "TEDARIKCI BARKODU"])), stok_df.columns[2])

        # ADIM 1: STOKLU PLAKALARI TESPİT ET (ZIRHLI MOTOR ENTEGRASYONU)
        is_emri_plakalar = df_emir[tanim_col].dropna().unique().tolist()
        stoklu_plakalar = []

        # Sadece depoda stoğu olan bloklara bağlı plakaları filtrele (Zırhlı Eşleşme Kullanılarak)
        for plaka in is_emri_plakalar:
            eslesme_res = find_best_match(plaka, matris_df, m_plaka_col, m_blok_kod_col, m_blok_adi_col)
            if eslesme_res:
                hedef_blok_kodu = eslesme_res["blok_kodu"]
                # Canlı stokta bu bloktan stok var mı?
                stok_match = stok_df[(stok_df[s_kod_col].astype(str).str.strip() == hedef_blok_kodu) & (pd.to_numeric(stok_df[s_miktar_col], errors='coerce') > 0)]
                if not stok_match.empty:
                    stoklu_plakalar.append(plaka)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1️⃣ Kesim Programınızı Oluşturun")
            secilen_plaka = st.selectbox("Stoğu Hazır Kesilebilir Plakalar:", ["Seçiniz..."] + stoklu_plakalar)

            if secilen_plaka != "Seçiniz...":
                # Zırhlı eşleşme ile bağlı bloğu tam tespit et
                eslesme_res = find_best_match(secilen_plaka, matris_df, m_plaka_col, m_blok_kod_col, m_blok_adi_col)

                if eslesme_res:
                    sec_kod = eslesme_res["blok_kodu"]
                    sec_ad = eslesme_res["blok_adi"]

                    st.success(f"🧱 Akıllı Matris Eşleşmesi Başarılı!")
                    st.info(f"Gereken Blok: **{sec_kod}** - {sec_ad}")

                    if st.button("➕ Kendi Kesim Listeme Ekle", use_container_width=True):
                        mevcut = st.session_state.operator_kesim_listesi
                        # Çift kayıt kontrolü
                        if not ((mevcut['Plaka'] == secilen_plaka) & (mevcut['Gerekli Blok Kodu'] == sec_kod)).any():
                            yeni_satir = pd.DataFrame([{"Plaka": secilen_plaka, "Gerekli Blok Kodu": sec_kod, "Gerekli Blok Adı": sec_ad}])
                            mevcut = pd.concat([mevcut, yeni_satir], ignore_index=True)
                            safe_save_operator_list(mevcut)  # Diske yedekle
                            st.toast("✅ Sepete eklendi!")
                            st.rerun()
                        else:
                            st.warning("Bu plaka zaten listenizde ekli!")
                else:
                    st.error("⚠️ Bu plaka matris tablosunda eşleşecek bir blok kodu bulamadı!")

            st.markdown("---")
            st.markdown("**Sizin Kesim Programınız (Sepet):**")
            st.dataframe(st.session_state.operator_kesim_listesi, use_container_width=True, hide_index=True)

            col_sepet1, col_sepet2 = st.columns(2)
            with col_sepet1:
                # El terminali veya bilgisayarda çalışırken manuel kaydetme güvencesi
                if st.button("💾 PROGRAMI MANUEL KAYDET", use_container_width=True):
                    safe_save_operator_list(st.session_state.operator_kesim_listesi)
                    st.success("💾 Sepet diske kilitlendi.")
            with col_sepet2:
                if st.button("🗑️ Listeyi Temizle", use_container_width=True):
                    safe_save_operator_list(pd.DataFrame(columns=["Plaka", "Gerekli Blok Kodu", "Gerekli Blok Adı"]))
                    st.rerun()

        with c2:
            st.subheader("2️⃣ Barkod Okut ve Kesimi İşle")

            if st.session_state.operator_kesim_listesi.empty:
                st.warning("👈 Lütfen önce sol taraftan kesim programınıza plaka ekleyin.")
            else:
                barkod_input = st.text_input("📦 Makineye Koyduğunuz Blok Barkodunu Okutun:", key="op_barkod").strip()

                if barkod_input:
                    stok_match = stok_df[stok_df[s_barkod_col].astype(str).str.strip() == str(barkod_input).strip()]

                    if stok_match.empty:
                        # ────────────────────────────────────────────────────
                        # YENİ: Stokta yoksa Tedarikçi Portalı (API) haritasına bak
                        # ────────────────────────────────────────────────────
                        api_harita = st.session_state.get('api_sevk_haritasi', {})
                        api_kayit = api_harita.get(str(barkod_input).strip())
                        if api_kayit:
                            st.warning(
                                f"⚠️ Bu barkod Tedarikçi Portalı kayıtlarında bulundu "
                                f"({api_kayit['MalzemeAdi']} - {api_kayit['MalzemeKodu']}) ancak henüz "
                                f"'Stok' sayfasına Mal Kabul ile işlenmemiş. Önce Mal Kabul ekranından "
                                f"stoğa alın, sonra kesim yapın."
                            )
                        else:
                            st.error(f"❌ '{barkod_input}' barkodlu blok depoda bulunamadı!")
                    else:
                        blok_row = stok_match.iloc[0]
                        okutulan_kod = str(blok_row.get(s_kod_col, "")).strip()

                        # Okutulan blok, operatörün sepetindeki bir plakanın ihtiyaç duyduğu blok koduyla uyuşuyor mu?
                        liste_df = st.session_state.operator_kesim_listesi
                        uyumlu_satirlar = liste_df[liste_df['Gerekli Blok Kodu'] == okutulan_kod]

                        if uyumlu_satirlar.empty:
                            st.error(f"🚨 YANLIŞ BLOK! Okutulan `{okutulan_kod}` kodu mevcut kesim listenizdeki hiçbir plaka ile eşleşmiyor!")
                            st.markdown(f"**Gereken Kodlar:** {', '.join(liste_df['Gerekli Blok Kodu'].unique())}")
                        else:
                            st.success(f"🎯 DOĞRU BLOK! ({okutulan_kod}) - {blok_row.get(s_kod_col, '')}")

                            uyumlu_plakalar = uyumlu_satirlar['Plaka'].tolist()
                            kesilen_plaka = st.selectbox("Hangi Plakayı Kesiyorsunuz?", uyumlu_plakalar)

                            mevcut_miktar = safe_float(blok_row.get(s_miktar_col, 0))
                            st.metric("Blok Mevcut Boy (cm)", f"{mevcut_miktar:.2f}")

                            with st.form("kesim_formu"):
                                c_form1, c_form2 = st.columns(2)
                                sarf_miktari = c_form1.number_input("📉 Bloktan Sarf Edilen (cm)", min_value=0.0, max_value=float(mevcut_miktar), step=1.0)
                                ek_fire = c_form2.number_input("🗑️ Varsa Fire (cm)", min_value=0.0, step=1.0)
                                cikan_adet = st.number_input("✨ Kesim Sonucu Çıkan Plaka (Adet)", min_value=0, step=1)

                                submitted = st.form_submit_button("🚀 KESİMİ ONAYLA VE STOKTAN DÜŞ")

                                if submitted:
                                    if sarf_miktari <= 0:
                                        st.warning("Sarfiyat sıfır olamaz!")
                                    elif (sarf_miktari + ek_fire) > mevcut_miktar:
                                        st.error("Mevcut stok aşıldı!")
                                    else:
                                        total_dus = sarf_miktari + ek_fire

                                        # Stok Güncelleme
                                        idx_val = stok_match.index[0]
                                        stok_df.at[idx_val, s_miktar_col] = mevcut_miktar - total_dus

                                        yeni_log = pd.DataFrame([{
                                            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "İşlem": "KESİM/SARF",
                                            "Kod": okutulan_kod,
                                            "Miktar": total_dus,
                                            "Açıklama": f"Plaka: {kesilen_plaka} | Çıkan Adet: {cikan_adet} | Fire: {ek_fire}"
                                        }])

                                        with st.spinner("İşleniyor..."):
                                            durum = update_stock_and_logs(stok_df, st.session_state.har_data, yeni_log)

                                        if durum:
                                            # Rapor ekranı kaydı
                                            st.session_state.gerceklesen_kesimler.append({
                                                "Plaka": kesilen_plaka,
                                                "Sarf Edilen (cm)": sarf_miktari,
                                                "Çıkan Adet": cikan_adet
                                            })
                                            st.session_state.stok_data = stok_df

                                            # Başarılı kesimden sonra bu plakayı listeden düşür/güncelle
                                            st.balloons()
                                            st.success("🎉 Kesim başarıyla işlendi ve stoklar düşüldü!")
                                            st.rerun()

    # ==========================================
    # 3. EKRAN: CANLI RAPORLAR
    # ==========================================
    elif st.session_state.bk_page == 'rapor_ekrani':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            go_menu()
            st.rerun()

        st.header("📈 Üretim ve Stok İhtiyaç Raporları")
        st.markdown("---")

        df_emir = st.session_state.get('main_data')
        stok_df, _ = load_live_stock()
        matris_df = st.session_state.eslesme_df

        if df_emir is None or df_emir.empty:
            st.info("⚠️ İş emri yüklenmediği için canlı rapor oluşturulamıyor.")
            st.stop()

        tanim_col = next((c for c in df_emir.columns if any(x in str(c).upper() for x in ["TANIM", "ÜRÜN", "AD"])), None)
        miktar_col = next((c for c in df_emir.columns if any(x in str(c).upper() for x in ["MİKTAR", "ADET"])), None)
        m_plaka_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper()), matris_df.columns[1])
        m_blok_kod_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK KODU" in str(c).upper()), matris_df.columns[2])
        m_blok_adi_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK ADI" in str(c).upper()), matris_df.columns[3])
        s_kod_col = next((c for c in stok_df.columns if "STOK KODU" in str(c).upper() or "KOD" in str(c).upper()), stok_df.columns[0])
        s_miktar_col = next((c for c in stok_df.columns if any(m in str(c).upper() for m in ['BAKİYE', 'MİKTAR', 'BOY', 'KALAN'])), stok_df.columns[4])

        # --- RAPOR 1: PLAKA ÜRETİM İLERLEMESİ ---
        st.subheader("📊 1. Plaka Kesim İlerleme Raporu")

        # İş emrindeki ihtiyaçları topla
        ihtiyac_df = df_emir.groupby(tanim_col, as_index=False)[miktar_col].sum()
        ihtiyac_df.rename(columns={tanim_col: "Plaka Tanımı", miktar_col: "İstenen Adet"}, inplace=True)

        # Gerçekleşenleri topla
        gerceklesen_df = pd.DataFrame(st.session_state.gerceklesen_kesimler)
        if not gerceklesen_df.empty:
            gercek_grup = gerceklesen_df.groupby("Plaka", as_index=False)["Çıkan Adet"].sum()
        else:
            gercek_grup = pd.DataFrame(columns=["Plaka", "Çıkan Adet"])

        # Birleştir (Merge)
        rapor1 = pd.merge(ihtiyac_df, gercek_grup, left_on="Plaka Tanımı", right_on="Plaka", how="left")
        rapor1['Çıkan Adet'] = rapor1['Çıkan Adet'].fillna(0).astype(int)
        rapor1['Kalan İhtiyaç'] = rapor1['İstenen Adet'] - rapor1['Çıkan Adet']
        rapor1.drop(columns=['Plaka'], inplace=True, errors='ignore')

        st.dataframe(rapor1.style.background_gradient(subset=['Kalan İhtiyaç'], cmap='Reds'), use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- RAPOR 2: BLOK STOK / İHTİYAÇ ANALİZİ (ZIRHLI MOTOR ENTEGRASYONLU) ---
        st.subheader("🧱 2. İhtiyaç Duyulan Blokların Canlı Stok Durumu")

        kalan_plakalar = rapor1[rapor1['Kalan İhtiyaç'] > 0]

        blok_rapor = []
        for _, row in kalan_plakalar.iterrows():
            plaka_adi = row['Plaka Tanımı']
            # Zırhlı eşleşme ile bağlı bloğu bul
            eslesme_res = find_best_match(plaka_adi, matris_df, m_plaka_col, m_blok_kod_col, m_blok_adi_col)

            if eslesme_res:
                b_kod = eslesme_res["blok_kodu"]
                b_ad = eslesme_res["blok_adi"]

                # Bu blok kodunun depodaki toplam miktarı
                stok_satirlari = stok_df[stok_df[s_kod_col].astype(str).str.strip() == b_kod]
                depo_mevcut = pd.to_numeric(stok_satirlari[s_miktar_col], errors='coerce').sum() if not stok_satirlari.empty else 0

                blok_rapor.append({
                    "Blok Kodu": b_kod,
                    "Blok Adı": b_ad,
                    "Etkilenen Plaka": plaka_adi,
                    "Depodaki Toplam Stok (cm)": depo_mevcut
                })

        if blok_rapor:
            df_blok = pd.DataFrame(blok_rapor)
            df_blok_unique = df_blok.drop_duplicates(subset=["Blok Kodu"]).reset_index(drop=True)

            # Kritik Stok Uyarı Renklendirmesi
            def highlight_stok(val):
                color = '#ff9999' if val <= 0 else '#99ff99'
                return f'background-color: {color}'

            st.dataframe(df_blok_unique.style.map(highlight_stok, subset=['Depodaki Toplam Stok (cm)']), use_container_width=True, hide_index=True)
        else:
            st.success("Tüm ihtiyaçlar karşılandı veya kesilecek plaka bulunmuyor.")
