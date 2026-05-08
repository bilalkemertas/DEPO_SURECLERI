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
        st.info("Sistem bu sipariş için otomatik bir numara atadı. Tedarikçi bilgisini ve ürünleri girerek siparişi kaydedin.")
        
        # Otomatik Sipariş Numarası Üretme (Sadece sayfaya ilk girildiğinde üretilir)
        if not st.session_state.new_po_no:
            zaman_damgasi = datetime.now().strftime("%Y%m%d-%H%M%S")
            st.session_state.new_po_no = f"SAS-{zaman_damgasi}"

        with st.container(border=True):
            st.write("📋 **Sipariş Temel Bilgileri**")
            col1, col2 = st.columns(2)
            with col1:
                sip_tedarikci = st.text_input("🏢 Tedarikçi Adı (Zorunlu):").upper().strip()
            with col2:
                # Sipariş numarası otomatik ve değiştirilemez
                sip_no = st.text_input("📄 Sipariş Numarası (Otomatik):", value=st.session_state.new_po_no, disabled=True)

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
            s_birim = st.selectbox("📏 Birim:", ["ADET", "KG", "METRE", "LİTRE", "PAKET", "KUTU", "RULO"], key="sip_birim_m")

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            if not sip_tedarikci or not s_kod or not s_isim or s_mik <= 0:
                st.error("Lütfen Tedarikçi Adını ve Ürün bilgilerini eksiksiz doldurun!")
            else:
                kalem = {
                    "Tedarikçi": sip_tedarikci,
                    "Sipariş No": st.session_state.new_po_no,
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
                st.session_state.new_po_no = None # Bir sonraki sipariş için sıfırla
                st.success("✅ Satınalma siparişi başarıyla veritabanına kaydedildi!")
                st.session_state.teslim_page = 'menu'
                st.rerun()

    # --- 2. FİLTRELEME VE SEÇİM EKRANI (MAL KABUL ADIM 1) ---
    elif st.session_state.teslim_page == 'secim':
        if st.button("⬅️ ANA MENÜYE DÖN"): 
            st.session_state.teslim_page = 'menu'
            st.rerun()

        st.subheader("🔍 Mal Kabul - Sipariş & İrsaliye Seçimi")
        st.markdown("---")

        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
            if "Sipariş No" not in df_siparis.columns:
                df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
        except:
            df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])

        # Bekleyen (Açık) Siparişleri Filtrele
        if not df_siparis.empty and "Sipariş Miktarı" in df_siparis.columns and "Gelen Miktar" in df_siparis.columns:
            df_bekleyen = df_siparis[(df_siparis['Sipariş Miktarı'] - df_siparis['Gelen Miktar']) > 0]
            # Tedarikçi listesine "Tümü" seçeneğini ekliyoruz
            tedarikci_listesi = ["Tümü"] + sorted(df_bekleyen['Tedarikçi'].dropna().unique().tolist())
        else:
            df_bekleyen = pd.DataFrame()
            tedarikci_listesi = ["Tümü"]

        with st.container(border=True):
            st.write("📋 **Evrak ve Cari Bilgileri**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Sadece mevcut açık tedarikçiler
                secilen_tedarikci = st.selectbox("🏢 Tedarikçi Seç (Opsiyonel):", tedarikci_listesi)

            with col2:
                # Tedarikçi "Tümü" ise tüm açık siparişler listelenir, değilse sadece o tedarikçinin siparişleri listelenir
                if secilen_tedarikci == "Tümü" and not df_bekleyen.empty:
                    siparis_listesi = sorted(df_bekleyen['Sipariş No'].dropna().unique().tolist())
                elif secilen_tedarikci != "Tümü" and not df_bekleyen.empty:
                    siparis_listesi = sorted(df_bekleyen[df_bekleyen['Tedarikçi'] == secilen_tedarikci]['Sipariş No'].dropna().unique().tolist())
                else:
                    siparis_listesi = []

                secilen_siparis = st.selectbox("📄 Satınalma Sipariş No:", ["Seçiniz..."] + siparis_listesi)

            irsaliye = st.text_input("🧾 İrsaliye & Fatura No (Zorunlu):").upper().strip()

            if st.button("🚀 MAL KABUL EKRANINA İLERLE", use_container_width=True, type="primary"):
                if secilen_siparis == "Seçiniz...":
                    st.error("Lütfen listeden bir Satınalma Sipariş Numarası seçin!")
                elif not irsaliye:
                    st.error("Lütfen İrsaliye & Fatura Numarasını girin!")
                else:
                    # Eğer tedarikçi "Tümü" bırakılıp sadece Sipariş No seçildiyse, sistem tedarikçiyi otomatik bulur
                    if secilen_tedarikci == "Tümü":
                        nihai_tedarikci = df_bekleyen[df_bekleyen['Sipariş No'] == secilen_siparis].iloc[0]['Tedarikçi']
                    else:
                        nihai_tedarikci = secilen_tedarikci

                    st.session_state.sel_tedarikci = nihai_tedarikci
                    st.session_state.sel_siparis = secilen_siparis
                    st.session_state.irsaliye_no = irsaliye
                    st.session_state.teslim_page = 'kabul'
                    st.rerun()

    # --- 3. MAL KABUL İŞLEM EKRANI (ÜRÜN GİRİŞİ ADIM 2) ---
    elif st.session_state.teslim_page == 'kabul':
        if st.button("⬅️ SİPARİŞ SEÇİMİNE DÖN"): 
            st.session_state.teslim_page = 'secim'
            st.rerun()

        st.subheader(f"📦 Mal Kabul: Sipariş {st.session_state.sel_siparis}")
        st.info(f"**🏢 Tedarikçi:** {st.session_state.sel_tedarikci} | **🧾 İrsaliye No:** {st.session_state.irsaliye_no}")

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

        # Sipariş Sistemde Kayıtlıysa
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
                    m1.metric("📦 Siparişteki Toplam", f"{row['Sipariş Miktarı']} {row['Birim']}")
                    m2.metric("🎯 Kalan (Gelecek Olan)", f"{kalan_ih} {row['Birim']}", delta_color="inverse")

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

        else:
            if not sub.empty:
                st.success("✅ Bu siparişe ait tüm malzemeler eksiksiz teslim alınmıştır. İşlem tamamlandı.")
            else:
                st.error("Sistemde bu sipariş numarasına ait geçerli bir kayıt bulunamadı.")
