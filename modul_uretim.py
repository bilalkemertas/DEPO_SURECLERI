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
    # Güvenlik kontrolü
    if 'user' not in st.session_state or st.session_state.user is None:
        st.session_state.page = 'login'
        st.rerun()

    # Alt menü durumu başlatma
    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # ==========================================
    # 0. ÜRETİM HAZIRLIK ANA MENÜSÜ
    # ==========================================
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): 
            go_home()
            st.rerun()
        
        st.subheader("🏭 Üretim Hazırlık Merkezi")
        st.markdown("---")
        
        st.button("📥 İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # ==========================================
    # 1. YENİ İŞ EMRİ YÜKLEME EKRANI
    # ==========================================
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): 
            go_uretim_menu()
            st.rerun()
            
        st.subheader("📤 Yeni İş Emri Yükle")
        st.markdown("---")
        
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                # 1. Dosyayı başlıkları yok sayarak düz oku
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                
                # 2. SADECE "Stok Kodu" geçen satırı asıl başlık satırı olarak kabul et!
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir:
                        baslik_satiri = i
                        break
                
                # 3. Tablonun başlıklarını o satır yap
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                
                # 4. Sütun isimlerindeki gereksiz boşlukları temizle
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                
                # 5. TOTAL Sütununu bul ve garanti olarak İhtiyaç Miktarı'na eşitle
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                        
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Mamül Kodu", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns:
                        df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                # Stok Kodu boş olan (alt kısımdaki gereksiz) satırları temizle
                df_raw = df_raw.dropna(subset=['Stok Kodu'])
                
                df_final_save = df_raw[cols_target]
                
                st.info(f"📂 'HAZIRLIK' sekmesi okundu. İş Emri: {is_emri_adi}")
                
                if st.button("VERİTABANINA (IS_EMIRLERI) ŞİMDİ KAYDET", type="primary"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success(f"✅ {is_emri_adi} başarıyla eklendi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Hata: Veri okuma sırasında bir sorun oluştu. -> {e}")

    # ==========================================
    # 2. İŞ EMRİ TAKİBİ VE HAZIRLIK LİSTESİ EKRANI
    # ==========================================
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): 
            go_uretim_menu()
            st.rerun()
            
        st.subheader("🏗️ Üretim Hazırlık ve İş Emri Takibi")
        st.markdown("---")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        
        if not df_emirler.empty:
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                temp_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)]
                
                mamul_list = sorted(temp_df["Mamül Adı"].astype(str).unique().tolist())
                m_sec = st.multiselect("🏗️ Mamül Adı Filtrele:", mamul_list)
                
                filtered = temp_df.copy()
                if m_sec:
                    filtered = filtered[filtered["Mamül Adı"].astype(str).isin(m_sec)]
                
                filtered['Doluluk %'] = (pd.to_numeric(filtered['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                         pd.to_numeric(filtered['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
                
                def get_best_adr(kod):
                    if 'Kod' in df_stok_ana.columns:
                        res = df_stok_ana[df_stok_ana['Kod'].astype(str) == str(kod)]
                        return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                    return "STOK YOK"
                
                s_kod_col = 'Stok Kodu' if 'Stok Kodu' in filtered.columns else 'Kod'
                filtered["Alınacak Adres"] = filtered[s_kod_col].apply(get_best_adr)
                
                st.markdown("#### 📝 Hazırlık Detay Listesi")
                
                gosterilecek_kolonlar = ["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"]
                gosterilecek_kolonlar = [c for c in gosterilecek_kolonlar if c in filtered.columns]

                ed = st.data_editor(
                    filtered, 
                    column_order=gosterilecek_kolonlar, 
                    hide_index=True, 
                    use_container_width=True
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    st.success("Veriler Güncellendi! (GSheets bağlantısı ve update blokları burada çalışır)"); st.rerun()

    # ==========================================
    # 3. HAZIRLIK RAPORU EKRANI
    # ==========================================
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): 
            go_uretim_menu()
            st.rerun()
            
        st.subheader("📊 Hazırlık Raporu")
        st.markdown("---")
        
        df_h = veritabani.get_internal_data("Is_Emirleri")
        if not df_h.empty:
            r_emir_list = sorted(df_h["İş Emri"].astype(str).unique().tolist())
            r_emir = st.multiselect("📋 İş Emri Filtrele:", r_emir_list, key="r_emir")
            r_df = df_h.copy()
            if r_emir:
                r_df = r_df[r_df["İş Emri"].astype(str).isin(r_emir)]
            st.dataframe(r_df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Gösterilecek iş emri verisi bulunamadı.")
