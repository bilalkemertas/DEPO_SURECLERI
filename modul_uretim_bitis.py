import streamlit as st
import pandas as pd
import os
from datetime import datetime

def run_uretim_bitis(conn):
    st.header("🏭 Üretim Planlama, Takip ve Bitiş Onay Merkezi")
    st.write("Haftalık üretim planlarınızı oluşturun ve günlük hedeflere göre üretim bitiş kayıtlarını yönetin.")
    st.divider()

    # --- 1. VERİLERİ ÇEK ---
    try:
        import veritabani
        df_stok = veritabani.load_sheet("Stok") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Stok")
        df_is_emirleri = veritabani.load_sheet("Is_Emirleri") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Is_Emirleri")
        df_Hareketler = veritabani.load_sheet("Hareketler") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Hareketler")
    except Exception as e:
        st.error(f"🚨 Veritabanı katmanı veya sayfaları yüklenirken bir sorun oluştu: {e}")
        return

    # Reçete matrisini yerelden oku
    csv_path = "eslesme_matrisi.csv"
    if os.path.exists(csv_path):
        try:
            df_recete = pd.read_csv(csv_path, dtype=str)
            df_recete.columns = [c.strip() for c in df_recete.columns]
        except Exception as e:
            st.error(f"🚨 'eslesme_matrisi.csv' okunamadı: {e}")
            return
    else:
        st.error("🚨 Kök dizinde 'eslesme_matrisi.csv' bulunamadı! Tüketim hesaplanamaz.")
        return

    # Sütun isimlerindeki boşlukları temizle ve zorunlu sütunları garanti et
    if df_is_emirleri is not None and not df_is_emirleri.empty:
        df_is_emirleri.columns = [c.strip() for c in df_is_emirleri.columns]
        for col in ['Plan Tarihi', 'Plan Miktarı', 'Üretilen Miktar']:
            if col not in df_is_emirleri.columns:
                df_is_emirleri[col] = ""
    else:
        st.warning("⚠️ Sistemde aktif iş emri kaydı bulunamadı.")
        return

    if df_Hareketler is not None and not df_Hareketler.empty:
        df_Hareketler.columns = [c.strip() for c in df_Hareketler.columns]
    else:
        df_Hareketler = pd.DataFrame(columns=["Tarih", "İşlem", "İş Emri", "Kod", "İsim", "Miktar", "Personel", "Adres", "Durum"])

    if df_stok is not None and not df_stok.empty:
        df_stok.columns = [c.strip() for c in df_stok.columns]

    # Dinamik Sütun Eşleme Zırhı
    ikod = 'Ürün Kodu' if 'Ürün Kodu' in df_is_emirleri.columns else ('Plaka Kodu' if 'Plaka Kodu' in df_is_emirleri.columns else 'Kod')
    iad = 'Ürün Adı' if 'Ürün Adı' in df_is_emirleri.columns else ('Plaka Adı' if 'Plaka Adı' in df_is_emirleri.columns else 'İsim')

    # Güncel tarih bilgileri
    bugun_str = datetime.now().strftime("%Y-%m-%d")

    # --- SESSİON STATE YÖNETİMİ ---
    if "gecici_plan_listesi" not in st.session_state:
        st.session_state["gecici_plan_listesi"] = []

    # --- SEKME YAPISI (RADIO BUTON YOK) ---
    tab_planlama, tab_uretim_bitis = st.tabs(["📅 Haftalık Üretim Planlama", "🏭 Günlük Üretim Bitiş Kaydı & Takip"])

    # =========================================================================
    # SEKME 1: HAFTALIK ÜRETİM PLANLAMA
    # =========================================================================
    with tab_planlama:
        st.subheader("📝 Haftalık Plan Oluşturma Ekranı")
        
        with st.container(border=True):
            # 1. En üstte plan tarihi
            secilen_plan_tarihi = st.date_input("1️⃣ Plan Tarihi Seçiniz:", value=datetime.now().date())
            plan_tarihi_str = secilen_plan_tarihi.strftime("%Y-%m-%d")
            
            # 2. Seçilen tarihte hangi siparişten ürün yapılacağı
            siparis_nolar = sorted(df_is_emirleri['İş Emri'].dropna().unique().astype(str))
            secilen_siparis = st.selectbox("2️⃣ Sipariş No Seçiniz:", ["Seçiniz..."] + siparis_nolar)
            
            if secilen_siparis != "Seçiniz...":
                # Seçilen siparişe ait mamülleri filtrele
                df_sip_mamuller = df_is_emirleri[df_is_emirleri['İş Emri'].astype(str) == secilen_siparis]
                mamul_listesi = df_sip_mamuller[iad].unique().tolist()
                
                # 3. Hangi mamülden kaç adet üretileceği
                secilen_mamul = st.selectbox("3️⃣ Üretilecek Mamülü Seçiniz:", mamul_listesi)
                
                # Seçilen mamülün kodunu çek
                mamul_kodu = df_sip_mamuller[df_sip_mamuller[iad] == secilen_mamul].iloc[0][ikod]
                
                plan_miktari = st.number_input("4️⃣ Planlanan Üretim Miktarı (Adet):", min_value=1, value=1, step=1)
                
                # Listeye Ekle Butonu
                if st.button("➕ Listeye Ekle", use_container_width=True):
                    st.session_state["gecici_plan_listesi"].append({
                        "Plan Tarihi": plan_tarihi_str,
                        "İş Emri": secilen_siparis,
                        "Ürün Kodu": mamul_kodu,
                        "Ürün Adı": secilen_mamul,
                        "Plan Miktarı": plan_miktari
                    })
                    st.toast("Kayıt önizleme tablosuna eklendi.", icon="📥")

        # 4. Kaydetmeden önce görebileceğimiz tablo
        st.subheader("📋 Plan Önizleme Tablosu")
        if st.session_state["gecici_plan_listesi"]:
            df_onizleme = pd.DataFrame(st.session_state["gecici_plan_listesi"])
            st.dataframe(df_onizleme, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Önizleme Listesini Temizle"):
                st.session_state["gecici_plan_listesi"] = []
                st.rerun()
                
            # --- ANA BUTON: DRİVE'A KAYDET ---
            st.write("---")
            if st.button("💾 ÜRETİM PLANINI ONAYLA VE DRIVE'A KAYDET", type="primary", use_container_width=True):
                # Is_Emirleri dataframe'i üzerinde güncelleme yap
                for plan in st.session_state["gecici_plan_listesi"]:
                    # Sipariş No ve Ürün Kodu eşleşen satırı bul
                    idx = df_is_emirleri[
                        (df_is_emirleri['İş Emri'].astype(str) == str(plan["İş Emri"])) & 
                        (df_is_emirleri[ikod].astype(str) == str(plan["Ürün Kodu"]))
                    ].index
                    
                    if not idx.empty:
                        # Hücreleri doldur
                        df_is_emirleri.at[idx[0], 'Plan Tarihi'] = str(plan["Plan Tarihi"])
                        df_is_emirleri.at[idx[0], 'Plan Miktarı'] = str(plan["Plan Miktarı"])
                
                # Google Sheets / Drive üzerine yazma kontrolü
                try:
                    if hasattr(veritabani, '_save_df'):
                        veritabani._save_df(df_is_emirleri, "Is_Emirleri")
                    elif hasattr(veritabani, 'update_data'):
                        veritabani.update_data("Is_Emirleri", df_is_emirleri)
                    
                    st.success("🎉 Planlama verileri 'Is_Emirleri' sekmesine başarıyla kaydedildi! Tablodan hiçbir veri silinmedi.")
                    # Önizleme listesini temizlemiyoruz (Kural: tablodan veri silmiyor olmamız gerekiyor)
                    st.balloons()
                except Exception as ex:
                    st.error(f"🚨 Drive'a kaydetme sırasında hata oluştu: {ex}")
        else:
            st.info("💡 Henüz planlanan bir veri yok. Yukarıdaki formdan ekleme yapabilirsiniz.")

    # =========================================================================
    # SEKME 2: ÜRETİM BİTİŞ KAYDI EKRANI & DASHBOARD (TARİH SEÇİMİ YOK)
    # =========================================================================
    with tab_uretim_bitis:
        st.subheader("🎯 Bugünün Üretim Hedefleri ve Gerçekleşme Takibi")
        
        # Bugün planlananlar ve geçmişten kalan açık (devreden) işleri filtreleme
        df_is_emirleri['Plan_Miktar_Sayısal'] = pd.to_numeric(df_is_emirleri['Plan Miktarı'], errors='coerce').fillna(0)
        df_is_emirleri['Uretilen_Miktar_Sayısal'] = pd.to_numeric(df_is_emirleri['Üretilen Miktar'], errors='coerce').fillna(0)
        
        # Bugünün saf plan toplamı
        bugunun_plan_toplami = df_is_emirleri[df_is_emirleri['Plan Tarihi'].astype(str) == bugun_str]['Plan_Miktar_Sayısal'].sum()
        
        # Geçmiş günlerden devreden borç (Planlanmış ama Üretilen < Planlanan olanlar)
        df_gecmis_planlar = df_is_emirleri[(df_is_emirleri['Plan Tarihi'].astype(str) != "") & (df_is_emirleri['Plan Tarihi'].astype(str) < bugun_str)]
        gecmis_devreden_toplam = 0
        if not df_gecmis_planlar.empty:
            gecmis_devreden_toplam = (df_gecmis_planlar['Plan_Miktar_Sayısal'] - df_gecmis_planlar['Uretilen_Miktar_Sayısal']).clip(lower=0).sum()
            
        # Toplam Dinamik Hedef
        toplam_hedef_kume = bugunun_plan_toplami + gecmis_devreden_toplam
        
        # Bugün fiili üretilen toplam miktar
        bugun_fiili_toplam = 0
        if 'Tarih' in df_Hareketler.columns and not df_Hareketler.empty:
            df_Hareketler['Tarih_Kisa'] = df_Hareketler['Tarih'].astype(str).str[:10]
            bugun_fiili_toplam = pd.to_numeric(
                df_Hareketler[(df_Hareketler['Tarih_Kisa'] == bugun_str) & (df_Hareketler['İşlem'] == 'MAMÜL GİRİŞ')]['Miktar'],
                errors='coerce'
            ).sum()

        # DASHBOARD METRİKLERİ
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric(label="📆 Bugün Fiili Üretilen", value=f"{int(bugun_fiili_toplam)} Adet")
        cm2.metric(label="🎯 Toplam Günlük Hedef (Plan + Devreden)", value=f"{int(toplam_hedef_kume)} Adet")
        
        ilerleme = min(1.0, float(bugun_fiili_toplam / toplam_hedef_kume)) if toplam_hedef_kume > 0 else 0.0
        cm3.metric(label="📈 Hedef Gerçekleşme Oranı", value=f"%{ilerleme * 100:.1f}")
        st.progress(ilerleme, text="Günlük Kota İlerleme Durumu")
        
        st.divider()
        st.subheader("📋 Bugünün ve Devreden Planların Onay Listesi")
        
        # Tabloda gösterilecek açık planlı satırları filtrele
        df_aktif_planlar = df_is_emirleri[
            (df_is_emirleri['Plan Tarihi'].astype(str) == bugun_str) | 
            ((df_is_emirleri['Plan Tarihi'].astype(str) != "") & (df_is_emirleri['Plan Tarihi'].astype(str) < bugun_str) & (df_is_emirleri['Uretilen_Miktar_Sayısal'] < df_is_emirleri['Plan_Miktar_Sayısal']))
        ].copy()

        if df_aktif_planlar.empty:
            st.info("✨ Bugün için planlanmış veya geçmişten devretmiş bekleyen bir üretim hedefi bulunmuyor.")
            return

        # Sadeleştirilmiş gösterim tablosu
        df_onay_gosterim = df_aktif_planlar[['İş Emri', ikod, iad, 'Plan Tarihi', 'Plan Miktarı', 'Üretilen Miktar']].copy()
        
        # İnteraktif Satır Seçimi
        secim_kapsami = st.dataframe(
            df_onay_gosterim,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )

        if secim_kapsami and "rows" in secim_kapsami["selection"] and len(secim_kapsami["selection"]["rows"]) > 0:
            secili_idx = secim_kapsami["selection"]["rows"][0]
            satir_detay = df_onay_gosterim.iloc[secili_idx]

            secilen_siparis = str(satir_detay['İş Emri'])
            mamul_kodu = str(satir_detay[ikod])
            mamul_adi = str(satir_detay[iad])
            
            # Sayısal güvenli dönüşüm zırhı
            try:
                mevcut_uretilmis = float(satir_detay['Üretilen Miktar']) if str(satir_detay['Üretilen Miktar']).strip() != "" else 0.0
            except:
                mevcut_uretilmis = 0.0

            st.write("---")
            st.success(f"🎯 **Seçilen Ürün:** {mamul_adi} ({mamul_kodu}) | **Sipariş:** {secilen_siparis}")

            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                with st.container(border=True):
                    st.subheader("🔢 Üretim Girişi")
                    girilen_uretim_miktari = st.number_input("Bu Dönem Üretilen Miktar (Adet):", min_value=1, value=1, step=1)
            
            # Reçete (BOM) Hesaplama
            recete_kalemleri = pd.DataFrame()
            if 'Plaka Kodu' in df_recete.columns:
                recete_kalemleri = df_recete[df_recete['Plaka Kodu'].astype(str).str.strip() == mamul_kodu.strip()]

            with col_u2:
                st.subheader("📋 Otomatik Tüketilecek Hammadde/Yarı Mamül")
                if not recete_kalemleri.empty:
                    tuketim_plani = []
                    for _, row in recete_kalemleri.iterrows():
                        b_kodu = row.get('Blok Kodu', 'Bilinmeyen Kod')
                        b_adi = row.get('Blok Adı', 'Bilinmeyen İsim')
                        birim_sarfiyat = float(row.get('Kalinlik', 1)) if 'Kalinlik' in row.columns else 1.0
                        toplam_tuketim = birim_sarfiyat * girilen_uretim_miktari

                        tuketim_plani.append({
                            "Bileşen Kodu": b_kodu,
                            "Bileşen Adı": b_adi,
                            "Birim Sarfiyat": birim_sarfiyat,
                            "Toplam Tüketim": toplam_tuketim
                        })
                    st.dataframe(pd.DataFrame(tuketim_plani), use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Bu mamüle ait reçete bağlantısı 'eslesme_matrisi.csv' içinde bulunamadı!")
                    tuketim_plani = []

            # --- KAYDET BUTONU ---
            st.write("---")
            aktif_personel = st.session_state.get('user', 'Üretim Personeli')
            
            if st.button("🚀 ÜRETİM MİKTARINI İŞLE VE STOKLARI GÜNCELLE", type="primary", use_container_width=True):
                zaman_damgasi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                yeni_hareketler = []

                # 1. HAREKETLER KAYITLARI (Stok geçmişi için)
                yeni_hareketler.append({
                    "Tarih": zaman_damgasi, "İşlem": "MAMÜL GİRİŞ", "İş Emri": secilen_siparis,
                    "Kod": mamul_kodu, "İsim": mamul_adi, "Miktar": girilen_uretim_miktari,
                    "Personel": aktif_personel, "Adres": "ÜRETİM-HATTI", "Durum": "Kullanılabilir"
                })

                for t in tuketim_plani:
                    yeni_hareketler.append({
                        "Tarih": zaman_damgasi, "İşlem": "ÜRETİM TÜKETİM", "İş Emri": secilen_siparis,
                        "Kod": t["Bileşen Kodu"], "İsim": t["Bileşen Adı"], "Miktar": -float(t["Toplam Tüketim"]),
                        "Personel": aktif_personel, "Adres": "ÜRETİM-TÜKETİM", "Durum": "Kullanılabilir"
                    })

                df_har_son = pd.concat([df_Hareketler, pd.DataFrame(yeni_hareketler)], ignore_index=True)

                # 2. CANLI STOK GÜNCELLEME
                if df_stok is not None and not df_stok.empty:
                    # Mamül stoğunu artır
                    m_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == mamul_kodu.strip()].index
                    if not m_idx.empty:
                        df_stok.at[m_idx[0], 'Miktar'] = pd.to_numeric(df_stok.at[m_idx[0], 'Miktar'], errors='coerce') + girilen_uretim_miktari
                    
                    # Bileşen stoklarını düş
                    for t in tuketim_plani:
                        b_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(t["Bileşen Kodu"]).strip()].index
                        if not b_idx.empty:
                            eski_stok = pd.to_numeric(df_stok.at[b_idx[0], 'Miktar'], errors='coerce')
                            df_stok.at[b_idx[0], 'Miktar'] = max(0.0, eski_stok - t["Toplam Tüketim"])

                # 3. İŞ EMİRLERİ SEKLESİNDEKİ "Üretilen Miktar" ALANINI KÜMÜLATİF GÜNCELLEME
                target_is_emri_idx = df_is_emirleri[
                    (df_is_emirleri['İş Emri'].astype(str) == secilen_siparis) & 
                    (df_is_emirleri[ikod].astype(str) == mamul_kodu)
                ].index
                
                if not target_is_emri_idx.empty:
                    df_is_emirleri.at[target_is_emri_idx[0], 'Üretilen Miktar'] = str(mevcut_uretilmis + girilen_uretim_miktari)

                # Drive / Sheets Güncellemesi
                try:
                    if hasattr(veritabani, '_save_df'):
                        veritabani._save_df(df_har_son, "Hareketler")
                        veritabani._save_df(df_stok, "Stok")
                        veritabani._save_df(df_is_emirleri, "Is_Emirleri")
                    elif hasattr(veritabani, 'update_data'):
                        veritabani.update_data("Hareketler", df_har_son)
                        veritabani.update_data("Stok", df_stok)
                        veritabani.update_data("Is_Emirleri", df_is_emirleri)
                        
                    st.success(f"🎉 Üretim başarıyla kaydedildi! İş Emirleri sekmesindeki 'Üretilen Miktar' {mevcut_uretilmis + girilen_uretim_miktari} olarak güncellendi.")
                    st.balloons()
                    st.rerun()
                except Exception as ex:
                    st.error(f"🚨 Veriler kaydedilirken hata oluştu: {ex}")
        else:
            st.info("💡 Yukarıdaki listeden üretimi tamamlanan bir mamül satırına tıklayarak üretim adedini girebilirsiniz.")
