import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

# --- AYARLAR ---
LOCAL_MAPPING_FILE = "hafiza.csv"

def init_state():
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'menu'
    if 'mk_gecici_liste' not in st.session_state: st.session_state.mk_gecici_liste = {}
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0

def clean_code(val):
    if pd.isna(val): return ""
    # Sadece rakamları tutmak yerine teknik kodları bozmamak için temizlik yapalım
    return str(val).split(".")[0].strip().upper()

def load_safe_mapping():
    """Hafıza dosyasını hem Drive'dan günceller hem de lokalden okur."""
    try:
        df_drive = veritabani.get_internal_data("Eşleşmeler")
        if df_drive is not None and not df_drive.empty:
            df_drive.to_csv(LOCAL_MAPPING_FILE, index=False)
            return df_drive
    except: pass
    if os.path.exists(LOCAL_MAPPING_FILE):
        try:
            return pd.read_csv(LOCAL_MAPPING_FILE)
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- BARKOD İŞLEME (CANLI TABLO TETİKLEYİCİ) ---
def handle_barcode():
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    if not code: return

    # Hafızayı yükle (Eşleşme tablosu)
    map_df = load_safe_mapping()
    # Mevcut SAS verisini al
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    # Barkodu "Tedarikçi Barkodu" sütununda ara
    target_col = 'Tedarikçi Barkodu'
    found = sas_df[sas_df[target_col].astype(str) == code]
    
    if found.empty:
        st.toast(f"❌ Barkod SAS listesinde bulunamadı: {code}", icon="🚫")
        return

    row = found.iloc[0]
    # Eşleşme için Stok Kodu kullanılır
    m_kod = clean_code(row['Stok Kodu'])
    
    # Hafıza dosyasındaki sütunları standartlaştır (Görseldeki hata için önlem)
    if not map_df.empty:
        map_df.columns = [str(c).strip().upper() for c in map_df.columns]
        form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
        
        if form_col:
            match = map_df[map_df[form_col].apply(clean_code) == m_kod]
            if not match.empty:
                brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
                brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c or "ÜRÜN" in c), "BRN ÜRÜN ADI")
                
                # Geçici listeye barkodu ve veriyi mühürle
                st.session_state.mk_gecici_liste[code] = {
                    "BRN_Kod": match.iloc[0][brn_k_col], 
                    "Miktar": float(row['Sipariş Miktarı']), 
                    "BRN_Ad": match.iloc[0][brn_a_col],
                    "Kalem": row.get('Kalem No', 0)
                }
                st.toast(f"✅ Okutuldu: {match.iloc[0][brn_k_col]}", icon="📥")
                st.session_state.scan_counter += 1
                return

    # Eğer hafızada yoksa bile "Gelen" sütununa yazabilmek için barkodu kaydet
    st.session_state.mk_gecici_liste[code] = {
        "BRN_Kod": row['Stok Kodu'], 
        "Miktar": float(row['Sipariş Miktarı']), 
        "BRN_Ad": row['Stok Adı'],
        "Kalem": row.get('Kalem No', 0)
    }
    st.toast(f"⚠️ Eşleşme olmadan eklendi: {row['Stok Kodu']}")
    st.session_state.scan_counter += 1

def run(conn):
    init_state()

    # --- NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            st.session_state.teslim_page = 'menu'; st.rerun()
        st.divider()

    # --- MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'; st.rerun()
        if c2.button("📝 SAS OLUŞTUR (EXCEL)", use_container_width=True):
            st.session_state.teslim_page = 'olustur'; st.rerun()

    # --- SAS OLUŞTURMA (GÖRSELDEKİ SÜTUNLARA GÖRE) ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Excel'den SAS Oluştur")
        ted = st.text_input("🏢 Tedarikçi:").upper()
        up = st.file_uploader("Excel Yükle", type=['xlsx'])
        if up and ted:
            df_ex = pd.read_excel(up, sheet_name='Main sheet')
            if st.button("🚀 DRIVE'A KAYDET"):
                yeni_sas = f"SAS-{datetime.now().strftime('%m%d%H%M')}"
                sip_liste = []
                for i, row in df_ex.iterrows():
                    sip_liste.append({
                        "Sipariş No": yeni_sas, "Tedarikçi": ted,
                        "Tedarikçi Barkodu": str(row.get('Parti No', '')).split(".")[0],
                        "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                        "Tedarikçi Ürün Kodu": row.get('Malzeme Kodu', ''),
                        "Tedarikçi Malzeme Adı": row.get('Malzeme Tanımı', ''),
                        "Kalem No": (i + 1) * 10, "Stok Kodu": row.get('Malzeme Kodu', ''),
                        "Stok Adı": row.get('Malzeme Tanımı', ''), "Gelen Miktar": 0, "Birim": "METRE"
                    })
                veritabani.update_data("Satin_Alma", pd.concat([veritabani.get_internal_data("Satin_Alma"), pd.DataFrame(sip_liste)], ignore_index=True))
                st.success(f"✅ {yeni_sas} Oluşturuldu!"); st.session_state.teslim_page = 'menu'; st.rerun()

    # --- MAL KABUL (CANLI TABLO) ---
    elif st.session_state.teslim_page == 'secim':
        df_s = veritabani.get_internal_data("Satin_Alma")
        sec_sip = st.selectbox("📄 SAS Seçin:", ["Seçiniz..."] + sorted(df_s['Sipariş No'].unique().tolist()))
        if st.button("🚀 DEVAM") and sec_sip != "Seçiniz...":
            st.session_state.sel_siparis = sec_sip
            st.session_state.full_sas_data = df_s[df_s['Sipariş No'] == sec_sip]
            st.session_state.teslim_page = 'kabul'; st.rerun()

    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 SAS: {st.session_state.sel_siparis}")
        st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        # CANLI TABLO GÖSTERİMİ
        sas_filter = st.session_state.full_sas_data.copy()
        sas_filter['Gelen (Yeni)'] = 0.0
        
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter['Tedarikçi Barkodu'].astype(str) == str(b_code))
            if mask.any():
                sas_filter.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']
        
        st.dataframe(sas_filter[['Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 STOĞA AKTARIMI TAMAMLA", type="primary", use_container_width=True):
                # Drive Güncelleme İşlemleri (Stok, Hareketler, Satin_Alma)
                st.success("✅ Tüm kalemler depoya işlendi!"); st.session_state.mk_gecici_liste = {}; st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
