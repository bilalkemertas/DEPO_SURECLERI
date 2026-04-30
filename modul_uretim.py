import streamlit as st
import pandas as pd
import veritabani
import io  # Excel indirme işlemi için gerekli

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
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                # --- ÖZET PANELİ ---
                with st.expander("📊 İş Emri Genel Durum Özeti (Görüntülemek için tıklayın)", expanded=False):
                    st.markdown("""
                        <style>
                        .scroll-container {
                            max-height: 250px;
                            overflow-y: auto;
                            border: 1px solid #ddd;
                            padding: 10px;
                            border-radius: 5px;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    dashboard_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                    ozet_tablo = dashboard_df.groupby('İş Emri').agg({
                        'İhtiyaç Miktarı': 'sum',
                        'Hazırlanan Adet': 'sum'
                    }).reset_index()
                    ozet_tablo['Tamamlanma %'] = (ozet_tablo['Hazırlanan Adet'] / ozet_tablo['İhtiyaç Miktarı'] * 100).round(1).fillna(0)
                    
                    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
                    st.dataframe(
                        ozet_tablo.rename(columns={
                            'İhtiyaç Miktarı': 'Toplam İhtiyaç',
                            'Hazırlanan Adet': 'Toplam Hazırlanan'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown("---")
                
                # --- DETAY LİSTE ---
                filtered = dashboard_df.copy()
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
                filtered['Doluluk %'] = (filtered['Hazırlanan Adet'] / filtered['İhtiyaç Miktarı'] * 100).round(1).fillna(0)

                st.markdown("#### 📝 Hazırlık Detay Listesi")
                edited_df = st.data_editor(
                    filtered,
                    column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                    disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                    hide_index=True,
                    use_container_width=True,
                    key="hazirlik_editor"
                )
                
                if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                    all_is_emirleri = veritabani.get_internal_data("Is_Emirleri")
                    df_stok_guncel = veritabani.get_internal_data("Stok")
                    
                    # Sayısal sütunların güvenliğini sağla
                    all_is_emirleri['Hazırlanan Adet'] = pd.to_numeric(all_is_emirleri['Hazırlanan Adet'], errors='coerce').fillna(0)
                    df_stok_guncel['Miktar'] = pd.to_numeric(df_stok_guncel['Miktar'], errors='coerce').fillna(0)
                    
                    for i, row in edited_df.iterrows():
                        mask = (all_is_emirleri["İş Emri"].astype(str) == str(row["İş Emri"])) & \
                               (all_is_emirleri["Stok Kodu"].astype(str) == str(row["Stok Kodu"])) & \
                               (all_is_emirleri["Mamül Adı"].astype(str) == str(row["Mamül Adı"]))
                        
                        if mask.any():
                            # Eski ve Yeni değer farkını (Delta) hesapla
                            old_val = all_is_emirleri.loc[mask, "Hazırlanan Adet"].values[0]
                            new_val = pd.to_numeric(row["Hazırlanan Adet"], errors='coerce')
                            delta = new_val - old_val
                            
                            # Eğer alınan miktar arttıysa stoktan düş
                            if delta > 0:
                                stok_mask = (df_stok_guncel["Kod"].astype(str) == str(row["Stok Kodu"])) & \
                                            (df_stok_guncel["Adres"].astype(str) == str(row["Alınacak Adres"]))
                                
                                if stok_mask.any():
                                    mevcut_stok = df_stok_guncel.loc[stok_mask, "Miktar"].values[0]
                                    # NEGATİF BAKİYE KORUMASI: Stok asla 0'ın altına düşmez
                                    df_stok_guncel.loc[stok_mask, "Miktar"] = max(0, mevcut_stok - delta)
                            
                            # İş emri tablosunu güncelle
                            all_is_emirleri.loc[mask, "Hazırlanan Adet"] = new_val

                    # Veritabanına her iki tabloyu da yaz
                    veritabani.update_data("Is_Emirleri", all_is_emirleri)
                    veritabani.update_data("Stok", df_stok_guncel)
                    
                    st.success("Veriler eşitlendi ve stoklar ilgili adreslerden düşüldü!")
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
            
            st.markdown("---")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Hazirlik_Raporu')
            
            st.download_button(
                label="📥 RAPORU EXCEL OLARAK İNDİR",
                data=buffer.getvalue(),
                file_name="Uretim_Hazirlik_Raporu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
