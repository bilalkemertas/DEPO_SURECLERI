import streamlit as st
import pandas as pd
import os
from datetime import datetime

def run_uretim_bitis(conn):
    st.header("🏭 Mamül Bazlı Üretim Bitiş ve Stok Tüketim Paneli")
    st.write("Üretilen nihai mamül adedini girerek reçeteye bağlı hammadde ve yarı mamülleri otomatik tüketin.")
    st.divider()

    # --- 1. VERİLERİ DRIVEO VE YERELDEN ÇEKMEYE ÇALIŞ ---
    # Mevcut veritabanı yapına göre fonksiyon çağrıları dinamikleştirilmiştir
    try:
        import veritabani
        df_stok = veritabani.load_sheet("Stok") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Stok")
        df_is_emirleri = veritabani.load_sheet("Is_Emirleri") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("Is_Emirleri")
        df_hareketler = veritabani.load_sheet("Hareketler") if hasattr(veritabani, 'load_sheet') else veritabani.get_internal_data("HAREKETLER")
    except:
        st.error("🚨 Veritabanı modülü yüklenirken veya Google Sheets sekmeleri okunurken hata oluştu!")
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
        st.error("🚨 Kök dizinde 'eslesme_matrisi.csv' (Reçete Verisi) bulunamadı! Tüketim hesaplanamaz.")
        return

    # --- 2. 📊 ANLIK ÜRETİM DASHBOARD (GÜNLÜK HEDEF TAKİBİ) ---
    st.subheader("🎯 Günlük Üretim Takip Dashboard'u")
    
    bugun = datetime.now().strftime("%Y-%m-%d")
    toplam_gunluk_uretim = 0
    
    if df_hareketler is not None and not df_hareketler.empty:
        # Tarih ve İşlem sütun isimlerini standartlaştır
        df_hareketler.columns = [c.strip() for c in df_hareketler.columns]
        if 'Tarih' in df_hareketler.columns and 'İşlem' in df_hareketler.columns:
            df_hareketler['Tarih_Kisa'] = df_hareketler['Tarih'].astype(str).str[:10]
            # 'MAMÜL GİRİŞ' tipindeki bugünün kayıtlarını filtrele
            bugunku_girisler = df_hareketler[(df_hareketler['Tarih_Kisa'] == bugun) & (df_hareketler['İşlem'] == 'MAMÜL GİRİŞ')]
            if 'Miktar' in bugunku_girisler.columns:
                toplam_gunluk_uretim = pd.to_numeric(bugunku_girisler['Miktar'], errors='coerce').sum()

    c1, c2, c3 = st.columns(3)
    c1.metric(label="📆 Bugün Üretilen Toplam Mamül", value=f"{int(toplam_gunluk_uretim)} Adet")
    
    # Günlük hedefi 500 kabul edelim (isteğe bağlı değiştirilebilir)
    gunluk_hedef = 500
    c2.metric(label="🎯 Günlük Fabrika Hedefi", value=f"{gunluk_hedef} Adet")
    
    ilerleme_orani = min(1.0, float(toplam_gunluk_uretim / gunluk_hedef)) if toplam_gunluk_uretim > 0 else 0.0
    c3.progress(ilerleme_orani, text=f"Hedef Gerçekleşme Oranı: %{ilerleme_orani * 100:.1f}")
    st.divider()

    # --- 3. 📝 ÜRETİM GİRİŞ FORMU ---
    st.subheader("📝 İş Emri Kapatma ve Üretim Onay Formu")
    
    if df_is_emirleri is not None and not df_is_emirleri.empty:
        df_is_emirleri.columns = [c.strip() for c in df_is_emirleri.columns]
        # Sipariş No listesini hazırla
        siparis_listesi = sorted(df_is_emirleri['Sipariş No'].dropna().unique().astype(str)) if 'Sipariş No' in df_is_emirleri.columns else []
    else:
        siparis_listesi = []

    if not siparis_listesi:
        st.warning("⚠️ Sistemde işlem yapılabilecek aktif bir Sipariş/İş Emri kaydı bulunamadı.")
        return

    with st.container(border=True):
        secilen_siparis = st.selectbox("🔎 Üretimi Tamamlanan Sipariş Numarasını Seçiniz:", ["Seçiniz..."] + siparis_listesi)
        
        if secilen_siparis != "Seçiniz...":
            # Sipariş satır detayını yakala
            sip_satir = df_is_emirleri[df_is_emirleri['Sipariş No'].astype(str) == secilen_siparis].iloc[0]
            
            # Sütun isimleri projenizdeki varyasyonlara göre atanır (Ürün Kodu / Plaka Kodu vb.)
            mamul_kodu = sip_satir.get('Ürün Kodu', sip_satir.get('Plaka Kodu', 'Tanımsız'))
            mamul_adi = sip_satir.get('Ürün Adı', sip_satir.get('Plaka Adı', 'Tanımsız'))
            hedef_miktar = sip_satir.get('Miktar', sip_satir.get('Adet', '0'))
            
            st.info(f"📦 **Mamül Detayı:** [{mamul_kodu}] - {mamul_adi}  |  🎯 **Sipariş Hedefi:** {hedef_miktar} Adet")
            
            # Miktar Girişi
            uretim_miktari = st.number_input("🔢 Fiili Üretilen Mamül Miktarı (Adet):", min_value=1, value=1, step=1)
            
            # Reçete Patlatma (Backflushing) Alanı
            # eslesme_matrisi.csv içerisindeki Plaka Kodu ile eşleşen Blok Kodu (Hammadde/Yarı mamül) aranıyor
            recete_kalemleri = pd.DataFrame()
            if 'Plaka Kodu' in df_recete.columns:
                recete_kalemleri = df_recete[df_recete['Plaka Kodu'].astype(str).str.strip() == str(mamul_kodu).strip()]
                
            if not recete_kalemleri.empty:
                st.write("📋 **Bu onay sonrası otomatik düşülecek Hammadde / Yarı Mamül listesi:**")
                tuketim_plani = []
                
                for _, row in recete_kalemleri.iterrows():
                    bilesen_kodu = row.get('Blok Kodu', 'Bilinmeyen Kod')
                    bilesen_adi = row.get('Blok Adı', 'Bilinmeyen İsim')
                    
                    # Kalınlık veya standart sarfiyat çarpanı (Yoksa 1 adet sayılır)
                    birim_sarfiyat = float(row.get('Kalinlik', 1)) if 'Kalinlik' in row.columns else 1.0
                    toplam_tuketim = birim_sarfiyat * uretim_miktari
                    
                    tuketim_plani.append({
                        "Bileşen Kodu": bilesen_kodu,
                        "Bileşen Adı": bilesen_adi,
                        "Birim Sarfiyat": birim_sarfiyat,
                        "Toplam Tüketim": toplam_tuketim
                    })
                
                st.dataframe(pd.DataFrame(tuketim_plani), use_container_width=True, hide_index=True)
                
                # --- ONAYLAMA VE VERİTABANINA YAZMA MOTORU ---
                aktif_personel = st.session_state.get('user', 'Üretim Personeli')
                
                if st.button("🚀 ÜRETİMİ BİTİR VE STOKLARDAN OTOMATİK DÜŞ", type="primary", use_container_width=True):
                    zaman_damgasi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    yeni_hareketler = []
                    
                    # A. Üretilen Mamül İçin Giriş Hareketi OLUŞTUR
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
                    
                    # B. Reçetedeki Hammadde / Yarı Mamüller İçin Tüketim Hareketi OLUŞTUR
                    for t in tuketim_plani:
                        yeni_hareketler.append({
                            "Tarih": zaman_damgasi,
                            "İşlem": "ÜRETİM TÜKETİM",
                            "İş Emri": secilen_siparis,
                            "Kod": t["Bileşen Kodu"],
                            "İsim": t["Bileşen Adı"],
                            "Miktar": -float(t["Toplam Tüketim"]), # Stoktan düşüş için eksi girilir
                            "Personel": aktif_personel,
                            "Adres": "ÜRETİM-TÜKETİM",
                            "Durum": "Kullanılabilir"
                        })
                        
                    # Hareketleri veritabanına ekle
                    df_har_yeni = pd.concat([df_hareketler, pd.DataFrame(yeni_hareketler)], ignore_index=True)
                    
                    # Anlık canlı stok tablosunu (Stok sekmesini) güncelle (Mevcut fonksiyonunuza göre tetiklenir)
                    if df_stok is not None and not df_stok.empty:
                        df_stok.columns = [c.strip() for c in df_stok.columns]
                        # Mamül stoğunu ekle
                        m_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(mamul_kodu).strip()].index
                        if not m_idx.empty:
                            df_stok.at[m_idx[0], 'Miktar'] = pd.to_numeric(df_stok.at[m_idx[0], 'Miktar'], errors='coerce') + uretim_miktari
                        
                        # Bileşen stoklarını eksilt
                        for t in tuketim_plani:
                            b_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(t["Bileşen Kodu"]).strip()].index
                            if not b_idx.empty:
                                eski_stok = pd.to_numeric(df_stok.at[b_idx[0], 'Miktar'], errors='coerce')
                                df_stok.at[b_idx[0], 'Miktar'] = max(0.0, eski_stok - t["Toplam Tüketim"])
                    
                    # Google Sheets'e Kaydet
                    try:
                        if hasattr(veritabani, '_save_df'):
                            veritabani._save_df(df_har_yeni, "Hareketler")
                            veritabani._save_df(df_stok, "Stok")
                        elif hasattr(veritabani, 'update_data'):
                            veritabani.update_data("HAREKETLER", df_har_yeni)
                            veritabani.update_data("Stok", df_stok)
                        st.success(f"🎉 Sipariş {secilen_siparis} başarıyla tamamlandı! Mamül stoğu artırıldı ve tüm alt bileşenler stoktan düşüldü.")
                        st.balloons()
                        st.rerun()
                    except Exception as ex:
                        st.error(f"🚨 Veritabanına kaydetme sırasında hata oluştu: {ex}")
            else:
                st.warning("⚠️ Bu mamüle ait 'eslesme_matrisi.csv' içerisinde bir reçete/BOM bağlantısı bulunamadı. Tüketim adımları atlanıyor.")
