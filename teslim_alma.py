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
    if 'sip_gecici_liste' not in st.session_state: st.session_state.sip_gecici_liste = []
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0

def clean_code(val):
    if pd.isna(val): return ""
    val = str(val).split(".")[0].strip()
    return re.sub(r'\D', '', val)

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

# --- BARKOD İŞLEME (GÜNCEL SÜTUNLAR) ---
def handle_barcode():
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    if not code: return

    map_df = load_safe_mapping()
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    # Yeni Sütun İsmi Kontrolü
    target_col = 'Tedarikçi Barkodu'
    if target_col not in sas_df.columns:
        st.toast(f"❌ '{target_col}' sütunu bulunamadı!", icon="🚨")
        return

    found = sas_df[(sas_df[target_col].astype(str) == code) & 
                   (sas_df['Sipariş No'] == st.session_state.sel_siparis)]
    
    if found.empty:
        st.toast(f"❌ Barkod SAS'ta yok: {code}", icon="🚫")
        return

    row = found.iloc[0]
    # Eşleşme için Stok Kodu (BRN Karşılığı) kullanılır
    m_kod = clean_code(row['Stok Kodu'])
    
    map_df.columns = [str(c).strip().upper() for c in map_df.columns]
    map_df['FORM_TEMİZ'] = map_df['FORM SÜNGER KOD'].apply(clean_code)
    match = map_df[map_df['FORM_TEMİZ'] == m_kod]
    
    if not match.empty:
        brn_kod = match.iloc[0]['BRN KOD']
        st.session_state.mk_gecici_liste[code] = {
            "Kod": brn_kod, "Miktar": float(row['Sipariş Miktarı']), "Ad": match.iloc[0]['BRN ÜRÜN ADI']
        }
        st.toast(f"✅ {brn_kod} eklendi.", icon="📥")
        st.session_state.scan_counter += 1
    else:
        st.toast(f"❓ Eşleşme yok: {m_kod}", icon="🔍")

def run(conn):
    init_state()

    if st.session_state.teslim_page != 'menu':
        c_nav = st.columns([1, 1, 4])
        if c_nav[0].button("⬅️ ANA MENÜ"):
            st.session_state.teslim_page = 'menu'; st.session_state.page = 'home'; st.rerun()
        if c_nav[1].button("⬅️ GERİ"):
            st.session_state.teslim_page = 'secim' if st.session_state.teslim_page == 'kabul' else 'menu'
            st.rerun()
        st.divider()

    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        c1.button("📦 MAL KABUL", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'secim'))
        c2.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'olustur'))

    # --- SAS OLUŞTURMA (Excel -> Tedarikçi Barkodu) ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Yeni SAS Oluştur")
        with st.container(border=True):
            ted = st.text_input("🏢 Tedarikçi Adı:").upper().strip()
            up = st.file_uploader("Excel Yükle (Main sheet)", type=['xlsx'])
            
            if up:
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                df_ex.columns = [str(c).strip() for c in df_ex.columns]
                
                # Excel "Parti No" -> SAS "Tedarikçi Barkodu" eşleşmesi
                if 'Parti No' in df_ex.columns:
                    st.success(f"✅ {len(df_ex)} satır analiz edildi.")
                    if st.button("🚀 SAS'I DRIVE'A MÜHÜRLE", use_container_width=True, type="primary"):
                        # Satin_Alma tablosuna uygun yeni kayıtlar
                        yeni_sas_no = f"SAS-{datetime.now().strftime('%m%d%H%M')}"
                        sip_liste = []
                        for i, row in df_ex.iterrows():
                            sip_liste.append({
                                "Sipariş No": yeni_sas_no,
                                "Tedarikçi": ted,
                                "Tedarikçi Barkodu": str(row['Parti No']).split(".")[0],
                                "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                                "Tedarikçi Ürün Kodu": row.get('Malzeme Kodu', ''),
                                "Tedarikçi Malzeme Adı": row.get('Malzeme Tanımı', ''),
                                "Kalem No": (i + 1) * 10,
                                "Stok Kodu": row.get('Malzeme Kodu', ''), # Eşleşme için
                                "Stok Adı": row.get('Malzeme Tanımı', ''),
                                "Gelen Miktar": 0, "Birim": "ADET"
                            })
                        df_db = veritabani.get_internal_data("Satin_Alma")
                        df_final = pd.concat([df_db, pd.DataFrame(sip_liste)], ignore_index=True)
                        veritabani.update_data("Satin_Alma", df_final)
                        st.success(f"✅ {yeni_sas_no} başarıyla oluşturuldu!")
                        st.session_state.teslim_page = 'menu'; st.rerun()

    # --- MAL KABUL (Seçim & Giriş) ---
    elif st.session_state.teslim_page == 'secim':
        df_s = veritabani.get_internal_data("Satin_Alma")
        df_s.columns = [str(c).strip() for c in df_s.columns]
        with st.container(border=True):
            sec_sip = st.selectbox("📄 SAS No Seçin:", ["Seçiniz..."] + sorted(df_s['Sipariş No'].unique().tolist()))
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()
            if st.button("🚀 DEVAM ET", use_container_width=True, type="primary"):
                if sec_sip != "Seçiniz..." and irs:
                    st.session_state.sel_siparis = sec_sip
                    st.session_state.irsaliye_no = irs
                    st.session_state.full_sas_data = df_s
                    st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
                    st.session_state.teslim_page = 'kabul'; st.rerun()

    elif st.session_state.teslim_page == 'kabul':
        st.caption(f"📍 {st.session_state.sel_siparis} | {st.session_state.irsaliye_no}")
        with st.container(border=True):
            st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        sub = st.session_state.full_sas_data[st.session_state.full_sas_data['Sipariş No'] == st.session_state.sel_siparis].copy()
        sub['Gelen (Yeni)'] = 0.0
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sub['Tedarikçi Barkodu'].astype(str) == b_code)
            if mask.any(): sub.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']
        
        st.dataframe(sub[['Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 KAYDI TAMAMLA", type="primary", use_container_width=True):
                df_stok = st.session_state.full_stok_data
                df_har = veritabani.get_internal_data("Hareketler")
                df_sas_up = veritabani.get_internal_data("Satin_Alma")
                
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    # Stok ve Hareket Kaydı
                    new_stok = pd.DataFrame([{"Kod": b_data['Kod'], "İsim": b_data['Ad'], "Adres": "DEPO-1", "Miktar": b_data['Miktar'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": b_code}])
                    df_stok = pd.concat([df_stok, new_stok], ignore_index=True)
                    
                    new_har = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis, "Kod": b_data['Kod'], "İsim": b_data['Ad'], "Miktar": b_data['Miktar'], "Personel": "Bilal", "Lot": st.session_state.irsaliye_no, "Tedarikçi Barkod": b_code, "Adres": "DEPO-1", "Durum": "Kullanılabilir"}])
                    df_har = pd.concat([df_har, new_har], ignore_index=True)
                    
                    # SAS Gelen Miktar Güncelle
                    df_sas_up.loc[(df_sas_up['Sipariş No'] == st.session_state.sel_siparis) & (df_sas_up['Tedarikçi Barkodu'].astype(str) == b_code), 'Gelen Miktar'] = b_data['Miktar']
                
                veritabani.update_data("Stok", df_stok)
                veritabani.update_data("Hareketler", df_har)
                veritabani.update_data("Satin_Alma", df_sas_up)
                st.session_state.mk_gecici_liste = {}
                st.success("✅ Mal Kabul mühürlendi patron!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b></div>", unsafe_allow_html=True)
