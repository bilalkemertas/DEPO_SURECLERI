import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- NAVİGASYON FONKSİYONLARI ---
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

    # --- 1. YÜKLEME ---
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
                    existing = existing[existing["İş Emri"] != is_emri_adi]
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success(f"✅ {is_emri_adi} güncellendi!"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (Geliştirilmiş Referans Sistemi) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        if 'local_stok' not in st.session_state: st.session_state.local_stok = veritabani.get_internal_data("Stok")
        if 'local_emirler' not in st.session_state: st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            s_list = st.multiselect("📋 İş Emri Seçin:", sorted(df_emirler["İş Emri"].unique().tolist()))
            
            if s_list:
                # GRUPLAMA: Ürün Kodu ve Mamül Adı eklendi
                sub_df = df_emirler[df_emirler["İş Emri"].isin(s_list)].copy()
                group_cols = ['İş Emri', 'Ürün Kodu', 'Mamül Adı', 'Stok Kodu', 'Stok Adı', 'Birim']
                pivot_df = sub_df.groupby(group_cols).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                pivot_df['Kalan'] = pivot_df['İhtiyaç Miktarı'] - pivot_df['Hazırlanan Adet']
                
                bekleyenler_df = pivot_df[pivot_df['Kalan'] > 0.01].copy()

                with st.container(border=True):
                    st.markdown("🔍 **Hazırlık Girişi**")
                    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
                    
                    if bekleyenler_df.empty:
                        st.success("✅ Bekleyen malzeme kalmadı!")
                    else:
                        # Seçim listesine Mamül bilgisi eklendi
                        secenekler = ["Seçiniz..."] + [
                            f"{r['İş Emri']} | {r['Mamül Adı']} | {r['Stok Kodu']} | {r['Stok Adı']}" 
                            for _, r in bekleyenler_df.iterrows()
                        ]
                        input_secim = p1.selectbox("📝 Malzeme Seçin:", secenekler)
                        
                        if input_secim != "Seçiniz...":
                            parts = input_secim.split(" | ")
                            sel_is_emri = parts[0]
                            sel_mamul_adi = parts[1]
                            sel_stok_kod = parts[2]
                            
                            # Tam eşleşme için Ürün/Mamül kriteri eklendi
                            row = bekleyenler_df[
                                (bekleyenler_df['İş Emri'] == sel_is_emri) & 
                                (bekleyenler_df['Mamül Adı'] == sel_mamul_adi) & 
                                (bekleyenler_df['Stok Kodu'] == sel_stok_kod)
                            ].iloc[0]
                            
                            sel_urun_kod = row['Ürün Kodu']
                            k_mik = row['Kalan']
                            p2.text_input("🎯 Kalan İhtiyaç:", value=f"{int(k_mik)} {row['Birim']}", disabled=True)
                            
                            # Stok Bilgileri
                            st_kod_c = next((c for c in df_stok_ana.columns if "Kod" in str(c)), "Kod")
                            st_adr_c = next((c for c in df_stok_ana.columns if "Adres" in str(c)), "Adres")
                            st_mik_c = next((c for c in df_stok_ana.columns if "Miktar" in str(c)), "Miktar")
                            
                            temp_stok = df_stok_ana[df_stok_ana[st_kod_c].astype(str).str.strip().str.upper() == str(sel_stok_kod).upper()]
                            toplam_depo_stok = temp_stok[st_mik_c].sum() if not temp_stok.empty else 0

                            adrs_list = ["Seçiniz..."]
                            if not temp_stok.empty:
                                active_adrs = temp_stok[temp_stok[st_mik_c] > 0][st_adr_c].unique().tolist()
                                adrs_list += sorted(active_adrs) if active_adrs else ["STOK YOK"]
                            else: adrs_list = ["STOK YOK"]

                            input_adr = p3.selectbox("📍 Raf Adresi:", adrs_list)
                            
                            if input_adr not in ["Seçiniz...", "STOK YOK"]:
                                r_stok = temp_stok[temp_stok[st_adr_c] == input_adr][st_mik_c].sum()
                                st.info(f"🏬 **Raf Mevcudu:** {int(r_stok)} | 🏢 **Toplam Depo:** {int(toplam_depo_stok)}")
                            
                            input_mik = p4.number_input("🔢 Verilen Miktar:", min_value=0.0)

                            if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                                if input_adr in ["Seçiniz...", "STOK YOK"]: st.error("Adres seçin!")
                                elif input_mik <= 0: st.error("Miktar girin!")
                                else:
                                    # Stok Güncelle
                                    mask_stok = (st.session_state.local_stok[st_kod_c].astype(str) == str(sel_stok_kod)) & (st.session_state.local_stok[st_adr_c] == input_adr)
                                    st.session_state.local_stok.loc[mask_stok, st_mik_c] -= input_mik
                                    
                                    # İş Emri Güncelle (Ürün Kodu kriteri eklendi)
                                    mask_emir = (
                                        (st.session_state.local_emirler['İş Emri'] == sel_is_emri) & 
                                        (st.session_state.local_emirler['Ürün Kodu'] == sel_urun_kod) & 
                                        (st.session_state.local_emirler['Stok Kodu'] == sel_stok_kod)
                                    )
                                    emir_indices = st.session_state.local_emirler[mask_emir].index
                                    
                                    d_kalan = input_mik
                                    for idx in emir_indices:
                                        if d_kalan <= 0: break
                                        bosluk = max(0, st.session_state.local_emirler.at[idx, 'İhtiyaç Miktarı'] - st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'])
                                        alinacak = min(d_kalan, bosluk)
                                        st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'] += alinacak
                                        d_kalan -= alinacak

                                    veritabani.update_data("Stok", st.session_state.local_stok)
                                    veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                    st.success("İşlem Başarılı!"); st.rerun()

                st.markdown("---")
                st.write("📊 **Hazırlık Durum Tablosu**")
                # Tablo artık Ürün bazlı detay veriyor
                st.dataframe(pivot_df.drop(columns=['Kalan']), use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_lh.empty:
            summary_df = df_lh.groupby("İş Emri").agg({"İhtiyaç Miktarı": "sum", "Hazırlanan Adet": "sum"}).reset_index()
            summary_df["Tamamlanma %"] = (summary_df["Hazırlanan Adet"] / summary_df["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
            
            st.markdown("### 📈 İş Emri Tamamlanma Durumu")
            st.dataframe(summary_df[["İş Emri", "Tamamlanma %"]], use_container_width=True, hide_index=True)
            
            st.divider()
            
            r_e = st.multiselect("📋 İş Emri Filtrele:", sorted(df_lh["İş Emri"].unique().tolist()))
            filtered = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            st.write("🔍 **Detaylı Malzeme Listesi**")
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered.to_excel(writer, index=False)
            st.download_button("📥 EXCEL RAPORU İNDİR", buffer.getvalue(), "Hazirlik_Raporu.xlsx", use_container_width=True)
