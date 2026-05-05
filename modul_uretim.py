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
def go_hazirlik(): 
    go_uretim_menu() 
    st.session_state.uretim_page = 'hazirlik'
def go_rapor(): 
    go_uretim_menu() 
    st.session_state.uretim_page = 'rapor'

def goster():
    if 'user' not in st.session_state or st.session_state.user is None:
        st.session_state.page = 'login'; st.rerun()

    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. YÜKLEME (TEMİZ VERİ ÇEKME MANTIĞI) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Excel'den Veri Çek")
        
        uploaded_file = st.file_uploader("Dosyayı seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                target_sheet = "HAZIRLIK" if "HAZIRLIK" in excel_file.sheet_names else ("Sheet4" if "Sheet4" in excel_file.sheet_names else excel_file.sheet_names[0])

                df_raw = pd.read_excel(uploaded_file, sheet_name=target_sheet, header=None)
                
                # Başlık satırını doğru bulalım (Stok Kodu nerdeyse başlık odur)
                baslik_satiri = 0
                for i in range(min(30, len(df_raw))):
                    satir_degerleri = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir_degerleri:
                        baslik_satiri = i; break
                
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                
                # KRİTİK: Ürün Kodu ve Mamül Adı bilgisini aşağı çekmeden önce sütunları kontrol et
                u_kod_col = "Ürün Kodu" if "Ürün Kodu" in df_raw.columns else ("Mamül Kodu" if "Mamül Kodu" in df_raw.columns else None)
                if u_kod_col:
                    df_raw["Ürün Kodu"] = df_raw[u_kod_col].ffill()
                
                # İhtiyaç Miktarı tespiti
                for col in df_raw.columns:
                    if "total" in str(col).lower() or "ihtiyaç" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0); break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                # Hatalı veri ayıklama: Sadece Stok Kodu olan ve Ürün Koduyla aynı olmayanları al
                df_final = df_raw.dropna(subset=['Stok Kodu']).copy()
                df_final = df_final[df_final["Stok Kodu"].astype(str).str.strip() != df_final["Ürün Kodu"].astype(str).str.strip()]
                
                cols_target = ["İş Emri", "Ürün Kodu", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_final.columns: df_final[c] = 0 if "Adet" in c else ""
                
                df_final = df_final[cols_target]
                st.dataframe(df_final, use_container_width=True, hide_index=True)

                if st.button("SİSTEMİ GÜNCELLE", type="primary"):
                    veritabani.update_data("Is_Emirleri", df_final)
                    st.success("✅ Veriler Tertemiz Yüklendi!"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (HATASIZ EŞLEŞME) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık")
        
        st.session_state.local_stok = veritabani.get_internal_data("Stok")
        st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        
        if not df_emirler.empty:
            s_list = st.multiselect("📋 İş Emri:", sorted(df_emirler["İş Emri"].unique().tolist()))
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].isin(s_list)].copy()
                # Personel sadece Kalanı olanları görür
                pivot_df = sub_df.groupby(['İş Emri', 'Ürün Kodu', 'Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                pivot_df['Kalan'] = (pivot_df['İhtiyaç Miktarı'] - pivot_df['Hazırlanan Adet']).round(3)
                bekleyenler = pivot_df[pivot_df['Kalan'] > 0.001].copy()

                if bekleyenler.empty:
                    st.success("✅ Eksik malzeme yok!")
                else:
                    with st.container(border=True):
                        secenekler = ["Seçiniz..."] + [f"{r['Ürün Kodu']} | {r['Stok Kodu']} | {r['Stok Adı']}" for _, r in bekleyenler.iterrows()]
                        sel = st.selectbox("📝 Malzeme Seç:", secenekler)
                        if sel != "Seçiniz...":
                            u_k = sel.split(" | ")[0]
                            s_k = sel.split(" | ")[1]
                            row = bekleyenler[(bekleyenler['Ürün Kodu']==u_k) & (bekleyenler['Stok Kodu']==s_k)].iloc[0]
                            
                            c1, c2 = st.columns(2)
                            c1.metric("🎯 Kalan", f"{row['Kalan']} {row['Birim']}")
                            input_mik = c2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(row['Kalan']), step=1.0)
                            
                            if st.button("⚡ KAYDET", use_container_width=True, type="primary"):
                                if input_mik > 0:
                                    mask = (st.session_state.local_emirler['Ürün Kodu'] == u_k) & (st.session_state.local_emirler['Stok Kodu'] == s_k)
                                    st.session_state.local_emirler.loc[mask, 'Hazırlanan Adet'] += input_mik
                                    veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                    st.success("Kaydedildi!"); st.rerun()
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)

    # --- 3. RAPOR (EXCEL BUTONU BURADA!) ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_lh.empty:
            # Özet Tablo (Yüzdeler)
            st.markdown("### 📈 Genel Durum")
            summary = df_lh.groupby("İş Emri").agg({"İhtiyaç Miktarı": "sum", "Hazırlanan Adet": "sum"}).reset_index()
            summary["Tamamlanma %"] = (summary["Hazırlanan Adet"] / summary["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
            st.dataframe(summary, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # Detaylı Filtreleme ve EXCEL BUTONU
            st.markdown("### 🔍 Detaylı Liste")
            r_list = st.multiselect("İş Emri Filtrele:", sorted(df_lh["İş Emri"].unique().tolist()))
            filtered = df_lh[df_lh["İş Emri"].isin(r_list)] if r_list else df_lh
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            
            # --- İŞTE O BUTON ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                filtered.to_excel(writer, index=False, sheet_name='Hazirlik_Raporu')
                # Excel'i güzelleştirelim (Opsiyonel)
                workbook = writer.book
                worksheet = writer.sheets['Hazirlik_Raporu']
                header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(filtered.columns.values):
                    worksheet.write(0, col_num, value, header_format)
            
            st.download_button(
                label="📥 RAPORU EXCEL OLARAK İNDİR",
                data=buffer.getvalue(),
                file_name=f"Hazirlik_Raporu_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True,
                type="primary"
            )
