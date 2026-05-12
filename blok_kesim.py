import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def run_blok_kesim(conn):
    # --- 1. GELİŞMİŞ AYIKLAMA MOTORU ---
    def ayikla_karakter_ve_olcu(text):
        if pd.isna(text) or str(text).strip() == "": return None
        t = str(text).upper().strip()
        
        # Ölçü tespiti (Boy X En)
        olcu = re.search(r'(\d+)\s*[Xx]\s*(\d+)', t)
        boy = float(olcu.group(1)) if olcu else 0
        en = float(olcu.group(2)) if olcu else 0
        
        # Karakteristik özellikler (Dansite, Özellik, Renk)
        # Ölçüden önceki metin bloğunu alır
        karakter = t
        if olcu:
            karakter = t[:olcu.start()].strip()
            
        return {"boy": boy, "en": en, "karakter": karakter}

    # --- NAVİGASYON ---
    c_back1, c_back2, _ = st.columns([1.5, 1.5, 4])
    with c_back1:
        if st.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.page = 'home'
            st.rerun()
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
                df_raw = pd.read_excel(uploaded_file, header=None)
                baslik_satiri = 0
                for i in range(min(15, len(df_raw))):
                    vals = [str(v).upper().strip() for v in df_raw.iloc[i].fillna("").values]
                    if "STOK ADI" in vals or "BLOKCM" in vals:
                        baslik_satiri = i
                        break
                
                df_load = pd.read_excel(uploaded_file, header=baslik_satiri)
                df_load.columns = [str(c).strip() for c in df_load.columns]
                st.session_state['main_data'] = df_load
                
                # Veritabanından taze verileri çek
                st.session_state['stok_data'] = veritabani.get_internal_data("Stok")
                st.session_state['har_data'] = veritabani.get_internal_data("Hareketler")
                st.success(f"✅ Liste ve Stok verileri senkronize edildi.")
            except Exception as e:
                st.error(f"Teknik bir hata oluştu: {e}")

    # --- 3. OPERASYON EKRANI ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        
        # Sütun Tespitleri
        tanim_col = next((c for c in df.columns if "STOK ADI" in c.upper()), None)
        blok_olcu_col = next((c for c in df.columns if "BLOKCM" in c.upper()), None)
        miktar_col = next((c for c in df.columns if "ADET" in c.upper() or "MIKTAR" in c.upper()), None)

        if not tanim_col or not blok_olcu_col:
            st.error("❌ Excel'de 'Stok Adı' veya 'Blokcm' sütunları bulunamadı!"); st.stop()

        st.divider()
        parti_barkod = st.text_input("🔍 Kesilecek Blok Barkodunu Okutun:").strip()

        if parti_barkod:
            stok_df = st.session_state['stok_data']
            # Barkod eşleşmesi
            blok_match = stok_df[stok_df['Tedarikçi Barkod'].astype(str) == parti_barkod]
            
            if not blok_match.empty:
                secilen_blok = blok_match.iloc[0]
                blok_karakteristik = ayikla_karakter_ve_olcu(secilen_blok['İsim'])
                
                # --- YENİ KURGU: DANSİTE, ÖZELLİK VE RENK EŞLEŞMESİ ---
                def satir_uygun_mu(row):
                    # 1. Hata Kontrolü: Hücre boşsa atla
                    if pd.isna(row[tanim_col]) or pd.isna(row[blok_olcu_col]):
                        return False
                        
                    # 2. Karakteristik Ayıklama
                    plaka_info = ayikla_karakter_ve_olcu(row[tanim_col])
                    hedef_blok_olcu = ayikla_karakter_ve_olcu(row[blok_olcu_col])
                    
                    if not plaka_info or not hedef_blok_olcu:
                        return False
                    
                    # 3. Eşleşme Mantığı
                    # Karakter eşleşmesi (Dansite ve Renk blok isminde geçiyor mu?)
                    karakter_tamam = plaka_info['karakter'] in blok_karakteristik['karakter']
                    # Ölçü eşleşmesi (Excel'deki Blokcm ile okutulan blok tutuyor mu?)
                    olcu_tamam = abs(hedef_blok_olcu['boy'] - blok_karakteristik['boy']) < 2 and abs(hedef_blok_olcu['en'] - blok_karakteristik['en']) < 2
                    
                    return karakter_tamam and olcu_tamam

                # Filtreleme
                uygun_satirlar = df[df.apply(satir_uygun_mu, axis=1)]

                if not uygun_satirlar.empty:
                    with st.container(border=True):
                        st.subheader("🏭 Üretim Emri Eşleşti")
                        emir = uygun_satirlar.iloc[0]
                        
                        # Kalınlık ayıklama (Sondaki X rakamı)
                        plaka_match = re.search(r'X(\d+)$', str(emir[tanim_col]).upper().strip())
                        plaka_kalinlik = float(plaka_match.group(1)) if plaka_match else 0
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.success(f"**Okutulan Blok:**\n{secilen_blok['İsim']}")
                            st.info(f"**Üretilecek Plaka:**\n{emir[tanim_col]}")
                        
                        with c2:
                            adet_val = emir[miktar_col] if miktar_col else 0
                            adet = float(adet_val) if not pd.isna(adet_val) else 0
                            net_tuketim = adet * plaka_kalinlik
                            
                            # Fire hesabı
                            df_har = st.session_state['har_data']
                            daha_once_kesilmis = ((df_har['Kod'] == secilen_blok['Kod']) & (df_har['İşlem'] == "KESİM/SARF")).any()
                            fire = 0.0 if daha_once_kesilmis else 2.0
                            toplam_dusulecek = net_tuketim + fire
                            
                            st.metric("Bloktan Düşecek Yükseklik", f"{toplam_dusulecek} cm", delta=f"Fire: {fire} cm")
                            st.write(f"**Mevcut Blok Yüksekliği:** {secilen_blok['Miktar']} cm")

                        if st.button("🔥 KESİMİ ONAYLA (STOKTAN DÜŞ)", use_container_width=True, type="primary"):
                            if secilen_blok['Miktar'] < toplam_dusulecek:
                                st.error("❌ Blok yüksekliği yetersiz!"); st.stop()
                            
                            # Stok Güncelle
                            stok_df.loc[stok_df['Kod'] == secilen_blok['Kod'], 'Miktar'] -= toplam_dusulecek
                            
                            yeni_har = pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "İşlem": "KESİM/SARF", 
                                "İş Emri": f"KESIM-{parti_barkod}",
                                "Kod": secilen_blok['Kod'], 
                                "İsim": secilen_blok['İsim'],
                                "Miktar": toplam_dusulecek, 
                                "Personel": "Bilal",
                                "Lot": parti_barkod, 
                                "Adres": secilen_blok['Adres'], 
                                "Durum": "Kullanıldı"
                            }])
                            
                            veritabani.update_data("Stok", stok_df)
                            veritabani.update_data("Hareketler", pd.concat([df_har, yeni_har], ignore_index=True))
                            
                            st.balloons()
                            st.success("✅ Stok Güncellendi!")
                            for k in ['stok_data', 'har_data']: del st.session_state[k]
                            st.rerun()
                else:
                    st.error("❌ Bu bloğa uygun bir plaka emri kesim listesinde bulunamadı! (Dansite, Karakter veya Blokcm uyuşmuyor)")
            else:
                st.error("❌ Okutulan barkod stokta bulunamadı.")

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
