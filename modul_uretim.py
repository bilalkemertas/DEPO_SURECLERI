import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): st.session_state.uretim_page = 'menu'
def go_is_emri(): st.session_state.uretim_page = 'is_emri'
def go_hazirlik(): st.session_state.uretim_page = 'hazirlik'
def go_rapor(): st.session_state.uretim_page = 'rapor'

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

    # --- 1. YÜKLEME ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
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
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. OPERASYON (GİRİŞ PANELİ + UYARI SİSTEMİ + SIRALAMA) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_emirler = veritabani.get_internal_data("Is_Emirleri")
        df_stok_ana = veritabani.get_internal_data("Stok")
        df_hareketler_ana = veritabani.get_internal_data("Hareketler")
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                # Pivot hazırlığı (Hammadde bazlı özet)
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()
                
                # Bitenleri sona atma mantığı (Hazırlanan >= İhtiyaç ise 1, değilse 0)
                pivot_df['Tamamlandi'] = (pivot_df['Hazırlanan Adet'] >= pivot_df['İhtiyaç Miktarı']).astype(int)
                pivot_df = pivot_df.sort_values(by=['Tamamlandi', 'Stok Adı'], ascending=[True, True])

                # --- ÜST GİRİŞ PANELİ (3 ALAN) ---
                with st.container(border=True):
                    st.markdown("🔍 **Hızlı Hazırlık Girişi**")
                    p1, p2, p3 = st.columns(3)
                    
                    # 1. Ürün Seçimi
                    bekleyen_kodlar = pivot_df[pivot_df['Tamamlandi'] == 0]['Stok Kodu'].unique().tolist()
                    input_kod = p1.selectbox("📦 Ürün Seç:", ["Seçiniz..."] + bekleyen_kodlar)
                    
                    # 2. Adres Önerisi (Alfabetik ilk dolu adres)
                    input_adr = "-"
                    current_stock_at_adr = 0
                    current_req = 0
                    current_prep = 0
                    
                    if input_kod != "Seçiniz...":
                        temp_stok = df_stok_ana.copy()
                        temp_stok['Kod'] = temp_stok['Kod'].astype(str).str.strip().upper()
                        # Alfabetik sıralı ve stok olan adresler
                        valid_stocks = temp_stok[(temp_stok['Kod'] == input_kod.upper()) & (temp_stok['Miktar'] > 0)].sort_values('Adres')
                        
                        if not valid_stocks.empty:
                            # Adresleri tıklandığında listelemek için expander kullanıyoruz
                            with p2:
                                with st.expander(f"📍 {valid_stocks.iloc[0]['Adres']} (Önerilen)", expanded=False):
                                    st.write("**Diğer Adresler:**")
                                    st.dataframe(valid_stocks[['Adres', 'Miktar']], hide_index=True)
                            
                            input_adr = valid_stocks.iloc[0]['Adres']
                            current_stock_at_adr = valid_stocks.iloc[0]['Miktar']
                        else:
                            p2.error("❌ STOK YOK!")
                        
                        # Mevcut Durum Bilgisi
                        row_info = pivot_df[pivot_df['Stok Kodu'] == input_kod].iloc[0]
                        current_req = row_info['İhtiyaç Miktarı']
                        current_prep = row_info['Hazırlanan Adet']
                    
                    input_mik = p3.number_input("🔢 Alınan Miktar:", min_value=0.0, step=1.0)
                    
                    if st.button("⚡ HAREKETİ İŞLE", use_container_width=True, type="primary"):
                        if input_kod == "Seçiniz..." or input_adr == "STOK YOK":
                            st.error("Hatalı ürün veya adres seçimi!")
                        else:
                            # KONTROL 1: Adres Stoğu Yetiyor mu?
                            if input_mik > current_stock_at_adr:
                                st.warning(f"⚠️ Adres stoğu {current_stock_at_adr}, diğer adresten devam edin!")
                            # KONTROL 2: İhtiyaç Miktarı Aşılıyor mu?
                            elif (current_prep + input_mik) > current_req:
                                st.error(f"🚫 İhtiyaç miktarından ({current_req}) fazla ürün alamazsınız!")
                            else:
                                # --- KAYIT İŞLEMLERİ ---
                                df_stok_guncel = veritabani.get_internal_data("Stok")
                                df_hareketler_guncel = veritabani.get_internal_data("Hareketler")
                                all_is_emirleri = veritabani.get_internal_data("Is_Emirleri")
                                
                                # 1. Stoktan Düş
                                s_mask = (df_stok_guncel['Kod'].astype(str).str.strip().str.upper() == input_kod.upper()) & \
                                         (df_stok_guncel['Adres'].astype(str).str.strip().str.upper() == input_adr.upper())
                                df_stok_guncel.loc[s_mask, 'Miktar'] -= input_mik
                                
                                # 2. Hareketler Logla
                                h_satir = {
                                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "İşlem": "ÜRETİM HAZIRLIK",
                                    "İş Emri": ", ".join(s_list),
                                    "Kod": input_kod,
                                    "İsim": row_info['Stok Adı'],
                                    "Adres": input_adr,
                                    "Miktar": input_mik,
                                    "Personel": st.session_state.user
                                }
                                df_h = pd.concat([df_hareketler_guncel, pd.DataFrame([h_satir])], ignore_index=True)
                                
                                # 3. İş Emirlerine Dağıt (Waterfall Dağıtım)
                                kalan_dagitilacak = input_mik
                                emir_indices = all_is_emirleri[(all_is_emirleri['İş Emri'].astype(str).isin(s_list)) & 
                                                              (all_is_emirleri['Stok Kodu'] == input_kod)].index
                                for idx in emir_indices:
                                    if kalan_dagitilacak <= 0: break
                                    ihtiyac = all_is_emirleri.at[idx, 'İhtiyaç Miktarı']
                                    hazir = all_is_emirleri.at[idx, 'Hazırlanan Adet']
                                    bosluk = ihtiyac - hazir
                                    alinacak = min(kalan_dagitilacak, bosluk if bosluk > 0 else 0)
                                    all_is_emirleri.at[idx, 'Hazırlanan Adet'] += alinacak
                                    kalan_dagitilacak -= alinacak

                                # Kaydet
                                veritabani.update_data("Stok", df_stok_guncel)
                                veritabani.update_data("Hareketler", df_h)
                                veritabani.update_data("Is_Emirleri", all_is_emirleri)
                                
                                st.success("Hazırlık kaydedildi!")
                                st.cache_data.clear(); st.rerun()

                # --- DETAY TABLO (PİVOT GÖRÜNÜM) ---
                st.markdown("---")
                st.dataframe(
                    pivot_df,
                    column_order=["Stok Kodu", "Stok Adı", "Önerilen Adres", "İhtiyaç Miktarı", "Hazırlanan Adet", "Depo Toplam Stok", "Birim"],
                    use_container_width=True,
                    hide_index=True
                )

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
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
