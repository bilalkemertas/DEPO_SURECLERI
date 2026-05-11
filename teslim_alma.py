import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

def init_state():
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'menu'
    if 'sel_siparis' not in st.session_state: st.session_state.sel_siparis = None
    if 'sel_tedarikci' not in st.session_state: st.session_state.sel_tedarikci = None
    if 'irsaliye_no' not in st.session_state: st.session_state.irsaliye_no = ""
    if 'mk_gecici_liste' not in st.session_state or not isinstance(st.session_state.mk_gecici_liste, dict):
        st.session_state.mk_gecici_liste = {}
    if 'sip_gecici_liste' not in st.session_state: st.session_state.sip_gecici_liste = []
    if 'new_po_no' not in st.session_state: st.session_state.new_po_no = None

def clean_code(val):
    if pd.isna(val): return ""
    val = str(val).split(".")[0].strip()
    return re.sub(r'\D', '', val)

def fix_dataframe(df, columns=None):
    if df is None or df.empty:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- BARKOD İŞLEME FONKSİYONU (Dışarı Alındı) ---
def handle_barcode():
    # Input key'inden veriyi çek
    code = st.session_state.get(f"barkod_input_{st.session_state.scan_counter}", "").strip().split(".")[0]
    
    if not code:
        return

    ex_df = st.session_state.db_excel_data
    found = ex_df[(ex_df['Parti No'].astype(str) == code) & (ex_df['SAS_No'] == st.session_state.sel_siparis)]
    
    if found.empty:
        st.toast(f"❌ Barkod bulunamadı: {code}", icon="⚠️")
        return
    
    if code in st.session_state.mk_gecici_liste and not st.session_state.get('undo_active', False):
        st.toast(f"⚠️ Zaten okutuldu: {code}")
        return

    df_stok_local = st.session_state.full_stok_data
    if 'Tedarikçi Barkod' in df_stok_local.columns:
        if code in df_stok_local['Tedarikçi Barkod'].astype(str).values and not st.session_state.get('undo_active', False):
            st.toast(f"❌ Bu barkod zaten stokta var!", icon="🚫")
            return
    
    row = found.iloc[0]
    m_kod = clean_code(row['Malzeme Kodu'])
    LOCAL_MAPPING_FILE = "eslesme_hafizasi.csv"
    map_df = pd.read_csv(LOCAL_MAPPING_FILE) if os.path.exists(LOCAL_MAPPING_FILE) else pd.DataFrame()
    
    if not map_df.empty:
        map_df.columns = [str(c).strip().upper() for c in map_df.columns]
        map_df['FORM_TEMİZ'] = map_df['FORM SÜNGER KOD'].apply(clean_code)
        match = map_df[map_df['FORM_TEMİZ'] == m_kod]
        
        if not match.empty:
            brn_kod = match.iloc[0]['BRN KOD']
            if st.session_state.get('undo_active', False):
                if code in st.session_state.mk_gecici_liste: del st.session_state.mk_gecici_liste[code]
            else:
                st.session_state.mk_gecici_liste[code] = {
                    "Kod": brn_kod, 
                    "Miktar": float(row['Teslimat Miktarı']), 
                    "Ad": match.iloc[0]['BRN ÜRÜN ADI']
                }
            # Okuma başarılı olunca counter'ı artır ki input temizlensin
            st.session_state.scan_counter += 1

def run(conn):
    init_state()
    LOCAL_MAPPING_FILE = "eslesme_hafizasi.csv"

    # --- ÜST NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        with c_nav1:
            if st.button("⬅️ ANA MENÜ", use_container_width=True):
                for k in ['full_stok_data', 'full_sas_data', 'full_har_data', 'db_excel_data']:
                    if k in st.session_state: del st.session_state[k]
                st.session_state.teslim_page = 'menu'; st.session_state.page = 'home'; st.rerun()
        with c_nav2:
            if st.session_state.teslim_page in ['kabul', 'secim', 'olustur']:
                prev = 'menu' if st.session_state.teslim_page in ['secim', 'olustur'] else 'secim'
                if st.button("⬅️ GERİ", use_container_width=True):
                    st.session_state.teslim_page = prev; st.rerun()
        st.divider()

    # --- 0. ANA MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        col1, col2 = st.columns(2)
        with col1:
            st.button("📦 MAL KABUL", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'secim'))
        with col2:
            st.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'olustur'))

    # --- 1. SAS OLUŞTURMA ---
    elif st.session_state.teslim_page == 'olustur':
        if not st.session_state.new_po_no:
            st.session_state.new_po_no = f"SAS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sip_tedarikci = c1.text_input("🏢 Tedarikçi:", placeholder="Zorunlu").upper().strip()
            sip_no = c2.text_input("📄 SAS No:", value=st.session_state.new_po_no, disabled=True)
        
        up_sas = st.file_uploader("DataGrid Dosyası Yükle", type=['xlsx'], key="sas_excel_up")
        if up_sas:
            try:
                df_excel = fix_dataframe(pd.read_excel(up_sas, sheet_name='Main sheet'))
                if not df_excel.empty:
                    df_excel['Parti No'] = df_excel['Parti No'].astype(str).str.strip().str.split(".").str[0]
                    mapping_df = pd.read_csv(LOCAL_MAPPING_FILE) if os.path.exists(LOCAL_MAPPING_FILE) else pd.DataFrame()
                    if not mapping_df.empty:
                        mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
                        mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                        df_excel['TEMİZ_KOD'] = df_excel['Malzeme Kodu'].apply(clean_code)
                        sas_ref = str(df_excel['Teslimat No'].iloc[0]).split(".")[0]
                        st.session_state.new_po_no = f"SAS-{sas_ref}"
                        df_merged = df_excel.merge(mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], left_on='TEMİZ_KOD', right_on='FORM_TEMİZ', how='left')
                        
                        if st.button("🚀 EXCEL VERİLERİNİ GITHUB'A AKTAR", use_container_width=True):
                            db_excel = veritabani.get_github_data()
                            new_records = df_excel[['Parti No', 'Malzeme Kodu', 'Teslimat Miktarı']].copy()
                            new_records['SAS_No'] = st.session_state.new_po_no
                            db_excel = pd.concat([db_excel, new_records], ignore_index=True).drop_duplicates(subset=['Parti No', 'SAS_No'])
                            basari = veritabani.update_github_data(db_excel, commit_message=f"Yeni SAS: {st.session_state.new_po_no}")
                            if basari:
                                st.session_state.sip_gecici_liste = []
                                for i, row in df_merged.iterrows():
                                    if pd.notna(row['BRN KOD']):
                                        st.session_state.sip_gecici_liste.append({
                                            "Tedarikçi": sip_tedarikci, "Sipariş No": st.session_state.new_po_no, "Kalem No": (i + 1) * 10,
                                            "Stok Kodu": str(row['BRN KOD']), "Stok Adı": str(row['BRN ÜRÜN ADI']), "Sipariş Miktarı": float(row['Teslimat Miktarı']),
                                            "Gelen Miktar": 0.0, "Birim": "ADET"
                                        })
                                st.rerun()
            except Exception as e: st.error(f"Hata: {e}")
        
        st.divider()
        if st.session_state.sip_gecici_liste:
            if st.button("🚀 SİPARİŞİ DRIVE'A KAYDET", type="primary", use_container_width=True):
                df_m = fix_dataframe(veritabani.get_internal_data("Satin_Alma"), columns=['Sipariş No', 'Tedarikçi', 'Sipariş Miktarı', 'Gelen Miktar'])
                df_son = pd.concat([df_m, pd.DataFrame(st.session_state.sip_gecici_liste)], ignore_index=True)
                veritabani.update_data("Satin_Alma", df_son)
                st.session_state.sip_gecici_liste = []; st.session_state.new_po_no = None; st.session_state.teslim_page = 'menu'; st.rerun()

    # --- 2. MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        df_s = fix_dataframe(veritabani.get_internal_data("Satin_Alma"), columns=['Sipariş No', 'Tedarikçi', 'Sipariş Miktarı', 'Gelen Miktar'])
        df_s['Sipariş Miktarı'] = pd.to_numeric(df_s['Sipariş Miktarı'], errors='coerce').fillna(0)
        df_s['Gelen Miktar'] = pd.to_numeric(df_s['Gelen Miktar'], errors='coerce').fillna(0)
        df_b = df_s[(df_s['Sipariş Miktarı'] - df_s['Gelen Miktar']) > 0]
        t_list = ["Tümü"] + sorted(df_b['Tedarikçi'].dropna().unique().tolist()) if not df_b.empty else ["Tümü"]
        
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sec_ted = c1.selectbox("🏢 Tedarikçi:", t_list)
            sip_f = df_b if sec_ted == "Tümü" else df_b[df_b['Tedarikçi'] == sec_ted]
            sec_sip = c2.selectbox("📄 SAS No:", ["Seçiniz..."] + sorted(sip_f['Sipariş No'].unique().tolist()))
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()
            if st.button("🚀 İLERLE", use_container_width=True, type="primary"):
                if sec_sip != "Seçiniz..." and irs:
                    st.session_state.sel_tedarikci = df_b[df_b['Sipariş No'] == sec_sip].iloc[0]['Tedarikçi']
                    st.session_state.sel_siparis = sec_sip; st.session_state.irsaliye_no = irs
                    st.session_state.mk_gecici_liste = {}
                    st.session_state.scan_counter = 0 # Sıfırla
                    st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
                    st.session_state.db_excel_data = veritabani.get_github_data()
                    st.session_state.full_sas_data = df_s
                    st.session_state.full_har_data = veritabani.get_internal_data("Hareketler")
                    st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- 3. MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        st.caption(f"**SAS:** {st.session_state.sel_siparis} | **Tedarikçi:** {st.session_state.sel_tedarikci} | **İrsaliye:** {st.session_state.irsaliye_no}")

        if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0

        with st.container(border=True):
            c_op1, c_op2 = st.columns([4, 1])
            # Enter'a basıldığı an handle_barcode fonksiyonunu çalıştırır
            c_op1.text_input("🔍 Barkod Okutun:", 
                           key=f"barkod_input_{st.session_state.scan_counter}", 
                           on_change=handle_barcode)
            st.checkbox("🔄 Geri Al", key="undo_active")

        # Canlı Tabloyu Göster
        sub = st.session_state.full_sas_data[st.session_state.full_sas_data['Sipariş No'] == st.session_state.sel_siparis].copy()
        sub['Gelen (Yeni)'] = 0.0; sub['Parti No'] = ""
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sub['Stok Kodu'] == b_data['Kod']) & (sub['Gelen (Yeni)'] == 0)
            if mask.any():
                idx = sub[mask].index[0]
                sub.at[idx, 'Gelen (Yeni)'] = b_data['Miktar']
                sub.at[idx, 'Parti No'] = b_code
        st.dataframe(sub[['Kalem No', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen Miktar', 'Gelen (Yeni)', 'Parti No']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 TÜMÜNÜ STOĞA KAYDET", type="primary", use_container_width=True):
                df_stok = st.session_state.full_stok_data
                df_s = st.session_state.full_sas_data
                df_har = st.session_state.full_har_data
                for _, row in sub[sub['Gelen (Yeni)'] > 0].iterrows():
                    df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": row['Stok Kodu'], "İsim": row['Stok Adı'], "Adres": "DEPO-1", "Miktar": row['Gelen (Yeni)'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": row['Parti No']}])], ignore_index=True)
                    df_s.loc[(df_s['Sipariş No'] == st.session_state.sel_siparis) & (df_s['Kalem No'] == row['Kalem No']), 'Gelen Miktar'] = \
                        pd.to_numeric(df_s.loc[(df_s['Sipariş No'] == st.session_state.sel_siparis) & (df_s['Kalem No'] == row['Kalem No']), 'Gelen Miktar'], errors='coerce').fillna(0) + row['Gelen (Yeni)']
                    df_har = pd.concat([df_har, pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis, "Kod": row['Stok Kodu'], "İsim": row['Stok Adı'], "Miktar": row['Gelen (Yeni)'], "Personel": "Bilal", "Lot": st.session_state.irsaliye_no, "Tedarikçi Barkod": row['Parti No'], "Adres": "DEPO-1", "Durum": "Kullanılabilir"}])], ignore_index=True)
                veritabani.update_data("Stok", df_stok); veritabani.update_data("Satin_Alma", df_s); veritabani.update_data("Hareketler", df_har)
                st.session_state.mk_gecici_liste = {}; st.success("✅ Kayıt Tamamlandı!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 {st.session_state.get('kullanici_adi', 'Bilal Kemertaş')}</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
