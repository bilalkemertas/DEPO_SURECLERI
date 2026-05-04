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

def go_is_emri():
    st.session_state.uretim_page = 'is_emri'

def go_hazirlik():
    st.session_state.uretim_page = 'hazirlik'

def go_rapor():
    st.session_state.uretim_page = 'rapor'

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
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
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
                
                if "Mamül Kodu" in df_raw.columns:
                    df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                
                # İhtiyaç miktarını bul
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns:
                        df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_raw = df_raw.dropna(subset=['Stok Kodu'])
                df_final_save = df_raw[cols_target]
                
                if st.button("VERİTABANINA ŞİMDİ KAYDET", type="primary"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success("İş Emri Kaydedildi!")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

    # --- 2. OPERASYON ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                dashboard_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                with st.container(border=True):
                    st.markdown("🔍 **Akıllı Arama ve Filtreleme**")
                    f1, f2, f3 = st.columns(3)
                    f_adr = f1.text_input("📍 Adres Filtre:")
                    f_kod = f2.text_input("📦 Kod Filtre:")
                    f_isi = f3.text_input("📝 İsim Filtre:")
                
                def get_best_adr(kod):
                    clean_kod = str(kod).strip()
                    if 'Kod' in df_stok_ana.columns:
                        temp_stok = df_stok_ana.copy()
                        temp_stok['Kod'] = temp_stok['Kod'].astype(str).str.strip()
                        res = temp_stok[temp_stok['Kod'] == clean_kod]
                        return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                    return "STOK YOK"
                
                dashboard_df["Alınacak Adres"] = dashboard_df["Stok Kodu"].apply(get_best_adr)
                
                filtered = dashboard_df.copy()
                if f_adr: filtered = filtered[filtered["Alınacak Adres"].str.contains(f_adr, case=False, na=False)]
                if f_kod: filtered = filtered[filtered["Stok Kodu"].astype(str).str.contains(f_kod, case=False, na=False)]
                if f_isi: filtered = filtered[filtered["Stok Adı"].astype(str).str.contains(f_isi, case=False, na=False)]
                
                filtered['Doluluk %'] = (filtered['Hazırlanan Adet'] / filtered['İhtiyaç Miktarı'] * 100).round(1).fillna(0)

                st.markdown(f"#### 📝 Hazırlık Detay Listesi ({len(filtered)} Kalem)")
                edited_df = st.data_editor(
                    filtered,
                    column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                    disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                    hide_index=True,
                    use_container_width=True,
                    key="hazirlik_editor"
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    all_data = veritabani.get_internal_data("Is_Emirleri")
                    df_stok_guncel = veritabani.get_internal_data("Stok")
                    df_hareketler = veritabani.get_internal_data("Hareketler")
                    
                    df_stok_guncel['Kod'] = df_stok_guncel['Kod'].astype(str).str.strip()
                    df_stok_guncel['Adres'] = df_stok_guncel['Adres'].astype(str).str.strip()
                    df_stok_guncel['Miktar'] = pd.to_numeric(df_stok_guncel['Miktar'], errors='coerce').fillna(0)
                    
                    yeni_loglar = []
                    
                    for i, row in edited_df.iterrows():
                        mask = (all_data["İş Emri"].astype(str) == str(row["İş Emri"])) & \
                               (all_data["Stok Kodu"].astype(str).str.strip() == str(row["Stok Kodu"]).strip()) & \
                               (all_data["Mamül Adı"].astype(str) == str(row["Mamül Adı"]))
                        
                        if mask.any():
                            # HATALI KISIM BURADA DÜZELTİLDİ: .fillna(0) kaldırıldı, manuel kontrol eklendi
                            eski_haz_val = pd.to_numeric(all_data.loc[mask, "Hazırlanan Adet"], errors='coerce').values[0]
                            eski_haz = 0 if pd.isna(eski_haz_val) else eski_haz_val
                            
                            yeni_haz_val = pd.to_numeric(row["Hazırlanan Adet"], errors='coerce')
                            yeni_haz = 0 if pd.isna(yeni_haz_val) else yeni_haz_val
                            
                            fark = yeni_haz - eski_haz
                            
                            if fark != 0:
                                s_kod = str(row["Stok Kodu"]).strip()
                                s_adr = str(row["Alınacak Adres"]).strip()
                                stok_mask = (df_stok_guncel["Kod"] == s_kod) & (df_stok_guncel["Adres"] == s_adr)
                                
                                if stok_mask.any():
                                    mevcut = df_stok_guncel.loc[stok_mask, "Miktar"].values[0]
                                    df_stok_guncel.loc[stok_mask, "Miktar"] = max(0, mevcut - fark)
                                    
                                    yeni_loglar.append({
                                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "İşlem": "ÜRETİM HAZIRLIK",
                                        "İş Emri": row["İş Emri"],
                                        "Kod": s_kod,
                                        "İsim": row["Stok Adı"],
                                        "Adres": s_adr,
                                        "Miktar": fark,
                                        "Personel": st.session_state.user if 'user' in st.session_state else "Sistem"
                                    })
                            
                            all_data.loc[mask, "Hazırlanan Adet"] = yeni_haz

                    veritabani.update_data("Is_Emirleri", all_data)
                    veritabani.update_data("Stok", df_stok_guncel)
                    
                    if yeni_loglar:
                        df_extre_son = pd.concat([df_hareketler, pd.DataFrame(yeni_loglar)], ignore_index=True)
                        veritabani.update_data("Hareketler", df_extre_son)

                    st.success("Stoklar güncellendi ve hareketler kaydedildi!")
                    st.cache_data.clear()
                    st.rerun()

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            with st.container(border=True):
                r_e = st.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
                rf1, rf2 = st.columns(2)
                f_kod_r = rf1.text_input("📦 Kod Ara:", key="rkod")
                f_isi_r = rf2.text_input("📝 İsim Ara:", key="risi")
            
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            if f_kod_r: res = res[res["Stok Kodu"].astype(str).str.contains(f_kod_r, case=False, na=False)]
            if f_isi_r: res = res[res["Stok Adı"].astype(str).str.contains(f_isi_r, case=False, na=False)]
            
            res['İhtiyaç Miktarı'] = pd.to_numeric(res['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            res['Hazırlanan Adet'] = pd.to_numeric(res['Hazırlanan Adet'], errors='coerce').fillna(0)
            res['Kalan'] = res['İhtiyaç Miktarı'] - res['Hazırlanan Adet']
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam İhtiyaç", f"{int(res['İhtiyaç Miktarı'].sum())}")
            m2.metric("Toplam Hazırlanan", f"{int(res['Hazırlanan Adet'].sum())}")
            m3.metric("Bekleyen", f"{int(res['Kalan'].sum())}")
            
            st.dataframe(res, use_container_width=True, hide_index=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Uretim_Raporu.xlsx", use_container_width=True)
