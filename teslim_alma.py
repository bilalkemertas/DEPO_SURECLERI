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
    # Hata önleyici: Sözlük yapısını garantiye alıyoruz
    if 'mk_gecici_liste' not in st.session_state: st.session_state.mk_gecici_liste = {}
    if 'sip_gecici_liste' not in st.session_state: st.session_state.sip_gecici_liste = []
    if 'new_po_no' not in st.session_state: st.session_state.new_po_no = None

def clean_code(val):
    if pd.isna(val): return ""
    val = str(val).split(".")[0].strip()
    return re.sub(r'\D', '', val)

def run(conn):
    init_state()
    LOCAL_MAPPING_FILE = "eslesme_hafizasi.csv"

    # Kompakt tasarım CSS
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 15px !important; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; }
        .stVerticalBlock { gap: 0.8rem !important; }
        .stButton button { height: 2.5rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- ÜST NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        with c_nav1:
            if st.button("⬅️ ANA MENÜ", use_container_width=True):
                st.session_state.teslim_page = 'menu'
                st.session_state.page = 'home'
                st.rerun()
        with c_nav2:
            if st.session_state.teslim_page in ['kabul', 'secim', 'olustur']:
                prev = 'menu' if st.session_state.teslim_page in ['secim', 'olustur'] else 'secim'
                if st.button("⬅️ GERİ", use_container_width=True):
                    st.session_state.teslim_page = prev
                    st.rerun()
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

        st.write("📂 **Excel ile SAS Oluştur (DataGrid)**")
        up_sas = st.file_uploader("DataGrid Dosyası Yükle", type=['xlsx'], key="sas_excel_up", label_visibility="collapsed")
        
        if up_sas:
            try:
                df_excel = pd.read_excel(up_sas, sheet_name='Main sheet')
                st.session_state['last_uploaded_excel'] = df_excel 
                mapping_df = pd.read_csv(LOCAL_MAPPING_FILE) if os.path.exists(LOCAL_MAPPING_FILE) else pd.DataFrame()
                if not mapping_df.empty:
                    mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
                    mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                    df_excel['TEMİZ_KOD'] = df_excel['Malzeme Kodu'].apply(clean_code)
                    sas_ref = str(df_excel['Teslimat No'].iloc[0]).split(".")[0]
                    st.session_state.new_po_no = f"SAS-{sas_ref}"
                    df_merged = df_excel.merge(mapping_df[['FORM_TEMİZ', 'BRN KOD', 'BRN ÜRÜN ADI']], left_on='TEMİZ_KOD', right_on='FORM_TEMİZ', how='left')
                    if st.button("🚀 EXCEL VERİLERİNİ AKTAR", use_container_width=True):
                        st.session_state.sip_gecici_liste = []
                        for i, row in df_merged.iterrows():
                            if pd.notna(row['BRN KOD']):
                                st.session_state.sip_gecici_liste.append({
                                    "Tedarikçi": sip_tedarikci, "Sipariş No": st.session_state.new_po_no, "Kalem No": (i + 1) * 10,
                                    "Stok Kodu": str(row['BRN KOD']), "Stok Adı": str(row['BRN ÜRÜN ADI']), "Sipariş Miktarı": float(row['Teslimat Miktarı']), 
                                    "Gelen Miktar": 0.0, "Birim": "ADET"
                                })
                        st.rerun()
            except Exception as e: st.error(f"Excel hatası: {e}")

    # --- 2. MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        df_s = veritabani.get_internal_data("Satin_Alma")
        df_b = df_s[(df_s['Sipariş Miktarı'] - df_s['Gelen Miktar']) > 0]
        t_list = ["Tümü"] + sorted(df_b['Tedarikçi'].dropna().unique().tolist())
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
                    st.session_state.mk_gecici_liste = {}; st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- 3. MAL KABUL GİRİŞ (CANLI LİSTE OPERASYONU) ---
    elif st.session_state.teslim_page == 'kabul':
        st.caption(f"**SAS:** {st.session_state.sel_siparis} | **İrsaliye:** {st.session_state.irsaliye_no}")

        # --- BARKOD PANELİ ---
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            scan_code = c1.text_input("🔍 Barkod (Parti No) Okutun:", key="scan_parti").strip()
            undo_mode = c2.checkbox("🔄 Geri Al", help="Okutulan barkodu listeden siler")
            
            if scan_code and 'last_uploaded_excel' in st.session_state:
                excel_df = st.session_state['last_uploaded_excel']
                found_in_excel = excel_df[excel_df['Parti No'].astype(str) == scan_code]
                
                if not found_in_excel.empty:
                    m_kod = clean_code(found_in_excel.iloc[0]['Malzeme Kodu'])
                    mapping_df = pd.read_csv(LOCAL_MAPPING_FILE) if os.path.exists(LOCAL_MAPPING_FILE) else pd.DataFrame()
                    if not mapping_df.empty:
                        mapping_df.columns = [str(c).strip().upper() for c in mapping_df.columns]
                        mapping_df['FORM_TEMİZ'] = mapping_df['FORM SÜNGER KOD'].apply(clean_code)
                        match_brn = mapping_df[mapping_df['FORM_TEMİZ'] == m_kod]
                        
                        if not match_brn.empty:
                            target_brn = match_brn.iloc[0]['BRN KOD']
                            
                            # Geri Al / Silme Modu
                            if undo_mode:
                                if scan_code in st.session_state.mk_gecici_liste:
                                    del st.session_state.mk_gecici_liste[scan_code]
                                    st.warning(f"🗑️ Barkod silindi: {scan_code}")
                            # Ekleme Modu
                            else:
                                mik = float(found_in_excel.iloc[0]['Teslimat Miktarı'])
                                st.session_state.mk_gecici_liste[scan_code] = {
                                    "Kod": target_brn, "Miktar": mik, "Barkod": scan_code
                                }
                                st.success(f"✅ Okundu: {match_brn.iloc[0]['BRN ÜRÜN ADI']} ({mik})")
                else: st.error("Parti No bulunamadı!")

        # --- LİSTE GÖRÜNÜMÜ ---
        df_s = veritabani.get_internal_data("Satin_Alma")
        sub = df_s[df_s['Sipariş No'] == st.session_state.sel_siparis].copy()
        
        # Hata koruması: ArrowTypeError için NaN temizliği
        sub['Stok Adı'] = sub['Stok Adı'].fillna("İSİMSİZ")
        sub['Stok Kodu'] = sub['Stok Kodu'].fillna("KODSUZ")
        sub['Gelen (Yeni)'] = 0.0
        sub['Okutulan Parti'] = ""
        
        # Barkod eşleştirme ve canlı güncelleme
        active_indices = []
        gecici_dict = st.session_state.get('mk_gecici_liste', {})
        for b_code, b_data in gecici_dict.items():
            mask = (sub['Stok Kodu'] == b_data['Kod']) & (sub['Gelen (Yeni)'] == 0)
            if mask.any():
                idx = sub[mask].index[0]
                sub.at[idx, 'Gelen (Yeni)'] = b_data['Miktar']
                sub.at[idx, 'Okutulan Parti'] = b_code
                active_indices.append(idx)

        # Okutulanları en üste çıkar
        sub['highlight'] = sub.index.isin(active_indices)
        sub = sub.sort_values(by='highlight', ascending=False).drop(columns=['highlight'])

        st.write("📊 **SAS Detay Kontrol Listesi**")
        st.dataframe(
            sub[['Kalem No', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen Miktar', 'Gelen (Yeni)', 'Okutulan Parti']], 
            use_container_width=True, hide_index=True,
            column_config={
                "Gelen (Yeni)": st.column_config.NumberColumn("Okutulan", format="%.2f"),
                "Okutulan Parti": st.column_config.TextColumn("Parti No")
            }
        )

        # --- KAYIT ---
        if st.session_state.mk_gecici_liste:
            st.divider()
            if st.button("🚀 TESLİMATI TAMAMLA", type="primary", use_container_width=True):
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                pers = st.session_state.get('kullanici_adi', "Sistem")
                
                for _, row in sub[sub['Gelen (Yeni)'] > 0].iterrows():
                    # Stok
                    m_stok = (df_stok['Kod'] == row['Stok Kodu']) & (df_stok.get('Tedarikçi Barkod', pd.Series()) == row['Okutulan Parti'])
                    if m_stok.any():
                        df_stok.loc[m_stok, 'Miktar'] += row['Gelen (Yeni)']
                    else:
                        df_stok = pd.concat([df_stok, pd.DataFrame([{
                            "Kod": row['Stok Kodu'], "İsim": row['Stok Adı'], "Adres": "DEPO-1", 
                            "Miktar": row['Gelen (Yeni)'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": row['Okutulan Parti']
                        }])], ignore_index=True)
                    
                    # SAS ve Hareket
                    df_s.loc[(df_s['Sipariş No'] == st.session_state.sel_siparis) & (df_s['Kalem No'] == row['Kalem No']), 'Gelen Miktar'] += row['Gelen (Yeni)']
                    df_har = pd.concat([df_har, pd.DataFrame([{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", 
                        "İş Emri": st.session_state.sel_siparis, "Kod": row['Stok Kodu'], "İsim": row['Stok Adı'], 
                        "Miktar": row['Gelen (Yeni)'], "Personel": pers, "Lot": st.session_state.irsaliye_no, "Tedarikçi Barkod": row['Okutulan Parti']
                    }])], ignore_index=True)

                veritabani.update_data("Stok", df_stok); veritabani.update_data("Satin_Alma", df_s); veritabani.update_data("Hareketler", df_har)
                st.session_state.mk_gecici_liste = {}; st.success("Kayıt Başarılı!"); st.rerun()

    # --- İMZA ---
    st.markdown("---")
    st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b></div>", unsafe_allow_html=True)
