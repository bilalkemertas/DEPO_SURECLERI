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
    # Uygulamanın geçici hafızasını temizliyoruz (Excel dosyalarına dokunmaz)
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
        st.session_state.page = 'login'
        st.rerun()

    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): 
            go_home()
            st.rerun()
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. YÜKLEME (SADECE UYGULAMA VERİSİNİ GÜNCELLEME) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Excel'den Veri Çek")
        st.info("Bu işlem orijinal Excel dosyanızı değiştirmez, sadece uygulamadaki çalışma listesini günceller.")
        
        uploaded_file = st.file_uploader("Dosyayı seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                target_sheet = "HAZIRLIK" if "HAZIRLIK" in excel_file.sheet_names else ("Sheet4" if "Sheet4" in excel_file.sheet_names else None)

                if not target_sheet:
                    st.error(f"❌ Sekme bulunamadı! Mevcutlar: {excel_file.sheet_names}"); return

                df_raw = pd.read_excel(uploaded_file, sheet_name=target_sheet, header=None)
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir: baslik_satiri = i; break
                
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                df_raw = df_raw.ffill() 

                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0); break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns: df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                # Malzemeleri çek (Ürün satırlarını ve boşları ele)
                df_final_save = df_raw.dropna(subset=['Stok Kodu']).copy()
                df_final_save = df_final_save[df_final_save["Stok Kodu"] != df_final_save["Ürün Kodu"]]
                df_final_save = df_final_save[cols_target]

                st.dataframe(df_final_save, use_container_width=True, hide_index=True)

                if st.button("UYGULAMA VERİSİNİ GÜNCELLE", type="primary"):
                    # Excel'e dokunmuyoruz, sadece uygulamanın 'Is_Emirleri' tablosunu bu yeni veriyle tazeliyoruz.
                    veritabani.update_data("Is_Emirleri", df_final_save)
                    st.success("✅ Uygulama verileri güncellendi!"); st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (KESİN EŞLEŞME - KECE HATASI FİX) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık")
        
        # Her girişte veritabanından taze veri çekiyoruz
        st.session_state.local_stok = veritabani.get_internal_data("Stok")
        st.session_state.local_emirler = veritabani.get_internal_data("Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            s_list = st.multiselect("📋 İş Emri:", sorted(df_emirler["İş Emri"].unique().tolist()))
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].isin(s_list)].copy()
                # Gruplamayı Ürün Kodu + Stok Kodu bazında yapıyoruz (KECE hatası burada biter)
                pivot_df = sub_df.groupby(['İş Emri', 'Ürün Kodu', 'Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                pivot_df['Kalan'] = pivot_df['İhtiyaç Miktarı'] - pivot_df['Hazırlanan Adet']
                
                bekleyenler_df = pivot_df[pivot_df['Kalan'] > 0.01].copy()

                with st.container(border=True):
                    if bekleyenler_df.empty:
                        st.success("✅ Hazırlanacak malzeme kalmadı!")
                    else:
                        # Seçim kutusunda Ürün Kodu ve Malzeme Kodu beraber (Tam isabet eşleşme)
                        secenekler = ["Seçiniz..."] + [f"{r['Ürün Kodu']} >> {r['Stok Kodu']} | {r['Stok Adı']}" for _, r in bekleyenler_df.iterrows()]
                        input_secim = st.selectbox("📝 Hazırlanacak Malzeme:", secenekler)
                        
                        if input_secim != "Seçiniz...":
                            u_kod = input_secim.split(" >> ")[0]
                            s_kod = input_secim.split(" >> ")[1].split(" | ")[0]
                            
                            row = bekleyenler_df[(bekleyenler_df['Ürün Kodu'] == u_kod) & (bekleyenler_df['Stok Kodu'] == s_kod)].iloc[0]
                            
                            c1, c2, c3 = st.columns(3)
                            c1.metric("🎯 Kalan İhtiyaç", f"{row['Kalan']} {row['Birim']}")
                            input_mik = c2.number_input("🔢 Verilen Miktar:", min_value=0.0)
                            
                            st_kod_c = next((c for c in df_stok_ana.columns if "Kod" in str(c)), "Kod")
                            st_adr_c = next((c for c in df_stok_ana.columns if "Adres" in str(c)), "Adres")
                            st_mik_c = next((c for c in df_stok_ana.columns if "Miktar" in str(c)), "Miktar")
                            
                            temp_stok = df_stok_ana[df_stok_ana[st_kod_c].astype(str).str.strip().str.upper() == str(s_kod).upper()]
                            input_adr = c3.selectbox("📍 Raf:", ["Seçiniz..."] + sorted(temp_stok[temp_stok[st_mik_c]>0][st_adr_c].unique().tolist()) if not temp_stok.empty else ["STOK YOK"])

                            if st.button("⚡ KAYDET", use_container_width=True, type="primary"):
                                if input_mik > 0 and input_adr not in ["Seçiniz...", "STOK YOK"]:
                                    # Stok Düş
                                    mask_stok = (st.session_state.local_stok[st_kod_c].astype(str) == str(s_kod)) & (st.session_state.local_stok[st_adr_c] == input_adr)
                                    st.session_state.local_stok.loc[mask_stok, st_mik_c] -= input_mik
                                    
                                    # Hazırlık Güncelle (Doğru Ürün ve Doğru Malzemeye)
                                    mask_emir = (st.session_state.local_emirler['İş Emri'].isin(s_list)) & (st.session_state.local_emirler['Ürün Kodu'] == u_kod) & (st.session_state.local_emirler['Stok Kodu'] == s_kod)
                                    st.session_state.local_emirler.loc[mask_emir, 'Hazırlanan Adet'] += input_mik
                                    
                                    veritabani.update_data("Stok", st.session_state.local_stok)
                                    veritabani.update_data("Is_Emirleri", st.session_state.local_emirler)
                                    st.success("İşlem Başarılı!"); st.rerun()

                st.write("📊 **Güncel Liste**")
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)

    # --- 3. RAPOR (DOĞRU EŞLEŞMEYLE) ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Rapor")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            r_e = st.multiselect("📋 Filtrele:", sorted(df_lh["İş Emri"].unique().tolist()))
            filtered = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            
            # Özet Tablo
            sum_df = filtered.groupby("İş Emri").agg({"İhtiyaç Miktarı": "sum", "Hazırlanan Adet": "sum"}).reset_index()
            sum_df["%"] = (sum_df["Hazırlanan Adet"] / sum_df["İhtiyaç Miktarı"] * 100).round(1)
            st.dataframe(sum_df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.write("🔍 **Detay**")
            st.dataframe(filtered, use_container_width=True, hide_index=True)
