import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- NAVİGASYON ---
def go_uretim_menu(): 
    st.session_state.uretim_page = 'menu'
    if 'local_emirler' in st.session_state: del st.session_state.local_emirler

def goster():
    if 'uretim_page' not in st.session_state: st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        st.subheader("🏭 Üretim Hazırlık Modülü (v17.0)")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik'))
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, on_click=lambda: setattr(st.session_state, 'uretim_page', 'rapor'))

    # --- 1. YÜKLEME (DOĞRU SÜTUNLARI ÇEKME) ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        uploaded_file = st.file_uploader("İş Emri Excel'ini Seçin:", type=['xlsx'])
        if uploaded_file:
            try:
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
                
                # Başlık satırını bul
                baslik_idx = 0
                for i in range(len(df_raw)):
                    row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in row_vals: baslik_idx = i; break
                
                df = df_raw.iloc[baslik_idx:].copy()
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = [str(c).strip() for c in df.columns]

                # KRİTİK: Mamül Adı ve Stok Kodu Boş Olanları Temizle
                df = df.dropna(subset=['Stok Kodu', 'Stok Adı'])
                # Mamül Adı bilgisini (Ürün Adı) ffill ile doldur ki her satırın hangi ürüne ait olduğu kesinleşsin
                if 'Mamül Adı' in df.columns: df['Mamül Adı'] = df['Mamül Adı'].ffill()
                if 'Ürün Adı' in df.columns: df['Mamül Adı'] = df['Ürün Adı'].ffill()

                df['İş Emri'] = is_emri_adi
                df['Hazırlanan Adet'] = 0
                
                # İhtiyaç Miktarını bul
                for col in df.columns:
                    if 'total' in col.lower() or 'ihtiyaç' in col.lower():
                        df['İhtiyaç Miktarı'] = pd.to_numeric(df[col], errors='coerce').fillna(0); break
                
                # Gereksiz (Mamül başlık) satırlarını ayıkla
                df = df[df['Stok Kodu'] != df.get('Ürün Kodu', '---')]
                
                cols = ["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                df_save = df[[c for c in cols if c in df.columns]]

                st.write(f"✅ {len(df_save)} kalem malzeme hazırlandı.")
                st.dataframe(df_save, use_container_width=True)

                if st.button("UYGULAMAYA YÜKLE (ESKİLERİ SİLER)", type="primary"):
                    veritabani.update_data("Is_Emirleri", df_save)
                    st.success("Veritabanı Güncellendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. HAZIRLIK (ÜÇLÜ KİLİTLEME) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        df_db = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_db.empty:
            sel_is = st.selectbox("İş Emri Seç:", ["Seçiniz..."] + sorted(df_db['İş Emri'].unique().tolist()))
            if sel_is != "Seçiniz...":
                sub = df_db[df_db['İş Emri'] == sel_is].copy()
                
                # Personel seçim kutusu: Artık Mamül + Stok Kodu + Stok Adı beraber görünüyor!
                options = ["Seçiniz..."] + [f"{r['Mamül Adı']} | {r['Stok Kodu']} | {r['Stok Adı']}" for _, r in sub.iterrows() if (r['İhtiyaç Miktarı'] - r['Hazırlanan Adet']) > 0]
                sel_item = st.selectbox("🎯 Hazırlanacak Satırı Seç (Birebir Eşleşme):", options)
                
                if sel_item != "Seçiniz...":
                    # Seçilen satırı üçlü anahtarla parçala
                    m_adi, s_kod, s_adi = sel_item.split(" | ")
                    
                    # Veritabanında tam o satırı bul
                    row = sub[(sub['Mamül Adı'] == m_adi) & (sub['Stok Kodu'] == s_kod) & (sub['Stok Adı'] == s_adi)].iloc[0]
                    kalan = row['İhtiyaç Miktarı'] - row['Hazırlanan Adet']
                    
                    st.info(f"**Mamül:** {m_adi}\n\n**Malzeme:** {s_adi}")
                    c1, c2 = st.columns(2)
                    c1.metric("📦 Kalan İhtiyaç", f"{kalan} {row.get('Birim', '')}")
                    input_adet = c2.number_input("🔢 Hazırlanan Miktar:", min_value=0.0, max_value=float(kalan), step=1.0)
                    
                    if st.button("⚡ KAYDET", use_container_width=True, type="primary"):
                        # ÜÇLÜ KİLİT MASKESİ
                        mask = (df_db['İş Emri'] == sel_is) & (df_db['Mamül Adı'] == m_adi) & (df_db['Stok Kodu'] == s_kod) & (df_db['Stok Adı'] == s_adi)
                        df_db.loc[mask, 'Hazırlanan Adet'] += input_adet
                        
                        veritabani.update_data("Is_Emirleri", df_db)
                        st.success("Kaydedildi!"); st.rerun()
                
                st.write("---")
                st.write("📋 **İş Emri Listesi**")
                st.dataframe(sub, use_container_width=True, hide_index=True)

    # --- 3. RAPOR (NO DUPLICATE - NO ERRORS) ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        
        if not df_rapor.empty:
            st.subheader("📊 Hazırlık Durum Raporu")
            
            # Excel İndirme Butonu (En Üstte)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_rapor.to_excel(writer, index=False, sheet_name='Hazirlik')
            st.download_button("📥 TÜM RAPORU EXCEL OLARAK İNDİR", data=buffer.getvalue(), file_name="Uretim_Raporu.xlsx", use_container_width=True)
            
            # Özet Görünüm
            summary = df_rapor.groupby("İş Emri").agg({"İhtiyaç Miktarı":"sum", "Hazırlanan Adet":"sum"}).reset_index()
            summary["%"] = (summary["Hazırlanan Adet"] / summary["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
            st.table(summary)
            
            # Detaylı Liste
            st.write("🔍 **Satır Bazlı Detay (Birebir Eşleşme)**")
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)
