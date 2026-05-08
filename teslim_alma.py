import streamlit as st
import pandas as pd
import veritabani
from datetime import datetime

def init_state():
    if 'teslim_page' not in st.session_state: st.session_state.teslim_page = 'secim'
    if 'sel_siparis' not in st.session_state: st.session_state.sel_siparis = None
    if 'sel_tedarikci' not in st.session_state: st.session_state.sel_tedarikci = None
    if 'irsaliye_no' not in st.session_state: st.session_state.irsaliye_no = ""

def run(conn):
    init_state()

    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 18px !important; }
        [data-testid="stMetricLabel"] { font-size: 12px !important; }
        .stCaption { font-size: 11px !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- ADIM 1: FİLTRELEME VE SEÇİM EKRANI ---
    if st.session_state.teslim_page == 'secim':
        st.subheader("📥 Mal Kabul - Sipariş & İrsaliye Seçimi")
        st.markdown("---")

        # Veritabanından satınalma siparişlerini çek (Tablo yoksa boş oluştur)
        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
        except:
            df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])

        if not df_siparis.empty and "Sipariş Miktarı" in df_siparis.columns and "Gelen Miktar" in df_siparis.columns:
            # Sadece tamamlanmamış (açık) siparişleri filtrele
            df_bekleyen = df_siparis[(df_siparis['Sipariş Miktarı'] - df_siparis['Gelen Miktar']) > 0]
            tedarikci_listesi = sorted(df_bekleyen['Tedarikçi'].dropna().unique().tolist())
        else:
            df_bekleyen = pd.DataFrame()
            tedarikci_listesi = []

        with st.container(border=True):
            st.write("📋 **Evrak ve Cari Bilgileri**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Tedarikçi Seçimi (Açılır Liste + Manuel Giriş)
                tedarikci_secim = st.selectbox("🏢 Tedarikçi:", ["Manuel Giriş..."] + tedarikci_listesi)
                if tedarikci_secim == "Manuel Giriş...":
                    tedarikci = st.text_input("Tedarikçi Adını Manuel Girin:")
                else:
                    tedarikci = tedarikci_secim

            with col2:
                # Sipariş Seçimi (Seçilen tedarikçiye göre filtrelenir)
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

            if st.button("🚀 MAL KABUL EKRANINA İLERLE", use_container_width=True, type="primary"):
                if not tedarikci or not siparis_no or not irsaliye:
                    st.error("Lütfen Tedarikçi, Sipariş No ve İrsaliye bilgilerinin tamamını doldurun!")
                else:
                    st.session_state.sel_tedarikci = tedarikci
                    st.session_state.sel_siparis = siparis_no
                    st.session_state.irsaliye_no = irsaliye
                    st.session_state.teslim_page = 'kabul'
                    st.rerun()

    # --- ADIM 2: MAL KABUL İŞLEM EKRANI ---
    elif st.session_state.teslim_page == 'kabul':
        if st.button("⬅️ GİRİŞ BİLGİLERİNE DÖN"): 
            st.session_state.teslim_page = 'secim'
            st.rerun()

        st.subheader(f"📦 Mal Kabul: {st.session_state.sel_siparis}")
        st.info(f"**🏢 Tedarikçi:** {st.session_state.sel_tedarikci} | **🧾 İrsaliye No:** {st.session_state.irsaliye_no}")

        try:
            df_siparis = veritabani.get_internal_data("Satin_Alma")
        except:
            df_siparis = pd.DataFrame(columns=["Tedarikçi", "Sipariş No", "Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"])
            
        df_stok = veritabani.get_internal_data("Stok")
        df_hareket = veritabani.get_internal_data("Hareketler")

        # Mevcut siparişe ait satırları çek
        sub = df_siparis[df_siparis['Sipariş No'] == st.session_state.sel_siparis].copy()
        
        if not sub.empty:
            bekleyenler = sub[(sub['Sipariş Miktarı'] - sub['Gelen Miktar']) > 0].copy()
        else:
            bekleyenler = pd.DataFrame()

        # EĞER SİPARİŞ SİSTEMDE VARSA (Açılır Listeden Geldiyse)
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

                    input_adr = r1c1.text_input("📍 Hedef Adres (Raf Numarası):").upper().strip()
                    input_mik = r1c2.number_input("🔢 Miktar:", min_value=0.0, max_value=float(kalan_ih), step=1.0)

                    m1, m2 = st.columns(2)
                    m1.metric("📦 Sipariş Edilen", f"{row['Sipariş Miktarı']}")
                    m2.metric("🎯 Kalan Bekleyen", f"{kalan_ih}", delta_color="inverse")

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

                            # Veritabanına Yaz
                            veritabani.update_data("Stok", df_stok)
                            veritabani.update_data("Hareketler", df_hareket)
                            veritabani.update_data("Satin_Alma", df_siparis)

                            st.success("✅ Mal Kabul Başarıyla Kaydedildi!")
                            st.rerun()
            
            # EĞER MANUEL SİPARİŞ GİRİLDİYSE VEYA SİPARİŞ TAMAMLANDIYSA (Serbest Kabul)
            else:
                if not sub.empty:
                    st.success("✅ Bu siparişe ait tüm malzemeler eksiksiz teslim alınmıştır.")
                else:
                    st.warning("⚠️ Sistemde bu sipariş numarasına ait bir kayıt bulunamadı. Aşağıdan bağımsız (serbest) mal kabulü yapabilirsiniz.")
                    
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
                        s_mik = st.number_input("🔢 Miktar:", min_value=0.0, step=1.0)
                        s_adr = st.text_input("📍 Hedef Adres (Raf Numarası):").upper().strip()

                    if st.button("⚡ SERBEST KABULÜ TAMAMLA", use_container_width=True, type="primary"):
                        if not s_kod or not s_isim or s_mik <= 0 or not s_adr:
                            st.error("Lütfen tüm alanları eksiksiz doldurun!")
                        else:
                            # 1. Stok Güncelle
                            df_stok['Kod'] = df_stok['Kod'].astype(str).str.strip().str.upper()
                            df_stok['Adres'] = df_stok['Adres'].astype(str).str.strip().str.upper()
                            mask_stok = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == s_adr)
                            
                            if mask_stok.any():
                                df_stok.loc[mask_stok, 'Miktar'] = pd.to_numeric(df_stok.loc[mask_stok, 'Miktar']) + s_mik
                            else:
                                new_stok = pd.DataFrame([{"Kod": s_kod, "İsim": s_isim, "Adres": s_adr, "Miktar": s_mik, "Durum": "Kullanılabilir"}])
                                df_stok = pd.concat([df_stok, new_stok], ignore_index=True)

                            # 2. Hareket Ekle
                            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            personel = st.session_state.kullanici_adi if 'kullanici_adi' in st.session_state else "Sistem"
                            new_hareket = pd.DataFrame([{
                                "Tarih": islem_zamani, "İşlem": "GİRİŞ", "İş Emri": st.session_state.sel_siparis,
                                "Kod": s_kod, "İsim": s_isim, "Adres": s_adr, "Miktar": s_mik,
                                "Personel": personel, "Durum": "Kullanılabilir", "Lot": st.session_state.irsaliye_no,
                                "Kaynak_Adres": st.session_state.sel_tedarikci, "Hedef_Adres": s_adr
                            }])
                            df_hareket = pd.concat([df_hareket, new_hareket], ignore_index=True)

                            # Veritabanına Yaz
                            veritabani.update_data("Stok", df_stok)
                            veritabani.update_data("Hareketler", df_hareket)

                            st.success("✅ Serbest Mal Kabul Başarıyla Kaydedildi!")
                            st.rerun()

            # Liste Görünümü
            st.divider()
            st.write("📝 **Sipariş Detay Listesi**")
            if not sub.empty:
                view_cols = ["Stok Kodu", "Stok Adı", "Sipariş Miktarı", "Gelen Miktar", "Birim"]
                st.dataframe(sub[[c for c in view_cols if c in sub.columns]], use_container_width=True, hide_index=True)
            else:
                st.info("Bu manuel siparişe ait önceden yüklenmiş bir liste bulunmuyor.")
