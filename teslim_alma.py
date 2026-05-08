import streamlit as st
import pandas as pd
import veritabani
from datetime import datetime

def init_state():
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'menu'
    if 'sel_siparis' not in st.session_state: st.session_state.sel_siparis = None
    if 'sel_tedarikci' not in st.session_state: st.session_state.sel_tedarikci = None
    if 'irsaliye_no' not in st.session_state: st.session_state.irsaliye_no = ""
    if 'mk_gecici_liste' not in st.session_state: st.session_state.mk_gecici_liste = []
    if 'sip_gecici_liste' not in st.session_state: st.session_state.sip_gecici_liste = []
    if 'new_po_no' not in st.session_state: st.session_state.new_po_no = None

def clear_form():
    st.session_state.reset_mk_form = True

def run(conn):
    init_state()

    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; }
        .stCaption { font-size: 11px !important; }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.get("reset_mk_form"):
        st.session_state.mk_mik = 0.0
        st.session_state.mk_adr = ""
        st.session_state.reset_mk_form = False

    # --- 0. ANA MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma Modülü")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("📦\nMAL KABUL\n(Açık Siparişleri Teslim Al)", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'secim'))
        with col2:
            st.button("📝\nSATINALMA SİPARİŞİ\n(Yeni Sipariş Oluştur)", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'olustur'))

    # --- 1. SİPARİŞ OLUŞTURMA EKRANI ---
    elif st.session_state.teslim_page == 'olustur':
        if st.button("⬅️ ANA MENÜYE DÖN"): 
            st.session_state.sip_gecici_liste = []
            st.session_state.new_po_no = None
            st.session_state.teslim_page = 'menu'
            st.rerun()

        st.subheader("📝 Yeni Satınalma Siparişi Oluştur")
        
        if not st.session_state.new_po_no:
            st.session_state.new_po_no = f"SAS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                sip_tedarikci = st.text_input("🏢 Tedarikçi Adı (Zorunlu):").upper().strip()
            with col2:
                sip_no = st.text_input("📄 Sipariş Numarası (Otomatik):", value=st.session_state.new_po_no, disabled=True)

        st.markdown("---")
        
        try:
            katalog = veritabani.get_katalog() 
        except:
            katalog = []
            
        sec_urun = st.selectbox("Katalogdan Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog, key="sip_katalog_secim")

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            if sec_urun != "+ MANUEL GİRİŞ" and " | " in sec_urun:
                s_kod = sec_urun.split(" | ")[0]; s_isim = sec_urun.split(" | ")[1]
                st.text_input("📦 Malzeme Kodu:", value=s_kod, disabled=True, key="sip_kod_d")
            else:
                s_kod = st.text_input("📦 Malzeme Kodu:", key="sip_kod_m").upper().strip()
                s_isim = st.text_input("📝 Malzeme Adı:", key="sip_isim_m").upper().strip()

        with c2:
            s_mik = st.number_input("🔢 Sipariş Miktarı:", min_value=0.0, step=1.0, key="sip_mik_m")
        with c3:
            s_birim = st.selectbox("📏 Birim:", ["ADET", "KG", "METRE", "LİTRE", "PAKET", "KUTU", "RULO"], key="sip_birim_m")

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            if not sip_tedarikci or not s_kod or s_mik <= 0:
                st.error("Eksik bilgileri doldurun!")
            else:
                next_kalem = (len(st.session_state.sip_gecici_liste) + 1) * 10
                kalem = {
                    "Tedarikçi": sip_tedarikci, "Sipariş No": st.session_state.new_po_no,
                    "Kalem No": next_kalem,
                    "Stok Kodu": s_kod, "Stok Adı": s_isim, "Sipariş Miktarı": s_mik,
                    "Gelen Miktar": 0.0, "Birim": s_birim
                }
                st.session_state.sip_gecici_liste.append(kalem)
                st.rerun()

        if st.session_state.sip_gecici_liste:
            st.markdown("### 📋 Sipariş Sepeti")
            for i, item in enumerate(st.session_state.sip_gecici_liste):
                with st.expander(f"Kalem {item['Kalem No']}: {item['Stok Adı']} - {item['Sipariş Miktarı']} {item['Birim']}"):
                    if st.button(f"🗑️ Satırı Sil", key=f"del_sip_{i}"):
                        st.session_state.sip_gecici_liste.pop(i); st.rerun()
            
            if st.button("🚀 SİPARİŞİ SİSTEME KAYDET", type="primary", use_container_width=True):
                try:
                    df_mevcut = veritabani.get_internal_data("Satin_Alma")
                    if "Kalem No" not in df_mevcut.columns: df_mevcut["Kalem No"] = 0
                except:
                    df_mevcut = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Kalem No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])

                df_yeni = pd.DataFrame(st.session_state.sip_gecici_liste)
                df_son = pd.concat([df_mevcut, df_yeni], ignore_index=True)
                veritabani.update_data("Satin_Alma", df_son)
                st.session_state.sip_gecici_liste = []; st.session_state.new_po_no = None
                st.success("✅ Kaydedildi!"); st.session_state.teslim_page = 'menu'; st.rerun()

    # --- 2. MAL KABUL SEÇİM (ADIM 1) ---
    elif st.session_state.teslim_page == 'secim':
        if st.button("⬅️ ANA MENÜYE DÖN"): st.session_state.teslim_page = 'menu'; st.rerun()
        st.subheader("🔍 Mal Kabul Seçimi")

        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
            if "Kalem No" not in df_siparis.columns: df_siparis["Kalem No"] = 10
            
            df_bekleyen = df_siparis[(df_siparis['Sipariş Miktarı'] - df_siparis['Gelen Miktar']) > 0]
            tedarikci_listesi = ["Tümü"] + sorted(df_bekleyen['Tedarikçi'].dropna().unique().tolist())
        except:
            df_bekleyen = pd.DataFrame(); tedarikci_listesi = ["Tümü"]

        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                secilen_tedarikci = st.selectbox("🏢 Tedarikçi Seç:", tedarikci_listesi)
            with col2:
                sip_filt = df_bekleyen if secilen_tedarikci == "Tümü" else df_bekleyen[df_bekleyen['Tedarikçi'] == secilen_tedarikci]
                siparis_listesi = sorted(sip_filt['Sipariş No'].dropna().unique().tolist())
                secilen_siparis = st.selectbox("📄 Sipariş No:", ["Seçiniz..."] + siparis_listesi)

            irsaliye = st.text_input("🧾 İrsaliye No:").upper().strip()

            if st.button("🚀 İLERLE", use_container_width=True, type="primary"):
                if secilen_siparis != "Seçiniz..." and irsaliye:
                    st.session_state.sel_tedarikci = df_bekleyen[df_bekleyen['Sipariş No'] == secilen_siparis].iloc[0]['Tedarikçi']
                    st.session_state.sel_siparis = secilen_siparis
                    st.session_state.irsaliye_no = irsaliye
                    st.session_state.mk_gecici_liste = []
                    st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- 3. ÜRÜN GİRİŞİ (ADIM 2) ---
    elif st.session_state.teslim_page == 'kabul':
        if st.button("⬅️ SEÇİME DÖN"): st.session_state.teslim_page = 'secim'; st.rerun()
        st.info(f"**Sipariş:** {st.session_state.sel_siparis} | **Tedarikçi:** {st.session_state.sel_tedarikci}")

        df_siparis = veritabani.get_internal_data("Satin_Alma")
        if "Kalem No" not in df_siparis.columns: df_siparis["Kalem No"] = 10
        
        df_stok = veritabani.get_internal_data("Stok")
        df_hareket = veritabani.get_internal_data("Hareketler")

        sub = df_siparis[df_siparis['Sipariş No'] == st.session_state.sel_siparis].copy()
        sub['unique_key'] = sub['Kalem No'].astype(str) + " | " + sub['Stok Adı'] + " (" + sub['Stok Kodu'] + ")"
        bekleyenler = sub[(sub['Sipariş Miktarı'] - sub['Gelen Miktar']) > 0].copy()

        if not bekleyenler.empty:
            sel_display = st.selectbox("🎯 Malzeme Seç:", ["Seçiniz..."] + bekleyenler['unique_key'].tolist())

            if sel_display != "Seçiniz...":
                row = bekleyenler[bekleyenler['unique_key'] == sel_display].iloc[0]
                sepetteki = sum([x['Miktar'] for x in st.session_state.mk_gecici_liste if x['Kalem No'] == row['Kalem No']])
                # Kalan ihtiyaç hesabı
                kalan_ih = round(row['Sipariş Miktarı'] - row['Gelen Miktar'] - sepetteki, 3)

                with st.container(border=True):
                    st.markdown(f"🛠️ **Kalem No: {row['Kalem No']}** | {row['Stok Adı']}")
                    
                    # METRİKLER: Sipariş Miktarı ve Kalan Teslim Alma
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("📦 Sipariş Miktarı", f"{row['Sipariş Miktarı']} {row['Birim']}")
                    col_m2.metric("🎯 Kalan Bekleyen", f"{kalan_ih} {row['Birim']}", delta_color="inverse")
                    
                    st.markdown("---")
                    
                    r1c1, r1c2 = st.columns([2, 1])
                    input_adr = r1c1.text_input("📍 Adres:", key="mk_adr").upper().strip()
                    input_mik = r1c2.number_input("🔢 Kabul Miktarı:", min_value=0.0, max_value=float(kalan_ih), step=1.0, key="mk_mik")

                    if st.button("➕ LİSTEYE EKLE", use_container_width=True):
                        if input_adr and input_mik > 0:
                            st.session_state.mk_gecici_liste.append({
                                "Kalem No": row['Kalem No'], "Stok Kodu": row['Stok Kodu'],
                                "Stok Adı": row['Stok Adı'], "Adres": input_adr, "Miktar": input_mik, "Birim": row['Birim']
                            })
                            clear_form(); st.rerun()

            if st.session_state.mk_gecici_liste:
                st.markdown("### 🛒 Sepet")
                for i, item in enumerate(st.session_state.mk_gecici_liste):
                    with st.expander(f"Kalem {item['Kalem No']}: {item['Miktar']} {item['Birim']}"):
                        if st.button(f"🗑️ Satırı Sil", key=f"del_mk_{i}"):
                            st.session_state.mk_gecici_liste.pop(i); st.rerun()
                
                if st.button("🚀 TÜMÜNÜ STOĞA KAYDET", type="primary", use_container_width=True):
                    personel = st.session_state.kullanici_adi if 'kullanici_adi' in st.session_state else "Sistem"
                    for item in st.session_state.mk_gecici_liste:
                        mask_stok = (df_stok['Kod'] == item['Stok Kodu']) & (df_stok['Adres'] == item['Adres'])
                        if mask_stok.any():
                            df_stok.loc[mask_stok, 'Miktar'] += item['Miktar']
                        else:
                            df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": item['Stok Kodu'], "İsim": item['Stok Adı'], "Adres": item['Adres'], "Miktar": item['Miktar'], "Durum": "Kullanılabilir"}])], ignore_index=True)

                        mask_emir = (df_siparis['Sipariş No'] == st.session_state.sel_siparis) & (df_siparis['Kalem No'] == item['Kalem No'])
                        df_siparis.loc[mask_emir, 'Gelen Miktar'] += item['Miktar']

                        df_hareket = pd.concat([df_hareket, pd.DataFrame([{
                            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", 
                            "İş Emri": st.session_state.sel_siparis, "Kod": item['Stok Kodu'], "Adres": item['Adres'], 
                            "Miktar": item['Miktar'], "Personel": personel, "Lot": st.session_state.irsaliye_no
                        }])], ignore_index=True)

                    veritabani.update_data("Stok", df_stok)
                    veritabani.update_data("Satin_Alma", df_siparis)
                    veritabani.update_data("Hareketler", df_hareket)
                    st.session_state.mk_gecici_liste = []; st.success("✅ Kaydedildi!"); st.rerun()
