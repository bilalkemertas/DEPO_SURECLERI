import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    st.session_state.uretim_page = 'menu'
    if 'local_stok' in st.session_state: del st.session_state.local_stok
    if 'local_emirler' in st.session_state: del st.session_state.local_emirler

def go_is_emri(): st.session_state.uretim_page = 'is_emri'
def go_hazirlik(): st.session_state.uretim_page = 'hazirlik'
def go_rapor(): st.session_state.uretim_page = 'rapor'

def goster():
    if 'user' not in st.session_state or st.session_state.user is None:
        st.session_state.page = 'login'
        st.rerun()

    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): 
            go_home()
            st.rerun()
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. YÜKLEME (ffill ve Sekme Esnekliği) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Yeni İş Emri Yükle")
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file.sheet_names
                target_sheet = "HAZIRLIK" if "HAZIRLIK" in sheet_names else ("Sheet4" if "Sheet4" in sheet_names else None)

                if not target_sheet:
                    st.error(f"❌ Uygun sekme bulunamadı! Mevcutlar: {sheet_names}")
                    return

                df_raw = pd.read_excel(uploaded_file, sheet_name=target_sheet, header=None)
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir:
                        baslik_satiri = i
                        break
                
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                df_raw = df_raw.ffill() 

                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns: df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_final_save = df_raw.dropna(subset=['Stok Kodu'])[cols_target]
                st.dataframe(df_final_save, use_container_width=True, hide_index=True)

                if st.button("VERİTABANINA ŞİMDİ KAYDET", type="primary"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success(f"✅ {target_sheet} kaydedildi!"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (Kalan İhtiyaç Filtresi & Detaylar & Toplam Stok) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        if 'local_stok' not in st.session_state: st.session_state.local_stok = veritabani.get_internal_data("Stok")
        if 'local_emirler' not in st.session_state: st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emri Seçin:", emir_list)
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                
                # Kalanı hesapla
                pivot_df['Kalan'] = pivot_df['İhtiyaç Miktarı'] - pivot_df['Hazırlanan Adet']
                # KRİTİK: Sadece kalan ihtiyacı > 0 olanları listede tut
                bekleyenler = sorted(pivot_df[pivot_df['Kalan'] > 0.01]['Stok Adı'].unique().tolist())

                with st.container(border=True):
                    st.markdown("🔍 **Hazırlık Girişi**")
                    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
                    
                    if not bekleyenler:
                        st.success("✅ Seçilen iş emirlerinde bekleyen malzeme kalmadı!")
                    else:
                        input_isim = p1.selectbox("📝 Malzeme Seçin:", ["Seçiniz..."] + bekleyenler)
                        
                        if input_isim != "Seçiniz...":
                            row = pivot_df[pivot_df['Stok Adı'] == input_isim].iloc[0]
                            sel_kod = str(row['Stok Kodu']).strip().upper()
                            is_haya = sel_kod.startswith("HAYA")
                            
                            # 🎯 Kalan İhtiyaç Bilgisi
                            kalan_mik = row['Kalan']
                            p2.text_input("🎯 Kalan İhtiyaç:", value=f"{int(kalan_mik)} {row['Birim']}", disabled=True)
                            
                            st.write(f"🏷️ **Seçili Ürün:** {input_isim} ({sel_kod})")

                            # Stok Sütunlarını Yakala
                            stok_kod_col = next((c for c in df_stok_ana.columns if "Kod" in str(c)), "Kod")
                            stok_adr_col = next((c for c in df_stok_ana.columns if "Adres" in str(c)), "Adres")
                            stok_mik_col = next((c for c in df_stok_ana.columns if "Miktar" in str(c)), "Miktar")
                            
                            # Stok Filtreleme
                            temp_stok = df_stok_ana[df_stok_ana[stok_kod_col].astype(str).str.strip().str.upper() == sel_kod]
                            
                            # 🏢 Toplam Depo Stoğu (Adres bağımsız)
                            toplam_depo_stok = temp_stok[stok_mik_col].sum() if not temp_stok.empty else 0

                            adrs_list = ["Seçiniz..."]
                            if not temp_stok.empty:
                                active_adrs = temp_stok[temp_stok[stok_mik_col] > 0][stok_adr_col].unique().tolist()
                                adrs_list += sorted(active_adrs) if active_adrs else ["STOK YOK"]
                            else:
                                adrs_list = ["STOK YOK"]

                            input_adr = p3.selectbox("📍 Raf Adresi:", adrs_list)
                            
                            # 🏬 Raf Stoğu Bilgisi
                            raf_stok = 0
                            if input_adr not in ["Seçiniz...", "STOK YOK"]:
                                raf_stok = temp_stok[temp_stok[stok_adr_col] == input_adr][stok_mik_col].sum()
                                # TÜM DETAYLAR BURADA GÖSTERİLİYOR
                                st.info(f"🏬 **Raf Mevcudu:** {int(raf_stok)} | 🏢 **Toplam Depo Stoğu:** {int(toplam_depo_stok)} | 🎯 **Kalan İhtiyaç:** {int(kalan_mik)}")
                            else:
                                st.warning(f"🏢 **Toplam Depo Stoğu:** {int(toplam_depo_stok)} | 🎯 **Kalan İhtiyaç:** {int(kalan_mik)}")
                            
                            input_mik = p4.number_input("🔢 Verilen Miktar:", min_value=0.0, step=1.0)

                            if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                                if input_adr in ["Seçiniz...", "STOK YOK"] and not is_haya:
                                    st.error("Lütfen raf adresi seçin!")
                                elif input_mik <= 0:
                                    st.error("Miktar giriniz!")
                                elif not is_haya and input_mik > raf_stok:
                                    st.warning("Rafta o kadar ürün yok!")
                                else:
                                    # Stok Güncelleme
                                    mask = (st.session_state.local_stok[stok_kod_col].astype(str).str.strip().str.upper() == sel_kod) & \
                                           (st.session_state.local_stok[stok_adr_col] == input_adr)
                                    
                                    if is_haya: st.session_state.local_stok.loc[mask, stok_mik_col] += input_mik
                                    else: st.session_state.local_stok.loc[mask, stok_mik_col] -= input_mik
                                    
                                    # İş Emrine Dağıt
                                    d_kalan = input_mik
                                    emir_idx = st.session_state.local_emirler[(st.session_state.local_emirler['İş Emri'].isin(s_list)) & \
                                                                              (st.session_state.local_emirler['Stok Kodu'] == row['Stok Kodu'])].index
                                    for idx in emir_idx:
                                        if d_kalan <= 0: break
                                        bosluk = max(0, st.session_state.local_emirler.at[idx, 'İhtiyaç Miktarı'] - st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'])
                                        alinacak = min(d_kalan, bosluk)
                                        st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'] += alinacak
                                        d_kalan -= alinacak

                                    veritabani.update_data("Stok", st.session_state.local_stok)
                                    veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                    st.success("İşlem başarıyla kaydedildi!"); st.rerun()

                st.markdown("---")
                st.write("📊 **Genel Durum Tablosu**")
                st.dataframe(pivot_df.drop(columns=['Kalan']), use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            c1, c2 = st.columns(2)
            r_e = c1.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            filtered = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered.to_excel(writer, index=False)
            st.download_button("📥 EXCEL OLARAK İNDİR", buffer.getvalue(), "Hazirlik_Raporu.xlsx", use_container_width=True)
