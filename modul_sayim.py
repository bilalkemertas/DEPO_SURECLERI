import streamlit as st
import pandas as pd
from datetime import datetime

def goster(conn):
    # --- 1. TEK SEFERLİK VERİ YÜKLEME VE GÜVENLİK ZIRHI ---
    if 'stok_df' not in st.session_state:
        with st.spinner("Veritabanı senkronize ediliyor..."):
            try:
                # Sütun isimlerini sabitleme ve temizleme zırhı
                df_temp = conn.read(worksheet="Urun_Listesi", ttl=0)
                df_temp.columns = [str(c).strip() for c in df_temp.columns]
                
                # Kod/İsim kontrolü
                k_col = 'Kod' if 'Kod' in df_temp.columns else df_temp.columns[0]
                n_col = 'İsim' if 'İsim' in df_temp.columns else df_temp.columns[1]
                df_temp = df_temp.rename(columns={k_col: 'Kod', n_col: 'İsim'})
                
                df_temp = df_temp.dropna(subset=["Kod", "İsim"])
                df_temp["Kod"] = df_temp["Kod"].astype(str).str.strip()
                
                st.session_state['stok_df'] = df_temp
                st.session_state['kod_isim_dict'] = pd.Series(df_temp.İsim.values, index=df_temp.Kod).to_dict()
                st.session_state['katalog'] = [f"{k} | {v}" for k, v in st.session_state['kod_isim_dict'].items()]
            except Exception as e:
                st.error(f"Veri çekme hatası: {e}")
                return

    if 'sayim_db' not in st.session_state:
        st.session_state['sayim_db'] = conn.read(worksheet="sayim", ttl=0)

    # --- 2. DEĞİŞKENLER ---
    df_Stok_ana = st.session_state.get('stok_df', pd.DataFrame())
    katalog = st.session_state.get('katalog', [])

    # --- 3. FONKSİYONLAR ---
    def urun_secildi():
        sec_val = st.session_state.get("sec_box")
        if sec_val:
            kod = str(sec_val).split(" | ")[0]
            st.session_state["manual_s_kod"] = kod

    # --- 4. ARAYÜZ ---
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    if 'manual_s_kod' not in st.session_state: st.session_state['manual_s_kod'] = ""

    st.title("🚀 Sayım ve Durum Takibi")
    tab1, tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])

    with tab1:
        st.subheader("📍 Yeni Veri Girişi")
        with st.container(border=True):
            st.selectbox("🔍 Ürün Seç:", options=katalog, index=None, placeholder="Ürün seçmek için tıklayın...", key="sec_box", on_change=urun_secildi)
            
            c1, c2 = st.columns(2)
            with c1:
                s_kod = st.text_input("📦 Malzeme Kodu:", key="manual_s_kod").upper().strip()
                s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            with c2:
                s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
                s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")
            
            s_adres = st.text_input("📍 Adres", key="adr_box").upper()

            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adres and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%d.%m.%Y"),
                        "Personel": st.session_state.get('kullanici_adi', 'Patron'),
                        "Adres": s_adres, "Kod": s_kod, "Lot": s_lot, "Miktar": s_mik, "Durum": s_dur
                    })
                    st.rerun()

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Sayımlar")
            for index, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_col1, r_col2, r_col3, r_col4, r_col5, r_col6 = st.columns([1, 1, 1.5, 0.8, 1.2, 0.5])
                r_col1.write(item["Adres"]); r_col2.write(item["Kod"]); r_col3.write(item["Lot"])
                r_col4.write(f"{item['Miktar']:,.0f}")
                status_color = "🔴" if item["Durum"] == "Hasarlı" else "🟢"
                r_col5.write(f"{status_color} {item['Durum']}")
                if r_col6.button("🗑️", key=f"del_{index}"):
                    st.session_state['gecici_sayim_listesi'].pop(index); st.rerun()

            if st.button("📤 DRIVE'A GÖNDER VE KAYDET", type="primary", use_container_width=True):
                df_son = pd.concat([st.session_state['sayim_db'], pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True)
                conn.update(worksheet="sayim", data=df_son)
                st.session_state['sayim_db'] = df_son
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Veriler kaydedildi!"); st.rerun()

    with tab2:
        st.subheader("🔍 Sayım ve Fark Analizi")
        if not st.session_state['sayim_db'].empty:
            sistem = df_Stok_ana[['Adres', 'Kod', 'İsim', 'Miktar']].copy()
            sistem.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]
            s_ozet = st.session_state['sayim_db'].groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            s_ozet.columns = ["Adres", "Kod", "Sayılan_Miktar"]
            final_df = pd.merge(sistem, s_ozet, on=['Adres', 'Kod'], how='outer').fillna(0)
            final_df['FARK'] = final_df['Sayılan_Miktar'] - final_df['Sistem_Miktarı']
            
            def style_f(v):
                if v < 0: return 'background-color: #ffcccc; color: red'
                if v > 0: return 'background-color: #ccffcc; color: green'
                return ''
            st.dataframe(final_df.style.map(style_f, subset=['FARK']), use_container_width=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Sistem", f"{final_df['Sistem_Miktarı'].sum():,.0f}")
            m2.metric("Toplam Sayılan", f"{final_df['Sayılan_Miktar'].sum():,.0f}")
            m3.metric("Toplam Fark", f"{final_df['FARK'].sum():,.0f}")
