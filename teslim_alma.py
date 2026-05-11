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
    val = str(val).split(".")[0].strip()
    return re.sub(r'\D', '', val)

# --- 🛠️ OTOMATİK HAFIZA TAMİR VE SENKRONİZASYON ---
def load_safe_mapping():
    """Lokal CSV boşsa veya yoksa Drive'dan çeker ve dosyayı otomatik doldurur."""
    df_final = pd.DataFrame()
    
    # 1. Adım: Yerel dosyayı kontrol et
    if os.path.exists(LOCAL_MAPPING_FILE):
        try:
            df_final = pd.read_csv(LOCAL_MAPPING_FILE)
            if not df_final.empty:
                return df_final
        except Exception:
            pass # Okuma hatası veya boş dosya durumunda 2. adıma geç

    # 2. Adım: Yerel dosya boşsa veya yoksa Drive'dan çek
    try:
        df_drive = veritabani.get_internal_data("Eşleşmeler")
        if df_drive is not None and not df_drive.empty:
            # Sütunları standartlaştır ve mühürle
            df_drive.to_csv(LOCAL_MAPPING_FILE, index=False)
            st.toast("🔄 Hafıza dosyası Drive'dan otomatik güncellendi.", icon="ℹ️")
            return df_drive
    except Exception as e:
        st.error(f"🚨 Drive'dan hafıza çekilemedi: {e}")
    
    return df_final

# --- BARKOD İŞLEME ---
def handle_barcode():
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    if not code: return

    # Hafızayı yükle (Boşsa otomatik tamir eder)
    map_df = load_safe_mapping()
    if map_df.empty:
        st.toast("🚨 Hafıza (hafiza.csv) hala boş! Drive 'Eşleşmeler' sekmesini kontrol et.", icon="🚨")
        return

    map_df.columns = [str(c).strip().upper() for c in map_df.columns]
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    target_col = 'Tedarikçi Barkodu'
    found = sas_df[(sas_df[target_col].astype(str) == code) & 
                   (sas_df['Sipariş No'] == st.session_state.sel_siparis)]
    
    if found.empty:
        st.toast(f"❌ Barkod SAS'ta yok: {code}", icon="🚫")
        return

    row = found.iloc[0]
    m_kod = clean_code(row['Stok Kodu'])
    
    # Dinamik Sütun Bulma
    form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
    
    if form_col:
        map_df['FORM_TEMİZ'] = map_df[form_col].apply(clean_code)
        match = map_df[map_df['FORM_TEMİZ'] == m_kod]
        
        if not match.empty:
            brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
            brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c), "BRN ÜRÜN ADI")
            
            st.session_state.mk_gecici_liste[code] = {
                "Kod": match.iloc[0][brn_k_col], 
                "Miktar": float(row['Sipariş Miktarı']), 
                "Ad": match.iloc[0][brn_a_col]
            }
            st.toast(f"✅ Okundu: {match.iloc[0][brn_k_col]}", icon="📥")
            st.session_state.scan_counter += 1
        else:
            st.toast(f"❓ Eşleşme yok: {m_kod}", icon="🔍")
    else:
        st.toast("🚨 Hafıza dosyasında 'FORM KOD' sütunu bulunamadı!", icon="🚨")

def run(conn):
    init_state()

    # --- NAVİGASYON ---
    if st.session_state.teslim_page != 'menu':
        c_nav = st.columns([1.5, 1.5, 4])
        if c_nav[0].button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.teslim_page = 'menu'; st.rerun()
        if c_nav[1].button("⬅️ GERİ", use_container_width=True):
            st.session_state.teslim_page = 'menu'; st.rerun()
        st.divider()

    # --- 0. MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'; st.rerun()
        if c2.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'olustur'; st.rerun()

    # --- 1. SAS OLUŞTURMA (PARTİ NO -> TEDARİKÇİ BARKODU) ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Yeni SAS Oluştur")
        with st.container(border=True):
            ted = st.text_input("🏢 Tedarikçi Adı:").upper().strip()
            up = st.file_uploader("Excel Yükle (Main sheet)", type=['xlsx'])
            
            if up and ted:
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                df_ex.columns = [str(c).strip() for c in df_ex.columns]
                
                if 'Parti No' in df_ex.columns:
                    st.success(f"✅ {len(df_ex)} satır analiz edildi.")
                    if st.button("🚀 SAS'I DRIVE'A MÜHÜRLE", use_container_width=True, type="primary"):
                        yeni_sas_no = f"SAS-{datetime.now().strftime('%m%d%H%M')}"
                        sip_liste = []
                        for i, row in df_ex.iterrows():
                            sip_liste.append({
                                "Sipariş No": yeni_sas_no, "Tedarikçi": ted,
                                "Tedarikçi Barkodu": str(row['Parti No']).split(".")[0],
                                "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                                "Tedarikçi Ürün Kodu": row.get('Malzeme Kodu', ''),
                                "Tedarikçi Malzeme Adı": row.get('Malzeme Tanımı', ''),
                                "Kalem No": (i + 1) * 10, "Stok Kodu": row.get('Malzeme Kodu', ''),
                                "Stok Adı": row.get('Malzeme Tanımı', ''), "Gelen Miktar": 0, "Birim": "ADET"
                            })
                        df_db = veritabani.get_internal_data("Satin_Alma")
                        df_final = pd.concat([df_db, pd.DataFrame(sip_liste)], ignore_index=True)
                        veritabani.update_data("Satin_Alma", df_final)
                        st.success(f"✅ {yeni_sas_no} oluşturuldu!"); st.session_state.teslim_page = 'menu'; st.rerun()

    # --- 2. MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        st.subheader("🔎 Kabul Edilecek SAS")
        df_s = veritabani.get_internal_data("Satin_Alma")
        df_s.columns = [str(c).strip() for c in df_s.columns]
        
        with st.container(border=True):
            sip_list = sorted(df_s['Sipariş No'].unique().tolist()) if not df_s.empty else []
            sec_sip = st.selectbox("📄 SAS No Seçin:", ["Seçiniz..."] + sip_list)
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()
            if st.button("🚀 DEVAM ET", use_container_width=True, type="primary"):
                if sec_sip != "Seçiniz..." and irs:
                    st.session_state.sel_siparis = sec_sip
                    st.session_state.irsaliye_no = irs
                    st.session_state.full_sas_data = df_s
                    st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
                    st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- 3. MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 {st.session_state.sel_siparis} | {st.session_state.irsaliye_no}")
        with st.container(border=True):
            st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        sas_filter = st.session_state.full_sas_data[st.session_state.full_sas_data['Sipariş No'] == st.session_state.sel_siparis].copy()
        sas_filter['Gelen (Yeni)'] = 0.0
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter['Tedarikçi Barkodu'].astype(str) == str(b_code))
            if mask.any(): sas_filter.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']
        
        st.dataframe(sas_filter[['Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 TÜMÜNÜ STOĞA KAYDET", type="primary", use_container_width=True):
                df_stok = st.session_state.full_stok_data
                df_har = veritabani.get_internal_data("Hareketler")
                df_sas_up = veritabani.get_internal_data("Satin_Alma")
                
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    new_stok = pd.DataFrame([{"Kod": b_data['Kod'], "İsim": b_data['Ad'], "Adres": "DEPO-1", "Miktar": b_data['Miktar'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": b_code}])
                    df_stok = pd.concat([df_stok, new_stok], ignore_index=True)
                    new_har = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis, "Kod": b_data['Kod'], "İsim": b_data['Ad'], "Miktar": b_data['Miktar'], "Personel": "Bilal", "Lot": st.session_state.irsaliye_no, "Tedarikçi Barkod": b_code, "Adres": "DEPO-1", "Durum": "Kullanılabilir"}])
                    df_har = pd.concat([df_har, new_har], ignore_index=True)
                    df_sas_up.loc[(df_sas_up['Sipariş No'] == st.session_state.sel_siparis) & (df_sas_up['Tedarikçi Barkodu'].astype(str) == str(b_code)), 'Gelen Miktar'] = b_data['Miktar']
                
                veritabani.update_data("Stok", df_stok)
                veritabani.update_data("Hareketler", df_har)
                veritabani.update_data("Satin_Alma", df_sas_up)
                st.session_state.mk_gecici_liste = {}; st.success("✅ Kayıt başarılı!"); st.session_state.teslim_page = 'menu'; st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
