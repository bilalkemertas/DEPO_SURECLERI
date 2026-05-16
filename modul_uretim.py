import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- GÜVENLİ BAŞLATICI ---
def init_state():
    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'
    
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    if 'sel_is_emri' not in st.session_state:
        st.session_state.sel_is_emri = None

    # RAM üzerinden çalışma için kritik state'ler
    if 'local_db_active' not in st.session_state:
        st.session_state.local_db_active = None
    
    if 'local_stok' not in st.session_state:
        st.session_state.local_stok = None

    # HAREKET KAYITLARI İÇİN RAM ALANI
    if 'local_movements' not in st.session_state:
        st.session_state.local_movements = []

# --- NAVİGASYON ---
def go_home(): 
    init_state()
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    init_state()
    st.session_state.uretim_page = 'menu'
    st.session_state.sel_is_emri = None
    st.session_state.local_db_active = None # Belleği temizle
    st.session_state.local_movements = [] # RAM Hareketleri temizle
    
    if 'local_emirler' in st.session_state:
        del st.session_state.local_emirler

def goster():
    init_state()
    
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; }
        .stCaption { font-size: 11px !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            go_home()
            st.rerun()
            
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        st.button("🏗️ ÜRETİM HAZIRLIK YAP", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik_secim'))
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'rapor'))

    # --- 1. YÜKLEME (GELİŞMİŞ TOPLU YÜKLEME) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ"):
            go_uretim_menu()
            st.rerun()
            
        st.subheader("📤 Çoklu İş Emri Excel'i Yükleme")
        
        uploaded_files = st.file_uploader("Dosyaları Seçin:", type=['xlsx'], accept_multiple_files=True)
        
        if uploaded_files:
            all_valid_dataframes = []
            successfully_parsed_names = []
            
            # Veritabanındaki güncel durumu DRIVE'dan çek
            df_current_db = veritabani.get_internal_data("Is_Emirleri")
            existing_emir_names = []
            if df_current_db is not None and not df_current_db.empty:
                df_current_db.columns = [str(c).strip() for c in df_current_db.columns]
                existing_emir_names = df_current_db['İş Emri'].unique().tolist()

            for current_file in uploaded_files:
                current_emri_adi = current_file.name.rsplit('.', 1)[0]
                
                # Mükerrer Kontrolü
                if current_emri_adi in existing_emir_names:
                    st.warning(f"⚠️ '{current_emri_adi}' zaten veritabanında mevcut. Atlanıyor.")
                    continue
                
                try:
                    # --- SEKME KONTROLÜ (HAZIRLIK veya Sheet4) ---
                    excel_obj = pd.ExcelFile(current_file)
                    target_sheet = None
                    for s in excel_obj.sheet_names:
                        if s.upper() in ["HAZIRLIK", "SHEET4"]:
                            target_sheet = s
                            break
                    
                    if not target_sheet:
                        st.error(f"❌ {current_file.name} içinde 'HAZIRLIK' veya 'Sheet4' bulunamadı!")
                        continue

                    df_raw = pd.read_excel(current_file, sheet_name=target_sheet, header=None)
                    header_row_index = 0
                    
                    for row_idx in range(min(30, len(df_raw))):
                        values_in_row = [str(cell).lower().strip() for cell in df_raw.iloc[row_idx].fillna("").values]
                        if "stok kodu" in values_in_row:
                            header_row_index = row_idx
                            break
                    
                    df_extracted = df_raw.iloc[header_row_index:].copy()
                    df_extracted.columns = df_extracted.iloc[0]
                    df_extracted = df_extracted.iloc[1:].reset_index(drop=True)
                    df_extracted.columns = [str(col_name).strip() for col_name in df_extracted.columns]
                    
                    # --- KALEM NO EKLEME ---
                    df_extracted['Kalem No'] = range(1, len(df_extracted) + 1)
                    
                    if 'Mamül Adı' in df_extracted.columns:
                        df_extracted['Mamül Adı'] = df_extracted['Mamül Adı'].ffill()
                    elif 'Ürün Adı' in df_extracted.columns:
                        df_extracted['Mamül Adı'] = df_extracted['Ürün Adı'].ffill()
                    
                    df_extracted = df_extracted.dropna(subset=['Stok Kodu', 'Stok Adı'])
                    df_extracted['İş Emri'] = current_emri_adi
                    df_extracted['Hazırlanan Adet'] = 0
                    
                    for col_name in df_extracted.columns:
                        if any(keyword in col_name.lower() for keyword in ['total', 'ihtiyaç', 'miktar']):
                            df_extracted['İhtiyaç Miktarı'] = pd.to_numeric(df_extracted[col_name], errors='coerce').fillna(0)
                            break
                    
                    target_columns = ["İş Emri", "Kalem No", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                    df_final_filtered = df_extracted[[c for c in target_columns if c in df_extracted.columns]]
                    
                    all_valid_dataframes.append(df_final_filtered)
                    successfully_parsed_names.append(current_emri_adi)
                    
                except Exception as file_error:
                    st.error(f"❌ {current_file.name} okunurken teknik bir hata oluştu: {file_error}")

            if all_valid_dataframes:
                st.write(f"📋 **{len(successfully_parsed_names)}** adet yeni iş emri Yüklenmeye hazır:")
                st.success(", ".join(successfully_parsed_names))
                
                df_to_upload = pd.concat(all_valid_dataframes, ignore_index=True)
                st.dataframe(df_to_upload, use_container_width=True, hide_index=True)
                
                if st.button("🚀 TÜMÜNÜ VERİTABANINA YÜKLE", type="primary", use_container_width=True):
                    # Birleştirme sırasında veritabanını tekrar tazeleyerek oku
                    df_refresh_db = veritabani.get_internal_data("Is_Emirleri")
                    if df_refresh_db is not None: df_refresh_db.columns = [str(c).strip() for c in df_refresh_db.columns]
                    df_master_concat = pd.concat([df_refresh_db, df_to_upload], ignore_index=True)
                    
                    # DRIVE GÜNCELLEME
                    veritabani.update_data("Is_Emirleri", df_master_concat)
                    st.success(f"✅ Başarılı! {len(successfully_parsed_names)} iş emri sisteme Yüklendi.")
                    st.rerun()

    # --- 2. SEÇİM EKRANI (ZIRHLANMIŞ OKUMA) ---
    elif st.session_state.uretim_page == 'hazirlik_secim':
        if st.button("⬅️ GERİ"):
            go_uretim_menu()
            st.rerun()
            
        st.subheader("🔍 İş Emri Hazırlık Seçimi")
        
        # Drive'dan en güncel veriyi zorla çek
        df_db_select = veritabani.get_internal_data("Is_Emirleri")
        
        # KRİTİK KONTROL
        if df_db_select is not None and not df_db_select.empty:
            df_db_select.columns = [str(c).strip() for c in df_db_select.columns]
            # Sayısal zırh
            if 'İhtiyaç Miktarı' in df_db_select.columns:
                df_db_select['İhtiyaç Miktarı'] = pd.to_numeric(df_db_select['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            if 'Hazırlanan Adet' in df_db_select.columns:
                df_db_select['Hazırlanan Adet'] = pd.to_numeric(df_db_select['Hazırlanan Adet'], errors='coerce').fillna(0)

            summary_emir = df_db_select.groupby('İş Emri').agg({
                'İhtiyaç Miktarı': 'sum', 
                'Hazırlanan Adet': 'sum'
            }).reset_index()
            
            def calculate_status(row_data):
                if row_data['Hazırlanan Adet'] >= row_data['İhtiyaç Miktarı'] - 0.001:
                    return "✅ Tamamlandı"
                elif row_data['Hazırlanan Adet'] > 0:
                    return "🏗️ Devam Ediyor"
                else:
                    return "🆕 Başlanmadı"
            
            summary_emir['Durum'] = summary_emir.apply(calculate_status, axis=1)
            
            # Filtreleme
            status_filter_choice = st.radio("🚩 Statü Filtresi:", ["Tümü", "🆕 Başlanmadı", "🏗️ Devam Ediyor", "✅ Tamamlandı"], horizontal=True)
            
            df_emir_filtered = summary_emir.copy()
            if status_filter_choice != "Tümü":
                df_emir_filtered = df_emir_filtered[df_emir_filtered['Durum'] == status_filter_choice]
            
            # Dropdown Listesi
            list_for_dropdown = [f"{record['İş Emri']} | {record['Durum']}" for _, record in df_emir_filtered.iterrows()]
            
            if list_for_dropdown:
                raw_selection = st.selectbox("Lütfen bir iş emri seçin:", ["Seçiniz..."] + list_for_dropdown)
                
                if raw_selection != "Seçiniz...":
                    clean_emri_name = raw_selection.split(" | ")[0]
                    if st.button("🚀 ÜRETİM HAZIRLIĞINA GİT", use_container_width=True, type="primary"):
                        st.session_state.sel_is_emri = clean_emri_name
                        # 🟢 KRİTİK: Drive'dan RAM'e Tek Seferlik Okuma
                        st.session_state.local_db_active = df_db_select.copy()
                        st.session_state.local_stok = veritabani.get_internal_data("Stok")
                        st.session_state.local_movements = [] # Yeni hazırlık için temizle
                        st.session_state.uretim_page = 'hazirlik_panel'
                        st.rerun()
            else:
                st.info(f"💡 Bu statüde ({status_filter_choice}) uygun iş emri bulunamadı.")
        else:
            st.error("⚠️ Drive verisi henüz okunmadı veya 'Is_Emirleri' sekmesi boş!")
            if st.button("🔄 VERİLERİ YENİDEN TARA"):
                st.rerun()

    # --- 3. HAZIRLIK PANELİ (RAM ÜZERİNDEN ÇALIŞMA + DİNAMİK HAREKET ENTEGRASYONU) ---
    elif st.session_state.uretim_page == 'hazirlik_panel':
        if st.button("⬅️ SEÇİM EKRANINA DÖN"):
            st.session_state.uretim_page = 'hazirlik_secim'
            st.rerun()
            
        st.subheader(f"🏗️ İş Emri: {st.session_state.sel_is_emri}")
        
        # Drive'a gitmek yerine RAM'den (session_state) okuyoruz
        df_db_active = st.session_state.local_db_active
        df_stok_active = st.session_state.local_stok
        
        # Kolon Zırhı
        if df_db_active is not None:
            df_db_active.columns = [str(c).strip() for c in df_db_active.columns]

        sub_view = df_db_active[df_db_active['İş Emri'] == st.session_state.sel_is_emri].copy()
        pending_items = sub_view[(sub_view['İhtiyaç Miktarı'] - sub_view['Hazırlanan Adet']) > 0.001].copy()
        
        if not pending_items.empty:
            # --- KALEM NO BAZLI SEÇİM ---
            pending_items['display_key'] = (
                "Kalem " + pending_items['Kalem No'].astype(str) + " | " + 
                pending_items['Stok Adı'] + " | " + pending_items['Stok Kodu']
            )
            active_item_selection = st.selectbox("🎯 Hazırlanacak Malzeme:", ["Seçiniz..."] + pending_items['display_key'].tolist())
            
            if active_item_selection != "Seçiniz...":
                selected_row_data = pending_items[pending_items['display_key'] == active_item_selection].iloc[0]
                target_stock_code = str(selected_row_data['Stok Kodu']).strip().upper()
                target_kalem_no = selected_row_data['Kalem No'] 
                remaining_need = round(selected_row_data['İhtiyaç Miktarı'] - selected_row_data['Hazırlanan Adet'], 3)
                
                specific_stock_view = df_stok_active[df_stok_active["Kod"].astype(str).str.strip().str.upper() == target_stock_code]
                
                with st.container(border=True):
                    st.markdown(f"🛠️ **Seçili Ürün:** {selected_row_data['Stok Adı']} (Kalem: {target_kalem_no})")
                    total_available_stock = specific_stock_view['Miktar'].sum() if not specific_stock_view.empty else 0
                    
                    metric_c1, metric_c2, metric_c3 = st.columns(3)
                    metric_c1.metric("Kalan İhtiyaç", f"{remaining_need} {selected_row_data.get('Birim','AD')}")
                    metric_c2.metric("Toplam Depo Stoğu", f"{total_available_stock} {selected_row_data.get('Birim','AD')}")
                    
                    input_col_1, input_col_2 = st.columns([2, 1])
                    valid_address_records = specific_stock_view[specific_stock_view["Miktar"] > 0]
                    address_dropdown_list = ["Adres Seçiniz..."] + [f"{r['Adres']} ({r['Miktar']} {selected_row_data.get('Birim','AD')})" for _, r in valid_address_records.iterrows()] if not valid_address_records.empty else ["STOKTA YOK"]
                    
                    raw_address_selection = input_col_1.selectbox("📍 Kaynak Raf:", address_dropdown_list)
                    
                    current_shelf_qty = 0
                    if "Adres Seçiniz..." not in raw_address_selection and "STOKTA YOK" not in raw_address_selection:
                        current_shelf_qty = float(raw_address_selection.split('(')[1].split(' ')[0])
                        metric_c3.metric("Seçili Raf Stoğu", f"{current_shelf_qty}")
                    else:
                        metric_c3.metric("Seçili Raf Stoğu", "0.0")
                    
                    output_quantity_input = input_col_2.number_input("🔢 Çıkış Miktarı:", min_value=0.0, max_value=float(remaining_need), step=1.0)
                    
                    if st.button("➕ RAM LİSTESİNE EKLE", use_container_width=True):
                        if "Adres Seçiniz..." in raw_address_selection or output_quantity_input <= 0:
                            st.warning("⚠️ Lütfen geçerli bir raf ve miktar girin.")
                        else:
                            # 🟢 Akıllı Kullanıcı Zırhı
                            islem_yapan = (
                                st.session_state.get('username') or 
                                st.session_state.get('kullanici') or 
                                st.session_state.get('user') or 
                                st.session_state.get('user_name') or 
                                st.session_state.get('aktif_kullanici') or 
                                'Bilal Kemertaş'
                            )
                            
                            # Adres belirleme (Stokta yoksa sanal raf oluştur)
                            if "STOKTA YOK" in raw_address_selection:
                                actual_address = "SİSTEM-GİRİŞ"
                                current_shelf_qty = 0.0
                            else:
                                actual_address = raw_address_selection.split(' ')[0]

                            eksik_miktar = output_quantity_input - current_shelf_qty

                            # 1. OTOMATİK GİRİŞ KONTROLÜ (Stok yetersizse aradaki farkı otomatik gir)
                            if eksik_miktar > 0:
                                st.session_state.local_movements.append({
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "İşlem": "OTOMATİK GİRİŞ",
                                    "İş Emri": st.session_state.sel_is_emri,
                                    "Kod": target_stock_code,
                                    "İsim": selected_row_data['Stok Adı'],
                                    "Adres": actual_address,
                                    "Miktar": eksik_miktar,
                                    "Personel": "SİSTEM",
                                    "Durum": "Giriş",
                                    "Lot": "-"
                                })
                                
                                mask_stok = (df_stok_active["Kod"].astype(str).str.strip().str.upper() == target_stock_code) & (df_stok_active["Adres"] == actual_address)
                                if df_stok_active[mask_stok].empty:
                                    yeni_stok_satiri = pd.DataFrame([{
                                        "Kod": target_stock_code,
                                        "İsim": selected_row_data['Stok Adı'],
                                        "Adres": actual_address,
                                        "Miktar": eksik_miktar,
                                        "Birim": selected_row_data.get('Birim', 'AD')
                                    }])
                                    df_stok_active = pd.concat([df_stok_active, yeni_stok_satiri], ignore_index=True)
                                    st.session_state.local_stok = df_stok_active
                                else:
                                    df_stok_active.loc[mask_stok, "Miktar"] += eksik_miktar

                            # 2. NORMAL HAZIRLIK ÇIKIŞINI TAMAMLA
                            df_stok_active.loc[(df_stok_active["Kod"].astype(str).str.strip().str.upper() == target_stock_code) & (df_stok_active["Adres"] == actual_address), "Miktar"] -= output_quantity_input
                            
                            mask = (df_db_active['İş Emri'] == st.session_state.sel_is_emri) & (df_db_active['Kalem No'] == target_kalem_no)
                            df_db_active.loc[mask, 'Hazırlanan Adet'] += output_quantity_input
                            df_db_active.loc[mask, 'Hazırlayan'] = islem_yapan 
                            
                            st.session_state.local_movements.append({
                                "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "İşlem": str(st.session_state.sel_is_emri).strip().upper(),
                                "İş Emri": st.session_state.sel_is_emri,
                                "Kod": target_stock_code,
                                "İsim": selected_row_data['Stok Adı'],
                                "Adres": actual_address,
                                "Miktar": output_quantity_input,
                                "Personel": islem_yapan,
                                "Durum": "Hazırlık",
                                "Lot": "-"
                            })
                            
                            st.toast("RAM Listesi Güncellendi (Henüz Kaydedilmedi)")
                            st.rerun()

        # 🚀 KRİTİK: TÜM RAM'İ TEK SEFERDE DRIVE'A YAZMA
        st.info("⚠️ Hazırlıklar bittiğinde aşağıdaki butonla Drive'a kaydedin.")
        if st.button("💾 HAZIRLIK KAYDINI TAMAMLA (DRIVE'A SENKRON ET)", use_container_width=True, type="primary"):
            with st.spinner("Drive veritabanı senkronize ediliyor..."):
                
                # === HATA BURADAYDI, ARTIK BOŞ KAYITTA SİLME YAPAMAZ ===
                if st.session_state.local_movements:
                    df_har_db = veritabani.get_internal_data("Hareketler")
                    if df_har_db is None: 
                        df_har_db = pd.DataFrame()
                    df_new_movs = pd.DataFrame(st.session_state.local_movements)
                    df_har_master = pd.concat([df_har_db, df_new_movs], ignore_index=True)
                    veritabani.update_data("Hareketler", df_har_master)
                
                # TÜMÜNÜ YAZ VE GÜNCELLE (Hareket yoksa bile stok/emir güncellenir)
                veritabani.update_data("Stok", df_stok_active)
                veritabani.update_data("Is_Emirleri", df_db_active)
                
                st.session_state.local_movements = [] # RAM'i sıfırla
                st.success("✅ Tüm işlemler başarıyla Drive'a kaydedildi!"); st.rerun()

        else:
            if pending_items.empty:
                st.success("🎉 Bu iş emrindeki tüm hazırlıklar tamamlanmış.")
        
        st.divider()
        st.dataframe(sub_view[["Kalem No", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]], use_container_width=True, hide_index=True)

    # --- 4. RAPOR (GELİŞMİŞ ANALİZ) ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ ANA MENÜYE DÖN"):
            go_uretim_menu()
            st.rerun()
            
        st.subheader("📊 Üretim Hazırlık Analizi")
        
        df_report_master = veritabani.get_internal_data("Is_Emirleri")
        if df_report_master is not None and not df_report_master.empty:
            df_report_master.columns = [str(c).strip() for c in df_report_master.columns]
            df_report_master['İhtiyaç Miktarı'] = pd.to_numeric(df_report_master['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            df_report_master['Hazırlanan Adet'] = pd.to_numeric(df_report_master['Hazırlanan Adet'], errors='coerce').fillna(0)

            with st.expander("📈 İş Emri Bazlı Tamamlanma Oranları", expanded=False):
                report_summary = df_report_master.groupby('İş Emri').agg({'Stok Kodu': 'count', 'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
                report_summary.columns = ['İş Emri', 'Kalem Sayısı', 'Toplam İhtiyaç', 'Toplam Hazırlanan']
                report_summary['Tamamlanma %'] = (report_summary['Toplam Hazırlanan'] / report_summary['Toplam İhtiyaç'] * 100).round(1)
                st.dataframe(report_summary, use_container_width=True, hide_index=True)

            st.divider()
            st.write("🔍 **Detaylı Rapor Filtreleme**")
            filter_c1, filter_c2 = st.columns(2)
            report_emir_list = ["Tümü"] + sorted(df_report_master['İş Emri'].unique().tolist())
            report_f_emir = filter_c1.selectbox("📋 İş Emri Filtresi:", report_emir_list)
            temp_report_df = df_report_master[df_report_master['İş Emri'] == report_f_emir] if report_f_emir != "Tümü" else df_report_master
            report_mamul_list = ["Tümü"] + sorted(temp_report_df['Mamül Adı'].dropna().unique().tolist())
            report_f_mamul = filter_c2.selectbox("🏗️ Mamül Filtresi:", report_mamul_list)

            report_final_view = temp_report_df.copy()
            if report_f_mamul != "Tümü": report_final_view = report_final_view[report_final_view['Mamül Adı'] == report_f_mamul]
            st.dataframe(report_final_view, use_container_width=True, hide_index=True)
        else: st.info("Raporlanacak veri bulunamadı.")

    # --- SAYFA SONU İMZASI ---
    st.markdown("---")
    sign_c1, sign_c2 = st.columns([3, 1])
    with sign_c2:
        st.markdown(
            """
            <div style='text-align: right;'>
                <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal KEMERTAŞ</p>
                <p style='margin:0; font-size: 12px; color: gray;'>BRN 2026</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
