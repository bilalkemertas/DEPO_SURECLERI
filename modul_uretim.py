import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- GÜVENLİ BAŞLATICI (KeyError Önleyici) ---
def init_state():
    """Tüm gerekli session_state anahtarlarını kontrol eder ve yoksa oluşturur."""
    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'
    if 'page' not in st.session_state:
        st.session_state.page = 'home'

# --- NAVİGASYON ---
def go_home(): 
    init_state()
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    init_state()
    st.session_state.uretim_page = 'menu'
    if 'local_emirler' in st.session_state: 
        del st.session_state.local_emirler

def goster():
    # Hata almamak için fonksiyonun başında anahtarları kontrol et
    init_state()

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"): 
            go_home()
            st.rerun()
            
        st.subheader("🏭 Üretim Hazırlık Modülü (v18.3)")
        st.markdown("---")
        st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        st.button("🏗️ ÜRETİM HAZIRLIK YAP", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik'))
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=lambda: setattr(st.session_state, 'uretim_page', 'rapor'))

    # --- 1. YÜKLEME ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📤 İş Emri Excel'i Yükle")
        uploaded_file = st.file_uploader("Dosya Seçin:", type=['xlsx'])
        if uploaded_file:
            try:
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
                
                baslik_idx = 0
                for i in range(min(30, len(df_raw))):
                    row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in row_vals: baslik_idx = i; break
                
                df = df_raw.iloc[baslik_idx:].copy()
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = [str(c).strip() for c in df.columns]

                if 'Mamül Adı' in df.columns: df['Mamül Adı'] = df['Mamül Adı'].ffill()
                elif 'Ürün Adı' in df.columns: df['Mamül Adı'] = df['Ürün Adı'].ffill()
                
                df = df.dropna(subset=['Stok Kodu', 'Stok Adı'])
                df['İş Emri'] = is_emri_adi
                df['Hazırlanan Adet'] = 0
                
                for col in df.columns:
                    if 'total' in col.lower() or 'ihtiyaç' in col.lower():
                        df['İhtiyaç Miktarı'] = pd.to_numeric(df[col], errors='coerce').fillna(0); break
                
                df = df[df['Stok Kodu'] != df.get('Ürün Kodu', '---')]
                
                cols = ["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                df_save = df[[c for c in cols if c in df.columns]]

                st.dataframe(df_save, use_container_width=True, hide_index=True)

                if st.button("UYGULAMAYI GÜNCELLE", type="primary"):
                    veritabani.update_data("Is_Emirleri", df_save)
                    st.success("✅ Veritabanı Sıfırlandı ve Güncellendi!"); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. HAZIRLIK (ÜÇLÜ KİLİTLEME) ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        df_db = veritabani.get_internal_data("Is_Emirleri")
        if not df_db.empty:
            sel_is = st.selectbox("📋 İş Emri Seçin:", ["Seçiniz..."] + sorted(df_db['İş Emri'].unique().tolist()))
            if sel_is != "Seçiniz...":
                sub = df_db[df_db['İş Emri'] == sel_is].copy()
                
                options = ["Seçiniz..."] + [f"{r['Mamül Adı']} | {r['Stok Kodu']} | {r['Stok Adı']}" for _, r in sub.iterrows() if (r['İhtiyaç Miktarı'] - r['Hazırlanan Adet']) > 0.001]
                sel_item = st.selectbox("🎯 Hazırlanacak Tam Satırı Seçin:", options)
                
                if sel_item != "Seçiniz...":
                    m_adi, s_kod, s_adi = sel_item.split(" | ")
                    row = sub[(sub['Mamül Adı'] == m_adi) & (sub['Stok Kodu'] == s_kod) & (sub['Stok Adı'] == s_adi)].iloc[0]
                    kalan = round(row['İhtiyaç Miktarı'] - row['Hazırlanan Adet'], 3)
                    
                    with st.container(border=True):
                        st.write(f"📂 **Ürün:** {m_adi}")
                        st.write(f"🛠️ **Malzeme:** {s_adi}")
                        c1, c2 = st.columns(2)
                        c1.metric("Kalan İhtiyaç", f"{kalan} {row.get('Birim', '')}")
                        input_adet = c2.number_input("Verilen Miktar:", min_value=0.0, max_value=float(kalan), step=1.0)
                        
                        if st.button("⚡ KAYDI TAMAMLA", use_container_width=True, type="primary"):
                            mask = (df_db['İş Emri'] == sel_is) & (df_db['Mamül Adı'] == m_adi) & (df_db['Stok Kodu'] == s_kod) & (df_db['Stok Adı'] == s_adi)
                            df_db.loc[mask, 'Hazırlanan Adet'] += input_adet
                            veritabani.update_data("Is_Emirleri", df_db)
                            st.success("Kaydedildi!"); st.rerun()
                
                st.divider()
                st.dataframe(sub, use_container_width=True, hide_index=True)

    # --- 3. RAPOR ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Durum Raporu")
        
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        if not df_rapor.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_rapor.to_excel(writer, index=False, sheet_name='Hazirlik')
            st.download_button("📥 TÜM LİSTEYİ EXCEL OLARAK İNDİR", data=buffer.getvalue(), file_name="Uretim_Hazirlik_Raporu.xlsx", use_container_width=True, type="primary")
            
            summary = df_rapor.groupby("İş Emri").agg({"İhtiyaç Miktarı":"sum", "Hazırlanan Adet":"sum"}).reset_index()
            summary["Tamamlanma %"] = (summary["Hazırlanan Adet"] / summary["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
            st.table(summary)
            
            st.write("🔍 **Detaylı Satır Verileri**")
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)
