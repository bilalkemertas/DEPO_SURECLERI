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
        # Ölçü tespiti (Örn: 200X180X20 veya 200X180)
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
                # Başlıklardaki gizli boşlukları temizle
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
        
        # --- [FIX] ZIRHLI SÜTUN TESPİTİ ---
        # Senin Excel'indeki "Stok Adı" veya alternatifleri akıllıca tarar
        tanim_col = next((c for c in df.columns if any(x in c.upper() for x in ["STOK ADI", "TANIM", "MALZEME"])), None)
        miktar_col = next((c for c in df.columns if any(x in c.upper() for x in ["ADET", "MİKTAR", "MIKTAR"])), None)

        if not tanim_col:
            st.error("❌ Excel'de 'Stok Adı' veya 'Tanım' sütunu bulunamadı! Lütfen dosyanızı kontrol edin."); st.stop()

        st.divider()
        st.caption(f"📍 Sistem Eşleşmesi: [Ürün Sütunu: {tanim_col}] | [Miktar Sütunu: {miktar_col if miktar_col else 'Bulunamadı'}]")
        
        parti_barkod = st.text_input("🔍 Kesilecek Blok/Parti Barkodunu Okutun:").strip()

        if parti_barkod:
            stok_df = st.session_state['stok_data']
            if 'Tedarikçi Barkod' not in stok_df.columns:
                st.error("❌ Stok tablosunda 'Tedarikçi Barkod' sütunu bulunamadı!"); st.stop()
            
            blok_match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == parti_barkod]
            
            if not blok_match.empty:
                secilen_row = blok_match.iloc[0]
                secilen_kod = secilen_row['Kod']
                
                blok_detay = ayikla_malzeme_detay(secilen_row['İsim'])
                
                if not blok_detay:
                    st.error("❌ Blok isminden ölçü ayıklanamadı (Örn: 200X180X20 olmalı)."); st.stop()

                # Excel listesinden uygun emri bul
                def uygun_emir_mi(tanim):
                    d = ayikla_malzeme_detay(tanim)
                    if not d: return False
                    # Ölçüler %99 tutuyorsa eşleştir
                    return abs(d['boy'] - blok_detay['boy']) < 0.1 and abs(d['en'] - blok_detay['en']) < 0.1

                # FIX: tanim_col artık güvenli bir şekilde tespit edildiği için KeyError vermez
                uygun_emirler = df[df[tanim_col].apply(uygun_emir_mi)]

                if not uygun_emirler.empty:
                    with st.container(border=True):
                        st.subheader("📍 Kesim Planı")
                        emir = uygun_emirler.iloc[0]
                        emir_detay = ayikla_malzeme_detay(emir[tanim_col])
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.info(f"**Üretilecek:** {emir_detay['ozellik']}\n\n**Ölçü:** {emir_detay['boy']}x{emir_detay['en']} cm\n\n**Kalınlık:** {emir_detay['kalinlik']} cm")
                        
                        with c2:
                            # Miktar tespiti (Adet veya Miktar sütunundan)
                            adet = float(emir[miktar_col]) if miktar_col and not pd.isna(emir[miktar_col]) else 0.0
                            net_tuketim = adet * (emir_detay['kalinlik'] if emir_detay['kalinlik'] else 0)
                            
                            df_har = st.session_state['har_data']
                            daha_once_kesilmis = ((df_har['Kod'] == secilen_kod) & (df_har['İşlem'] == "KESİM/SARF")).any()
                            fire = 0.0 if daha_once_kesilmis else 2.0
                            toplam_dusulecek = net_tuketim + fire
                            
                            st.metric("Bloktan Düşecek", f"{toplam_dusulecek} cm", delta=f"Fire: {fire} cm")
                            st.write(f"**Blok Kalan (Şu an):** {secilen_row['Miktar']} cm")

                        if st.button("🔥 KESİMİ ONAYLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                            if secilen_row['Miktar'] < toplam_dusulecek:
                                st.error("❌ Stok yetersiz!"); st.stop()
                            
                            stok_df.loc[stok_df['Kod'] == secilen_kod, 'Miktar'] -= toplam_dusulecek
                            yeni_kalan = stok_df.loc[stok_df['Kod'] == secilen_kod, 'Miktar'].values[0]
                            
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
                            
                            # Önbelleği temizle ve sayfayı yenile
                            for k in ['stok_data', 'har_data']: 
                                if k in st.session_state: del st.session_state[k]
                            st.rerun()
                else:
                    st.error(f"❌ Excel listesinde bu bloğa uygun ({blok_detay['boy']}x{blok_detay['en']}) bir kesim emri bulunamadı.")
            else:
                st.error("❌ Okutulan barkod stokta bulunamadı.")

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
