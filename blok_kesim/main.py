"""Blok & Rulo Sünger Kesim Otomasyonu - Ana Modül

Bu modül, sekmeler yerine bağımsız ekranlar (state routing) kullanarak
İş Emri Yükleme, Operatör Kesim Listesi Oluşturma ve Raporlama süreçlerini yönetir.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Clean Architecture - Göreli İçe Aktarımlar
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import safe_float

def go_menu():
    st.session_state.bk_page = 'menu'

def run_blok_kesim(conn=None):
    """Ana Blok Kesim Ekranı Kontrol Merkezi"""
    
    # --- 1. HAFIZA VE DURUM BAŞLATMA (STATE INIT) ---
    init_blok_kesim_state()
    
    # Ekran yönlendirme anahtarı
    if 'bk_page' not in st.session_state:
        st.session_state.bk_page = 'menu'
        
    # Operatörün kendi oluşturacağı kesim listesi
    if 'operator_kesim_listesi' not in st.session_state:
        st.session_state.operator_kesim_listesi = pd.DataFrame(columns=["Plaka", "Gerekli Blok Kodu", "Gerekli Blok Adı"])
        
    # Raporlar için kesim geçmişi (RAM üzerinde anlık takip)
    if 'gerceklesen_kesimler' not in st.session_state:
        st.session_state.gerceklesen_kesimler = []

    # Eşleşme Matrisini Yükle
    if st.session_state.eslesme_df is None or st.session_state.eslesme_df.empty:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()

    # Ortak Canlı Veri Çekimi (Ekran 2 ve 3 için gerekecek)
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
            st.info("Üretimden gelen excel kesim listelerini sisteme tanıtın.")
            
        with c2:
            st.button("🎯 2. KESİM LİSTESİ & BARKOD", use_container_width=True, type="primary",
                      on_click=lambda: setattr(st.session_state, 'bk_page', 'kesim_ekrani'))
            st.warning("Operatörlerin listesini oluşturup barkod okutacağı alan.")
            
        with c3:
            st.button("📈 3. ÜRETİM VE STOK RAPORU", use_container_width=True, type="primary",
                      on_click=lambda: setattr(st.session_state, 'bk_page', 'rapor_ekrani'))
            st.success("Kesilen plakalar, kalanlar ve blok stok ihtiyaç analizleri.")

    # ==========================================
    # 1. EKRAN: İŞ EMRİ YÜKLEME
    # ==========================================
    elif st.session_state.bk_page == 'is_emri':
        if st.button("⬅️ ANA MENÜYE DÖN"): go_menu(); st.rerun()
        
        st.header("📂 Excel İş Emri / Kesim Listesi Yükleme")
        up_file = st.file_uploader("Lütfen Güncel İş Emri / Kesim Listesini Seçin:", type=['xlsx', 'xls'])
        
        if up_file:
            if 'main_data' not in st.session_state or st.session_state.get('uploaded_file_name') != up_file.name:
                try:
                    raw_df = pd.read_excel(up_file, header=None)
                    header_idx = 0
                    for i in range(min(20, len(raw_df))):
                        row_vals = [str(x).upper() for x in raw_df.iloc[i].dropna().tolist()]
                        if any("TANIM" in v or "KOD" in v or "MİKTAR" in v or "ADET" in v for v in row_vals):
                            header_idx = i
                            break
                    
                    df = pd.read_excel(up_file, header=header_idx)
                    st.session_state.main_data = df
                    st.session_state.uploaded_file_name = up_file.name
                    st.success("✅ İş emri başarıyla sisteme yüklendi ve hafızaya alındı!")
                except Exception as e:
                    st.error(f"Dosya okunurken hata oluştu: {e}")
            
            df = st.session_state.get('main_data')
            if df is not None and not df.empty:
                st.dataframe(df.head(10), use_container_width=True)
                st.info("İş emri hazır. Ana menüye dönüp 'Kesim Listesi' ekranına geçebilirsiniz.")

    # ==========================================
    # 2. EKRAN: OPERATÖR SEÇİM VE BARKOD KESİM
    # ==========================================
    elif st.session_state.bk_page == 'kesim_ekrani':
        if st.button("⬅️ ANA MENÜYE DÖN"): go_menu(); st.rerun()
        
        st.header("🎯 Operatör Kesim Masası")
        st.markdown("---")
        
        df_emir = st.session_state.get('main_data')
        matris_df = st.session_state.eslesme_df
        stok_df, har_df = load_live_stock()
        
        if df_emir is None or df_emir.empty:
            st.error("⚠️ Henüz bir İş Emri yüklenmedi! Lütfen önce 1. Ekrandan excel yükleyin.")
            st.stop()
            
        if matris_df is None or matris_df.empty:
            st.error("⚠️ Eşleşme matrisi (eslesme_matrisi.csv) bulunamadı!")
            st.stop()
            
        # Sütunları dinamik bul
        tanim_col = next((c for c in df_emir.columns if "TANIM" in str(c).upper() or "ÜRÜN" in str(c).upper() or "AD" in str(c).upper()), None)
        m_plaka_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper()), matris_df.columns[1])
        m_blok_kod_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK KODU" in str(c).upper()), matris_df.columns[2])
        m_blok_adi_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK ADI" in str(c).upper()), matris_df.columns[3])
        s_kod_col = next((c for c in stok_df.columns if "STOK KODU" in str(c).upper() or "KOD" in str(c).upper()), stok_df.columns[0])
        s_miktar_col = next((c for c in stok_df.columns if any(m in str(c).upper() for m in ['BAKİYE', 'MİKTAR', 'BOY', 'KALAN'])), stok_df.columns[4])
        s_barkod_col = next((c for c in stok_df.columns if "BARKOD" in str(c).upper()), stok_df.columns[2])

        # ADIM 1: STOKLU PLAKALARI TESPİT ET
        is_emri_plakalar = df_emir[tanim_col].dropna().unique().tolist()
        stoklu_plakalar = []
        
        # Sadece depoda stoğu olan bloklara bağlı plakaları filtrele
        for plaka in is_emri_plakalar:
            eslesme = matris_df[matris_df[m_plaka_col].astype(str).str.strip() == str(plaka).strip()]
            if not eslesme.empty:
                hedef_blok_kodu = str(eslesme.iloc[0][m_blok_kod_col]).strip()
                # Canlı stokta bu bloktan 0'dan büyük miktar var mı?
                stok_var_mi = stok_df[(stok_df[s_kod_col].astype(str).str.strip() == hedef_blok_kodu) & (pd.to_numeric(stok_df[s_miktar_col], errors='coerce') > 0)]
                if not stok_var_mi.empty:
                    stoklu_plakalar.append(plaka)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("1️⃣ Kesim Listenizi Oluşturun")
            secilen_plaka = st.selectbox("Stoğu Hazır Olan Kesilebilir Plakalar:", ["Seçiniz..."] + stoklu_plakalar)
            
            if secilen_plaka != "Seçiniz...":
                eslesme_row = matris_df[matris_df[m_plaka_col].astype(str).str.strip() == str(secilen_plaka).strip()].iloc[0]
                sec_kod = str(eslesme_row[m_blok_kod_col]).strip()
                sec_ad = str(eslesme_row[m_blok_adi_col]).strip()
                
                st.info(f"🧱 Gereken Blok: **{sec_kod}** - {sec_ad}")
                
                if st.button("➕ Kendi Kesim Listeme Ekle"):
                    # Listede zaten yoksa ekle
                    mevcut = st.session_state.operator_kesim_listesi
                    if not ((mevcut['Plaka'] == secilen_plaka) & (mevcut['Gerekli Blok Kodu'] == sec_kod)).any():
                        yeni_satir = pd.DataFrame([{"Plaka": secilen_plaka, "Gerekli Blok Kodu": sec_kod, "Gerekli Blok Adı": sec_ad}])
                        st.session_state.operator_kesim_listesi = pd.concat([mevcut, yeni_satir], ignore_index=True)
                        st.success("✅ Listeye eklendi!")
                        st.rerun()
                    else:
                        st.warning("Bu plaka zaten listenizde!")
                        
            st.markdown("---")
            st.markdown("**Sizin Kesim Listeniz (Sepet):**")
            st.dataframe(st.session_state.operator_kesim_listesi, use_container_width=True, hide_index=True)
            if not st.session_state.operator_kesim_listesi.empty:
                if st.button("🗑️ Listemi Temizle"):
                    st.session_state.operator_kesim_listesi = pd.DataFrame(columns=["Plaka", "Gerekli Blok Kodu", "Gerekli Blok Adı"])
                    st.rerun()

        with c2:
            st.subheader("2️⃣ Barkod Okut ve Kesimi İşle")
            
            if st.session_state.operator_kesim_listesi.empty:
                st.warning("👈 Lütfen önce sol taraftan kesim listenize plaka ekleyin.")
            else:
                barkod_input = st.text_input("📦 Makineye Koyduğunuz Blok Barkodunu Okutun:", key="op_barkod").strip()
                
                if barkod_input:
                    stok_match = stok_df[stok_df[s_barkod_col].astype(str).str.strip() == str(barkod_input).strip()]
                    
                    if stok_match.empty:
                        st.error(f"❌ '{barkod_input}' barkodlu blok depoda bulunamadı!")
                    else:
                        blok_row = stok_match.iloc[0]
                        okutulan_kod = str(blok_row.get(s_kod_col, "")).strip()
                        
                        # Okutulan blok, operatörün listesindeki BİR bloğa uyuyor mu?
                        liste_df = st.session_state.operator_kesim_listesi
                        uyumlu_satirlar = liste_df[liste_df['Gerekli Blok Kodu'] == okutulan_kod]
                        
                        if uyumlu_satirlar.empty:
                            st.error(f"🚨 YANLIŞ BLOK! Okutulan `{okutulan_kod}` kodu mevcut kesim listenizdeki hiçbir plaka ile eşleşmiyor!")
                        else:
                            st.success(f"🎯 DOĞRU BLOK! ({okutulan_kod})")
                            
                            # Aynı bloktan birden fazla plaka kesilebilir, operatöre hangisini kestiğini soralım
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
                                    if sarf_miktari <= 0: st.warning("Sarfiyat sıfır olamaz!")
                                    elif (sarf_miktari + ek_fire) > mevcut_miktar: st.error("Mevcut stok aşıldı!")
                                    else:
                                        total_dus = sarf_miktari + ek_fire
                                        
                                        # Veritabanı Güncelleme
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
                                            # Rapor ekranı için RAM'e gerçekleşen üretim kaydını ekle
                                            st.session_state.gerceklesen_kesimler.append({
                                                "Plaka": kesilen_plaka,
                                                "Sarf Edilen (cm)": sarf_miktari,
                                                "Çıkan Adet": cikan_adet
                                            })
                                            st.session_state.stok_data = stok_df
                                            st.balloons()
                                            st.success("🎉 Kesim başarıyla işlendi!")

    # ==========================================
    # 3. EKRAN: CANLI RAPORLAR
    # ==========================================
    elif st.session_state.bk_page == 'rapor_ekrani':
        if st.button("⬅️ ANA MENÜYE DÖN"): go_menu(); st.rerun()
        
        st.header("📈 Üretim ve Stok İhtiyaç Raporları")
        st.markdown("---")
        
        df_emir = st.session_state.get('main_data')
        stok_df, _ = load_live_stock()
        matris_df = st.session_state.eslesme_df
        
        if df_emir is None or df_emir.empty:
            st.info("⚠️ İş emri yüklenmediği için rapor oluşturulamıyor.")
            st.stop()
            
        tanim_col = next((c for c in df_emir.columns if "TANIM" in str(c).upper() or "ÜRÜN" in str(c).upper() or "AD" in str(c).upper()), None)
        miktar_col = next((c for c in df_emir.columns if "MİKTAR" in str(c).upper() or "ADET" in str(c).upper()), None)
        m_plaka_col = next((c for c in matris_df.columns if "YARI MAMUL ADI" in str(c).upper()), matris_df.columns[1])
        m_blok_kod_col = next((c for c in matris_df.columns if "BAĞLI BLOK STOK KODU" in str(c).upper()), matris_df.columns[2])
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
        
        # --- RAPOR 2: BLOK STOK / İHTİYAÇ ANALİZİ ---
        st.subheader("🧱 2. İhtiyaç Duyulan Blokların Canlı Stok Durumu")
        
        # Rapor1'deki kalan ihtiyacı > 0 olan plakaları bul
        kalan_plakalar = rapor1[rapor1['Kalan İhtiyaç'] > 0]
        
        blok_rapor = []
        for _, row in kalan_plakalar.iterrows():
            plaka_adi = row['Plaka Tanımı']
            eslesme = matris_df[matris_df[m_plaka_col].astype(str).str.strip() == str(plaka_adi).strip()]
            
            if not eslesme.empty:
                b_kod = str(eslesme.iloc[0][m_blok_kod_col]).strip()
                b_ad = str(eslesme.iloc[0][m_blok_adi_col]).strip()
                
                # Bu blok kodunun depodaki toplam miktarı
                stok_satirlari = stok_df[stok_df[s_kod_col].astype(str).str.strip() == b_kod]
                depo_mevcut = pd.to_numeric(stok_satirlari[s_miktar_col], errors='coerce').sum() if not stok_satirlari.empty else 0
                
                # Listeye ekle (Aynı bloktan birden fazla talep olabilir, sonra gruplayacağız)
                blok_rapor.append({
                    "Blok Kodu": b_kod,
                    "Blok Adı": b_ad,
                    "Etkilenen Plaka": plaka_adi,
                    "Depodaki Toplam Stok (cm)": depo_mevcut
                })
                
        if blok_rapor:
            df_blok = pd.DataFrame(blok_rapor)
            # Eğer aynı blok birden fazla plaka için lazımsa benzersiz listele
            df_blok_unique = df_blok.drop_duplicates(subset=["Blok Kodu"]).reset_index(drop=True)
            
            # Kritik Stok Uyarı Renklendirmesi
            def highlight_stok(val):
                color = '#ff9999' if val <= 0 else '#99ff99'
                return f'background-color: {color}'
                
            st.dataframe(df_blok_unique.style.map(highlight_stok, subset=['Depodaki Toplam Stok (cm)']), use_container_width=True, hide_index=True)
        else:
            st.success("Tüm ihtiyaçlar karşılandı veya kesilecek plaka bulunmuyor.")
