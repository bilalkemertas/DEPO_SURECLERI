import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani

def goster(conn):
    # --- 1. TEK SEFERLİK VERİ YÜKLEME ---
    df_stok = veritabani.get_internal_data("Stok")
    df_k = veritabani.get_internal_data("Urun_Listesi")
    
    if df_k is None or df_k.empty:
        df_k = veritabani.get_internal_data("Katalog")

    if df_k is None or df_k.empty:
        katalog = []
        kod_isim_dict = {}
    else:
        df_k.columns = [str(c).strip() for c in df_k.columns]
        k_col = 'Kod' if 'Kod' in df_k.columns else df_k.columns[0]
        n_col = 'İsim' if 'İsim' in df_k.columns else df_k.columns[1]
        katalog = (df_k[k_col].astype(str) + " | " + df_k[n_col].astype(str)).tolist()
        kod_isim_dict = pd.Series(df_k[n_col].values, index=df_k[k_col].astype(str)).to_dict()

    if 'sayim_db' not in st.session_state:
        st.session_state['sayim_db'] = veritabani.get_internal_data("sayim")

    # --- 2. DEĞİŞKENLER VE OTURUM YÖNETİMİ ---
    if st.session_state['sayim_db'] is None: st.session_state['sayim_db'] = pd.DataFrame()
    if 'aktif_sayim_oturumu' not in st.session_state: st.session_state['aktif_sayim_oturumu'] = False
    if 'sayim_info' not in st.session_state: st.session_state['sayim_info'] = {}

    def urun_secildi():
        sec_val = st.session_state.get("sec_box")
        if sec_val:
            kod = str(sec_val).split(" | ")[0]
            st.session_state["manual_s_kod"] = kod

    # --- 4. ARAYÜZ VE SESSION STATE ---
    if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
    if 'manual_s_kod' not in st.session_state: st.session_state['manual_s_kod'] = ""

    st.title("🚀 Sayım ve Durum Takibi")
    tab1, tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])

    with tab1:
        # --- YENİ SAYIM MENÜSÜ ---
        st.subheader("⚙️ Sayım Oturumu Yönetimi")
        if not st.session_state['aktif_sayim_oturumu']:
            with st.expander("➕ Sayım Başlatma Menüsü"):
                c_tarih, c_belge = st.columns(2)
                s_tarih = c_tarih.date_input("Sayım Günü", datetime.now())
                s_belge = c_belge.text_input("Sayım Belge No")
                if st.button("🚀 Oturumu Başlat"):
                    if s_belge:
                        st.session_state['aktif_sayim_oturumu'] = True
                        st.session_state['sayim_info'] = {"Tarih": str(s_tarih), "Belge_No": s_belge}
                        st.rerun()
                    else:
                        st.warning("Lütfen Belge Numarası girin!")
        else:
            st.success(f"🟢 Aktif Sayım: {st.session_state['sayim_info']['Belge_No']} | {st.session_state['sayim_info']['Tarih']}")
            m1, m2, m3 = st.columns(3)
            m1.button("🔍 Sayım Okutma Modu (Aktif)")
            if m3.button("🛑 Sayımı Tamamla"):
                st.session_state['aktif_sayim_oturumu'] = False
                st.session_state['sayim_info'] = {}
                st.rerun()

        st.divider()
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
                    # Oturum bilgileri varsa listeye ekle
                    yeni_kayit = {
                        "Tarih": datetime.now().strftime("%d.%m.%Y"),
                        "Personel": st.session_state.get('kullanici_adi', 'Patron'),
                        "Adres": s_adres, "Kod": s_kod, "Lot": s_lot, "Miktar": s_mik, "Durum": s_dur
                    }
                    if st.session_state['aktif_sayim_oturumu']:
                        yeni_kayit.update(st.session_state['sayim_info'])
                        
                    st.session_state['gecici_sayim_listesi'].append(yeni_kayit)
                    st.rerun()

        # DİNAMİK SİLİNEBİLİR LİSTE
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
                veritabani.update_data("sayim", df_son)
                st.session_state['sayim_db'] = df_son
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Tüm veriler kaydedildi!"); st.rerun()

    with tab2:
        st.subheader("🔍 Sayım ve Fark Analizi")
        if not st.session_state['sayim_db'].empty and df_stok is not None:
            sistem = df_stok[['Adres', 'Kod', 'İsim', 'Miktar']].copy()
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
