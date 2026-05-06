import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- GÜVENLİ BAŞLATICI ---
def init_state():
    if 'uretim_page' not in st.session_state: st.session_state.uretim_page = 'menu'
    if 'page' not in st.session_state: st.session_state.page = 'home'

# --- NAVİGASYON ---
def go_home(): 
    init_state(); st.session_state.page = 'home'; st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    init_state(); st.session_state.uretim_page = 'menu'
    if 'local_emirler' in st.session_state: del st.session_state.local_emirler

def goster():
    init_state()
    
    # --- STİL AYARLARI (KÜÇÜK PUNTO) ---
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; }
        .stCaption { font-size: 11px !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"): go_home(); st.rerun()
        st.subheader("🏭 Üretim Hazırlık Modülü (v18.13)")
        st.markdown("---")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        st.button("🏗️ ÜRETİM HAZIRLIK YAP", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik'))
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'rapor'))

    # --- 1. YÜKLEME ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📤 İş Emri Excel'i Yükle")
        uploaded_file = st.file_uploader("Dosya Seçin:", type=['xlsx'])
        if uploaded_file:
            try:
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
                baslik_idx = 0
                for i in range(min(30, len(df_raw))):
                    row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in row_vals: baslik_idx = i; break
                df = df_raw.iloc[baslik_idx:].copy()
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = [str(c).strip() for c in df.columns]
                if 'Mamül Adı' in df.columns: df['Mamül Adı'] = df['Mamül Adı'].ffill()
                elif 'Ürün Adı' in df.columns: df['Mamül Adı'] = df['Ürün Adı'].ffill()
                df = df.dropna(subset=['Stok Kodu', 'Stok Adı'])
                df['İş Emri'] = is_emri_adi
                df['Hazırlanan Adet'] = 0
                for col in df.columns:
                    if any(x in col.lower() for x in ['total', 'ihtiyaç', 'miktar']):
                        df['İhtiyaç Miktarı'] = pd.to_numeric(df[col], errors='coerce').fillna(0); break
                df = df[df['Stok Kodu'] != df.get('Ürün Kodu', '---')]
                cols = ["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                df_save = df[[c for c in cols if c in df.columns]]
                with st.expander("📋 Yüklenecek Veri Önizlemesi", expanded=True):
                    st.dataframe(df_save, use_container_width=True, hide_index=True)
                if st.button("UYGULAMAYI GÜNCELLE", type="primary", use_container_width=True):
                    veritabani.update_data("Is_Emirleri", df_save); st.success("✅ Güncellendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. HAZIRLIK (KOMPAKT PANEL) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık")
        
        st.session_state.local_stok = veritabani.get_internal_data("Stok")
        df_db = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_db.empty:
            sel_is = st.selectbox("📋 İş Emri Seçin:", ["Seçiniz..."] + sorted(df_db['İş Emri'].unique().tolist()))
            if sel_is != "Seçiniz...":
                sub = df_db[df_db['İş Emri'] == sel_is].copy()
                bekleyenler = sub[(sub['İhtiyaç Miktarı'] - sub['Hazırlanan Adet']) > 0.001].copy()
                
                if not bekleyenler.empty:
                    bekleyenler['unique_key'] = bekleyenler['Stok Adı'] + " | " + bekleyenler['Stok Kodu'] + " (Ürün: " + bekleyenler['Mamül Adı'] + ")"
                    sel_display = st.selectbox("🎯 Hazırlanacak Malzemeyi Seçin:", ["Seçiniz..."] + bekleyenler['unique_key'].tolist())
                    
                    if sel_display != "Seçiniz...":
                        row = bekleyenler[bekleyenler['unique_key'] == sel_display].iloc[0]
                        s_kod = str(row['Stok Kodu']).strip().upper()
                        kalan_ih = round(row['İhtiyaç Miktarı'] - row['Hazırlanan Adet'], 3)
                        
                        df_stok = st.session_state.local_stok
                        st_kod_col = next((c for c in df_stok.columns if "Kod" in str(c)), "Kod")
                        st_adr_col = next((c for c in df_stok.columns if "Adres" in str(c)), "Adres")
                        st_mik_col = next((c for c in df_stok.columns if "Miktar" in str(c)), "Miktar")
                        
                        temp_stok = df_stok[df_stok[st_kod_col].astype(str).str.strip().str.upper() == s_kod]
                        toplam_depo = temp_stok[st_mik_col].sum() if not temp_stok.empty else 0
                        
                        with st.container(border=True):
                            st.markdown(f"🛠️ **{row['Stok Adı']}** ({s_kod})")
                            
                            # Üst Satır
                            r1c1, r1c2 = st.columns([2, 1])
                            adrs_list = ["Seçiniz..."]
                            if not temp_stok.empty:
                                active_adrs = temp_stok[temp_stok[st_mik_col] > 0][st_adr_col].unique().tolist()
                                adrs_list += sorted(active_adrs) if active_adrs else ["STOK YOK"]
                            else: adrs_list = ["STOK YOK"]
                            
                            input_adr = r1c1.selectbox("📍 Raf Adresi:", adrs_list, label_visibility="collapsed")
                            input_mik = r1c2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(kalan_ih), step=1.0, label_visibility="collapsed")
                            
                            # Alt Satır (Gelişmiş & Kompakt Gösterge)
                            r_stok = 0
                            if input_adr not in ["Seçiniz...", "STOK YOK"]:
                                r_stok = temp_stok[temp_stok[st_adr_col] == input_adr][st_mik_col].sum()
                            
                            m1, m2, m3 = st.columns(3)
                            m1.metric("🏢 Raf", f"{int(r_stok)}")
                            m2.metric("📦 Toplam", f"{int(toplam_depo)}")
                            m3.metric("🎯 Kalan", f"{kalan_ih}", delta_color="inverse")
                            
                            if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                                if input_adr in ["Seçiniz...", "STOK YOK"] or input_mik <= 0:
                                    st.error("Adres ve miktar kontrolü yapın!")
                                else:
                                    mask_stok = (df_stok[st_kod_col].astype(str).str.strip().str.upper() == s_kod) & (df_stok[st_adr_col] == input_adr)
                                    df_stok.loc[mask_stok, st_mik_col] -= input_mik
                                    mask_emir = (df_db['İş Emri'] == sel_is) & (df_db['Mamül Adı'] == row['Mamül Adı']) & \
                                                (df_db['Stok Kodu'] == row['Stok Kodu']) & (df_db['Stok Adı'] == row['Stok Adı'])
                                    df_db.loc[mask_emir, 'Hazırlanan Adet'] += input_mik
                                    veritabani.update_data("Stok", df_stok)
                                    veritabani.update_data("Is_Emirleri", df_db)
                                    st.success("✅ Kaydedildi!"); st.rerun()
                else:
                    st.success("✅ Malzeme kalmadı.")
                
                st.divider()
                st.write("📝 **Tam Malzeme Listesi**")
                view_cols = ["İş Emri", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                st.dataframe(sub[view_cols], use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Rapor")
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        if not df_rapor.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_rapor.to_excel(writer, index=False, sheet_name='Hazirlik')
            st.download_button("📥 EXCEL İNDİR", data=buffer.getvalue(), file_name="Rapor.xlsx", use_container_width=True, type="primary")
            with st.expander("📈 Özet Oranlar", expanded=False):
                summary = df_rapor.groupby("İş Emri").agg({"İhtiyaç Miktarı":"sum", "Hazırlanan Adet":"sum"}).reset_index()
                summary["%"] = (summary["Hazırlanan Adet"] / summary["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
                st.table(summary)
            st.write("🔍 **Detaylı Veriler**")
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)
