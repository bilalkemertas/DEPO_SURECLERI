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
    # Menüye dönünce belleği temizle ki bir sonraki girişte taze veri çeksin
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

    # --- 2. OPERASYON ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        if 'local_stok' not in st.session_state:
            with st.spinner("Stok Verileri Çekiliyor..."):
                st.session_state.local_stok = veritabani.get_internal_data("Stok")
        
        if 'local_emirler' not in st.session_state:
            with st.spinner("İş Emirleri Çekiliyor..."):
                st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                # --- SABİT GENEL DURUM TABLOSU ---
                st.markdown("### 📈 İş Emri Genel Durumu")
                status_df = sub_df.groupby(['İş Emri', 'Ürün Kodu', 'Mamül Adı']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()
                status_df['İlerleme %'] = ((status_df['Hazırlanan Adet'] / status_df['İhtiyaç Miktarı']) * 100).fillna(0).astype(int)
                st.dataframe(status_df, use_container_width=True, hide_index=True)
                st.markdown("---")

                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()
                
                pivot_df['Tamamlandi'] = (pivot_df['Hazırlanan Adet'] >= pivot_df['İhtiyaç Miktarı']).astype(int)
                pivot_df = pivot_df.sort_values(by=['Tamamlandi', 'Stok Adı'], ascending=[True, True])

                s_cols = df_stok_ana.columns.tolist()
                stok_kod_col = next((c for c in s_cols if "Kod" in str(c)), None)
                stok_adr_col = next((c for c in s_cols if "Adres" in str(c)), None)
                stok_mik_col = next((c for c in s_cols if "Miktar" in str(c)), None)

                if not stok_kod_col or not stok_adr_col or not stok_mik_col:
                    st.error(f"⚠️ Stok tablosunda gerekli sütunlar bulunamadı!")
                    return

                with st.container(border=True):
                    st.markdown("🔍 **Üretim Hazırlık Girişi**")
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
                        
                        p2.text_input("📊 İhtiyaç:", value=f"{int(current_req)} {row_info['Birim']}", disabled=True)

                        temp_stok = df_stok_ana.copy()
                        temp_stok[stok_kod_col] = temp_stok[stok_kod_col].astype(str).str.strip().str.upper()
                        
                        valid_stocks = temp_stok[(temp_stok[stok_kod_col] == str(selected_kod).upper()) & (temp_stok[stok_mik_col] > 0)].sort_values(stok_adr_col)
                        
                        st.write(f"🏷️ **Ürün:** {input_isim}")
                        kalan_yazi = int(current_req - current_prep)
                        
                        if not valid_stocks.empty:
                            adrs_list = valid_stocks[stok_adr_col].unique().tolist()
                            input_adr = p3.selectbox(f"📍 Adres:", ["Seçiniz..."] + adrs_list)
                            
                            if input_adr != "Seçiniz...":
                                current_stock_at_adr = valid_stocks[valid_stocks[stok_adr_col] == input_adr][stok_mik_col].sum()
                                st.write(f"📦 **Raf Stoğu:** `{int(current_stock_at_adr)}` | 🎯 **Kalan İhtiyaç:** `{kalan_yazi}`")
                            else:
                                st.write(f"📦 **Raf Stoğu:** `-` | 🎯 **Kalan İhtiyaç:** `{kalan_yazi}`")
                        else:
                            p3.selectbox("📍 Adres:", ["STOK YOK"], disabled=True)
                            st.write(f"📦 **Raf Stoğu:** `0` | 🎯 **Kalan İhtiyaç:** `{kalan_yazi}`")
                    else:
                        p2.text_input("📊 İhtiyaç:", value="-", disabled=True)
                        p3.selectbox("📍 Adres:", ["Seçiniz..."], disabled=True)
                    
                    input_mik = p4.number_input("🔢 Miktar:", min_value=0.0, step=1.0)
                    
                    if st.button("⚡ HAREKETİ KAYDET", use_container_width=True, type="primary"):
                        if input_isim == "Seçiniz..." or input_adr in ["Seçiniz...", "STOK YOK"]:
                            st.error("Lütfen geçerli malzeme ve stoklu bir adres seçiniz!")
                        elif input_mik <= 0:
                            st.error("Miktar 0'dan büyük olmalıdır!")
                        elif input_mik > current_stock_at_adr:
                            st.warning(f"⚠️ Adres stoğu yetersiz!")
                        elif (current_prep + input_mik) > current_req:
                            st.error(f"🚫 İhtiyaçtan fazlasını alamazsınız!")
                        else:
                            # Kayıt İşlemleri
                            mask_stok = (st.session_state.local_stok[stok_kod_col].astype(str).str.strip().str.upper() == str(selected_kod).upper()) & \
                                        (st.session_state.local_stok[stok_adr_col].astype(str).str.strip().str.upper() == str(input_adr).upper())
                            st.session_state.local_stok.loc[mask_stok, stok_mik_col] -= input_mik
                            
                            kalan = input_mik
                            emir_indices = st.session_state.local_emirler[(st.session_state.local_emirler['İş Emri'].astype(str).isin(s_list)) & \
                                                                         (st.session_state.local_emirler['Stok Kodu'] == selected_kod)].index
                            for idx in emir_indices:
                                if kalan <= 0: break
                                iht_tek = st.session_state.local_emirler.at[idx, 'İhtiyaç Miktarı']
                                haz_tek = st.session_state.local_emirler.at[idx, 'Hazırlanan Adet']
                                bosluk = iht_tek - haz_tek
                                alinacak = min(kalan, bosluk if bosluk > 0 else 0)
                                st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'] += alinacak
                                kalan -= alinacak
                            
                            df_h_eski = veritabani.get_internal_data("Hareketler")
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
                            df_h_yeni = pd.concat([df_h_eski, pd.DataFrame([h_satir])], ignore_index=True)

                            with st.status("Veriler Senkronize Ediliyor...", expanded=False) as status:
                                veritabani.update_data("Stok", st.session_state.local_stok)
                                veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                veritabani.update_data("Hareketler", df_h_yeni)
                                status.update(label="Kayıt Başarılı!", state="complete")
                            
                            st.success(f"✅ {input_isim} başarıyla hazırlandı.")
                            st.rerun()

                st.markdown("---")
                st.dataframe(pivot_df.drop(columns=['Tamamlandi']), use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            # Filtreleme Paneli
            c1, c2 = st.columns(2)
            r_e = c1.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            
            # İş emrine göre ürünleri filtrele
            filtered_by_emir = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            r_p = c2.multiselect("📦 Ana Ürün (Mamül) Seç:", sorted(filtered_by_emir["Ürün Kodu"].unique().tolist()))
            
            # Nihai Filtreleme
            res = filtered_by_emir
            if r_p:
                res = res[res["Ürün Kodu"].isin(r_p)]
                
            st.dataframe(res, use_container_width=True, hide_index=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Rapor.xlsx", use_container_width=True)
