import streamlit as st
import pandas as pd
import veritabani

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
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
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
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        
        if not df_emirler.empty:
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                filtered = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                mamul_list = sorted(filtered["Mamül Adı"].astype(str).unique().tolist())
                m_sec = st.multiselect("🏗️ Mamül Adı Filtrele:", mamul_list)
                if m_sec:
                    filtered = filtered[filtered["Mamül Adı"].astype(str).isin(m_sec)]
                
                def get_best_adr(kod):
                    if 'Kod' in df_stok_ana.columns:
                        res = df_stok_ana[df_stok_ana['Kod'].astype(str) == str(kod)]
                        return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                    return "STOK YOK"
                filtered["Alınacak Adres"] = filtered["Stok Kodu"].apply(get_best_adr)
                
                # Doluluk hesaplama sütunu (Görsel amaçlı)
                filtered['Doluluk %'] = (pd.to_numeric(filtered['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                         pd.to_numeric(filtered['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)

                st.markdown("#### 📝 Hazırlık Detay Listesi")
                
                # Tablo Düzenleme
                edited_df = st.data_editor(
                    filtered,
                    column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                    disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                    hide_index=True,
                    use_container_width=True,
                    key="hazirlik_editor"
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    # Veritabanını tekrar oku (En güncel hali)
                    all_data = veritabani.get_internal_data("Is_Emirleri")
                    
                    # KAYDETME STRATEJİSİ GÜNCELLENDİ:
                    # Satır bazlı birebir eşleştirme (İş Emri + Stok Kodu + Mamül Adı)
                    for i, row in edited_df.iterrows():
                        mask = (all_data["İş Emri"].astype(str) == str(row["İş Emri"])) & \
                               (all_data["Stok Kodu"].astype(str) == str(row["Stok Kodu"])) & \
                               (all_data["Mamül Adı"].astype(str) == str(row["Mamül Adı"]))
                        
                        if mask.any():
                            # Sadece ilgili satırın Hazırlanan Adet değerini güncelle
                            all_data.loc[mask, "Hazırlanan Adet"] = row["Hazırlanan Adet"]

                    # Veriyi GSheets'e geri bas
                    veritabani.update_data("Is_Emirleri", all_data)
                    st.success("Veriler başarıyla eşitlendi!")
                    st.cache_data.clear()
                    st.rerun()

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu ve Arşiv")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            r_e = st.multiselect("📋 İş Emri Süz:", sorted(df_lh["İş Emri"].unique().tolist()))
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            res['Doluluk %'] = (pd.to_numeric(res['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                pd.to_numeric(res['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            st.dataframe(res, use_container_width=True, hide_index=True)import streamlit as st
import pandas as pd
import veritabani

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
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
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
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (GÜNCELLENEN KISIM) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        
        if not df_emirler.empty:
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                # 1. Seçili iş emri verilerini çek
                filtered = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                # 2. Mamül filtreleme
                mamul_list = sorted(filtered["Mamül Adı"].astype(str).unique().tolist())
                m_sec = st.multiselect("🏗️ Mamül Adı Filtrele:", mamul_list)
                if m_sec:
                    filtered = filtered[filtered["Mamül Adı"].astype(str).isin(m_sec)]
                
                # 3. Adresleri getir
                def get_best_adr(kod):
                    if 'Kod' in df_stok_ana.columns:
                        res = df_stok_ana[df_stok_ana['Kod'].astype(str) == str(kod)]
                        return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                    return "STOK YOK"
                filtered["Alınacak Adres"] = filtered["Stok Kodu"].apply(get_best_adr)
                
                # 4. Doluluk Hesapla
                filtered['Doluluk %'] = (pd.to_numeric(filtered['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                         pd.to_numeric(filtered['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)

                st.markdown("#### 📝 Hazırlık Detay Listesi")
                st.warning("Aşağıdaki 'Hazırlanan Adet' sütununa topladığınız miktarları girin.")

                # 5. DÜZENLEME ALANI (Data Editor)
                # Hazırlanan Adet sütununu düzenlenebilir yapıyoruz
                edited_df = st.data_editor(
                    filtered,
                    column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                    disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                    hide_index=True,
                    use_container_width=True,
                    key="hazirlik_editor"
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    # 6. GÜNCELLEME MANTIĞI
                    # Veritabanındaki tüm iş emirlerini al
                    all_data = veritabani.get_internal_data("Is_Emirleri")
                    
                    # Düzenlenen satırları veritabanına işle
                    # 'İş Emri' ve 'Stok Kodu' kombinasyonunu anahtar olarak kullanıyoruz
                    for index, row in edited_df.iterrows():
                        mask = (all_data["İş Emri"] == row["İş Emri"]) & (all_data["Stok Kodu"] == row["Stok Kodu"])
                        if any(mask):
                            all_data.loc[mask, "Hazırlanan Adet"] = row["Hazırlanan Adet"]
                    
                    # Veritabanını komple güncelle
                    veritabani.update_data("Is_Emirleri", all_data)
                    st.success("Hazırlanan miktarlar başarıyla kaydedildi!")
                    st.cache_data.clear()
                    st.rerun()

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu ve Arşiv")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            r_e = st.multiselect("📋 İş Emri Süz:", sorted(df_lh["İş Emri"].unique().tolist()))
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            res['Doluluk %'] = (pd.to_numeric(res['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                pd.to_numeric(res['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            st.dataframe(res, use_container_width=True, hide_index=True)
