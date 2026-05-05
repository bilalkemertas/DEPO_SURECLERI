import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): st.session_state.uretim_page = 'menu'
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
        st.subheader("🏭 Üretim Hazırlık Merkezi")
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
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir:
                        baslik_satiri = i
                        break
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
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
                df_raw = df_raw.dropna(subset=['Stok Kodu'])
                df_final_save = df_raw[cols_target]
                if st.button("VERİTABANINA ŞİMDİ KAYDET", type="primary"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success("İş Emri Kaydedildi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (GİRİŞ PANELİ + TAM AD GÖSTERİMİ) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()
                
                pivot_df['Tamamlandi'] = (pivot_df['Hazırlanan Adet'] >= pivot_df['İhtiyaç Miktarı']).astype(int)
                pivot_df = pivot_df.sort_values(by=['Tamamlandi', 'Stok Adı'], ascending=[True, True])

                # Sütun İsimlerini Akıllıca Bulma
                s_cols = df_stok_ana.columns.tolist()
                stok_kod_col = next((c for c in s_cols if "Kod" in str(c)), None)
                stok_adr_col = next((c for c in s_cols if "Adres" in str(c)), None)
                stok_mik_col = next((c for c in s_cols if "Miktar" in str(c)), None)

                if not stok_kod_col or not stok_adr_col or not stok_mik_col:
                    st.error(f"⚠️ Stok tablosunda gerekli sütunlar bulunamadı! (Bulunanlar: {s_cols})")
                    return

                # --- ÜST GİRİŞ PANELİ ---
                with st.container(border=True):
                    st.markdown("🔍 **Saha Hazırlık Girişi**")
                    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
                    
                    bekleyen_isimler = sorted(pivot_df[pivot_df['Tamamlandi'] == 0]['Stok Adı'].unique().tolist())
                    input_isim = p1.selectbox("📝 Malzeme İsmi:", ["Seçiniz..."] + bekleyen_isimler)
                    
                    input_adr = "Seçiniz..."
                    current_stock_at_adr = 0
                    current_req = 0
                    current_prep = 0
                    selected_kod = ""
                    
                    if input_isim != "Seçiniz...":
                        row_info = pivot_df[pivot_df['Stok Adı'] == input_isim].iloc[0]
                        selected_kod = row_info['Stok Kodu']
                        current_req = row_info['İhtiyaç Miktarı']
                        current_prep = row_info['Hazırlanan Adet']
                        
                        # İhtiyaç Miktarı (Salt Okunur)
                        p2.text_input("📊 İhtiyaç:", value=f"{int(current_req)} {row_info['Birim']}", disabled=True)

                        temp_stok = df_stok_ana.copy()
                        temp_stok[stok_kod_col] = temp_stok[stok_kod_col].astype(str).str.strip().str.upper()
                        
                        valid_stocks = temp_stok[(temp_stok[stok_kod_col] == str(selected_kod).upper()) & (temp_stok[stok_mik_col] > 0)].sort_values(stok_adr_col)
                        adrs_list = valid_stocks[stok_adr_col].unique().tolist()
                        input_adr = p3.selectbox(f"📍 Adres:", ["Seçiniz..."] + adrs_list)
                        
                        if input_adr != "Seçiniz...":
                            current_stock_at_adr = valid_stocks[valid_stocks[stok_adr_col] == input_adr][stok_mik_col].sum()
                            
                            # Ürün Tam Adı ve Bilgi Satırı
                            st.write(f"🏷️ **Ürün:** {input_isim}")
                            st.write(f"📦 **Raf Stoğu:** `{int(current_stock_at_adr)}` | 🎯 **Kalan İhtiyaç:** `{int(current_req - current_prep)}`")
                    else:
                        p2.text_input("📊 İhtiyaç:", value="-", disabled=True)
                        p3.selectbox("📍 Adres:", ["Seçiniz..."], disabled=True)
                    
                    input_mik = p4.number_input("🔢 Miktar:", min_value=0.0, step=1.0)
                    
                    if st.button("⚡ HAREKETİ KAYDET", use_container_width=True, type="primary"):
                        if input_isim == "Seçiniz..." or input_adr == "Seçiniz...":
                            st.error("Lütfen malzeme ve adres seçiniz!")
                        elif input_mik <= 0:
                            st.error("Miktar 0'dan büyük olmalıdır!")
                        elif input_mik > current_stock_at_adr:
                            st.warning(f"⚠️ **{input_adr}** rafında sadece {int(current_stock_at_adr)} adet var!")
                        elif (current_prep + input_mik) > current_req:
                            st.error(f"🚫 Toplam ihtiyaçtan fazlasını alamazsınız!")
                        else:
                            df_stok_guncel = veritabani.get_internal_data("Stok")
                            df_hareketler_guncel = veritabani.get_internal_data("Hareketler")
                            all_is_emirleri = veritabani.get_internal_data("Is_Emirleri")
                            
                            df_stok_guncel[stok_kod_col] = df_stok_guncel[stok_kod_col].astype(str).str.strip().str.upper()
                            df_stok_guncel[stok_adr_col] = df_stok_guncel[stok_adr_col].astype(str).str.strip().str.upper()
                            
                            s_mask = (df_stok_guncel[stok_kod_col] == str(selected_kod).upper()) & (df_stok_guncel[stok_adr_col] == str(input_adr).upper())
                            df_stok_guncel.loc[s_mask, stok_mik_col] -= input_mik
                            
                            h_satir = {
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İşlem": "ÜRETİM HAZIRLIK",
                                "İş Emri": ", ".join(s_list),
                                "Kod": selected_kod,
                                "İsim": input_isim,
                                "Adres": input_adr,
                                "Miktar": input_mik,
                                "Personel": st.session_state.user
                            }
                            df_h = pd.concat([df_hareketler_guncel, pd.DataFrame([h_satir])], ignore_index=True)
                            
                            kalan = input_mik
                            emir_indices = all_is_emirleri[(all_is_emirleri['İş Emri'].astype(str).isin(s_list)) & (all_is_emirleri['Stok Kodu'] == selected_kod)].index
                            for idx in emir_indices:
                                if kalan <= 0: break
                                ihtiyac_tek = all_is_emirleri.at[idx, 'İhtiyaç Miktarı']
                                hazir_tek = all_is_emirleri.at[idx, 'Hazırlanan Adet']
                                bosluk = ihtiyac_tek - hazir_tek
                                alinacak = min(kalan, bosluk if bosluk > 0 else 0)
                                all_is_emirleri.at[idx, 'Hazırlanan Adet'] += alinacak
                                kalan -= alinacak

                            veritabani.update_data("Stok", df_stok_guncel)
                            veritabani.update_data("Hareketler", df_h)
                            veritabani.update_data("Is_Emirleri", all_is_emirleri)
                            
                            st.success(f"✅ Hazırlık kaydedildi!")
                            st.cache_data.clear(); st.rerun()

                st.markdown("---")
                st.dataframe(pivot_df.drop(columns=['Tamamlandi']), use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            r_e = st.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            st.dataframe(res, use_container_width=True, hide_index=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Rapor.xlsx", use_container_width=True)
