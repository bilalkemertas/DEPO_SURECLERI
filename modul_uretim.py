# --- 2. OPERASYON (ZIRHLI STOK DÜŞME VE EXTRE KAYDI) ---
elif st.session_state.uretim_page == 'hazirlik':
    if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
    st.subheader("🏗️ Üretim Hazırlık Operasyonu")
    
    df_emirler = veritabani.get_internal_data("Is_Emirleri")
    df_stok_ana = veritabani.get_internal_data("Stok")
    
    if not df_emirler.empty:
        # Sayısal alanları garantiye al
        df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
        df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
        
        emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
        s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
        
        if s_list:
            dashboard_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
            
            # --- FİLTRE PANELİ ---
            with st.container(border=True):
                st.markdown("🔍 **Akıllı Arama**")
                f1, f2, f3 = st.columns(3)
                f_adr = f1.text_input("📍 Adres Filtre:", placeholder="Örn: A-01")
                f_kod = f2.text_input("📦 Kod Filtre:", placeholder="Örn: P001")
                f_isi = f3.text_input("📝 İsim Filtre:", placeholder="Örn: Sünger")
            
            def get_best_adr(kod):
                # Kodları normalize ederek ara (Boşlukları sil, stringe çevir)
                clean_kod = str(kod).strip()
                if 'Kod' in df_stok_ana.columns:
                    # Stok veritabanındaki kodları da normalize et
                    temp_stok = df_stok_ana.copy()
                    temp_stok['Kod'] = temp_stok['Kod'].astype(str).str.strip()
                    res = temp_stok[temp_stok['Kod'] == clean_kod]
                    return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                return "STOK YOK"
            
            dashboard_df["Alınacak Adres"] = dashboard_df["Stok Kodu"].apply(get_best_adr)
            
            # Filtre Uygulama
            filtered = dashboard_df.copy()
            if f_adr: filtered = filtered[filtered["Alınacak Adres"].str.contains(f_adr, case=False, na=False)]
            if f_kod: filtered = filtered[filtered["Stok Kodu"].astype(str).str.contains(f_kod, case=False, na=False)]
            if f_isi: filtered = filtered[filtered["Stok Adı"].astype(str).str.contains(f_isi, case=False, na=False)]
            
            filtered['Doluluk %'] = (filtered['Hazırlanan Adet'] / filtered['İhtiyaç Miktarı'] * 100).round(1).fillna(0)

            st.markdown(f"#### 📝 Hazırlık Detay Listesi ({len(filtered)} Kalem)")
            edited_df = st.data_editor(
                filtered,
                column_order=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim", "Doluluk %"],
                disabled=["Stok Kodu", "Stok Adı", "Alınacak Adres", "İhtiyaç Miktarı", "Birim", "Doluluk %"],
                hide_index=True,
                use_container_width=True,
                key="hazirlik_editor"
            )
            
            if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                all_data = veritabani.get_internal_data("Is_Emirleri")
                df_stok_guncel = veritabani.get_internal_data("Stok")
                df_hareketler = veritabani.get_internal_data("Hareketler")
                
                # Stok tablosunu normalize et (Eşleşme garantisi için)
                df_stok_guncel['Kod'] = df_stok_guncel['Kod'].astype(str).str.strip()
                df_stok_guncel['Adres'] = df_stok_guncel['Adres'].astype(str).str.strip()
                df_stok_guncel['Miktar'] = pd.to_numeric(df_stok_guncel['Miktar'], errors='coerce').fillna(0)
                
                yeni_loglar = []
                stok_hatalari = []

                for i, row in edited_df.iterrows():
                    # İş emri satırını bul
                    mask = (all_data["İş Emri"].astype(str) == str(row["İş Emri"])) & \
                           (all_data["Stok Kodu"].astype(str).str.strip() == str(row["Stok Kodu"]).strip()) & \
                           (all_data["Mamül Adı"].astype(str) == str(row["Mamül Adı"]))
                    
                    if mask.any():
                        eski_haz = pd.to_numeric(all_data.loc[mask, "Hazırlanan Adet"], errors='coerce').fillna(0).values[0]
                        yeni_haz = pd.to_numeric(row["Hazırlanan Adet"], errors='coerce').fillna(0)
                        fark = yeni_haz - eski_haz
                        
                        if fark != 0:
                            # STOK EŞLEŞTİRME (ZIRHLI)
                            s_kod = str(row["Stok Kodu"]).strip()
                            s_adr = str(row["Alınacak Adres"]).strip()
                            
                            stok_mask = (df_stok_guncel["Kod"] == s_kod) & (df_stok_guncel["Adres"] == s_adr)
                            
                            if stok_mask.any():
                                mevcut = df_stok_guncel.loc[stok_mask, "Miktar"].values[0]
                                df_stok_guncel.loc[stok_mask, "Miktar"] = max(0, mevcut - fark)
                                
                                # EXTREYE YAZ
                                yeni_loglar.append({
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "İşlem": "ÜRETİM HAZIRLIK",
                                    "İş Emri": row["İş Emri"],
                                    "Kod": s_kod,
                                    "İsim": row["Stok Adı"],
                                    "Adres": s_adr,
                                    "Miktar": fark,
                                    "Personel": st.session_state.user if 'user' in st.session_state else "Sistem"
                                })
                            else:
                                stok_hatalari.append(f"{s_kod} ({s_adr})")
                        
                        all_data.loc[mask, "Hazırlanan Adet"] = yeni_haz

                # VERİTABANINI GÜNCELLE
                veritabani.update_data("Is_Emirleri", all_data)
                veritabani.update_data("Stok", df_stok_guncel)
                
                if yeni_loglar:
                    df_extre_son = pd.concat([df_hareketler, pd.DataFrame(yeni_loglar)], ignore_index=True)
                    veritabani.update_data("Hareketler", df_extre_son)

                # Kullanıcıya Geri Bildirim
                if stok_hatalari:
                    st.warning(f"Hazırlık kaydedildi ama şu kalemler stokta (Adres/Kod) bulunamadığı için stoktan düşülemedi: {', '.join(stok_hatalari)}")
                else:
                    st.success("Tüm hazırlıklar başarıyla kaydedildi ve stoklardan düşüldü!")
                
                st.cache_data.clear(); st.rerun()
