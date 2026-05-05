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

    # --- 0. MENÜ ---
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

                # --- ÖĞE ETİKETLERİNİ YİNELE ---
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

    # --- 2. OPERASYON (Geri Gelen Bilgilendirme Ekranı) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        if 'local_stok' not in st.session_state: st.session_state.local_stok = veritabani.get_internal_data("Stok")
        if 'local_emirler' not in st.session_state: st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                pivot_df['Tamamlandi'] = (pivot_df['Hazırlanan Adet'] >= pivot_df['İhtiyaç Miktarı']).astype(int)
                pivot_df = pivot_df.sort_values(by=['Tamamlandi', 'Stok Adı'], ascending=[True, True])

                with st.container(border=True):
                    st.markdown("🔍 **Üretim Hazırlık Girişi**")
                    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
                    bekleyenler = sorted(pivot_df[pivot_df['Tamamlandi'] == 0]['Stok Adı'].unique().tolist())
                    input_isim = p1.selectbox("📝 Malzeme İsmi:", ["Seçiniz..."] + bekleyenler)
                    
                    if input_isim != "Seçiniz...":
                        row = pivot_df[pivot_df['Stok Adı'] == input_isim].iloc[0]
                        sel_kod = row['Stok Kodu']
                        is_haya = str(sel_kod).upper().startswith("HAYA")
                        
                        # --- İhtiyaç ve Ürün Bilgisi ---
                        p2.text_input("📊 İhtiyaç:", value=f"{int(row['İhtiyaç Miktarı'])} {row['Birim']}", disabled=True)
                        st.write(f"🏷️ **Ürün:** {input_isim}")
                        kalan_mik = int(row['İhtiyaç Miktarı'] - row['Hazırlanan Adet'])

                        # --- Adres ve Stok Bilgisi ---
                        stok_kod_col = next((c for c in df_stok_ana.columns if "Kod" in c), "Kod")
                        stok_adr_col = next((c for c in df_stok_ana.columns if "Adres" in c), "Adres")
                        stok_mik_col = next((c for c in df_stok_ana.columns if "Miktar" in c), "Miktar")
                        
                        temp_stok = df_stok_ana[df_stok_ana[stok_kod_col].astype(str) == str(sel_kod)]
                        adrs_list = ["Seçiniz..."] + (temp_stok[stok_adr_col].unique().tolist() if not temp_stok.empty else ["STOK YOK"])
                        input_adr = p3.selectbox("📍 Adres:", adrs_list)
                        
                        # --- Raf Stoğu Gösterimi ---
                        if input_adr not in ["Seçiniz...", "STOK YOK"]:
                            raf_stok = temp_stok[temp_stok[stok_adr_col] == input_adr][stok_mik_col].sum()
                            st.write(f"📦 **Raf Stoğu:** `{int(raf_stok)}` | 🎯 **Kalan İhtiyaç:** `{kalan_mik}`")
                        else:
                            st.write(f"📦 **Raf Stoğu:** `-` | 🎯 **Kalan İhtiyaç:** `{kalan_mik}`")

                        input_mik = p4.number_input("🔢 Miktar:", min_value=0.0, step=1.0)

                        if st.button("⚡ HAREKETİ KAYDET", use_container_width=True, type="primary"):
                            if input_adr in ["Seçiniz...", "STOK YOK"]: st.error("Geçerli adres seçin!")
                            elif input_mik <= 0: st.error("Miktar girin!")
                            elif not is_haya and input_mik > raf_stok: st.warning("Stok yetersiz!")
                            else:
                                # Kayıt
                                mask = (st.session_state.local_stok[stok_kod_col].astype(str) == str(sel_kod)) & (st.session_state.local_stok[stok_adr_col] == input_adr)
                                if is_haya: st.session_state.local_stok.loc[mask, stok_mik_col] += input_mik
                                else: st.session_state.local_stok.loc[mask, stok_mik_col] -= input_mik
                                
                                # İş emri dağıtımı
                                d_kalan = input_mik
                                emir_indices = st.session_state.local_emirler[(st.session_state.local_emirler['İş Emri'].isin(s_list)) & (st.session_state.local_emirler['Stok Kodu'] == sel_kod)].index
                                for idx in emir_indices:
                                    if d_kalan <= 0: break
                                    bosluk = max(0, st.session_state.local_emirler.at[idx, 'İhtiyaç Miktarı'] - st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'])
                                    alinacak = min(d_kalan, bosluk)
                                    st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'] += alinacak
                                    d_kalan -= alinacak

                                veritabani.update_data("Stok", st.session_state.local_stok)
                                veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                st.success("Hazırlık Kaydedildi!"); st.rerun()

                st.markdown("---")
                st.dataframe(pivot_df.drop(columns=['Tamamlandi']), use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            c1, c2 = st.columns(2)
            r_e = c1.multiselect("📋 İş Emri:", sorted(df_lh["İş Emri"].unique().tolist()))
            filtered = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            r_p = c2.multiselect("📦 Ana Ürün:", sorted(filtered["Mamül Adı"].unique().tolist()))
            if r_p: filtered = filtered[filtered["Mamül Adı"].isin(r_p)]
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer: filtered.to_excel(writer, index=False)
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Rapor.xlsx", use_container_width=True)
