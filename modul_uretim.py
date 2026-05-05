import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu():
    st.session_state.uretim_page = 'menu'

def go_is_emri():
    st.session_state.uretim_page = 'is_emri'

def go_hazirlik():
    st.session_state.uretim_page = 'hazirlik'

def go_rapor():
    st.session_state.uretim_page = 'rapor'

def goster():
    if 'user' not in st.session_state or st.session_state.user is None:
        st.session_state.page = 'login'
        st.rerun()

    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜ"): 
            go_home()
            st.rerun()
        st.subheader("🏭 Üretim Hazırlık Merkezi")
        st.markdown("---")
        st.button("📥 İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. YÜKLEME (SADELEŞTİRME YOK) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("📤 Yeni İş Emri Yükle")
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir:
                        baslik_satiri = i
                        break
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns: df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                df_raw = df_raw.dropna(subset=['Stok Kodu'])
                df_final_save = df_raw[cols_target]
                if st.button("VERİTABANINA ŞİMDİ KAYDET", type="primary"):
                    existing = veritabani.get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    veritabani.update_data("Is_Emirleri", updated)
                    st.success("İş Emri Kaydedildi!")
                    st.cache_data.clear()
                    st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (PIVOT + ŞELALE + ADRES SIRALAMA) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("🏗️ Üretim Hazırlık (Pivot Görünüm)")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        df_hareketler_ana = veritabani.get_internal_data("Hareketler")
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                # 1. PIVOT OLUŞTURMA (Hammadde Bazlı Gruplama)
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()

                # 2. ADRES VE STOK BİLGİSİ ENTEGRASYONU
                def get_stock_info(kod):
                    clean_kod = str(kod).strip().upper()
                    temp_stok = df_stok_ana.copy()
                    temp_stok['Kod'] = temp_stok['Kod'].astype(str).str.strip().str.upper()
                    # Alfabetik sıralama ve miktar kontrolü
                    res = temp_stok[(temp_stok['Kod'] == clean_kod) & (temp_stok['Miktar'] > 0)].sort_values('Adres')
                    if not res.empty:
                        return str(res.iloc[0]['Adres']), res['Miktar'].sum()
                    return "STOK YOK", 0

                pivot_df[['Önerilen Adres', 'Depo Toplam Stok']] = pivot_df['Stok Kodu'].apply(lambda x: pd.Series(get_stock_info(x)))
                
                st.info("💡 Hazırlanan Adet hücresine toplam hazırlığı girin. Sistem stokları alfabetik adres sırasına göre düşecektir.")
                
                edited_pivot = st.data_editor(
                    pivot_df,
                    column_order=["Stok Kodu", "Stok Adı", "Önerilen Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Depo Toplam Stok", "Birim"],
                    disabled=["Stok Kodu", "Stok Adı", "Önerilen Adres", "İhtiyaç Miktarı", "Depo Toplam Stok", "Birim"],
                    hide_index=True,
                    use_container_width=True,
                    key="pivot_editor"
                )

                if st.button("✅ TÜM HAZIRLIĞI KAYDET", use_container_width=True, type="primary"):
                    all_data = veritabani.get_internal_data("Is_Emirleri")
                    df_stok_guncel = veritabani.get_internal_data("Stok")
                    df_hareketler_guncel = veritabani.get_internal_data("Hareketler")
                    
                    df_stok_guncel['Kod'] = df_stok_guncel['Kod'].astype(str).str.strip().str.upper()
                    df_stok_guncel['Adres'] = df_stok_guncel['Adres'].astype(str).str.strip().str.upper()
                    df_stok_guncel['Miktar'] = pd.to_numeric(df_stok_guncel['Miktar'], errors='coerce').fillna(0)
                    
                    yeni_loglar = []
                    degisiklik_var = False

                    for idx, row in edited_pivot.iterrows():
                        s_kod = str(row["Stok Kodu"]).strip().upper()
                        yeni_toplam_haz = round(float(row["Hazırlanan Adet"]), 2)
                        eski_toplam_haz = round(float(pivot_df.loc[idx, "Hazırlanan Adet"]), 2)
                        fark_toplam = round(yeni_toplam_haz - eski_toplam_haz, 2)

                        if fark_toplam == 0: continue
                        degisiklik_var = True

                        # A) STOKTAN DÜŞME (Waterfall - Adres Sıralı)
                        if fark_toplam > 0:
                            kalan_dusulecek = fark_toplam
                            # Depodaki adresleri alfabetik çek
                            depo_raflari = df_stok_guncel[df_stok_guncel['Kod'] == s_kod].sort_values('Adres')
                            
                            for r_idx, r_row in depo_raflari.iterrows():
                                if kalan_dusulecek <= 0: break
                                if r_row['Miktar'] <= 0: continue
                                
                                alinabilir = min(r_row['Miktar'], kalan_dusulecek)
                                df_stok_guncel.at[r_idx, 'Miktar'] -= alinabilir
                                
                                yeni_loglar.append({
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "İşlem": "ÜRETİM HAZIRLIK",
                                    "İş Emri": "TOPLU PIVOT",
                                    "Kod": s_kod,
                                    "İsim": str(row["Stok Adı"]),
                                    "Adres": r_row['Adres'],
                                    "Miktar": alinabilir,
                                    "Personel": st.session_state.user if 'user' in st.session_state else "Sistem"
                                })
                                kalan_dusulecek -= alinabilir
                            
                            if kalan_dusulecek > 0:
                                st.warning(f"⚠️ {s_kod} için {kalan_dusulecek} adet stok yetersiz kaldığından düşülemedi!")

                        # B) İŞ EMİRLERİNE DAĞITMA (Waterfall)
                        emir_satirlari = all_data[(all_data["Stok Kodu"].astype(str).str.strip().str.upper() == s_kod) & 
                                                  (all_data["İş Emri"].astype(str).isin(s_list))].index
                        
                        dagitilacak = fark_toplam
                        for e_idx in emir_satirlari:
                            if dagitilacak == 0: break
                            suanki = all_data.at[e_idx, "Hazırlanan Adet"]
                            ihtiyac = all_data.at[e_idx, "İhtiyaç Miktarı"]
                            
                            if dagitilacak > 0: # Hazırlık Ekleme
                                bosluk = ihtiyac - suanki
                                eklenecek = min(dagitilacak, bosluk if bosluk > 0 else dagitilacak)
                                all_data.at[e_idx, "Hazırlanan Adet"] += eklenecek
                                dagitilacak -= eklenecek
                            else: # İade / Azaltma
                                azaltilacak = min(abs(dagitilacak), suanki)
                                all_data.at[e_idx, "Hazırlanan Adet"] -= azaltilacak
                                dagitilacak += azaltilacak

                    if degisiklik_var:
                        veritabani.update_data("Is_Emirleri", all_data)
                        veritabani.update_data("Stok", df_stok_guncel)
                        if yeni_loglar:
                            df_l = pd.concat([df_hareketler_guncel, pd.DataFrame(yeni_loglar)], ignore_index=True)
                            veritabani.update_data("Hareketler", df_l)
                        st.success("Pivot Hazırlık Başarıyla Kaydedildi!")
                        st.cache_data.clear()
                        st.rerun()

    # --- 3. RAPOR (SADELEŞTİRME YOK) ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"):
            go_uretim_menu()
            st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = veritabani.get_internal_data("Is_Emirleri")
        if not df_lh.empty:
            r_e = st.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
            st.dataframe(res, use_container_width=True, hide_index=True)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL İNDİR", buffer.getvalue(), "Rapor.xlsx", use_container_width=True)
