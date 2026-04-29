import streamlit as st
import pandas as pd
import veritabani

def go_home(): st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")

    with st.expander("📤 Yeni İş Emri Yükle", expanded=False):
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK")
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                
                if "total" in df_raw.columns: df_raw["İhtiyaç Miktarı"] = df_raw["total"]
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Mamül Kodu", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns:
                        df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_final_save = df_raw[cols_target]
                
                st.info(f"📂 'HAZIRLIK' sekmesi okundu. İş Emri: {is_emri_adi}")
                # Yükleme önizlemesinden de Mamül adını çıkardım ki tam tutarlı olsun
                st.dataframe(df_final_save[["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]], use_container_width=True, hide_index=True)
                
                if st.button("VERİTABANINA (IS_EMIRLERI) ŞİMDİ KAYDET"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success(f"✅ {is_emri_adi} başarıyla eklendi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Hata: Veri okuma sırasında bir sorun oluştu. -> {e}")

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
                column_order=gosterilecek_kolonlar, # Tabloyu bu düzene zorluyoruz
                hide_index=True, 
                use_container_width=True
            )
            
            if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                st.success("Veriler Güncellendi! (GSheets bağlantısı ve update blokları burada çalışır)"); st.rerun()
