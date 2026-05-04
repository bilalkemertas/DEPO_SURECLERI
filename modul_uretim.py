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

    # --- 2. OPERASYON (Gelişmiş Hareket Bazlı Sorgu) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        df_hareketler_ana = veritabani.get_internal_data("Hareketler")
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                dashboard_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                def get_best_adr(kod):
                    clean_kod = str(kod).strip().upper()
                    if 'Kod' in df_stok_ana.columns:
                        temp_stok = df_stok_ana.copy()
                        temp_stok['Kod'] = temp_stok['Kod'].astype(str).str.strip().str.upper()
                        res = temp_stok[temp_stok['Kod'] == clean_kod]
                        return str(res.iloc[0]['Adres']).strip().upper() if not res.empty else "STOK YOK"
                    return "STOK YOK"
                
                dashboard_df["Alınacak Adres"] = dashboard_df["Stok Kodu"].apply(get_best_adr)
                dashboard_df['Doluluk %'] = (dashboard_df['Hazırlanan Adet'] / dashboard_df['İhtiyaç Miktarı'] * 100).round(1).fillna(0)

                st.markdown(f"#### 📝 Hazırlık Detay Listesi ({len(dashboard_df)} Kalem)")
                edited_df = st.data_editor(
                    dashboard_df,
                    column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                    disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                    hide_index=True,
                    use_container_width=True,
                    key="hazirlik_editor"
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    all_data = veritabani.get_internal_data("Is_Emirleri")
                    df_stok_guncel = veritabani.get_internal_data("Stok")
                    df_hareketler_guncel = veritabani.get_internal_data("Hareketler")
                    
                    df_stok_guncel['Kod'] = df_stok_guncel['Kod'].astype(str).str.strip().str.upper()
                    df_stok_guncel['Adres'] = df_stok_guncel['Adres'].astype(str).str.strip().str.upper()
                    df_stok_guncel['Miktar'] = pd.to_numeric(df_stok_guncel['Miktar'], errors='coerce').fillna(0)
                    
                    yeni_loglar = []
                    degisiklik_var_mi = False
                    
                    for i, row in edited_df.iterrows():
                        # --- HAREKETLER SEKMESİNDEN TOPLAM ÇIKIŞI SORGULA ---
                        s_emir = str(row["İş Emri"]).strip()
                        s_kod = str(row["Stok Kodu"]).strip().upper()
                        s_adr = str(row["Alınacak Adres"]).strip().upper()
                        
                        mask_hareket = (df_hareketler_guncel['İş Emri'].astype(str) == s_emir) & \
                                       (df_hareketler_guncel['Kod'].astype(str).str.strip().str.upper() == s_kod)
                        
                        # Bu iş emri için Hareketler sekmesine yazılmış toplam miktar
                        eski_hareket_toplami = pd.to_numeric(df_hareketler_guncel[mask_hareket]['Miktar'], errors='coerce').sum()
                        
                        # Ekranda girilen yeni hedef miktar
                        try:
                            v_yeni = round(float(row["Hazırlanan Adet"]), 2)
                        except:
                            v_yeni = eski_hareket_toplami

                        # Fark (Hareketler sekmesine yeni eklenecek miktar)
                        fark = round(v_yeni - eski_hareket_toplami, 2)

                        if fark != 0:
                            degisiklik_var_mi = True
                            
                            # 1. HAREKET KAYDI OLUŞTUR
                            yeni_loglar.append({
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "İşlem": "ÜRETİM HAZIRLIK",
                                "İş Emri": s_emir,
                                "Kod": s_kod,
                                "İsim": str(row["Stok Adı"]),
                                "Adres": s_adr,
                                "Miktar": fark,
                                "Personel": st.session_state.user if 'user' in st.session_state else "Sistem"
                            })
                            
                            # 2. STOKTAN DÜŞÜŞ (Sadece adres STOK YOK değilse)
                            if s_adr != "STOK YOK":
                                stok_mask = (df_stok_guncel["Kod"] == s_kod) & (df_stok_guncel["Adres"] == s_adr)
                                if stok_mask.any():
                                    mevcut = df_stok_guncel.loc[stok_mask, "Miktar"].values[0]
                                    # Kural: Stok eksiye düşmesin
                                    df_stok_guncel.loc[stok_mask, "Miktar"] = max(0, mevcut - fark)
                            
                            # 3. ANA VERİ TABLOSUNU GÜNCELLE (Görsel tutarlılık için)
                            mask_emir = (all_data["İş Emri"].astype(str) == s_emir) & \
                                        (all_data["Stok Kodu"].astype(str).str.strip().str.upper() == s_kod)
                            if mask_emir.any():
                                all_data.loc[mask_emir, "Hazırlanan Adet"] = v_yeni

                    if degisiklik_var_mi:
                        veritabani.update_data("Is_Emirleri", all_data)
                        veritabani.update_data("Stok", df_stok_guncel)
                        
                        if yeni_loglar:
                            df_final_hareket = pd.concat([df_hareketler_guncel, pd.DataFrame(yeni_loglar)], ignore_index=True)
                            veritabani.update_data("Hareketler", df_final_hareket)
                            st.success(f"✅ {len(yeni_loglar)} hareket işlendi. Hareketler sekmesi baz alınarak stoklar güncellendi.")
                    else:
                        st.info("ℹ️ Hareketler sekmesindeki toplam ile girilen miktar aynı. İşlem yapılmadı.")

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
            r_e = st.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            st.dataframe(res, use_container_width=True, hide_index=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Rapor.xlsx", use_container_width=True)
