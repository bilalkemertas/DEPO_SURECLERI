import streamlit as st
import pandas as pd
import veritabani
import re
import os
from datetime import datetime

# --- AYARLAR ---
LOCAL_MAPPING_FILE = "hafiza.csv"

def init_state():
    """Hafızayı zırhlı hale getirir, yoksa oluşturur."""
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'menu'
    if 'mk_gecici_liste' not in st.session_state: st.session_state.mk_gecici_liste = {}
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0
    if 'full_sas_data' not in st.session_state: st.session_state.full_sas_data = pd.DataFrame()

def clean_code(val):
    if pd.isna(val): return ""
    return str(val).split(".")[0].strip().upper()

def load_safe_mapping():
    try:
        df_drive = veritabani.get_internal_data("Eşleşmeler")
        if df_drive is not None and not df_drive.empty:
            df_drive.to_csv(LOCAL_MAPPING_FILE, index=False)
            return df_drive
    except: pass
    if os.path.exists(LOCAL_MAPPING_FILE):
        try: return pd.read_csv(LOCAL_MAPPING_FILE)
        except: return pd.DataFrame()
    return pd.DataFrame()

# --- BARKOD İŞLEME (ZIRHLI VE HATASIZ) ---
def handle_barcode():
    # HATA ÖNLEYİCİ: Counter yoksa hemen oluştur
    if 'scan_counter' not in st.session_state:
        st.session_state.scan_counter = 0
    
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    
    if not code: return

    map_df = load_safe_mapping()
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    if sas_df.empty:
        st.toast("⚠️ Önce bir SAS seçmelisin patron!", icon="👀")
        return

    # Barkodu SAS içinde ara
    target_col = 'Tedarikçi Barkodu'
    found = sas_df[sas_df[target_col].astype(str) == code]
    
    if found.empty:
        st.toast(f"❌ Barkod SAS listesinde yok: {code}", icon="🚫")
        return

    row = found.iloc[0]
    m_kod = clean_code(row['Stok Kodu'])
    
    final_kod = row['Stok Kodu']
    final_ad = row['Stok Adı']
    
    if not map_df.empty:
        map_df.columns = [str(c).strip().upper() for c in map_df.columns]
        form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
        
        if form_col:
            match = map_df[map_df[form_col].apply(clean_code) == m_kod]
            if not match.empty:
                brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
                brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c or "ÜRÜN" in c), "BRN ÜRÜN ADI")
                
                final_kod = match.iloc[0][brn_k_col]
                final_ad = match.iloc[0][brn_a_col]
                st.toast(f"✅ {final_kod} listeye girdi.", icon="📥")

    # STANDART ANAHTARLARLA KAYDET (KeyError Önleyici)
    st.session_state.mk_gecici_liste[code] = {
        "Kod": final_kod, 
        "Ad": final_ad, 
        "Miktar": float(row['Sipariş Miktarı'])
    }
    st.session_state.scan_counter += 1

def run(conn):
    init_state() # En başta her şeyi kur

    # --- ÜST NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        if c_nav1.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.teslim_page = 'menu'; st.rerun()
        if c_nav2.button("⬅️ GERİ", use_container_width=True):
            st.session_state.teslim_page = 'menu' if st.session_state.teslim_page != 'kabul' else 'secim'
            st.rerun()
        st.divider()

    # --- MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'; st.rerun()
        if c2.button("📝 SAS OLUŞTUR (EXCEL)", use_container_width=True):
            st.session_state.teslim_page = 'olustur'; st.rerun()

    # --- SAS OLUŞTURMA ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Excel'den SAS Oluştur")
        with st.container(border=True):
            ted = st.text_input("🏢 Tedarikçi Adı:").upper().strip()
            up = st.file_uploader("Excel Yükle (Main sheet)", type=['xlsx'])
            if up and ted:
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                if st.button("🚀 DRIVE'A MÜHÜRLE", use_container_width=True, type="primary"):
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

    # --- MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        st.subheader("🔎 SAS Seçimi")
        df_s = veritabani.get_internal_data("Satin_Alma")
        with st.container(border=True):
            sec_sip = st.selectbox("📄 SAS Seçin:", ["Seçiniz..."] + sorted(df_s['Sipariş No'].unique().tolist()) if not df_s.empty else ["Boş"])
            if st.button("🚀 DEVAM", use_container_width=True, type="primary") and sec_sip != "Seçiniz...":
                st.session_state.sel_siparis = sec_sip
                st.session_state.full_sas_data = df_s[df_s['Sipariş No'] == sec_sip]
                st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 SAS: {st.session_state.sel_siparis}")
        with st.container(border=True):
            # Key hatasını önlemek için dinamik key kullanımı
            st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        # CANLI TABLO
        sas_filter = st.session_state.full_sas_data.copy()
        sas_filter['Gelen (Yeni)'] = 0.0
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter['Tedarikçi Barkodu'].astype(str) == str(b_code))
            if mask.any(): 
                sas_filter.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']
        
        st.dataframe(sas_filter[['Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 STOĞA AKTARIMI TAMAMLA", type="primary", use_container_width=True):
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                df_sas_up = veritabani.get_internal_data("Satin_Alma")
                
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    # 1. Stok Kaydı
                    new_stok = pd.DataFrame([{
                        "Kod": b_data['Kod'], "İsim": b_data['Ad'], "Adres": "DEPO-1", 
                        "Miktar": b_data['Miktar'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": b_code
                    }])
                    df_stok = pd.concat([df_stok, new_stok], ignore_index=True)

                    # 2. Hareket Kaydı
                    new_har = pd.DataFrame([{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", 
                        "İş Emri": st.session_state.sel_siparis, "Kod": b_data['Kod'], "İsim": b_data['Ad'], 
                        "Miktar": b_data['Miktar'], "Personel": "Bilal", "Adres": "DEPO-1", "Tedarikçi Barkod": b_code
                    }])
                    df_har = pd.concat([df_har, new_har], ignore_index=True)

                    # 3. SAS Güncelleme
                    df_sas_up.loc[(df_sas_up['Sipariş No'] == st.session_state.sel_siparis) & 
                                  (df_sas_up['Tedarikçi Barkodu'].astype(str) == b_code), 'Gelen Miktar'] = b_data['Miktar']
                
                veritabani.update_data("Stok", df_stok)
                veritabani.update_data("Hareketler", df_har)
                veritabani.update_data("Satin_Alma", df_sas_up)
                
                st.session_state.mk_gecici_liste = {}
                st.success("✅ Depoya başarıyla işlendi patron!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
