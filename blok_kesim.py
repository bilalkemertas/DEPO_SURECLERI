import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def run_blok_kesim(conn):
    # --- 1. AYIKLAMA MOTORU ---
    def ayikla_malzeme_detay(tanim):
        if pd.isna(tanim): return None
        text = str(tanim).upper()
        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)(?:\s*[Xx]\s*(\d+))?', text)
        if not olcu: return None
        boy, en, yuk = olcu.groups()
        return {
            "boy": float(boy), "en": float(en),
            "kalinlik": float(yuk) if yuk else None,
            "ozellik": text[:olcu.start()].strip()
        }

    # --- NAVİGASYON ---
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 4])
    with c_back1:
        if st.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.page = 'home'; st.rerun()
    with c_back2:
        if st.button("⬅️ TEMİZLE", use_container_width=True):
            for k in ['main_data', 'stok_data', 'har_data']: 
                if k in st.session_state: del st.session_state[k]
            st.rerun()

    st.title("✂️ Blok & Rulo Kesim")

    # --- 2. VERİ YÜKLEME ---
    with st.container(border=True):
        uploaded_file = st.file_uploader("Kesim Listesi Yükle (Excel)", type=['xlsx'], key="bk_uploader")
        if uploaded_file and 'main_data' not in st.session_state:
            try:
                df_load = pd.read_excel(uploaded_file)
                df_load.columns = [str(c).strip() for c in df_load.columns]
                st.session_state['main_data'] = df_load
                # Veritabanından taze verileri çek
                st.session_state['stok_data'] = veritabani.get_internal_data("Stok")
                st.session_state['har_data'] = veritabani.get_internal_data("Hareketler")
                st.success("✅ Kesim listesi ve taze veritabanı yüklendi.")
            except Exception as e: st.error(f"Hata: {e}")

    # --- 3. OPERASYON EKRANI ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        # Excel'de parti no yoksa Malzeme Tanımı üzerinden ilerliyoruz
        tanim_col = next((c for c in df.columns if "Tanım" in c or "Malzeme" in c), "Malzeme Tanımı")

        st.divider()
        # PATRONUN NOTU: Burada okutulan kod, Teslim Alma'daki Parti No/Barkod'dur.
        parti_barkod = st.text_input("🔍 Kesilecek Blok/Parti Barkodunu Okutun:").strip()

        if parti_barkod:
            # 1. Önce bu barkodun stoktaki karşılığını bul (Mal Kabul'den gelen Tedarikçi Barkod)
            stok_df = st.session_state['stok_data']
            if 'Tedarikçi Barkod' not in stok_df.columns:
                st.error("❌ Stok tablosunda 'Tedarikçi Barkod' sütunu bulunamadı!"); st.stop()
            
            blok_match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == parti_barkod]
            
            if not blok_match.empty:
                secilen_row = blok_match.iloc[0]
                secilen_kod = secilen_row['Kod']
                
                # Blok özelliklerini ayıkla
                blok_detay = ayikla_malzeme_detay(secilen_row['İsim'])
                
                if not blok_detay:
                    st.error("❌ Blok isminden ölçü ayıklanamadı."); st.stop()

                # 2. Excel listesinden bu bloğa uygun olan Üretim emrini bul
                # (Aynı Boy x En ölçüsündeki plaka emrini arıyoruz)
                def uygun_emir_mi(tanim):
                    d = ayikla_malzeme_detay(tanim)
                    if not d: return False
                    return abs(d['boy'] - blok_detay['boy']) < 0.1 and abs(d['en'] - blok_detay['en']) < 0.1

                uygun_emirler = df[df[tanim_col].apply(uygun_emir_mi)]

                if not uygun_emirler.empty:
                    with st.container(border=True):
                        st.subheader("📍 Kesim Planı")
                        # İlk uygun emri alalım (Veya operatöre seçtirelim)
                        emir = uygun_emirler.iloc[0]
                        emir_detay = ayikla_malzeme_detay(emir[tanim_col])
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.info(f"**Üretilecek:** {emir_detay['ozellik']}\n\n**Ölçü:** {emir_detay['boy']}x{emir_detay['en']} cm\n\n**Kalınlık:** {emir_detay['kalinlik']} cm")
                        with c2:
                            adet = float(emir.get('Miktar', 0))
                            net_tuketim = adet * (emir_detay['kalinlik'] if emir_detay['kalinlik'] else 0)
                            
                            # 🔥 OTOMATİK FİRE MANTIĞI
                            df_har = st.session_state['har_data']
                            daha_once_kesilmis = ((df_har['Kod'] == secilen_kod) & (df_har['İşlem'] == "KESİM/SARF")).any()
                            fire = 0.0 if daha_once_kesilmis else 2.0
                            toplam_dusulecek = net_tuketim + fire
                            
                            st.metric("Bloktan Düşecek", f"{toplam_dusulecek} cm", delta=f"Fire: {fire} cm")
                            st.write(f"**Blok Kalan (Şu an):** {secilen_row['Miktar']} cm")

                        if st.button("🔥 KESİMİ ONAYLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                            if secilen_row['Miktar'] < toplam_dusulecek:
                                st.error("❌ Stok yetersiz!"); st.stop()
                            
                            # Stok Güncelle
                            stok_df.loc[stok_df['Kod'] == secilen_kod, 'Miktar'] -= toplam_dusulecek
                            yeni_kalan = stok_df.loc[stok_df['Kod'] == secilen_kod, 'Miktar'].values[0]
                            
                            # Hareket Kaydı
                            yeni_har = pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "İşlem": "KESİM/SARF", "İş Emri": f"KESIM-{parti_barkod}",
                                "Kod": secilen_kod, "İsim": secilen_row['İsim'],
                                "Miktar": toplam_dusulecek, "Personel": "Bilal",
                                "Lot": parti_barkod, "Adres": secilen_row['Adres'], "Durum": "Kullanıldı"
                            }])
                            df_har_son = pd.concat([df_har, yeni_har], ignore_index=True)

                            veritabani.update_data("Stok", stok_df)
                            veritabani.update_data("Hareketler", df_har_son)
                            
                            st.balloons()
                            st.success(f"✅ İşlem Başarılı! Blok Kalan: {yeni_kalan} cm")
                            # Belleği temizle ve tazele
                            for k in ['stok_data', 'har_data']: del st.session_state[k]
                            st.rerun()
                else:
                    st.error(f"❌ Excel listesinde bu bloğa uygun ({blok_detay['boy']}x{blok_detay['en']}) bir kesim emri bulunamadı.")
            else:
                st.error("❌ Okutulan barkod stokta bulunamadı.")

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
