import streamlit as st
import pandas as pd
import os
from datetime import datetime

def run_uretim_bitis(conn):
    st.header("🏭 Üretim Planlama, Takip ve Bitiş Onay Merkezi")
    st.write("Günlük üretim hedeflerinizi yönetin, açık iş emirlerini seçerek mamül bazlı tüketimleri gerçekleştirin.")
    st.divider()

    # --- 1. VERİLERİ ÇEK ---
    try:
        import veritabani
        df_stok = veritabani.load_sheet("Stok") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Stok")
        df_is_emirleri = veritabani.load_sheet("Is_Emirleri") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Is_Emirleri")
        df_hareketler = veritabani.load_sheet("Hareketler") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("HAREKETLER")
    except:
        st.error("🚨 Veritabanı katmanı yüklenirken bir sorun oluştu!")
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

    # Sütun isimlerindeki boşlukları temizle
    if df_is_emirleri is not None and not df_is_emirleri.empty:
        df_is_emirleri.columns = [c.strip() for c in df_is_emirleri.columns]
    if df_hareketler is not None and not df_hareketler.empty:
        df_hareketler.columns = [c.strip() for c in df_hareketler.columns]

    # --- 2. SESSİON STATE VE HEDEF YÖNETİMİ ---
    bugun = datetime.now().strftime("%Y-%m-%d")
    if "gunluk_hedef" not in st.session_state:
        st.session_state["gunluk_hedef"] = 500

    # --- SEKME YAPISI ---
    tab_dashboard, tab_kayit = st.tabs(["📊 Üretim Dashboard & Hedef Girişi", "🏗️ Üretim Bitiş Kaydı Girişi"])

    # =========================================================================
    # TAB 1: DASHBOARD & HEDEF GİRİŞİ
    # =========================================================================
    with tab_dashboard:
        col_target1, col_target2 = st.columns([1, 2])
        with col_target1:
            with st.container(border=True):
                st.subheader("🎯 Günlük Plan Girişi")
                yeni_hedef = st.number_input("Bugünkü Üretim Hedefi (Adet):", min_value=1, value=int(st.session_state["gunluk_hedef"]), step=10)
                if st.button("💾 Hedefi Güncelle", use_container_width=True):
                    st.session_state["gunluk_hedef"] = yeni_hedef
                    st.toast("🎯 Günlük üretim hedefi başarıyla güncellendi!", icon="✅")
        
        # Günlük Fiili Üretim Hesaplama
        toplam_gunluk_uretim = 0
        if df_hareketler is not None and not df_hareketler.empty:
            if 'Tarih' in df_hareketler.columns and 'İşlem' in df_hareketler.columns:
                df_hareketler['Tarih_Kisa'] = df_hareketler['Tarih'].astype(str).str[:10]
                bugunku_girisler = df_hareketler[(df_hareketler['Tarih_Kisa'] == bugun) & (df_hareketler['İşlem'] == 'MAMÜL GİRİŞ')]
                if 'Miktar' in bugunku_girisler.columns:
                    toplam_gunluk_uretim = pd.to_numeric(bugunku_girisler['Miktar'], errors='coerce').sum()

        with col_target2:
            st.subheader("📈 Anlık Üretim Performansı")
            c1, c2, c3 = st.columns(3)
            c1.metric(label="📆 Bugün Üretilen", value=f"{int(toplam_gunluk_uretim)} Adet")
            c2.metric(label="🎯 Günlük Hedef", value=f"{st.session_state['gunluk_hedef']} Adet")
            
            ilerleme_orani = min(1.0, float(toplam_gunluk_uretim / st.session_state["gunluk_hedef"])) if st.session_state["gunluk_hedef"] > 0 else 0.0
            c3.metric(label="📈 Gerçekleşme", value=f"%{ilerleme_orani * 100:.1f}")
            st.progress(ilerleme_orani, text="Günlük Kota Durumu")

    # =========================================================================
    # TAB 2: ÜRETİM BİTİŞ KAYDI GİRİŞİ (SEÇİM MODLU DATAFRAME)
    # =========================================================================
    with tab_kayit:
        st.subheader("📋 Açık İş Emirleri ve Mamül Seçim Listesi")
        st.caption("Aşağıdaki tablodan üretimi biten mamül satırına tıklayıp ardından miktar girerek onaylayın.")

        if df_is_emirleri is None or df_is_emirleri.empty:
            st.warning("⚠️ Sistemde yüklü iş emri bulunamadı.")
            return

        # Sütun varyasyonlarını esnek yönet
        ikod = 'Ürün Kodu' if 'Ürün Kodu' in df_is_emirleri.columns else ('Plaka Kodu' if 'Plaka Kodu' in df_is_emirleri.columns else 'Kod')
        iad = 'Ürün Adı' if 'Ürün Adı' in df_is_emirleri.columns else ('Plaka Adı' if 'Plaka Adı' in df_is_emirleri.columns else 'İsim')
        imik = 'Miktar' if 'Miktar' in df_is_emirleri.columns else ('Adet' if 'Adet' in df_is_emirleri.columns else 'Miktar')

        # Görüntülenecek dataframe'i sadeleştir ve hazırla
        df_gosterim = df_is_emirleri[['Sipariş No', ikod, iad, imik]].dropna(subset=['Sipariş No']).copy()
        
        # Streamlit interaktif seçim mekanizması (Single-select row)
        secim_kapsami = st.dataframe(
            df_gosterim,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )

        # Personel bir satır seçtiyse tetiklenir
        if secim_kapsami and "rows" in secim_kapsami["selection"] and len(secim_kapsami["selection"]["rows"]) > 0:
            secili_indeks = secim_kapsami["selection"]["rows"][0]
            satir_detay = df_gosterim.iloc[secili_indeks]

            secilen_siparis = str(satir_detay['Sipariş No'])
            mamul_kodu = str(satir_detay[ikod])
            mamul_adi = str(satir_detay[iad])
            hedef_miktar = satir_detay[imik]

            st.write("---")
            st.success(f"🎯 **Seçilen İş Emri:** {secilen_siparis} | **Ürün:** {mamul_adi} ({mamul_kodu})")

            col_form1, col_form2 = st.columns([1, 2])
            with col_form1:
                with st.container(border=True):
                    st.subheader("🔢 Üretim Miktarı")
                    uretim_miktari = st.number_input("Fiili Üretilen Adet:", min_value=1, value=1, step=1)
            
            # Reçete patlatma adımları
            recete_kalemleri = pd.DataFrame()
            if 'Plaka Kodu' in df_recete.columns:
                recete_kalemleri = df_recete[df_recete['Plaka Kodu'].astype(str).str.strip() == mamul_kodu.strip()]

            with col_form2:
                st.subheader("📋 Otomatik Tüketilecek Bileşen Projeksiyonu")
                if not recete_kalemleri.empty:
                    tuketim_plani = []
                    for _, row in recete_kalemleri.iterrows():
                        b_kodu = row.get('Blok Kodu', 'Bilinmeyen Kod')
                        b_adi = row.get('Blok Adı', 'Bilinmeyen İsim')
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

            # --- KAYIT BUTONU ---
            st.write("---")
            aktif_personel = st.session_state.get('user', 'Üretim Personeli')
            
            if st.button("🚀 ÜRETİM BİTİŞİNİ ONAYLA VE STOKLARI GÜNCELLE", type="primary", use_container_width=True):
                zaman_damgasi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                yeni_hareketler = []

                # A. Mamül Giriş Hareketi
                yeni_hareketler.append({
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

                # B. Bileşen Tüketim Hareketleri
                for t in tuketim_plani:
                    yeni_hareketler.append({
                        "Tarih": zaman_damgasi,
                        "İşlem": "ÜRETİM TÜKETİM",
                        "İş Emri": secilen_siparis,
                        "Kod": t["Bileşen Kodu"],
                        "İsim": t["Bileşen Adı"],
                        "Miktar": -float(t["Toplam Tüketim"]),
                        "Personel": aktif_personel,
                        "Adres": "ÜRETİM-TÜKETİM",
                        "Durum": "Kullanılabilir"
                    })

                # Veritabanına kaydet/birleştir
                df_har_yeni = pd.concat([df_hareketler, pd.DataFrame(yeni_hareketler)], ignore_index=True)

                # Stok bakiyelerini canlı güncelleme
                if df_stok is not None and not df_stok.empty:
                    df_stok.columns = [c.strip() for c in df_stok.columns]
                    
                    # Mamül stoğunu ekle
                    m_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == mamul_kodu.strip()].index
                    if not m_idx.empty:
                        df_stok.at[m_idx[0], 'Miktar'] = pd.to_numeric(df_stok.at[m_idx[0], 'Miktar'], errors='coerce') + uretim_miktari

                    # Bileşen stoklarını düş
                    for t in tuketim_plani:
                        b_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(t["Bileşen Kodu"]).strip()].index
                        if not b_idx.empty:
                            eski_stok = pd.to_numeric(df_stok.at[b_idx[0], 'Miktar'], errors='coerce')
                            df_stok.at[b_idx[0], 'Miktar'] = max(0.0, eski_stok - t["Toplam Tüketim"])

                # Google Sheets / Local Drive Entegrasyonu
                try:
                    if hasattr(veritabani, '_save_df'):
                        veritabani._save_df(df_har_yeni, "Hareketler")
                        veritabani._save_df(df_stok, "Stok")
                    elif hasattr(veritabani, 'update_data'):
                        veritabani.update_data("HAREKETLER", df_har_yeni)
                        veritabani.update_data("Stok", df_stok)
                    
                    st.success(f"🎉 İş Emri {secilen_siparis} kapatıldı! {uretim_miktari} adet mamül girişi yapıldı ve hammadde/yarı mamül stokları düşüldü.")
                    st.balloons()
                    st.rerun()
                except Exception as ex:
                    st.error(f"🚨 Kayıt işlenirken veritabanı hatası oluştu: {ex}")
        else:
            st.info("💡 İşlem yapmak için yukarıdaki listeden bir iş emri satırının üzerine tıklayın.")
