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

    # --- 2. SEÇİM EKRANI (DURUM FİLTRELİ) ---
    elif st.session_state.uretim_page == 'hazirlik_secim':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("🔍 İş Emri Seçimi")
        df_db = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_db.empty:
            # İş emri bazında durum tespiti
            emir_ozet = df_db.groupby('İş Emri').agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            
            def durum_belirle(row):
                if row['Hazırlanan Adet'] >= row['İhtiyaç Miktarı'] - 0.001: return "✅ Tamamlandı"
                if row['Hazırlanan Adet'] > 0: return "🏗️ Devam Ediyor"
                return "🆕 Başlanmadı"
            
            emir_ozet['Durum'] = emir_ozet.apply(durum_belirle, axis=1)
            
            # Filtreleme Seçenekleri
            f_durum = st.radio("🚩 Duruma Göre Filtrele:", ["Tümü", "🆕 Başlanmadı", "🏗️ Devam Ediyor", "✅ Tamamlandı"], horizontal=True)
            
            filtered_emirler = emir_ozet.copy()
            if f_durum != "Tümü":
                filtered_emirler = filtered_emirler[filtered_emirler['Durum'] == f_durum]
            
            # Seçim Kutusu Listesi
            display_list = [f"{r['İş Emri']} | {r['Durum']}" for _, r in filtered_emirler.iterrows()]
            secilen_raw = st.selectbox("Lütfen bir iş emri seçin:", ["Seçiniz..."] + display_list)
            
            if secilen_raw != "Seçiniz...":
                secilen_is_emri = secilen_raw.split(" | ")[0]
                if st.button("🚀 HAZIRLIĞA BAŞLA", use_container_width=True, type="primary"):
                    st.session_state.sel_is_emri = secilen_is_emri
                    st.session_state.uretim_page = 'hazirlik_panel'; st.rerun()
        else:
            st.warning("Henüz yüklü iş emri bulunamadı.")

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
                    toplam_mevcut = temp_stok['Miktar'].sum() if not temp_stok.empty else 0
                    m1, m2, m3 = st.columns(3)
                    m1.metric("İhtiyaç", f"{kalan_ih} {row.get('Birim','AD')}")
                    m2.metric("Toplam Stok", f"{toplam_mevcut} {row.get('Birim','AD')}")
                    
                    r1c1, r1c2 = st.columns([2, 1])
                    adrs_data = temp_stok[temp_stok["Miktar"] > 0]
                    adrs_list = ["Adres Seçiniz..."] + [f"{r['Adres']} ({r['Miktar']} {row.get('Birim','AD')})" for _, r in adrs_data.iterrows()] if not adrs_data.empty else ["STOK YOK"]
                    input_adr_raw = r1c1.selectbox("📍 Raf Seçimi:", adrs_list)
                    
                    if "Adres Seçiniz..." not in input_adr_raw and "STOK YOK" not in input_adr_raw:
                        adr_miktari = float(input_adr_raw.split('(')[1].split(' ')[0])
                        m3.metric("Raf Stoğu", f"{adr_miktari}")
                    
                    input_mik = r1c2.number_input("🔢 Çıkış Miktarı:", min_value=0.0, max_value=float(kalan_ih), step=1.0)
                    
                    if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                        if "Adres Seçiniz..." not in input_adr_raw and "STOK YOK" not in input_adr_raw and input_mik > 0:
                            secilen_adres = input_adr_raw.split(' ')[0]
                            mask_stok = (df_stok["Kod"].astype(str).str.strip().str.upper() == s_kod) & (df_stok["Adres"] == secilen_adres)
                            df_stok.loc[mask_stok, "Miktar"] -= input_mik
                            mask_emir = (df_db['İş Emri'] == st.session_state.sel_is_emri) & (df_db['Stok Kodu'] == row['Stok Kodu'])
                            df_db.loc[mask_emir, 'Hazırlanan Adet'] += input_mik
                            veritabani.update_data("Stok", df_stok)
                            veritabani.update_data("Is_Emirleri", df_db)
                            st.success("✅ Kaydedildi!"); st.rerun()
        else:
            st.success("🌟 Bu iş emrindeki tüm kalemler hazırlandı!")
            
        st.divider()
        st.dataframe(sub[["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]], use_container_width=True, hide_index=True)

    # --- 4. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        if not df_rapor.empty:
            with st.expander("📈 İş Emri Hazırlık Özetleri (Devam Edenler)", expanded=False):
                ozet = df_rapor.groupby('İş Emri').agg({'Stok Kodu': 'count', 'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                ozet.columns = ['İş Emri', 'Kalem Sayısı', 'Toplam İhtiyaç', 'Toplam Hazırlanan']
                ozet['Tamamlanma %'] = (ozet['Toplam Hazırlanan'] / ozet['Toplam İhtiyaç'] * 100).round(1)
                eksik_ozet = ozet[ozet['Toplam İhtiyaç'] - ozet['Toplam Hazırlanan'] > 0.001].copy()
                st.dataframe(eksik_ozet, use_container_width=True, hide_index=True) if not eksik_ozet.empty else st.success("Her şey tamam!")

            st.divider()
            f_col1, f_col2 = st.columns(2)
            emirler = ["Tümü"] + sorted(df_rapor['İş Emri'].unique().tolist())
            f_emir = f_col1.selectbox("📋 İş Emri Seçin:", emirler)
            temp_df = df_rapor[df_rapor['İş Emri'] == f_emir] if f_emir != "Tümü" else df_rapor
            mamuller = ["Tümü"] + sorted(temp_df['Mamül Adı'].dropna().unique().tolist())
            f_mamul = f_col2.selectbox("🏗️ Mamül Adı Seçin:", mamuller)

            filtrelenmis_df = temp_df.copy()
            if f_mamul != "Tümü": filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['Mamül Adı'] == f_mamul]

            st.dataframe(filtrelenmis_df, use_container_width=True, hide_index=True)
        else:
            st.info("Raporlanacak veri bulunamadı.")

    # --- SAYFA SONU İMZASI ---
    st.markdown("---")
    col_sign1, col_sign2 = st.columns([3, 1])
    with col_sign2:
        st.markdown("<div style='text-align: right;'><p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p><p style='margin:0; font-size: 12px; color: gray;'>BRN 2026</p></div>", unsafe_allow_html=True)
