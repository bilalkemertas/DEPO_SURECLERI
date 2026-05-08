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

def run(conn):
    init_state()

    # Kompakt tasarım CSS
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 15px !important; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; }
        .stVerticalBlock { gap: 0.8rem !important; }
        .stButton button { height: 2.5rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 0. ANA MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma")
        col1, col2 = st.columns(2)
        with col1:
            st.button("📦 MAL KABUL", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'secim'))
        with col2:
            st.button("📝 SAS OLUŞTUR", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'olustur'))

    # --- 1. SAS OLUŞTURMA ---
    elif st.session_state.teslim_page == 'olustur':
        if st.button("⬅️ MENÜ"): 
            st.session_state.sip_gecici_liste = []; st.session_state.new_po_no = None; st.session_state.teslim_page = 'menu'; st.rerun()

        if not st.session_state.new_po_no:
            st.session_state.new_po_no = f"SAS-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        with st.container(border=True):
            c1, c2 = st.columns(2)
            sip_tedarikci = c1.text_input("🏢 Tedarikçi:", placeholder="Zorunlu").upper().strip()
            sip_no = c2.text_input("📄 SAS No:", value=st.session_state.new_po_no, disabled=True)

        try: katalog = veritabani.get_katalog() 
        except: katalog = []
            
        sec_urun = st.selectbox("🎯 Ürün:", ["+ MANUEL GİRİŞ"] + katalog, key="sip_katalog_secim")

        c1, c2, c3 = st.columns([2, 1, 1])
        if sec_urun != "+ MANUEL GİRİŞ" and " | " in sec_urun:
            s_kod = sec_urun.split(" | ")[0]; s_isim = sec_urun.split(" | ")[1]
            c1.text_input("📦 Kod:", value=s_kod, disabled=True, key="fixed_kod_view")
        else:
            s_kod = c1.text_input("📦 Kod:", key="sip_kod_m").upper().strip()
            s_isim = st.text_input("📝 Ad:", key="sip_isim_m").upper().strip()

        s_mik = c2.number_input("🔢 Miktar:", min_value=0.0, step=1.0, key="sip_mik_input")
        s_birim = c3.selectbox("📏 Birim:", ["ADET", "KG", "METRE", "PAKET", "RULO"], key="sip_birim_input")

        if st.button("➕ EKLE", use_container_width=True, key="btn_sas_ekle"):
            if sip_tedarikci and s_kod and s_mik > 0:
                next_kalem = (len(st.session_state.sip_gecici_liste) + 1) * 10
                st.session_state.sip_gecici_liste.append({
                    "Tedarikçi": sip_tedarikci, "Sipariş No": st.session_state.new_po_no, "Kalem No": next_kalem,
                    "Stok Kodu": s_kod, "Stok Adı": s_isim, "Sipariş Miktarı": s_mik, "Gelen Miktar": 0.0, "Birim": s_birim
                })
                st.rerun()

        if st.session_state.sip_gecici_liste:
            if st.button("🚀 SİPARİŞİ KAYDET", type="primary", use_container_width=True):
                df_m = veritabani.get_internal_data("Satin_Alma")
                df_son = pd.concat([df_m, pd.DataFrame(st.session_state.sip_gecici_liste)], ignore_index=True)
                veritabani.update_data("Satin_Alma", df_son)
                st.session_state.sip_gecici_liste = []; st.session_state.new_po_no = None; st.session_state.teslim_page = 'menu'; st.rerun()

    # --- 2. MAL KABUL SEÇİM ---
    elif st.session_state.teslim_page == 'secim':
        if st.button("⬅️ MENÜ"): st.session_state.teslim_page = 'menu'; st.rerun()
        try:
            df_s = veritabani.get_internal_data("Satin_Alma")
            df_b = df_s[(df_s['Sipariş Miktarı'] - df_s['Gelen Miktar']) > 0]
            t_list = ["Tümü"] + sorted(df_b['Tedarikçi'].dropna().unique().tolist())
        except:
            df_b = pd.DataFrame(); t_list = ["Tümü"]

        with st.container(border=True):
            c1, c2 = st.columns(2)
            sec_ted = c1.selectbox("🏢 Tedarikçi:", t_list)
            sip_f = df_b if sec_ted == "Tümü" else df_b[df_b['Tedarikçi'] == sec_ted]
            sec_sip = c2.selectbox("📄 SAS No:", ["Seçiniz..."] + sorted(sip_f['Sipariş No'].unique().tolist()))
            irs = st.text_input("🧾 İrsaliye No:").upper().strip()

            if st.button("🚀 İLERLE", use_container_width=True, type="primary"):
                if sec_sip != "Seçiniz..." and irs:
                    st.session_state.sel_tedarikci = df_b[df_b['Sipariş No'] == sec_sip].iloc[0]['Tedarikçi']
                    st.session_state.sel_siparis = sec_sip; st.session_state.irsaliye_no = irs
                    st.session_state.mk_gecici_liste = []; st.session_state.teslim_page = 'kabul'; st.rerun()

    # --- 3. MAL KABUL GİRİŞ ---
    elif st.session_state.teslim_page == 'kabul':
        c1, c2 = st.columns([1, 4])
        if c1.button("⬅️"): st.session_state.teslim_page = 'secim'; st.rerun()
        c2.caption(f"**PO:** {st.session_state.sel_siparis}")

        df_s = veritabani.get_internal_data("Satin_Alma")
        sub = df_s[df_s['Sipariş No'] == st.session_state.sel_siparis].copy()
        sub['key'] = sub['Kalem No'].astype(str) + " | " + sub['Stok Adı'] + " (" + sub['Stok Kodu'] + ")"
        bekleyenler = sub[(sub['Sipariş Miktarı'] - sub['Gelen Miktar']) > 0].copy()

        if not bekleyenler.empty:
            sel_d = st.selectbox("🎯 Malzeme:", ["Seçiniz..."] + bekleyenler['key'].tolist(), label_visibility="collapsed", key="mk_select_item")

            if sel_d != "Seçiniz...":
                row = bekleyenler[bekleyenler['key'] == sel_d].iloc[0]
                sep = sum([x['Miktar'] for x in st.session_state.mk_gecici_liste if x['Kalem No'] == row['Kalem No']])
                k_ih = round(row['Sipariş Miktarı'] - row['Gelen Miktar'] - sep, 3)

                with st.container(border=True):
                    st.write(f"**{row['Stok Adı']}**")
                    m_col1, m_col2 = st.columns(2)
                    m_col1.metric("📦 Sipariş", f"{row['Sipariş Miktarı']}")
                    m_col2.metric("🎯 Kalan", f"{k_ih}", delta_color="inverse")
                    
                    r1, r2, r3 = st.columns([1.5, 1, 1])
                    i_adr = r1.text_input("📍 Adres:", key="mk_adr_input").upper().strip()
                    i_mik = r2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(k_ih), step=1.0, key="mk_mik_input")
                    # Sayım ve Stok ekranındaki Durum seçenekleri eklendi
                    i_dur = r3.selectbox("🛡️ Durum:", ["Kullanılabilir", "Bloke", "Karantina"], key="mk_dur_input")

                    if st.button("➕ EKLE", use_container_width=True, key="btn_mk_ekle"):
                        if i_adr and i_mik > 0:
                            st.session_state.mk_gecici_liste.append({
                                "Kalem No": row['Kalem No'], "Stok Kodu": row['Stok Kodu'],
                                "Stok Adı": row['Stok Adı'], "Adres": i_adr, "Miktar": i_mik, 
                                "Birim": row['Birim'], "Durum": i_dur
                            })
                            st.rerun()

            if st.session_state.mk_gecici_liste:
                st.markdown("🛒 **Sepettekiler**")
                for i, item in enumerate(st.session_state.mk_gecici_liste):
                    with st.expander(f"{item['Stok Adı']} | {item['Miktar']} ({item['Adres']}) - {item['Durum']}", expanded=False):
                        if st.button(f"🗑️ Sil", key=f"del_mk_{i}"):
                            st.session_state.mk_gecici_liste.pop(i); st.rerun()
                
                if st.button("🚀 TÜMÜNÜ STOĞA KAYDET", type="primary", use_container_width=True, key="btn_final_save"):
                    df_stok = veritabani.get_internal_data("Stok")
                    df_har = veritabani.get_internal_data("Hareketler")
                    pers = st.session_state.get('kullanici_adi', "Sistem")
                    
                    for item in st.session_state.mk_gecici_liste:
                        # Stok Güncelleme (Kod, Adres VE Durum bazlı kontrol)
                        m_stok = (df_stok['Kod'] == item['Stok Kodu']) & (df_stok['Adres'] == item['Adres']) & (df_stok['Durum'] == item['Durum'])
                        if m_stok.any(): 
                            df_stok.loc[m_stok, 'Miktar'] += item['Miktar']
                        else: 
                            df_stok = pd.concat([df_stok, pd.DataFrame([{
                                "Kod": item['Stok Kodu'], 
                                "İsim": item['Stok Adı'], 
                                "Adres": item['Adres'], 
                                "Miktar": item['Miktar'], 
                                "Durum": item['Durum']
                            }])], ignore_index=True)
                        
                        # SAS Güncelleme
                        m_sas = (df_s['Sipariş No'] == st.session_state.sel_siparis) & (df_s['Kalem No'] == item['Kalem No'])
                        df_s.loc[m_sas, 'Gelen Miktar'] += item['Miktar']
                        
                        # Hareket Kaydı
                        df_har = pd.concat([df_har, pd.DataFrame([{
                            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                            "İşlem": "GİRİŞ", 
                            "İş Emri": st.session_state.sel_siparis, 
                            "Kod": item['Stok Kodu'], 
                            "İsim": item['Stok Adı'], 
                            "Adres": item['Adres'], 
                            "Miktar": item['Miktar'], 
                            "Personel": pers, 
                            "Durum": item['Durum'], # Hareketler tablosuna durum eklendi
                            "Lot": st.session_state.irsaliye_no
                        }])], ignore_index=True)

                    veritabani.update_data("Stok", df_stok); veritabani.update_data("Satin_Alma", df_s); veritabani.update_data("Hareketler", df_har)
                    st.session_state.mk_gecici_liste = []; st.success("Başarılı"); st.rerun()

            st.caption("**Açık SAS Kalemleri**")
            st.dataframe(bekleyenler[["Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar"]], use_container_width=True, hide_index=True)

veritabani.footer()
