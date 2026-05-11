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

def get_mapping_data():
    """Hafıza verisini Drive'dan çeker ve sütunları temizler."""
    try:
        df = veritabani.get_internal_data("Eşleşmeler")
        if df is not None and not df.empty:
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df
    except:
        if os.path.exists(LOCAL_MAPPING_FILE):
            df = pd.read_csv(LOCAL_MAPPING_FILE)
            df.columns = [str(c).strip().upper() for c in df.columns]
            return df
    return pd.DataFrame()

# --- BARKOD İŞLEME (PARTİ BAZLI) ---
def handle_barcode():
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    if not code: return

    map_df = get_mapping_data()
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    # Satin_Alma verisindeki Tedarikçi Barkodu (Parti No) ile eşleştir
    target_col = 'Tedarikçi Barkodu'
    found = sas_df[(sas_df[target_col].astype(str) == code) & 
                   (sas_df['Sipariş No'] == st.session_state.sel_siparis)]
    
    if found.empty:
        st.toast(f"❌ Barkod SAS'ta yok: {code}", icon="🚫")
        return

    row = found.iloc[0]
    m_kod = clean_code(row['Stok Kodu'])
    
    # Form Kodu eşleşmesi (Hafıza üzerinden BRN karşılığı bulma)
    form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
    
    if form_col:
        map_df['FORM_TEMİZ'] = map_df[form_col].apply(clean_code)
        match = map_df[map_df['FORM_TEMİZ'] == m_kod]
        
        if not match.empty:
            brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
            brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c or "ÜRÜN" in c), "BRN ÜRÜN ADI")
            
            # Geçici listeye ekle (Tabloyu besleyecek)
            st.session_state.mk_gecici_liste[code] = {
                "BRN_Kod": match.iloc[0][brn_k_col], 
                "Miktar": float(row['Sipariş Miktarı']), 
                "BRN_Ad": match.iloc[0][brn_a_col],
                "Orijinal_Kod": row['Stok Kodu']
            }
            st.toast(f"📥 Okundu: {match.iloc[0][brn_k_col]}", icon="✅")
            st.session_state.scan_counter += 1
        else:
            st.toast(f"❓ Hafızada Eşleşme Yok: {m_kod}", icon="🔍")
    else:
        st.toast("🚨 Eşleşmeler sekmesi formatı hatalı!", icon="🚨")

def run(conn):
    init_state()

    if st.session_state.teslim_page != 'menu':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        if c_nav1.button("⬅️ ANA MENÜ", use_container_width=True):
            st.session_state.teslim_page = 'menu'; st.rerun()
        if c_nav2.button("⬅️ GERİ", use_container_width=True):
            st.session_state.teslim_page = 'menu'; st.rerun()
        st.divider()

    # --- MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'; st.rerun()
        if c2.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'olustur'; st.rerun()

    # --- SAS OLUŞTURMA (PARTİ NO AKTARIMI) ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Yeni SAS Oluştur")
        with st.container(border=True):
            ted = st.text_input("🏢 Tedarikçi Adı:").upper().strip()
            up = st.file_uploader("Excel Yükle (Main sheet)", type=['xlsx'])
            
            if up and ted:
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                df_ex.columns = [str(c).strip() for c in df_ex.columns]
                
                if 'Parti No' in df_ex.columns:
                    st.success(f"✅ {len(df_ex)} satır bulundu.")
                    if st.button("🚀 SAS'I MÜHÜRLE", use_container_width=True, type="primary"):
                        yeni_sas_no = f"SAS-{datetime.now().strftime('%m%d%H%M')}"
                        sip_liste = []
                        for i, row in df_ex.iterrows():
                            sip_liste.append({
                                "Sipariş No": yeni_sas_no, "Tedarikçi": ted,
                                "Tedarikçi Barkodu": str(row['Parti No']).split(".")[0],
                                "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                                "Stok Kodu": row.get('Malzeme Kodu', ''),
                                "Stok Adı": row.get('Malzeme Tanımı', ''),
                                "Gelen Miktar": 0, "Birim": "ADET"
                            })
                        veritabani.update_data("Satin_Alma", pd.concat([veritabani.get_internal_data("Satin_Alma"), pd.DataFrame(sip_liste)], ignore_index=True))
                        st.success(f"✅ {yeni_sas_no} oluşturuldu!"); st.session_state.teslim_page = 'menu'; st.rerun()

    # --- MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        st.subheader("🔎 SAS Seçimi")
        df_s = veritabani.get_internal_data("Satin_Alma")
        if df_s.empty: st.warning("SAS verisi bulunamadı!"); return
        
        with st.container(border=True):
            sip_list = sorted(df_s['Sipariş No'].unique().tolist())
            sec_sip = st.selectbox("📄 SAS No Seçin:", ["Seçiniz..."] + sip_list)
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()
            if st.button("🚀 DEVAM ET", use_container_width=True, type="primary") and sec_sip != "Seçiniz..." and irs:
                st.session_state.sel_siparis = sec_sip
                st.session_state.irsaliye_no = irs
                st.session_state.full_sas_data = df_s
                st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- MAL KABUL GİRİŞ (CANLI TABLO) ---
    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 SAS: {st.session_state.sel_siparis} | İrsaliye: {st.session_state.irsaliye_no}")
        
        # Barkod Girişi
        st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        # 📊 CANLI TABLO OLUŞTURMA
        sas_filter = st.session_state.full_sas_data[st.session_state.full_sas_data['Sipariş No'] == st.session_state.sel_siparis].copy()
        sas_filter['Gelen'] = 0.0
        sas_filter['BRN Kod'] = ""
        
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter['Tedarikçi Barkodu'].astype(str) == str(b_code))
            if mask.any():
                sas_filter.loc[mask, 'Gelen'] = b_data['Miktar']
                sas_filter.loc[mask, 'BRN Kod'] = b_data['BRN_Kod']
        
        # Tabloyu ekrana bas
        st.dataframe(
            sas_filter[['Tedarikçi Barkodu', 'Stok Kodu', 'BRN Kod', 'Stok Adı', 'Sipariş Miktarı', 'Gelen']], 
            use_container_width=True, 
            hide_index=True
        )

        # Onay Butonu
        if st.session_state.mk_gecici_liste:
            if st.button("🚀 TESLİM ALMAYI ONAYLA VE STOĞA AT", type="primary", use_container_width=True):
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                df_sas_up = veritabani.get_internal_data("Satin_Alma")
                
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    # Stok ve Hareket Kaydı
                    new_stok = pd.DataFrame([{"Kod": b_data['BRN_Kod'], "İsim": b_data['BRN_Ad'], "Adres": "DEPO-1", "Miktar": b_data['Miktar'], "Durum": "Kullanılabilir", "Tedarikçi Barkod": b_code}])
                    df_stok = pd.concat([df_stok, new_stok], ignore_index=True)
                    
                    new_har = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis, "Kod": b_data['BRN_Kod'], "İsim": b_data['BRN_Ad'], "Miktar": b_data['Miktar'], "Personel": "Bilal", "Lot": st.session_state.irsaliye_no, "Tedarikçi Barkod": b_code}])
                    df_har = pd.concat([df_har, new_har], ignore_index=True)
                    
                    # Satin_Alma'da Gelen Miktarı Güncelle
                    df_sas_up.loc[(df_sas_up['Sipariş No'] == st.session_state.sel_siparis) & (df_sas_up['Tedarikçi Barkodu'].astype(str) == str(b_code)), 'Gelen Miktar'] = b_data['Miktar']
                
                veritabani.update_data("Stok", df_stok)
                veritabani.update_data("Hareketler", df_har)
                veritabani.update_data("Satin_Alma", df_sas_up)
                
                st.session_state.mk_gecici_liste = {}
                st.success("✅ Teslim alma başarıyla tamamlandı!"); st.session_state.teslim_page = 'menu'; st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN Sleep Products</b></div>", unsafe_allow_html=True)
