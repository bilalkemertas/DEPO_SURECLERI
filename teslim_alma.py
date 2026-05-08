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

    # Sepete ekle dedikten sonra formdaki miktar ve adresleri sıfırlayan tetikleyici
    if st.session_state.get("reset_mk_form"):
        st.session_state.mk_mik = 0.0
        st.session_state.mk_adr = ""
        st.session_state.reset_mk_form = False

    # --- 0. ANA MENÜ ---
    if st.session_state.teslim_page == 'menu':
        st.subheader("📦 Mal Kabul & Teslim Alma Modülü")
        st.markdown("---")
        
        st.button("📝 SATINALMA SİPARİŞİ OLUŞTUR", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'olustur'))
        st.button("🚛 MAL KABUL İŞLEMİ (GİRİŞ YAP)", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'teslim_page', 'secim'))

    # --- 0.5 SİPARİŞ OLUŞTURMA EKRANI ---
    elif st.session_state.teslim_page == 'olustur':
        if st.button("⬅️ MAL KABUL MENÜSÜNE DÖN"): 
            st.session_state.sip_gecici_liste = [] # Geri dönerken sepeti temizle
            st.session_state.teslim_page = 'menu'
            st.rerun()

        st.subheader("📝 Yeni Satınalma Siparişi Oluştur")
        st.info("Tedarikçi ve Sipariş Numarasını girdikten sonra ürünleri listeye ekleyin. Tüm liste bittiğinde kaydedin.")
        
        with st.container(border=True):
            st.write("📋 **Sipariş Temel Bilgileri**")
            col1, col2 = st.columns(2)
            with col1:
                sip_tedarikci = st.text_input("🏢 Tedarikçi Adı:").upper().strip()
            with col2:
                sip_no = st.text_input("📄 Sipariş Numarası:").upper().strip()

        st.markdown("---")
        st.write("🔍 **Siparişe Ürün Ekle**")
        
        try:
            katalog = veritabani.get_katalog() 
        except:
            katalog = []
            
        sec_urun = st.selectbox("Katalogdan Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog, key="sip_katalog_secim")

        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            if sec_urun != "+ MANUEL GİRİŞ" and " | " in sec_urun:
                s_kod = sec_urun.split(" | ")[0]
                s_isim = sec_urun.split(" | ")[1]
                st.text_input("📦 Malzeme Kodu:", value=s_kod, disabled=True, key="sip_kod_d")
            else:
                s_kod = st.text_input("📦 Malzeme Kodu:", key="sip_kod_m").upper().strip()
                s_isim = st.text_input("📝 Malzeme Adı:", key="sip_isim_m").upper().strip()

        with c2:
            s_mik = st.number_input("🔢 Sipariş Miktarı:", min_value=0.0, step=1.0, key="sip_mik_m")
        with c3:
            s_birim = st.selectbox("📏 Birim:", ["ADET", "KG", "METRE", "LİTRE", "PAKET", "KUTU"], key="sip_birim_m")

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            if not sip_tedarikci or not sip_no or not s_kod or not s_isim or s_mik <= 0:
                st.error("Lütfen Tedarikçi, Sipariş No ve Ürün bilgilerini eksiksiz doldurun!")
            else:
                kalem = {
                    "Tedarikçi": sip_tedarikci,
                    "Sipariş No": sip_no,
                    "Stok Kodu": s_kod,
                    "Stok Adı": s_isim,
                    "Sipariş Miktarı": s_mik,
                    "Gelen Miktar": 0.0,
                    "Birim": s_birim
                }
                st.session_state.sip_gecici_liste.append(kalem)
                st.rerun()

        if st.session_state.sip_gecici_liste:
            st.markdown("### 📋 Sipariş Sepeti (Henüz Kaydedilmedi)")
            for i, item in enumerate(st.session_state.sip_gecici_liste):
                with st.expander(f"{i+1}. {item['Stok Kodu']} | {item['Stok Adı']} - {item['Sipariş Miktarı']} {item['Birim']}"):
                    if st.button(f"🗑️ Bu Satırı Sil", key=f"del_sip_{i}"):
                        st.session_state.sip_gecici_liste.pop(i)
                        st.rerun()
            
            st.divider()
            if st.button("🚀 OLUŞTURULAN SİPARİŞİ SİSTEME KAYDET", type="primary", use_container_width=True):
                try:
                    df_mevcut = veritabani.get_internal_data("Satin_Alma")
                    if "Sipariş No" not in df_mevcut.columns:
                        df_mevcut = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
                except:
                    df_mevcut = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])

                df_yeni = pd.DataFrame(st.session_state.sip_gecici_liste)
                df_son = pd.concat([df_mevcut, df_yeni], ignore_index=True)
                
                veritabani.update_data("Satin_Alma", df_son)
                
                st.session_state.sip_gecici_liste = []
                st.success("✅ Satınalma siparişi başarıyla veritabanına kaydedildi!")
                st.session_state.teslim_page = 'menu'
                st.rerun()

    # --- ADIM 1: FİLTRELEME VE SEÇİM EKRANI (MAL KABUL) ---
    elif st.session_state.teslim_page == 'secim':
        if st.button("⬅️ MAL KABUL MENÜSÜNE DÖN"): 
            st.session_state.teslim_page = 'menu'
            st.rerun()

        st.subheader("🔍 Adım 1: Sipariş & İrsaliye Seçimi")
        st.markdown("---")

        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
            if "Sipariş No" not in df_siparis.columns:
                df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
        except:
            df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])

        if not df_siparis.empty and "Sipariş Miktarı" in df_siparis.columns and "Gelen Miktar" in df_siparis.columns:
            df_bekleyen = df_siparis[(df_siparis['Sipariş Miktarı'] - df_siparis['Gelen Miktar']) > 0]
            tedarikci_listesi = sorted(df_bekleyen['Tedarikçi'].dropna().unique().tolist())
        else:
            df_bekleyen = pd.DataFrame()
            tedarikci_listesi = []

        with st.container(border=True):
            st.write("📋 **Evrak ve Cari Bilgileri**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                tedarikci_secim = st.selectbox("🏢 Tedarikçi:", ["Manuel Giriş..."] + tedarikci_listesi)
                if tedarikci_secim == "Manuel Giriş...":
                    tedarikci = st.text_input("Tedarikçi Adını Manuel Girin:")
                else:
                    tedarikci = tedarikci_secim

            with col2:
                if tedarikci and tedarikci != "Manuel Giriş..." and not df_bekleyen.empty:
                    siparis_listesi = sorted(df_bekleyen[df_bekleyen['Tedarikçi'] == tedarikci]['Sipariş No'].dropna().unique().tolist())
                else:
                    siparis_listesi = []

                siparis_secim = st.selectbox("📄 Satınalma Sipariş No:", ["Manuel Giriş..."] + siparis_listesi)
                if siparis_secim == "Manuel Giriş...":
                    siparis_no = st.text_input("Sipariş Numarasını Manuel Girin:")
                else:
                    siparis_no = siparis_secim

            irsaliye = st.text_input("🧾 İrsaliye & Fatura No:")

            if st.button("🚀 MAL KABUL EKRANINA İLERLE (ÜRÜN GİRİŞİ)", use_container_width=True, type="primary"):
                if not tedarikci or not siparis_no or not irsaliye:
                    st.error("Lütfen Tedarikçi, Sipariş No ve İrsaliye bilgilerinin tamamını doldurun!")
                else:
                    st.session_state.sel_tedarikci = tedarikci
                    st.session_state.sel_siparis = siparis_no
                    st.session_state.irsaliye_no = irsaliye
                    st.session_state.teslim_page = 'kabul'
                    st.rerun()

    # --- ADIM 2: MAL KABUL İŞLEM EKRANI (ÜRÜN GİRİŞİ) ---
    elif st.session_state.teslim_page == 'kabul':
        if st.button("⬅️ GİRİŞ BİLGİLERİNE DÖN (Adım 1)"): 
            st.session_state.teslim_page = 'secim'
            st.rerun()

        st.subheader(f"📦 Adım 2: Ürün Girişi - Sipariş: {st.session_state.sel_siparis}")
        st.info(f"**🏢 Tedarikçi:** {st.session_state.sel_tedarikci} | **🧾 İrsaliye No:** {st.session_state.irsaliye_no}")

        # Veritabanı çekimleri
        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
            if "Sipariş No" not in df_siparis.columns:
                df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
        except:
            df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
            
        try:
            df_stok = veritabani.get_internal_data("Stok")
            if "Kod" not in df_stok.columns:
                df_stok = pd.DataFrame(columns=["Kod", "İsim", "Adres", "Miktar", "Durum"])
        except:
            df_stok = pd.DataFrame(columns=["Kod", "İsim", "Adres", "Miktar", "Durum"])

        try:
            df_hareket = veritabani.get_internal_data("Hareketler")
            if "Tarih" not in df_hareket.columns:
                df_hareket = pd.DataFrame(columns=["Tarih", "İşlem", "İş Emri", "Kod", "İsim", "Adres", "Miktar", "Personel", "Durum", "Lot", "Kaynak_Adres", "Hedef_Adres"])
        except:
            df_hareket = pd.DataFrame(columns=["Tarih", "İşlem", "İş Emri", "Kod", "İsim", "Adres", "Miktar", "Personel", "Durum", "Lot", "Kaynak_Adres", "Hedef_Adres"])

        sub = df_siparis[df_siparis['Sipariş No'] == st.session_state.sel_siparis].copy()
        
        if not sub.empty:
            bekleyenler = sub[(sub['Sipariş Miktarı'] - sub['Gelen Miktar']) > 0].copy()
        else:
            bekleyenler = pd.DataFrame()

        # SENARYO A: SİPARİŞ EXCEL'DEN VEYA SİSTEMDEN OLUŞTURULMUŞSA (Kayıtlı Sipariş)
        if not bekleyenler.empty:
            bekleyenler['unique_key'] = bekleyenler['Stok Adı'] + " | " + bekleyenler['Stok Kodu']
            sel_display = st.selectbox("🎯 Kabul Edilecek Malzemeyi Seç:", ["Malzeme Seçiniz..."] + bekleyenler['unique_key'].tolist())

            if sel_display != "Malzeme Seçiniz...":
                row = bekleyenler[bekleyenler['unique_key'] == sel_display].iloc[0]
                s_kod = str(row['Stok Kodu']).strip().upper()
                kalan_ih = round(row['Sipariş Miktarı'] - row['Gelen Miktar'], 3)

                with st.container(border=True):
                    st.markdown(f"🛠️ **{row['Stok Adı']}** ({s_kod})")
                    r1c1, r1c2 = st.columns([2, 1])

                    input_adr = r1c1.text_input("📍 Hedef Adres (Nereye Konulacak?):").upper().strip()
                    input_mik = r1c2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(kalan_ih), step=1.0)

                    m1, m2 = st.columns(2)
                    m1.metric("📦 Siparişteki Toplam", f"{row['Sipariş Miktarı']}")
                    m2.metric("🎯 Kalan (Gelecek Olan)", f"{kalan_ih}", delta_color="inverse")

                    if st.button("⚡ KABULÜ TAMAMLA VE STOĞA AL", use_container_width=True, type="primary"):
                        if not input_adr or input_mik <= 0:
                            st.error("Lütfen geçerli bir adres ve miktar girin!")
                        else:
                            # 1. Stok Güncelle
                            df_stok['Kod'] = df_stok['Kod'].astype(str).str.strip().str.upper()
                            df_stok['Adres'] = df_stok['Adres'].astype(str).str.strip().str.upper()
                            mask_stok = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == input_adr)
                            
                            if mask_stok.any():
                                df_stok.loc[mask_stok, 'Miktar'] = pd.to_numeric(df_stok.loc[mask_stok, 'Miktar']) + input_mik
                            else:
                                new_stok = pd.DataFrame([{"Kod": s_kod, "İsim": row['Stok Adı'], "Adres": input_adr, "Miktar": input_mik, "Durum": "Kullanılabilir"}])
                                df_stok = pd.concat([df_stok, new_stok], ignore_index=True)

                            # 2. Sipariş Güncelle
                            mask_emir = (df_siparis['Sipariş No'] == st.session_state.sel_siparis) & (df_siparis['Stok Kodu'] == row['Stok Kodu'])
                            df_siparis.loc[mask_emir, 'Gelen Miktar'] += input_mik

                            # 3. Hareket Ekle
                            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            personel = st.session_state.kullanici_adi if 'kullanici_adi' in st.session_state else "Sistem"
                            new_hareket = pd.DataFrame([{
                                "Tarih": islem_zamani, "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis,
                                "Kod": s_kod, "İsim": row['Stok Adı'], "Adres": input_adr, "Miktar": input_mik,
                                "Personel": personel, "Durum": "Kullanılabilir", "Lot": st.session_state.irsaliye_no,
                                "Kaynak_Adres": st.session_state.sel_tedarikci, "Hedef_Adres": input_adr
                            }])
                            df_hareket = pd.concat([df_hareket, new_hareket], ignore_index=True)

                            veritabani.update_data("Stok", df_stok)
                            veritabani.update_data("Hareketler", df_hareket)
                            veritabani.update_data("Satin_Alma", df_siparis)

                            st.success("✅ Mal Kabul Başarıyla Kaydedildi!")
                            st.rerun()
            
            st.divider()
            st.write("📝 **Sipariş Detay Listesi (Bekleyenler)**")
            if not sub.empty:
                view_cols = ["Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"]
                st.dataframe(sub[[c for c in view_cols if c in sub.columns]], use_container_width=True, hide_index=True)

        # SENARYO B: SİPARİŞ KAYITLI DEĞİLSE (Serbest/Manuel Kabul) Toplu Liste Mantığı
        else:
            st.warning("⚠️ Bu sipariş sisteme önceden yüklenmemiş. Aşağıdan ürünleri tek tek ekleyip toplu olarak kaydedebilirsiniz.")
            
            try:
                katalog = veritabani.get_katalog() 
            except:
                katalog = []
                
            sec_urun = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog)

            c1, c2 = st.columns(2)
            with c1:
                if sec_urun != "+ MANUEL GİRİŞ" and " | " in sec_urun:
                    s_kod = sec_urun.split(" | ")[0]
                    s_isim = sec_urun.split(" | ")[1]
                    st.text_input("📦 Malzeme Kodu:", value=s_kod, disabled=True)
                else:
                    s_kod = st.text_input("📦 Malzeme Kodu:").upper().strip()
                    s_isim = st.text_input("📝 Malzeme Adı:").upper().strip()

            with c2:
                s_mik = st.number_input("🔢 Miktar:", min_value=0.0, step=1.0, key="mk_mik")
                s_adr = st.text_input("📍 Hedef Adres (Nereye Konulacak?):", key="mk_adr").upper().strip()

            # LİSTEYE EKLEME
            if st.button("➕ LİSTEYE EKLE", use_container_width=True):
                if not s_kod or not s_isim or s_mik <= 0 or not s_adr:
                    st.error("Lütfen tüm alanları eksiksiz doldurun!")
                else:
                    kalem = {
                        "Kod": s_kod,
                        "İsim": s_isim,
                        "Miktar": s_mik,
                        "Adres": s_adr
                    }
                    st.session_state.mk_gecici_liste.append(kalem)
                    clear_form() # Eklenen miktarı formdan temizle
                    st.rerun()

            # LİSTEYİ GÖSTER VE KAYDET
            if st.session_state.mk_gecici_liste:
                st.markdown("### 📋 İrsaliyedeki Kalemler (Henüz Kaydedilmedi)")
                for i, item in enumerate(st.session_state.mk_gecici_liste):
                    with st.expander(f"{i+1}. {item['Kod']} | {item['İsim']} - {item['Miktar']} Adet"):
                        st.write(f"**Hedef Adres:** {item['Adres']}")
                        if st.button(f"🗑️ Bu Satırı Sil", key=f"del_mk_{i}"):
                            st.session_state.mk_gecici_liste.pop(i)
                            st.rerun()

                st.divider()
                if st.button("🚀 LİSTEDEKİ TÜM ÜRÜNLERİ STOĞA KAYDET", type="primary", use_container_width=True):
                    df_stok['Kod'] = df_stok['Kod'].astype(str).str.strip().str.upper()
                    df_stok['Adres'] = df_stok['Adres'].astype(str).str.strip().str.upper()
                    
                    islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    personel = st.session_state.kullanici_adi if 'kullanici_adi' in st.session_state else "Sistem"
                    
                    for item in st.session_state.mk_gecici_liste:
                        # 1. Stok Güncelle
                        mask_stok = (df_stok['Kod'] == item['Kod']) & (df_stok['Adres'] == item['Adres'])
                        if mask_stok.any():
                            df_stok.loc[mask_stok, 'Miktar'] = pd.to_numeric(df_stok.loc[mask_stok, 'Miktar']) + item['Miktar']
                        else:
                            new_stok = pd.DataFrame([{"Kod": item['Kod'], "İsim": item['İsim'], "Adres": item['Adres'], "Miktar": item['Miktar'], "Durum": "Kullanılabilir"}])
                            df_stok = pd.concat([df_stok, new_stok], ignore_index=True)

                        # 2. Hareket Ekle
                        new_hareket = pd.DataFrame([{
                            "Tarih": islem_zamani, "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis,
                            "Kod": item['Kod'], "İsim": item['İsim'], "Adres": item['Adres'], "Miktar": item['Miktar'],
                            "Personel": personel, "Durum": "Kullanılabilir", "Lot": st.session_state.irsaliye_no,
                            "Kaynak_Adres": st.session_state.sel_tedarikci, "Hedef_Adres": item['Adres']
                        }])
                        df_hareket = pd.concat([df_hareket, new_hareket], ignore_index=True)

                    veritabani.update_data("Stok", df_stok)
                    veritabani.update_data("Hareketler", df_hareket)
                    
                    st.session_state.mk_gecici_liste = []
                    st.success("✅ Tüm ürünler başarıyla stoğa eklendi!")
                    st.session_state.teslim_page = 'menu'
                    st.rerun()
