import streamlit as st
import pandas as pd
import os
from datetime import datetime

def run_uretim_bitis(conn):
    st.header("🏭 Üretim Planlama, Takip ve Bitiş Onay Merkezi")
    st.write("Planlanan ve devreden hedefleri izleyin, iş emirlerinden ana mamülleri seçerek tüketimleri yapın.")
    st.divider()

    # --- 1. VERİLERİ ÇEK ---
    try:
        import veritabani
        df_stok = veritabani.load_sheet("Stok") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Stok")
        df_is_emirleri = veritabani.load_sheet("Is_Emirleri") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Is_Emirleri")
        df_Hareketler = veritabani.load_sheet("Hareketler") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Hareketler")
        
        # 🗓️ HAFTALIK/GÜNLÜK ÜRETİM PLANI TABLOSU (Format: Tarih, Plan_Miktar)
        df_plan = veritabani.load_sheet("Uretim_Plani") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Uretim_Plani")
    except:
        st.error("🚨 Veritabanı katmanı veya sayfaları yüklenirken bir sorun oluştu!")
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

    # Sütun isimlerindeki boşlukları ve veri tiplerini standartlaştır
    if df_is_emirleri is not None and not df_is_emirleri.empty:
        df_is_emirleri.columns = [c.strip() for c in df_is_emirleri.columns]
    if df_Hareketler is not None and not df_Hareketler.empty:
        df_Hareketler.columns = [c.strip() for c in df_Hareketler.columns]
    if df_plan is not None and not df_plan.empty:
        df_plan.columns = [c.strip() for c in df_plan.columns]
    else:
        # Plan tablosu boş veya yoksa çökmemesi için boş bir şablon üretelim
        df_plan = pd.DataFrame(columns=["Tarih", "Plan_Miktar"])

    # Tarihleri datetime tipine çevirelim (Karşılaştırma için)
    bugun_dt = datetime.now().date()
    bugun_str = bugun_dt.strftime("%Y-%m-%d")

    # --- 2. DİNAMİK HEDEF VE DEVREDEN (BACKLOG) HESAPLAMA MOTORU ---
    # Toplam fiili üretimleri tarih bazlı özetleyelim
    df_Hareketler['Tarih_Kisa'] = ""
    if 'Tarih' in df_Hareketler.columns and not df_Hareketler.empty:
        df_Hareketler['Tarih_Kisa'] = df_Hareketler['Tarih'].astype(str).str[:10]
    
    # Bugün yapılan toplam mamül girişi
    bugunku_fiili_uretim = 0
    if not df_Hareketler.empty and 'İşlem' in df_Hareketler.columns:
        bugunku_fiili_uretim = pd.to_numeric(
            df_Hareketler[(df_Hareketler['Tarih_Kisa'] == bugun_str) & (df_Hareketler['İşlem'] == 'MAMÜL GİRİŞ')]['Miktar'], 
            errors='coerce'
        ).sum()

    # Plan tablosundaki tarihleri sanitize et
    df_plan['Tarih_Dt'] = pd.to_datetime(df_plan['Tarih'], errors='coerce').dt.date
    df_plan['Plan_Miktar'] = pd.to_numeric(df_plan['Plan_Miktar'], errors='coerce').fillna(0)

    # A. Bugünün net planı
    bugun_plani = df_plan[df_plan['Tarih_Dt'] == bugun_dt]['Plan_Miktar'].sum()

    # B. Geçmiş günlerden devreden (Backlog) hesabı
    gecmis_planlar = df_plan[df_plan['Tarih_Dt'] < bugun_dt]
    devreden_eksik_hedef = 0

    for idx, row in gecmis_planlar.iterrows():
        p_tarih = row['Tarih_Dt'].strftime("%Y-%m-%d")
        p_miktar = row['Plan_Miktar']
        
        # O geçmiş tarihte yapılan toplam mamül girişi
        gecmis_fiili = 0
        if not df_Hareketler.empty and 'İşlem' in df_Hareketler.columns:
            gecmis_fiili = pd.to_numeric(
                df_Hareketler[(df_Hareketler['Tarih_Kisa'] == p_tarih) & (df_Hareketler['İşlem'] == 'MAMÜL GİRİŞ')]['Miktar'],
                errors='coerce'
            ).sum()
        
        # Eğer o gün planlanandan az üretildiyse aradaki farkı devredene ekle
        if gecmis_fiili < p_miktar:
            devreden_eksik_hedef += (p_miktar - gecmis_fiili)

    # Toplam Gerçekleşmesi Gereken Hedef = Bugünün Planı + Geçmişten Kalan Eksikler
    toplam_dinamik_hedef = bugun_plani + devreden_eksik_hedef
    if toplam_dinamik_hedef <= 0:
        toplam_dinamik_hedef = 500  # Master data boşsa koruma amaçlı fallback varsayılan

    # --- 3. SEKME YAPISI (RADIO BUTON YOK) ---
    tab_dashboard, tab_kayit = st.tabs(["📊 Üretim Dashboard (Canlı Takip)", "🏗️ İş Emirleri & Üretim Bitiş Girişi"])

    # =========================================================================
    # SEKME 1: DASHBOARD
    # =========================================================================
    with tab_dashboard:
        st.subheader("📈 Gerçek Zamanlı Üretim Performans Göstergeleri")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric(label="📆 Bugün Üretilen Fiili", value=f"{int(bugunku_fiili_uretim)} Adet")
        col_m2.metric(label="📋 Bugünün Saf Planı", value=f"{int(bugun_plani)} Adet")
        col_m3.metric(label="⚠️ Geçmişten Devreden Eksik", value=f"{int(devreden_eksik_hedef)} Adet", delta="-Kalan Yük", delta_color="inverse")
        col_m4.metric(label="🎯 Toplam Güncel Hedef", value=f"{int(toplam_dinamik_hedef)} Adet")

        st.write("")
        ilerleme_orani = min(1.0, float(bugunku_fiili_uretim / toplam_dinamik_hedef)) if toplam_dinamik_hedef > 0 else 0.0
        st.progress(ilerleme_orani, text=f"Kümülatif Günlük Hedef Gerçekleşme Oranı: %{ilerleme_orani * 100:.1f}")
        
        if devreden_eksik_hedef > 0:
            st.warning(f"💡 Bilgi: Günlük hedefe, geçmiş günlerde tamamlanamayan **{int(devreden_eksik_hedef)} Adet** üretim borcu dahil edilmiştir.")

    # =========================================================================
    # SEKME 2: İŞ EMİRLERİNDEN SEÇEREK ÜRETİM BİTİŞ GİRİŞİ
    # =========================================================================
    with tab_kayit:
        st.subheader("📋 Açık İş Emirleri & Ana Ürün Listesi")
        st.caption("Aşağıdaki tablodan üretimi tamamlanan ana ürüne tıklayın, alt alanda reçete patlatılacaktır.")

        if df_is_emirleri is None or df_is_emirleri.empty:
            st.warning("⚠️ Sistemde aktif iş emri kaydı bulunamadı.")
            return

        # Esnek sütun ismi eşleme zırhı
        ikod = 'Ürün Kodu' if 'Ürün Kodu' in df_is_emirleri.columns else ('Plaka Kodu' if 'Plaka Kodu' in df_is_emirleri.columns else 'Kod')
        iad = 'Ürün Adı' if 'Ürün Adı' in df_is_emirleri.columns else ('Plaka Adı' if 'Plaka Adı' in df_is_emirleri.columns else 'İsim')
        imik = 'Miktar' if 'Miktar' in df_is_emirleri.columns else ('Adet' if 'Adet' in df_is_emirleri.columns else 'Miktar')

        # Tabloyu temizle ve sadece ana ürün satırlarını listelenebilir yap
        df_gosterim = df_is_emirleri[['Sipariş No', ikod, iad, imik]].dropna(subset=['Sipariş No']).copy()
        
        # İnteraktif Satır Seçim Modu (Tek Satır)
        secim_kapsami = st.dataframe(
            df_gosterim,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )

        # Satır tıklandığında açılacak onay ve backflush alanı
        if secim_kapsami and "rows" in secim_kapsami["selection"] and len(secim_kapsami["selection"]["rows"]) > 0:
            secili_indeks = secim_kapsami["selection"]["rows"][0]
            satir_detay = df_gosterim.iloc[secili_indeks]

            secilen_siparis = str(satir_detay['Sipariş No'])
            mamul_kodu = str(satir_detay[ikod])
            mamul_adi = str(satir_detay[iad])

            st.write("---")
            st.success(f"🏭 **Seçilen İş Emri:** {secilen_siparis}  |  **Ana Ürün:** {mamul_adi} ({mamul_kodu})")

            col_form1, col_form2 = st.columns([1, 2])
            with col_form1:
                with st.container(border=True):
                    st.subheader("🔢 Üretim Miktarı")
                    uretim_miktari = st.number_input("Fiili Üretilen Adet (Giriş):", min_value=1, value=1, step=1)
            
            # eslesme_matrisi.csv üzerinden Reçete (BOM) Çözümleme
            recete_kalemleri = pd.DataFrame()
            if 'Plaka Kodu' in df_recete.columns:
                recete_kalemleri = df_recete[df_recete['Plaka Kodu'].astype(str).str.strip() == mamul_kodu.strip()]

            with col_form2:
                st.subheader("📋 Otomatik Tüketilecek Bileşen Projeksiyonu (Hammadde & Yarı Mamül)")
                if not recete_kalemleri.empty:
                    tuketim_plani = []
                    for _, row in recete_kalemleri.iterrows():
                        b_kodu = row.get('Blok Kodu', 'Bilinmeyen Kod')
                        b_adi = row.get('Blok Adı', 'Bilinmeyen İsim')
                        
                        # Kalınlık veya sarfiyat katsayısı çarpanı
                        birim_sarfiyat = float(row.get('Kalinlik', 1)) if 'Kalinlik' in row.columns else 1.0
                        toplam_tuketim = birim_sarfiyat * uretim_miktari

                        tuketim_plani.append({
                            "Bileşen Kodu": b_kodu,
                            "Bileşen Adı": b_adi,
                            "Birim Sarfiyat": birim_sarfiyat,
                            "Toplam Tüketim": toplam_tuketim
                        })
                    
                    df_tuketim_view = pd.DataFrame(tuketim_plani)
                    st.dataframe(df_tuketim_view, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ Bu ürüne ait reçete (BOM) bağlantısı 'eslesme_matrisi.csv' içinde tanımlanmamış!")
                    tuketim_plani = []

            # --- VERİTABANINA YAZMA VE STOK DÜŞÜM MOTORU ---
            st.write("---")
            aktif_personel = st.session_state.get('user', 'Üretim Personeli')
            
            if st.button("🚀 ÜRETİM BİTİŞİNİ ONAYLA VE STOKLARI GÜNCELLE", type="primary", use_container_width=True):
                zaman_damgasi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                yeni_Hareketler = []

                # A. Üretilen Ana Ürün Giriş Hareketi
                yeni_Hareketler.append({
                    "Tarih": zaman_damgasi,
                    "İşlem": "MAMÜL GİRİŞ",
                    "İş Emri": secilen_siparis,
                    "Kod": mamul_kodu,
                    "İsim": mamul_adi,
                    "Miktar": uretim_miktari,
                    "Personel": aktif_personel,
                    "Adres": "ÜRETİM-HATTI",
                    "Durum": "Kullanılabilir"
                })

                # B. Alt Bileşenlerin (Hammadde ve Yarı Mamül) Tüketim Hareketi
                for t in tuketim_plani:
                    yeni_Hareketler.append({
                        "Tarih": zaman_damgasi,
                        "İşlem": "ÜRETİM TÜKETİM",
                        "İş Emri": secilen_siparis,
                        "Kod": t["Bileşen Kodu"],
                        "İsim": t["Bileşen Adı"],
                        "Miktar": -float(t["Toplam Tüketim"]), # Eksi değer düşüm sağlar
                        "Personel": aktif_personel,
                        "Adres": "ÜRETİM-TÜKETİM",
                        "Durum": "Kullanılabilir"
                    })

                # Hareketleri birleştir
                df_har_yeni = pd.concat([df_Hareketler, pd.DataFrame(yeni_Hareketler)], ignore_index=True)

                # Stok bakiyelerini canlı güncelle
                if df_stok is not None and not df_stok.empty:
                    df_stok.columns = [c.strip() for c in df_stok.columns]
                    
                    # Mamül stoğunu ekle
                    m_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == mamul_kodu.strip()].index
                    if not m_idx.empty:
                        df_stok.at[m_idx[0], 'Miktar'] = pd.to_numeric(df_stok.at[m_idx[0], 'Miktar'], errors='coerce') + uretim_miktari

                    # Bileşen stoklarını eksilt
                    for t in tuketim_plani:
                        b_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(t["Bileşen Kodu"]).strip()].index
                        if not b_idx.empty:
                            eski_stok = pd.to_numeric(df_stok.at[b_idx[0], 'Miktar'], errors='coerce')
                            df_stok.at[b_idx[0], 'Miktar'] = max(0.0, eski_stok - t["Toplam Tüketim"])

                # Google Sheets / Local Drive üzerine yazma kontrolü
                try:
                    if hasattr(veritabani, '_save_df'):
                        veritabani._save_df(df_har_yeni, "Hareketler")
                        veritabani._save_df(df_stok, "Stok")
                    elif hasattr(veritabani, 'update_data'):
                        veritabani.update_data("Hareketler", df_har_yeni)
                        veritabani.update_data("Stok", df_stok)
                    
                    st.success(f"🎉 İş Emri {secilen_siparis} kapatıldı! {uretim_miktari} adet mamül girişi işlendi. Tüm alt bileşenler (hammadde/yarı mamül) stoktan düşüldü.")
                    st.balloons()
                    st.rerun()
                except Exception as ex:
                    st.error(f"🚨 Kayıt işlenirken veritabanı hatası oluştu: {ex}")
        else:
            st.info("💡 İşlem yapmak için yukarıdaki listeden üretimi tamamlanan bir ana ürün satırına tıklayın.")
