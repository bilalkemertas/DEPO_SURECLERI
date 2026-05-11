import streamlit as st
import pd
import veritabani
import re
import os
from datetime import datetime

# --- 1. AYARLAR VE YARDIMCI FONKSİYONLAR ---
LOCAL_MAPPING_FILE = "eslesme_hafizasi.csv"

def init_state():
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'menu'
    if 'sel_siparis' not in st.session_state: st.session_state.sel_siparis = None
    if 'irsaliye_no' not in st.session_state: st.session_state.irsaliye_no = ""
    if 'mk_gecici_liste' not in st.session_state: st.session_state.mk_gecici_liste = {}
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0

def clean_code(val):
    if pd.isna(val): return ""
    val = str(val).split(".")[0].strip()
    return re.sub(r'\D', '', val)

def fix_dataframe(df, columns=None):
    if df is None or df.empty:
        return pd.DataFrame(columns=columns) if columns else pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --- 2. BARKOD İŞLEME (TÜM BAĞIMSIZLIKLAR GİDERİLDİ) ---
def handle_barcode():
    # Güncel barkodu al
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    
    if not code:
        return

    # Gerekli veriler session_state'de var mı kontrol et
    if 'db_excel_data' not in st.session_state or 'sel_siparis' not in st.session_state:
        st.toast("⚠️ Hafıza hatası! Lütfen sayfayı yenileyip tekrar deneyin.")
        return

    ex_df = st.session_state.db_excel_data
    found = ex_df[(ex_df['Parti No'].astype(str) == code) & (ex_df['SAS_No'] == st.session_state.sel_siparis)]
    
    if found.empty:
        st.toast(f"❌ Barkod bulunamadı: {code}", icon="🚫")
        return
    
    # Eşleşme dosyasına bak
    map_df = pd.read_csv(LOCAL_MAPPING_FILE) if os.path.exists(LOCAL_MAPPING_FILE) else pd.DataFrame()
    if map_df.empty:
        st.toast("⚠️ Eşleşme hafızası (CSV) bulunamadı!")
        return

    row = found.iloc[0]
    m_kod = clean_code(row['Malzeme Kodu'])
    
    map_df.columns = [str(c).strip().upper() for c in map_df.columns]
    map_df['FORM_TEMİZ'] = map_df['FORM SÜNGER KOD'].apply(clean_code)
    match = map_df[map_df['FORM_TEMİZ'] == m_kod]
    
    if not match.empty:
        brn_kod = match.iloc[0]['BRN KOD']
        st.session_state.mk_gecici_liste[code] = {
            "Kod": brn_kod, 
            "Miktar": float(row['Teslimat Miktarı']), 
            "Ad": match.iloc[0]['BRN ÜRÜN ADI']
        }
        st.toast(f"✅ {brn_kod} listeye eklendi.", icon="📥")
        # Barkod okunduysa input kutusunu yenilemek için counter artır
        st.session_state.scan_counter += 1
    else:
        st.toast(f"❌ Bu malzemenin BRN karşılığı yok: {m_kod}")

# --- 3. ANA EKRAN ---
def run(conn):
    init_state()

    # --- ÜST NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        c_nav = st.columns([1, 1, 4])
        if c_nav[0].button("⬅️ ANA MENÜ"):
            st.session_state.teslim_page = 'menu'; st.rerun()
        if c_nav[1].button("⬅️ GERİ"):
            st.session_state.teslim_page = 'secim' if st.session_state.teslim_page == 'kabul' else 'menu'
            st.rerun()
        st.divider()

    # --- MAL KABUL SEÇİM ---
    if st.session_state.teslim_page == 'secim':
        df_s = fix_dataframe(veritabani.get_internal_data("Satin_Alma"))
        sec_sip = st.selectbox("📄 SAS No Seçin:", ["Seçiniz..."] + sorted(df_s['Sipariş No'].unique().tolist()))
        irs = st.text_input("🧾 İrsaliye No:").upper().strip()
        
        if st.button("🚀 MAL KABULÜ BAŞLAT", use_container_width=True, type="primary"):
            if sec_sip != "Seçiniz..." and irs:
                st.session_state.sel_siparis = sec_sip
                st.session_state.irsaliye_no = irs
                st.session_state.db_excel_data = veritabani.get_github_data()
                st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
                st.session_state.full_sas_data = df_s
                st.session_state.full_har_data = veritabani.get_internal_data("Hareketler")
                st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        st.subheader(f"📦 {st.session_state.sel_siparis}")
        
        with st.container(border=True):
            # Input kutusu
            st.text_input("🔍 Barkod Okutun ve Enter'a Basın:", 
                           key=f"barkod_input_{st.session_state.scan_counter}", 
                           on_change=handle_barcode)
        
        # TABLO GÖSTERİMİ
        sub = st.session_state.full_sas_data[st.session_state.full_sas_data['Sipariş No'] == st.session_state.sel_siparis].copy()
        sub['Gelen (Yeni)'] = 0.0
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sub['Stok Kodu'] == b_data['Kod']) & (sub['Gelen (Yeni)'] == 0)
            if mask.any():
                idx = sub[mask].index[0]
                sub.at[idx, 'Gelen (Yeni)'] = b_data['Miktar']
        
        st.dataframe(sub[['Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 VERİLERİ KAYDET", type="primary", use_container_width=True):
                # Veritabanı kayıt işlemleri burada yapılacak (mevcut update_data fonksiyonlarınla)
                st.success("Kayıt yapılıyor...")
                # ... (mevcut kayıt kodların)
                st.session_state.mk_gecici_liste = {}; st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b></div>", unsafe_allow_html=True)
