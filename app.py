# --- TAB 2: TRANSFER (GÜNCELLENDİ) ---
    with t2:
        with st.container(border=True):
            st.subheader("Transfer")
            e_adr = st.text_input("Nereden:", key="ea2").strip().upper()
            y_adr = st.text_input("Nereye:", key="ya2").strip().upper()
            
            t_secim = st.selectbox("🔍 Ürün Ara:", arama_listesi, key="t_sec1")
            
            if t_secim == "+ YENİ / MANUEL GİRİŞ":
                t_kod = st.text_input("Kod:", key="b2", placeholder="KOD GİRİN...").strip().upper()
                t_isim = st.text_input("İsim:", key="n2", placeholder="ÜRÜN ADI GİRİN...").strip().upper()
            else:
                t_bolunmus = str(t_secim).split(" | ")
                t_kod = t_bolunmus[0].strip() if len(t_bolunmus) > 0 else ""
                t_isim = t_bolunmus[1].strip() if len(t_bolunmus) > 1 else ""
                
                st.text_input("Kod:", value=t_kod, disabled=True, key="b2_locked")
                st.text_input("İsim:", value=t_isim, disabled=True, key="n2_locked")
                
            t_qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
            t_unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
            
            if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
                if t_kod and t_isim and y_adr and e_adr:
                    log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                    
                    cikis_kaydi = [{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "İşlem": "ÇIKIŞ",
                        "Adres": e_adr,
                        "Malzeme Kodu": t_kod,
                        "Malzeme Adı": t_isim,
                        "Birim": t_unit,
                        "Miktar": t_qty,
                        "Operatör": st.session_state.user
                    }]
                    
                    giris_kaydi = [{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "İşlem": "GİRİŞ",
                        "Adres": y_adr,
                        "Malzeme Kodu": t_kod,
                        "Malzeme Adı": t_isim,
                        "Birim": t_unit,
                        "Miktar": t_qty,
                        "Operatör": st.session_state.user
                    }]
                    
                    c_log = pd.DataFrame(cikis_kaydi)
                    g_log = pd.DataFrame(giris_kaydi)
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, c_log, g_log]))
                    update_stock_record(t_kod, t_isim, e_adr, t_unit, t_qty, is_increase=False)
                    update_stock_record(t_kod, t_isim, y_adr, t_unit, t_qty, is_increase=True)
                    st.success("Transfer Kaydedildi!")
                    st.cache_data.clear()
                else:
                    st.error("Lütfen tüm alanları (Adres, Kod ve İsim) doldurun!")
