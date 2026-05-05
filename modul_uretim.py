import streamlit as st
import pandas as pd
import veritabani
import io
from datetime import datetime

# --- NAVİGASYON: Yolların Kaybolmaması İçin ---
def go_home(): 
    # Uygulamanın ana kumanda merkezine (app.py ana sayfası) dönüş bileti
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    # Modül içi ana menüye dönüş
    st.session_state.uretim_page = 'menu'

def goster():
    # Sayfa durumu tanımlı değilse menüden başla
    if 'uretim_page' not in st.session_state: 
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ (NAVİGASYON GARANTİLİ) ---
    if st.session_state.uretim_page == 'menu':
        # İşte geri getirdiğimiz ve asla silinmeyecek olan o buton
        if st.button("⬅️ SİSTEM ANA MENÜSÜNE DÖN"): 
            go_home()
            st.rerun()
            
        st.subheader("🏭 Üretim Hazırlık Modülü (v18.1)")
        st.info("Bu modül 'Üçlü Eşleşme' mantığıyla çalışır: Mamül, Kod ve İsim birebir tutmalıdır.")
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button("📥 YENİ İŞ EMRİ YÜKLE", use_container_width=True, type="primary", 
                      on_click=lambda: setattr(st.session_state, 'uretim_page', 'is_emri'))
        with col2:
            st.button("🏗️ HAZIRLIK YAP", use_container_width=True, type="primary", 
                      on_click=lambda: setattr(st.session_state, 'uretim_page', 'hazirlik'))
        with col3:
            st.button("📊 DURUM RAPORU", use_container_width=True, type="primary", 
                      on_click=lambda: setattr(st.session_state, 'uretim_page', 'rapor'))

    # --- 1. YÜKLEME: VERİYİ "ÜÇLÜ KİLİT"E HAZIRLAMA ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ MODÜL MENÜSÜNE DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Yeni İş Emri Tanımla")
        
        uploaded_file = st.file_uploader("İş Emri Excel'ini Seçin:", type=['xlsx'])
        if uploaded_file:
            try:
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
                
                # Başlık satırı tespiti (Stok Kodu'nu bulana kadar ara)
                baslik_idx = 0
                for i in range(min(40, len(df_raw))):
                    row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in row_vals: baslik_idx = i; break
                
                df = df_raw.iloc[baslik_idx:].copy()
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = [str(c).strip() for c in df.columns]

                # KRİTİK: Her satıra hangi yatağa (Mamül) ait olduğunu işle (ffill)
                # Bu sayede 'Keçe' satırı hangi yatağın keçesi olduğunu bilir.
                if 'Mamül Adı' in df.columns: df['Mamül Adı'] = df['Mamül Adı'].ffill()
                elif 'Ürün Adı' in df.columns: df['Mamül Adı'] = df['Ürün Adı'].ffill()
                
                df = df.dropna(subset=['Stok Kodu', 'Stok Adı'])
                df['İş Emri'] = is_emri_adi
                df['Hazırlanan Adet'] = 0
                
                # İhtiyaç miktarını sütun isminden bağımsız (ihtiyaç/total geçen sütun) yakala
                for col in df.columns:
                    if any(key in str(col).lower() for key in ['total', 'ihtiyaç', 'miktar']):
                        df['İhtiyaç Miktarı'] = pd.to_numeric(df[col], errors='coerce').fillna(0); break
                
                # Sadece gerçek malzemeleri (hammadde/yarı mamül) ayıkla
                df = df[df['Stok Kodu'] != df.get('Ürün Kodu', '---')]
                
                final_cols = ["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                df_save = df[[c for c in final_cols if c in df.columns]]

                st.write(f"✅ {len(df_save)} kalem malzeme bulundu.")
                st.dataframe(df_save, use_container_width=True, hide_index=True)

                if st.button("VERİTABANINA YÜKLE", type="primary", use_container_width=True):
                    veritabani.update_data("Is_Emirleri", df_save)
                    st.success("İş Emri başarıyla kaydedildi!"); st.rerun()
            except Exception as e: st.error(f"Excel Okuma Hatası: {e}")

    # --- 2. HAZIRLIK: ÜÇLÜ KİLİTLEME OPERASYONU ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ MODÜL MENÜSÜNE DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Hazırlık Kaydı")
        
        df_db = veritabani.get_internal_data("Is_Emirleri")
        if not df_db.empty:
            sel_is = st.selectbox("📋 İş Emrini Seç:", ["Seçiniz..."] + sorted(df_db['İş Emri'].unique().tolist()))
            
            if sel_is != "Seçiniz...":
                sub = df_db[df_db['İş Emri'] == sel_is].copy()
                
                # Personelin Hata Yapma Şansını Sıfırlayan Seçenek: Mamül + Kod + Ad
                options = ["Seçiniz..."] + [f"{r['Mamül Adı']} | {r['Stok Kodu']} | {r['Stok Adı']}" 
                                            for _, r in sub.iterrows() if (r['İhtiyaç Miktarı'] - r['Hazırlanan Adet']) > 0.001]
                
                sel_item = st.selectbox("🎯 Hazırlanacak Malzemeyi Seç (Tam Eşleşme):", options)
                
                if sel_item != "Seçiniz...":
                    # Seçilen metni parçalarına ayırıp veritabanındaki o tek satıra odaklanıyoruz
                    m_adi, s_kod, s_adi = sel_item.split(" | ")
                    row = sub[(sub['Mamül Adı'] == m_adi) & (sub['Stok Kodu'] == s_kod) & (sub['Stok Adı'] == s_adi)].iloc[0]
                    kalan = round(row['İhtiyaç Miktarı'] - row['Hazırlanan Adet'], 3)
                    
                    with st.container(border=True):
                        st.write(f"📦 **Mamül:** {m_adi}")
                        st.write(f"🛠️ **Malzeme:** {s_adi} ({s_kod})")
                        c1, c2 = st.columns(2)
                        c1.metric("Kalan İhtiyaç", f"{kalan} {row.get('Birim', '')}")
                        input_adet = c2.number_input("Hazırlanan Miktar:", min_value=0.0, max_value=float(kalan), step=1.0)
                        
                        if st.button("💾 MİKTARI KAYDET", use_container_width=True, type="primary"):
                            # ÜÇLÜ KİLİT MASKESİ: Veritabanında tam o satırı bulup günceller
                            mask = (df_db['İş Emri'] == sel_is) & (df_db['Mamül Adı'] == m_adi) & \
                                   (df_db['Stok Kodu'] == s_kod) & (df_db['Stok Adı'] == s_adi)
                            df_db.loc[mask, 'Hazırlanan Adet'] += input_adet
                            
                            veritabani.update_data("Is_Emirleri", df_db)
                            st.success("Veri başarıyla güncellendi!"); st.rerun()
                
                st.divider()
                st.write("📝 **Mevcut Hazırlık Durumu**")
                st.dataframe(sub, use_container_width=True, hide_index=True)

    # --- 3. RAPOR: BİREBİR EŞLEŞME DETAYI ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ MODÜL MENÜSÜNE DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        
        df_rapor = veritabani.get_internal_data("Is_Emirleri")
        if not df_rapor.empty:
            # Excel İndirme Aracı
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_rapor.to_excel(writer, index=False, sheet_name='Uretim_Hazirlik')
            st.download_button("📥 DETAYLI RAPORU EXCEL İNDİR", data=buffer.getvalue(), 
                               file_name=f"Hazirlik_Raporu_{datetime.now().strftime('%d_%m_%Y')}.xlsx", 
                               use_container_width=True, type="primary")
            
            # İş Emri Bazlı Özet
            st.write("📈 **İş Emri Özetleri**")
            summary = df_rapor.groupby("İş Emri").agg({"İhtiyaç Miktarı":"sum", "Hazırlanan Adet":"sum"}).reset_index()
            summary["Tamamlanma %"] = (summary["Hazırlanan Adet"] / summary["İhtiyaç Miktarı"] * 100).fillna(0).round(1)
            st.table(summary)
            
            # Satır Bazlı Detay
            st.write("🔍 **Satır Bazlı Detay (Birebir İzleme)**")
            st.dataframe(df_rapor, use_container_width=True, hide_index=True)
