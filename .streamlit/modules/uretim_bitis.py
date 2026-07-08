import streamlit as st
import pandas as pd
import veritabani
import os
from datetime import datetime

def init_state():
    if 'ub_page' not in st.session_state:
        st.session_state.ub_page = 'menu'
    if 'secili_siparis' not in st.session_state:
        st.session_state.secili_siparis = None

def run_uretim_bitis(conn):
    init_state()
    
    # 1. OTURUM CANLI TUTMA MEKANİZMASI
    # Tarayıcının ve el terminalinin uykuya dalmasını engeller
    import streamlit.components.v1 as components
    components.html("<script>setInterval(function(){window.parent.postMessage({type:'streamlit:render'},'*');},30000);</script>", height=0)

    st.title("🏭 Mamül Bazlı Üretim Bitiş Paneli")
    st.write("Üretimi tamamlanan mamül miktarını girerek otomatik hammadde/yarı mamül tüketimini gerçekleştirin.")
    st.divider()

    # --- VERİLERİ ÇEK ---
    df_stok = veritabani.get_internal_data("Stok")
    df_is_emirleri = veritabani.get_internal_data("Is_Emirleri")
    
    # Reçete/Eşleşme Matrisini Yükle
    if os.path.exists("eslesme_matrisi.csv"):
        df_recete = pd.read_csv("eslesme_matrisi.csv")
    else:
        st.error("🚨 'eslesme_matrisi.csv' (Reçete Matrisi) bulunamadı! Tüketim yapılamaz.")
        return

    # --- 📊 ANLIK ÜRETİM DASHBOARD (EN ÜSTTE) ---
    st.subheader("🎯 Günlük Üretim Takip Dashboard'u")
    df_hareketler = veritabani.get_internal_data("HAREKETLER")
    
    bugun = datetime.now().strftime("%Y-%m-%d")
    toplam_gunluk_uretim = 0
    
    if df_hareketler is not None and not df_hareketler.empty:
        # Tarih sütununu temizle ve bugüne ait MAMÜL GİRİŞ'leri filtrele
        df_hareketler['Tarih_Kisa'] = df_hareketler['Tarih'].astype(str).str[:10]
        bugunku_girisler = df_hareketler[(df_hareketler['Tarih_Kisa'] == bugun) & (df_hareketler['İşlem'] == 'MAMÜL GİRİŞ')]
        toplam_gunluk_uretim = pd.to_numeric(bugunku_girisler['Miktar'], errors='coerce').sum()

    c1, c2, c3 = st.columns(3)
    c1.metric(label="📆 Bugün Üretilen Toplam Mamül", value=f"{int(toplam_gunluk_uretim)} ADET")
    c2.metric(label="🎯 Günlük Hedef", value="500 ADET") # Şirket hedefinize göre dinamikleşebilir
    ilerleme = min(1.0, toplam_gunluk_uretim / 500) if toplam_gunluk_uretim > 0 else 0.0
    c3.progress(ilerleme, text=f"Hedef Gerçekleşme: %{ilerleme*100:.1f}")
    
    st.divider()

    # --- 🏗️ OPERASYON EKRANI ---
    if df_is_emirleri is not None and not df_is_emirleri.empty:
        siparis_listesi = sorted(df_is_emirleri['Sipariş No'].dropna().unique().astype(str))
    else:
        siparis_listesi = []
        st.warning("⚠️ Aktif İş Emri/Sipariş bulunamadı.")

    with st.container(border=True):
        st.subheader("📝 Üretim Onay Formu")
        
        secilen_siparis = st.selectbox("🔎 Üretimi Biten Sipariş / İş Emri Seçiniz:", ["Seçiniz..."] + siparis_listesi)
        
        if secilen_siparis != "Seçiniz...":
            # Seçilen siparişin detaylarını getir
            sip_detay = df_is_emirleri[df_is_emirleri['Sipariş No'].astype(str) == secilen_siparis].iloc[0]
            mamul_kodu = sip_detay.get('Ürün Kodu', 'Tanımsız')
            mamul_adi = sip_detay.get('Ürün Adı', 'Tanımsız')
            siparis_adedi = sip_detay.get('Miktar', 0)
            
            st.info(f"📦 **Mamül:** [{mamul_kodu}] - {mamul_adi} | **Sipariş Hedefi:** {siparis_adedi} ADET")
            
            # Üretim Miktar Girişi
            uretim_miktari = st.number_input("🔢 Gerçekleşen Üretim Miktarı (Adet):", min_value=1, step=1, value=1)
            
            # Bu mamüle ait reçeteyi bul (Backflush Tüketim Listesi Oluşturma)
            # Reçete matrisinizdeki sütun isimlerine göre buraları filtreliyoruz (Örn: Plaka Kodu -> Blok Kodu eşleşmesi gibi)
            recete_kalemleri = df_recete[df_recete['Plaka Kodu'].astype(str).str.strip() == str(mamul_kodu).strip()]
            
            if not recete_kalemleri.empty:
                st.write("📋 **Bu Üretimle Beraber Stoktan Düşecek Bileşenler:**")
                tuketim_ozet = []
                
                for _, row in recete_kalemleri.navigate(): # Matris satırları
                    bilesen_kod = row.get('Blok Kodu') # Yarı mamül ya da hammadde kodu
                    bilesen_adi = row.get('Blok Adı')
                    # Örn: 1 plaka için gereken tüketim miktarı matristen alınır, yoksa 1 kabul edilir
                    birim_ihtiyac = float(row.get('Kalinlik', 1) if 'Kalinlik' in row else 1) 
                    toplam_tuketim = birim_ihtiyac * uretim_miktari
                    
                    tuketim_ozet.append({
                        "Bileşen Kodu": bilesen_kod,
                        "Bileşen Adı": bilesen_adi,
                        "Birim Sarfiyat": birim_ihtiyac,
                        "Toplam Tüketim": toplam_tuketim
                    })
                
                st.dataframe(pd.DataFrame(tuketim_ozet), use_container_width=True, hide_index=True)
                
                # --- ONAY VE KAYIT ---
                aktif_user = st.session_state.get('user', 'Üretim Personeli')
                
                if st.button("🚀 ÜRETİMİ TAMAMLA VE STOKLARI GÜNCELLE", type="primary", use_container_width=True):
                    # 1. ADIM: HAREKETLER TABLOSUNU ÇEK VE GÜNCELLE
                    df_har_yeni = veritabani.get_internal_data("HAREKETLER") or pd.DataFrame()
                    
                    zaman_damgasi = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # A. Mamül Giriş Kaydı
                    yeni_kayitlar = [{
                        "Tarih": zaman_damgasi,
                        "İşlem": "MAMÜL GİRİŞ",
                        "İş Emri": secilen_siparis,
                        "Kod": mamul_kodu,
                        "İsim": mamul_adi,
                        "Adres": "ÜRETİM-HATTI",
                        "Miktar": uretim_miktari,
                        "Personel": aktif_user,
                        "Durum": "Kullanılabilir",
                        "Lot": "URETIM-" + datetime.now().strftime("%d%m%y")
                    }]
                    
                    # B. Reçete Bileşenlerinin Tüketim Kayıtları
                    for t in tuketim_ozet:
                        yeni_kayitlar.append({
                            "Tarih": zaman_damgasi,
                            "İşlem": "ÜRETİM TÜKETİM",
                            "İş Emri": secilen_siparis,
                            "Kod": t["Bileşen Kodu"],
                            "İsim": t["Bileşen Adı"],
                            "Adres": "DEPO-1", # Varsayılan tüketim deposu
                            "Miktar": -float(t["Toplam Tüketim"]), # Stoktan düşeceği için eksi değer
                            "Personel": aktif_user,
                            "Durum": "Kullanılabilir",
                            "Lot": "OTOMATİK"
                        })
                    
                    # Excel/Sheets Güncellemesi
                    df_yeni_har = pd.concat([df_har_yeni, pd.DataFrame(yeni_kayitlar)], ignore_index=True)
                    veritabani.update_data("HAREKETLER", df_yeni_har)
                    
                    # 2. ADIM: MEVCUT ANLIK STOK TABLOSUNU GÜNCELLE
                    if df_stok is not None and not df_stok.empty:
                        # Mamül stoğunu arttır
                        mamul_stok_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(mamul_kodu).strip()].index
                        if not mamul_stok_idx.empty:
                            df_stok.at[mamul_stok_idx[0], 'Miktar'] = float(df_stok.at[mamul_stok_idx[0], 'Miktar']) + uretim_miktari
                        
                        # Bileşen stoklarını düş
                        for t in tuketim_ozet:
                            bilesen_idx = df_stok[df_stok['Kod'].astype(str).str.strip() == str(t["Bileşen Kodu"]).strip()].index
                            if not bilesen_idx.empty:
                                df_stok.at[bilesen_idx[0], 'Miktar'] = max(0.0, float(df_stok.at[bilesen_idx[0], 'Miktar']) - t["Toplam Tüketim"])
                        
                        veritabani.update_data("Stok", df_stok)
                    
                    st.success(f"🎉 Sipariş {secilen_siparis} için {uretim_miktari} Adet üretim başarıyla işlendi! Hammadde ve yarı mamüller stoktan düşüldü.")
                    st.balloons()
                    st.rerun()
            else:
                st.warning("⚠️ Bu mamüle ait `eslesme_matrisi.csv` üzerinde bir reçete tanımı bulunamadı. Tüketim adımları hesaplanamıyor.")
