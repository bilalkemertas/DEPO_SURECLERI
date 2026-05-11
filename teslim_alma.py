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
    if 'manuel_sas_liste' not in st.session_state: st.session_state.manuel_sas_liste = []
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0
    if 'full_sas_data' not in st.session_state: st.session_state.full_sas_data = pd.DataFrame()
    if 'def_adres' not in st.session_state: st.session_state.def_adres = "DEPO-1"
    if 'def_durum' not in st.session_state: st.session_state.def_durum = "Kullanılabilir"

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

# --- BARKOD İŞLEME (DİNAMİK KİMLİK ATAMALI) ---
def handle_barcode():
    if 'scan_counter' not in st.session_state: st.session_state.scan_counter = 0
    input_key = f"barkod_input_{st.session_state.scan_counter}"
    code = st.session_state.get(input_key, "").strip().split(".")[0]
    if not code: return

    # 🛡️ Mükerrer Kontrolü (Stok ve Hareketler)
    df_stok_check = veritabani.get_internal_data("Stok")
    if code in df_stok_check.get('Tedarikçi Barkod', pd.Series()).astype(str).values:
        st.toast(f"🚨 HATA: {code} zaten stokta!", icon="🛑"); return

    map_df = load_safe_mapping()
    sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
    
    # Barkod SAS içinde var mı? (Önceden tanımlanmışsa)
    found = sas_df[sas_df['Tedarikçi Barkodu'].astype(str) == code]
    
    # Eğer barkod SAS'ta yoksa ama malzeme SAS'ta "BEKLIYOR" durumundaysa (Yeni Mantık)
    if found.empty:
        # Boş olan (BEKLIYOR) ilk kalemi bulmaya çalış
        pending = sas_df[sas_df['Tedarikçi Barkodu'].isin(['BEKLIYOR', '', 'None', None])]
        if pending.empty:
            st.toast(f"❌ Bu SAS'ta boş kalem kalmadı veya barkod hatalı!", icon="🚫"); return
        row = pending.iloc[0]
    else:
        row = found.iloc[0]

    m_kod = clean_code(row['Stok Kodu'])
    final_kod, final_ad = row['Stok Kodu'], row['Stok Adı']
    
    # Eşleşme kontrolü (BRN Kodları için)
    if not map_df.empty:
        map_df.columns = [str(c).strip().upper() for c in map_df.columns]
        form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
        if form_col:
            match = map_df[map_df[form_col].apply(clean_code) == m_kod]
            if not match.empty:
                brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
                brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c or "ÜRÜN" in c), "BRN ÜRÜN ADI")
                final_kod, final_ad = match.iloc[0][brn_k_col], match.iloc[0][brn_a_col]

    st.session_state.mk_gecici_liste[code] = {
        "Kod": final_kod, "Ad": final_ad, "Miktar": float(row['Sipariş Miktarı']),
        "Adres": st.session_state.def_adres, "Durum": st.session_state.def_durum,
        "SAS_Kalem_ID": row.name # Hangi satırı güncelleyeceğimizi tutar
    }
    st.session_state.scan_counter += 1

def run(conn):
    init_state()

    if st.session_state.teslim_page != 'menu' or st.session_state.get('page') != 'main':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        if c_nav1.button("🏠 ANA MENÜ", use_container_width=True):
            st.session_state['page'] = 'main'; st.session_state.teslim_page = 'menu'; st.rerun()
        if c_nav2.button("⬅️ GERİ", use_container_width=True):
            st.session_state.teslim_page = 'menu' if st.session_state.teslim_page in ['olustur', 'secim'] else 'secim'
            st.rerun()
        st.divider()

    # --- MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'; st.rerun()
        if c2.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'olustur'; st.rerun()

    # --- SAS OLUŞTURMA ---
    elif st.session_state.teslim_page == 'olustur':
        st.subheader("📝 Yeni SAS Oluştur")
        tab1, tab2 = st.tabs(["📄 Manuel Kalem Ekle", "📂 Excel'den Yükle"])
        
        with tab1:
            with st.container(border=True):
                ted_m = st.text_input("🏢 Tedarikçi Firma:").upper()
                df_ref = veritabani.get_internal_data("Stok")
                kod_list = sorted(df_ref['Kod'].unique().tolist()) if not df_ref.empty else []
                ad_list = sorted(df_ref['İsim'].unique().tolist()) if not df_ref.empty else []

                col_m1, col_m2 = st.columns(2)
                m_kod_sec = col_m1.selectbox("🔎 Malzeme Kod:", ["Seçiniz..."] + kod_list)
                def_ad_val = df_ref[df_ref['Kod'] == m_kod_sec]['İsim'].iloc[0] if m_kod_sec != "Seçiniz..." else "Seçiniz..."
                m_ad_sec = col_m2.selectbox("📦 Malzeme Adı:", ["Seçiniz..."] + ad_list, index=(ad_list.index(def_ad_val) + 1) if def_ad_val in ad_list else 0)

                col_m3, col_m4 = st.columns(2)
                sip_mik = col_m3.number_input("🔢 Sipariş Miktarı:", min_value=0.0, step=1.0)
                # BARKOD ARTIK OPSİYONEL
                parti_no = col_m4.text_input("🏷️ Tedarikçi Barkod (Opsiyonel):", help="Boş bırakılırsa kabul anında atanır.").strip().upper()
                final_barkod = parti_no if parti_no else "BEKLIYOR"

                if st.button("➕ KALEMİ LİSTEYE EKLE", use_container_width=True):
                    f_kod = m_kod_sec if m_kod_sec != "Seçiniz..." else (df_ref[df_ref['İsim'] == m_ad_sec]['Kod'].iloc[0] if m_ad_sec != "Seçiniz..." else "")
                    f_ad = m_ad_sec if m_ad_sec != "Seçiniz..." else (df_ref[df_ref['Kod'] == m_kod_sec]['İsim'].iloc[0] if m_kod_sec != "Seçiniz..." else "")
                    
                    if f_kod and sip_mik > 0:
                        st.session_state.manuel_sas_liste.append({
                            "Tedarikçi": ted_m, "Stok Kodu": f_kod, "Stok Adı": f_ad,
                            "Sipariş Miktarı": sip_mik, "Tedarikçi Barkodu": final_barkod
                        })
                        st.toast(f"✅ Eklendi: {f_kod}")
                    else: st.error("Lütfen Malzeme ve Miktar girin!")

            if st.session_state.manuel_sas_liste:
                st.dataframe(pd.DataFrame(st.session_state.manuel_sas_liste), use_container_width=True, hide_index=True)
                if st.button("🚀 SAS'I KAYDET", use_container_width=True, type="primary"):
                    yeni_no = f"SAS-M{datetime.now().strftime('%m%d%H%M')}"
                    sas_data = pd.DataFrame(st.session_state.manuel_sas_liste)
                    sas_data["Sipariş No"] = yeni_no
                    sas_data["Gelen Miktar"] = 0
                    sas_data["Birim"] = "ADET"
                    veritabani.update_data("Satin_Alma", pd.concat([veritabani.get_internal_data("Satin_Alma"), sas_data], ignore_index=True))
                    st.session_state.manuel_sas_liste = []; st.success(f"✅ {yeni_no} oluşturuldu!"); st.rerun()

        with tab2: # Excel Yükleme (Barkod yoksa otomatik BEKLIYOR atar)
            ted_e = st.text_input("🏢 Tedarikçi (Excel):").upper()
            up = st.file_uploader("Dosya Seç", type=['xlsx'])
            if up and ted_e and st.button("🚀 EXCEL AKTAR"):
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                yeni_sas_e = f"SAS-E{datetime.now().strftime('%m%d%H%M')}"
                sip_ex = pd.DataFrame([{
                    "Sipariş No": yeni_sas_e, "Tedarikçi": ted_e,
                    "Tedarikçi Barkodu": str(row.get('Parti No', 'BEKLIYOR')).split(".")[0] if not pd.isna(row.get('Parti No')) else "BEKLIYOR",
                    "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                    "Stok Kodu": row.get('Malzeme Kodu', ''), "Stok Adı": row.get('Malzeme Tanımı', ''),
                    "Gelen Miktar": 0, "Birim": "METRE"
                } for i, row in df_ex.iterrows()])
                veritabani.update_data("Satin_Alma", pd.concat([veritabani.get_internal_data("Satin_Alma"), sip_ex], ignore_index=True))
                st.success(f"✅ {yeni_sas_e} yüklendi!"); st.rerun()

    # --- MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        st.subheader("🔎 SAS Seçimi")
        df_s = veritabani.get_internal_data("Satin_Alma")
        df_s['Sipariş Miktarı'] = pd.to_numeric(df_s['Sipariş Miktarı'], errors='coerce').fillna(0)
        df_s['Gelen Miktar'] = pd.to_numeric(df_s['Gelen Miktar'], errors='coerce').fillna(0)
        df_incomplete = df_s[df_s['Sipariş Miktarı'] > df_s['Gelen Miktar']]
        
        with st.container(border=True):
            ted_list = ["Tümü"] + sorted(df_incomplete['Tedarikçi'].unique().tolist())
            sec_ted = st.selectbox("🏢 Tedarikçi Filtrele:", ted_list)
            filtered_sas = df_incomplete[df_incomplete['Tedarikçi'] == sec_ted] if sec_ted != "Tümü" else df_incomplete
            sip_options = sorted(filtered_sas['Sipariş No'].unique().tolist())
            sec_sip = st.selectbox("📄 SAS No Seçin:", ["Seçiniz..."] + sip_options)
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()
            if st.button("🚀 DEVAM", use_container_width=True, type="primary") and sec_sip != "Seçiniz..." and irs:
                st.session_state.sel_siparis = sec_sip
                st.session_state.sel_tedarikci = df_s[df_s['Sipariş No'] == sec_sip]['Tedarikçi'].iloc[0]
                st.session_state.full_sas_data = df_s[df_s['Sipariş No'] == sec_sip]
                st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 SAS: {st.session_state.sel_siparis} | {st.session_state.get('sel_tedarikci')}")
        with st.expander("⚙️ Varsayılan Depo Ayarları", expanded=True):
            c_adr, c_dur = st.columns(2)
            st.session_state.def_adres = c_adr.text_input("📍 Adres:", value=st.session_state.def_adres).upper()
            st.session_state.def_durum = c_dur.selectbox("🛡️ Durum:", ["Kullanılabilir", "Kalite Kontrol", "Bloke"])

        with st.container(border=True):
            st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)
        
        # Canlı Tablo & Sıralama
        sas_filter = st.session_state.full_sas_data.copy()
        sas_filter['Gelen (Yeni)'] = 0.0
        scanned_codes = list(st.session_state.mk_gecici_liste.keys())
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter.index == b_data['SAS_Kalem_ID'])
            if mask.any(): sas_filter.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']

        st.dataframe(sas_filter[['Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']], use_container_width=True, hide_index=True)

        if st.session_state.mk_gecici_liste:
            if st.button("🚀 STOĞA AKTARIMI TAMAMLA", type="primary", use_container_width=True):
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                df_sas_up = veritabani.get_internal_data("Satin_Alma")
                
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    # 1. Stok Girişi
                    df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": b_data['Kod'], "İsim": b_data['Ad'], "Adres": b_data['Adres'], "Miktar": b_data['Miktar'], "Durum": b_data['Durum'], "Tedarikçi Barkod": b_code}])], ignore_index=True)
                    # 2. Hareket Kaydı
                    df_har = pd.concat([df_har, pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis, "Kod": b_data['Kod'], "İsim": b_data['Ad'], "Miktar": b_data['Miktar'], "Personel": "Bilal", "Adres": b_data['Adres'], "Tedarikçi Barkod": b_code, "Durum": b_data['Durum']}])], ignore_index=True)
                    # 3. SAS Güncelleme (Barkod "BEKLIYOR" ise artık gerçek barkodla mühürlenir)
                    df_sas_up.loc[b_data['SAS_Kalem_ID'], 'Gelen Miktar'] = b_data['Miktar']
                    df_sas_up.loc[b_data['SAS_Kalem_ID'], 'Tedarikçi Barkodu'] = b_code
                
                veritabani.update_data("Stok", df_stok); veritabani.update_data("Hareketler", df_har); veritabani.update_data("Satin_Alma", df_sas_up)
                st.session_state.mk_gecici_liste = {}; st.success("✅ Tüm ürünler gerçek barkodlarıyla işlendi!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
