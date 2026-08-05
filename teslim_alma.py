import streamlit as st
import pandas as pd
import veritabani
import tedarikci_api
import yetkilendirme
import re
import os
from datetime import datetime

LOCAL_MAPPING_FILE = "hafiza.csv"


def init_state():
    if 'teslim_page' not in st.session_state:
        st.session_state.teslim_page = 'menu'
    if 'mk_gecici_liste' not in st.session_state:
        st.session_state.mk_gecici_liste = {}
    if 'manuel_sas_liste' not in st.session_state:
        st.session_state.manuel_sas_liste = []
    if 'scan_counter' not in st.session_state:
        st.session_state.scan_counter = 0
    if 'full_sas_data' not in st.session_state:
        st.session_state.full_sas_data = pd.DataFrame()
    if 'def_adres' not in st.session_state:
        st.session_state.def_adres = "DEPO-1"
    if 'def_durum' not in st.session_state:
        st.session_state.def_durum = "Kullanılabilir"


def clean_code(val):
    if pd.isna(val):
        return ""
    return str(val).split(".")[0].strip().upper()


def load_safe_mapping():
    try:
        df_drive = veritabani.get_internal_data("Eşleşmeler")
        if df_drive is not None and not df_drive.empty:
            df_drive.to_csv(LOCAL_MAPPING_FILE, index=False)
            return df_drive
    except:
        pass

    if os.path.exists(LOCAL_MAPPING_FILE):
        try:
            return pd.read_csv(LOCAL_MAPPING_FILE)
        except:
            return pd.DataFrame()

    return pd.DataFrame()


def handle_barcode():
    if 'scan_counter' not in st.session_state:
        st.session_state.scan_counter = 0

    input_key = f"barkod_input_{st.session_state.scan_counter}"
    raw_code = st.session_state.get(input_key, "").strip()

    if not raw_code:
        return

    parti_no = raw_code[-10:] if len(raw_code) >= 10 else raw_code

    st.toast(f"🔍 Barkod Çözümlendi! Parti No: {parti_no} aranıyor...", icon="⏳")

    df_stok_check = veritabani.get_internal_data("Stok")

    if raw_code in df_stok_check.get('Tedarikçi Barkod', pd.Series()).astype(str).values:
        st.toast(f"🚨 HATA: {raw_code} zaten stokta mevcut!", icon="🛑")
        return

    map_df = load_safe_mapping()

    df_sas_all = veritabani.get_internal_data("Satin_Alma")
    if df_sas_all is None or df_sas_all.empty:
        st.error("Satın Alma veritabanı boş!")
        return

    df_sas_all['Temiz_Barkod'] = df_sas_all['Tedarikçi Barkodu'].astype(str).str.strip()

    found = df_sas_all[df_sas_all['Temiz_Barkod'] == parti_no]

    if found.empty:
        found = df_sas_all[df_sas_all['Temiz_Barkod'] == raw_code]

    if found.empty:
        sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
        if not sas_df.empty:
            pending = sas_df[sas_df['Tedarikçi Barkodu'].isin(['BEKLIYOR', '', 'None', None, 'nan'])]
            if pending.empty:
                st.toast(f"❌ '{parti_no}' bulunamadı ve aktif SAS'ta atanacak boş kalem kalmadı!", icon="🚫")
                return
            row = pending.iloc[0]
            st.toast(f"⚠️ Parti No ({parti_no}) eşleşmedi, listedeki bekleyen boş kaleme atandı.", icon="⚠️")
        else:
            st.toast(f"❌ '{parti_no}' Parti No Satın Alma (SAS) listesinde bulunamadı!", icon="🚫")
            return
    else:
        row = found.iloc[0]
        st.toast(f"✅ Ürün Bulundu: {row.get('Stok Adı', '')}", icon="✔️")

        sas_df = st.session_state.get('full_sas_data', pd.DataFrame())
        if row.name not in sas_df.index:
            st.session_state.full_sas_data = pd.concat([sas_df, pd.DataFrame([row])])

    m_kod = clean_code(row['Stok Kodu'])
    final_kod, final_ad = row['Stok Kodu'], row['Stok Adı']

    if not map_df.empty:
        map_df.columns = [str(c).strip().upper() for c in map_df.columns]
        form_col = next((c for c in map_df.columns if "FORM" in c and "KOD" in c), None)
        if form_col:
            match = map_df[map_df[form_col].apply(clean_code) == m_kod]
            if not match.empty:
                brn_k_col = next((c for c in map_df.columns if "BRN" in c and "KOD" in c), "BRN KOD")
                brn_a_col = next((c for c in map_df.columns if "BRN" in c and "AD" in c or "ÜRÜN" in c), "BRN ÜRÜN ADI")
                final_kod, final_ad = match.iloc[0][brn_k_col], match.iloc[0][brn_a_col]

    st.session_state.mk_gecici_liste[raw_code] = {
        "Kod": final_kod,
        "Ad": final_ad,
        "Miktar": float(row['Sipariş Miktarı']),
        "Adres": st.session_state.def_adres,
        "Durum": st.session_state.def_durum,
        "SAS_Kalem_ID": row.name,
        "Siparis_No": row.get('Sipariş No', '')
    }
    st.session_state.scan_counter += 1


def run(conn):
    init_state()

    if st.session_state.teslim_page != 'menu' or st.session_state.get('page') != 'main':
        c_nav1, c_nav2, _ = st.columns([1.5, 1.5, 4])
        if c_nav1.button("🏠 ANA MENÜ", use_container_width=True):
            st.session_state['page'] = 'main'
            st.session_state.teslim_page = 'menu'
            st.rerun()
        if c_nav2.button("⬅️ GERİ", use_container_width=True):
            st.session_state.teslim_page = 'menu' if st.session_state.teslim_page in ['olustur', 'secim'] else 'secim'
            st.rerun()
        st.divider()

    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        c1, c2 = st.columns(2)
        if c1.button("📦 MAL KABUL", use_container_width=True, type="primary"):
            st.session_state.teslim_page = 'secim'
            st.rerun()

        if yetkilendirme.is_admin():
            if c2.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary"):
                st.session_state.teslim_page = 'olustur'
                st.rerun()
        else:
            c2.button("📝 SAS OLUŞTUR", use_container_width=True, disabled=True)
            c2.caption("🔒 Sadece Admin kullanıcılar içindir.")

    elif st.session_state.teslim_page == 'olustur':
        if not yetkilendirme.admin_only("🔒 SAS Oluşturma ekranı sadece Admin kullanıcılar içindir."):
            st.stop()

        st.subheader("📝 Yeni SAS Oluştur")
        tab1, tab2 = st.tabs(["📄 Manuel Kalem Ekle", "📂 Excel'den Yükle"])

        with tab1:
            with st.container(border=True):
                ted_m = st.text_input("🏢 Tedarikçi Firma:").upper()
                df_ref = veritabani.get_internal_data("Stok")

                if not df_ref.empty and 'Kod' in df_ref.columns:
                    kod_list = sorted(list(set(str(x).strip() for x in df_ref['Kod'].dropna() if str(x).strip() != "")))
                else:
                    kod_list = []

                if not df_ref.empty and 'İsim' in df_ref.columns:
                    ad_list = sorted(list(set(str(x).strip() for x in df_ref['İsim'].dropna() if str(x).strip() != "")))
                else:
                    ad_list = []

                col_m1, col_m2 = st.columns(2)
                m_kod_sec = col_m1.selectbox("🔎 Malzeme Kod:", ["Seçiniz..."] + kod_list)

                def_ad_val = "Seçiniz..."
                if m_kod_sec != "Seçiniz...":
                    filtre = df_ref[df_ref['Kod'].astype(str).str.strip() == m_kod_sec]
                    if not filtre.empty:
                        def_ad_val = str(filtre['İsim'].iloc[0]).strip()

                m_ad_sec = col_m2.selectbox(
                    "📦 Malzeme Adı:",
                    ["Seçiniz..."] + ad_list,
                    index=(ad_list.index(def_ad_val) + 1) if def_ad_val in ad_list else 0
                )

                col_m3, col_m4 = st.columns(2)
                sip_mik = col_m3.number_input("🔢 Sipariş Miktarı:", min_value=0.0, step=1.0)
                parti_no = col_m4.text_input(
                    "🏷️ Tedarikçi Barkod (Opsiyonel):",
                    help="Boş bırakılırsa kabul anında atanır."
                ).strip().upper()
                final_barkod = parti_no if parti_no else "BEKLIYOR"

                if st.button("➕ KALEMİ LİSTEYE EKLE", use_container_width=True):
                    f_kod = m_kod_sec if m_kod_sec != "Seçiniz..." else ""
                    f_ad = m_ad_sec if m_ad_sec != "Seçiniz..." else ""

                    if f_kod == "" and f_ad != "":
                        f_kod_fil = df_ref[df_ref['İsim'].astype(str).str.strip() == f_ad]
                        if not f_kod_fil.empty:
                            f_kod = str(f_kod_fil['Kod'].iloc[0]).strip()

                    if f_ad == "" and f_kod != "":
                        f_ad_fil = df_ref[df_ref['Kod'].astype(str).str.strip() == f_kod]
                        if not f_ad_fil.empty:
                            f_ad = str(f_ad_fil['İsim'].iloc[0]).strip()

                    if f_kod and sip_mik > 0:
                        st.session_state.manuel_sas_liste.append({
                            "Tedarikçi": ted_m,
                            "Stok Kodu": f_kod,
                            "Stok Adı": f_ad,
                            "Sipariş Miktarı": sip_mik,
                            "Tedarikçi Barkodu": final_barkod
                        })
                        st.toast(f"✅ Eklendi: {f_kod}")
                    else:
                        st.error("Lütfen Malzeme ve Miktar girin!")

                if st.session_state.manuel_sas_liste:
                    st.dataframe(pd.DataFrame(st.session_state.manuel_sas_liste), use_container_width=True, hide_index=True)

                    if st.button("🚀 SAS'I KAYDET", use_container_width=True, type="primary"):
                        yeni_no = f"SAS-M{datetime.now().strftime('%m%d%H%M')}"
                        sas_data = pd.DataFrame(st.session_state.manuel_sas_liste)
                        sas_data["Sipariş No"] = yeni_no
                        sas_data["Gelen Miktar"] = 0
                        sas_data["Birim"] = "ADET"

                        veritabani.update_data(
                            "Satin_Alma",
                            pd.concat([veritabani.get_internal_data("Satin_Alma"), sas_data], ignore_index=True)
                        )
                        st.session_state.manuel_sas_liste = []
                        st.success(f"✅ {yeni_no} oluşturuldu!")
                        st.rerun()

        with tab2:
            ted_e = st.text_input("🏢 Tedarikçi (Excel):").upper()
            up = st.file_uploader("Dosya Seç", type=['xlsx'])

            if up and ted_e and st.button("🚀 EXCEL AKTAR"):
                df_ex = pd.read_excel(up, sheet_name='Main sheet')
                yeni_sas_e = f"SAS-E{datetime.now().strftime('%m%d%H%M')}"

                sip_ex = pd.DataFrame([{
                    "Sipariş No": yeni_sas_e,
                    "Tedarikçi": ted_e,
                    "Tedarikçi Barkodu": str(row.get('Parti No', 'BEKLIYOR')).split(".")[0] if not pd.isna(row.get('Parti No')) else "BEKLIYOR",
                    "Sipariş Miktarı": row.get('Teslimat Miktarı', 0),
                    "Stok Kodu": row.get('Malzeme Kodu', ''),
                    "Stok Adı": row.get('Malzeme Tanımı', ''),
                    "Gelen Miktar": 0,
                    "Birim": "METRE"
                } for i, row in df_ex.iterrows()])

                veritabani.update_data(
                    "Satin_Alma",
                    pd.concat([veritabani.get_internal_data("Satin_Alma"), sip_ex], ignore_index=True)
                )
                st.success(f"✅ {yeni_sas_e} yüklendi!")
                st.rerun()

    elif st.session_state.teslim_page == 'secim':
        st.subheader("🔎 SAS Seçimi")
        df_s = veritabani.get_internal_data("Satin_Alma")

        if df_s is not None and not df_s.empty:
            df_s.columns = [str(c).strip() for c in df_s.columns]
            gerekli_sutunlar = ['Sipariş Miktarı', 'Gelen Miktar', 'Tedarikçi', 'Sipariş No']
            eksik_sutunlar = [s for s in gerekli_sutunlar if s not in df_s.columns]

            if eksik_sutunlar:
                st.error(f"⚠️ HATA: Veritabanında şu sütunlar bulunamadı: {eksik_sutunlar}")
                st.info(f"Mevcut Sütunların: {list(df_s.columns)}")
            else:
                df_s['Sipariş Miktarı'] = pd.to_numeric(df_s['Sipariş Miktarı'], errors='coerce').fillna(0)
                df_s['Gelen Miktar'] = pd.to_numeric(df_s['Gelen Miktar'], errors='coerce').fillna(0)
                df_incomplete = df_s[df_s['Sipariş Miktarı'] > df_s['Gelen Miktar']]

                with st.container(border=True):
                    ted_list = ["Tümü"] + sorted(list(set(str(x).strip() for x in df_incomplete['Tedarikçi'].dropna() if str(x).strip() != "")))
                    sec_ted = st.selectbox("🏢 Tedarikçi Filtrele:", ted_list)

                    filtered_sas = df_incomplete[df_incomplete['Tedarikçi'].astype(str).str.strip() == sec_ted] if sec_ted != "Tümü" else df_incomplete
                    sip_options = sorted(list(set(str(x).strip() for x in filtered_sas['Sipariş No'].dropna() if str(x).strip() != "")))

                    sec_sip_list = st.multiselect("📄 SAS No(ları) Seçin:", sip_options)
                    irs = st.text_input("🧾 İrsaliye No:").upper().strip()

                    if st.button("🚀 DEVAM", use_container_width=True, type="primary") and len(sec_sip_list) > 0 and irs:
                        st.session_state.sel_siparis = ", ".join(sec_sip_list)

                        siparis_filtre = df_s[df_s['Sipariş No'].astype(str).str.strip().isin(sec_sip_list)]
                        st.session_state.sel_tedarikci = str(siparis_filtre['Tedarikçi'].iloc[0]) if not siparis_filtre.empty else ""
                        st.session_state.full_sas_data = siparis_filtre
                        st.session_state.teslim_page = 'kabul'
                        st.rerun()
        else:
            st.warning("Veritabanında açık SAS kaydı bulunamadı!")

    elif st.session_state.teslim_page == 'kabul':
        st.info(f"📍 SAS: {st.session_state.sel_siparis} | {st.session_state.get('sel_tedarikci')}")

        with st.expander("⚙️ Varsayılan Depo Ayarları", expanded=True):
            c_adr, c_dur = st.columns(2)
            st.session_state.def_adres = c_adr.text_input("📍 Adres:", value=st.session_state.def_adres).upper()
            st.session_state.def_durum = c_dur.selectbox("🛡️ Durum:", ["Kullanılabilir", "Kalite Kontrol", "Bloke"])

        with st.container(border=True):
            st.text_input("🔍 Barkod Okutun:", key=f"barkod_input_{st.session_state.scan_counter}", on_change=handle_barcode)

        sas_filter = st.session_state.full_sas_data.copy()
        sas_filter['Gelen (Yeni)'] = 0.0
        
        for b_code, b_data in st.session_state.mk_gecici_liste.items():
            mask = (sas_filter.index == b_data['SAS_Kalem_ID'])
            if mask.any():
                sas_filter.loc[mask, 'Gelen (Yeni)'] = b_data['Miktar']

        st.subheader("📦 Gelen Miktar Tablosu (Düzenlenebilir)")
        
        sas_gosterim = sas_filter[['Sipariş No', 'Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı', 'Gelen (Yeni)']].copy()
        sas_gosterim.index = sas_filter.index
        
        edited_sas = st.data_editor(
            sas_gosterim,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Gelen (Yeni)": st.column_config.NumberColumn(
                    "Gelen (Yeni)",
                    min_value=0,
                    step=1,
                    format="%d"
                )
            },
            disabled=['Sipariş No', 'Tedarikçi Barkodu', 'Stok Kodu', 'Stok Adı', 'Sipariş Miktarı'],
            key='sas_editor'
        )

        if edited_sas is not None:
            for idx, row in edited_sas.iterrows():
                for b_code, b_data in st.session_state.mk_gecici_liste.items():
                    if b_data['SAS_Kalem_ID'] == idx:
                        b_data['Miktar'] = float(row['Gelen (Yeni)'])
                        break

        st.markdown("---")
        
        # KAYIT BUTONU VE KONTROL
        if len(st.session_state.mk_gecici_liste) > 0:
            st.success(f"✅ {len(st.session_state.mk_gecici_liste)} ürün barkod ile tarandı. Aşağıdaki butona tıkla.")
            
            if st.button("🚀 STOĞA AKTARIMI TAMAMLA", type="primary", use_container_width=True):
                with st.spinner("Veritabanına kaydediliyor..."):
                    try:
                        df_stok = veritabani.get_internal_data("Stok")
                        df_har = veritabani.get_internal_data("Hareketler")
                        df_sas_up = veritabani.get_internal_data("Satin_Alma")

                        if df_stok is None or df_stok.empty:
                            df_stok = pd.DataFrame(columns=['Kod', 'İsim', 'Adres', 'Miktar', 'Durum', 'Tedarikçi Barkod'])
                        if df_har is None or df_har.empty:
                            df_har = pd.DataFrame(columns=['Tarih', 'İşlem', 'İş Emri', 'Kod', 'İsim', 'Miktar', 'Personel', 'Adres', 'Tedarikçi Barkod', 'Durum'])
                        if df_sas_up is None or df_sas_up.empty:
                            df_sas_up = pd.DataFrame()

                        basarili_kayit = 0
                        
                        for b_code, b_data in st.session_state.mk_gecici_liste.items():
                            # 1. STOK TABLOSUNA EKLE
                            df_stok = pd.concat([df_stok, pd.DataFrame([{
                                "Kod": b_data['Kod'],
                                "İsim": b_data['Ad'],
                                "Adres": b_data['Adres'],
                                "Miktar": b_data['Miktar'],
                                "Durum": b_data['Durum'],
                                "Tedarikçi Barkod": b_code
                            }])], ignore_index=True)

                            # 2. HAREKETLER TABLOSUNA EKLE
                            gercek_siparis_no = b_data.get('Siparis_No', st.session_state.sel_siparis)
                            df_har = pd.concat([df_har, pd.DataFrame([{
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "İşlem": "GİRİŞ",
                                "İş Emri": gercek_siparis_no,
                                "Kod": b_data['Kod'],
                                "İsim": b_data['Ad'],
                                "Miktar": b_data['Miktar'],
                                "Personel": st.session_state.get('kullanici_adi', 'Sistem'),
                                "Adres": b_data['Adres'],
                                "Tedarikçi Barkod": b_code,
                                "Durum": b_data['Durum']
                            }])], ignore_index=True)

                            # 3. SATIN_ALMA TABLOSUNDA GELEN MİKTARI GÜNCELLE
                            if b_data.get('SAS_Kalem_ID') is not None:
                                try:
                                    df_sas_up.loc[b_data['SAS_Kalem_ID'], 'Gelen Miktar'] = b_data['Miktar']
                                    df_sas_up.loc[b_data['SAS_Kalem_ID'], 'Tedarikçi Barkodu'] = b_code
                                except:
                                    pass

                            basarili_kayit += 1

                        # VERİTABANINA KAYDET
                        veritabani.update_data("Stok", df_stok)
                        veritabani.update_data("Hareketler", df_har)
                        veritabani.update_data("Satin_Alma", df_sas_up)

                        # BAŞARILI İLETİSİ
                        st.balloons()
                        st.success(f"✅ {basarili_kayit} ürün başarıyla stoğa aktarıldı!")
                        st.info("📍 Stok, Hareketler ve Satın Alma tabloları güncellendi.")

                        # LİSTEYİ TEMİZLE
                        st.session_state.mk_gecici_liste = {}
                        st.session_state.full_sas_data = pd.DataFrame()
                        st.session_state.teslim_page = 'menu'
                        
                        # YENİ SAYFAYı YÜKLE
                        import time
                        time.sleep(2)
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Hata oluştu: {str(e)}")
                        st.write("**Detay:**", str(e))
        else:
            st.warning("⚠️ Henüz barkod okutulmamış. Lütfen barkod okutun ve miktar girin.")

        st.markdown("---")
        st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş | BRN 2026</b></div>", unsafe_allow_html=True)
