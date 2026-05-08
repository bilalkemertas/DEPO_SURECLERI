import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- GÜVENLİ BAŞLATICI ---
def init_state():
    if 'uretim_page' not in st.session_state: st.session_state.uretim_page = 'menu'
    if 'page' not in st.session_state: st.session_state.page = 'home'
    if 'sel_is_emri' not in st.session_state: st.session_state.sel_is_emri = None

# --- NAVİGASYON ---
def go_home(): 
    init_state(); st.session_state.page = 'home'; st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    init_state(); st.session_state.uretim_page = 'menu'; st.session_state.sel_is_emri = None
    if 'local_emirler' in st.session_state: del st.session_state.local_emirler

def goster():
    init_state()
    
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
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        st.button("🏗️ ÜRETİM HAZIRLIK YAP", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik_secim'))
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
                
                cols = ["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                df_save = df[[c for c in cols if c in df.columns]]
                
                st.dataframe(df_save, use_container_width=True, hide_index=True)
                
                if st.button("LİSTEYE İLAVE ET (GÜVENLİ YÜKLEME)", type="primary", use_container_width=True):
                    df_old = veritabani.get_internal_data("Is_Emirleri")
                    df_old = df_old[df_old['İş Emri'] != is_emri_adi]
                    df_final = pd.concat([df_old, df_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", df_final)
                    st.success(f"✅ {is_emri_adi} başarıyla eklendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. SEÇİM EKRANI ---
    elif st.session_state.uretim_page == 'hazirlik_secim':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("🔍 İş Emri Seçimi")
        df_db = veritabani.get_internal_data("Is_Emirleri")
        if not df_db.empty:
            is_emirleri = sorted(df_db['İş Emri'].unique().tolist())
            secilen = st.selectbox("Lütfen iş emrini seçin:", ["İş Emri Seçiniz..."] + is_emirleri)
            if secilen != "İş Emri Seçiniz...":
                if st.button("🚀 HAZIRLIĞA BAŞLA", use_container_width=True, type="primary"):
                    st.session_state.sel_is_emri = secilen
                    st.session_state.uretim_page = 'hazirlik_panel'; st.rerun()
        else:
            st.warning("İş emri bulunamadı.")

    # --- 3. HAZIRLIK PANELİ ---
    elif st.session_state.uretim_page == 'hazirlik_panel':
        if st.button("⬅️ İŞ EMRİ LİSTESİNE DÖN"): st.session_state.uretim_page = 'hazirlik_secim'; st.rerun()
        st.subheader(f"🏗️ {st.session_state.sel_is_emri}")
        
        st.session_state.local_stok = veritabani.get_internal_data("Stok")
        df_db = veritabani.get_internal_data("Is_Emirleri")
        sub = df_db[df_db['İş Emri'] == st.session_state.sel_is_emri].copy()
        bekleyenler = sub[(sub['İhtiyaç Miktarı'] - sub['Hazırlanan Adet']) > 0.001].copy()
        
        if not bekleyenler.empty:
            bekleyenler['key'] = bekleyenler['Stok Adı'] + " | " + bekleyenler['Stok Kodu']
            sel_display = st.selectbox("🎯 Malzeme Seç:", ["Seçiniz..."] + bekleyenler['key'].tolist())
            
            if sel_display != "Seçiniz...":
                row = bekleyenler[bekleyenler['key'] == sel_display].iloc[0]
                s_kod = str(row['Stok Kodu']).strip().upper()
                kalan_ih = round(row['İhtiyaç Miktarı'] - row['Hazırlanan Adet'], 3)
                df_stok = st.session_state.local_stok
                temp_stok = df_stok[df_stok["Kod"].astype(str).str.strip().str.upper() == s_kod]
                
                with st.container(border=True):
                    st.markdown(f"🛠️ **{row['Stok Adı']}**")
                    r1c1, r1c2 = st.columns([2, 1])
                    adrs_list = ["Adres Seçiniz..."] + sorted(temp_stok[temp_stok["Miktar"] > 0]["Adres"].unique().tolist()) if not temp_stok.empty else ["STOK YOK"]
                    input_adr = r1c1.selectbox("📍 Raf:", adrs_list)
                    input_mik = r1c2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(kalan_ih), step=1.0)
                    
                    if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                        if input_adr not in ["Adres Seçiniz...", "STOK YOK"] and input_mik > 0:
                            mask_stok = (df_stok["Kod"].astype(str).str.strip().str.upper() == s_kod) & (df_stok["Adres"] == input_adr)
                            df_stok.loc[mask_stok, "Miktar"] -= input_mik
                            mask_emir = (df_db['İş Emri'] == st.session_state.sel_is_emri) & (df_db['Stok Kodu'] == row['Stok Kodu'])
                            df_db.loc[mask_emir, 'Hazırlanan Adet'] += input_mik
                            veritabani.update_data("Stok", df_stok)
                            veritabani.update_data("Is_Emirleri", df_db)
                            st.success("✅ Kaydedildi!"); st.rerun()
        
        st.dataframe(sub[["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]], use_container_width=True, hide_index=True)

    # --- 4. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Rapor")
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        if not df_rapor.empty:
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)

    # --- SAYFA SONU İMZASI ---
    st.markdown("---")
    col_sign1, col_sign2 = st.columns([3, 1])
    with col_sign2:
        st.markdown(
            """
            <div style='text-align: right;'>
                <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p>
                <p style='margin:0; font-size: 12px; color: gray;'>Logistics Solutions</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
