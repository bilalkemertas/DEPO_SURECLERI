import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani

def goster(conn):
    # --- VERİ YÜKLEME ---
    df_stok = veritabani.get_internal_data("Stok")
    df_k = veritabani.get_internal_data("Urun_Listesi")

    if not isinstance(df_stok, pd.DataFrame):
        df_stok = pd.DataFrame()

    if not isinstance(df_k, pd.DataFrame) or df_k.empty:
        df_k = veritabani.get_internal_data("Katalog")

    if not isinstance(df_k, pd.DataFrame) or df_k.empty:
        katalog = []
    else:
        df_k.columns = [str(c).strip() for c in df_k.columns]
        k_col = 'Kod' if 'Kod' in df_k.columns else df_k.columns[0]
        n_col = 'İsim' if 'İsim' in df_k.columns else df_k.columns[1]
        katalog = (df_k[k_col].astype(str) + " | " + df_k[n_col].astype(str)).tolist()

    if 'sayim_db' not in st.session_state:
        st.session_state['sayim_db'] = veritabani.get_internal_data("sayim")

    if not isinstance(st.session_state.get('sayim_db'), pd.DataFrame):
        st.session_state['sayim_db'] = pd.DataFrame()

    if 'sayim_info' not in st.session_state:
        st.session_state['sayim_info'] = {}

    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []

    if 'manual_s_kod' not in st.session_state:
        st.session_state['manual_s_kod'] = ""

    def urun_secildi():
        sec_val = st.session_state.get("sec_box")
        if sec_val:
            kod = str(sec_val).split(" | ")[0]
            st.session_state["manual_s_kod"] = kod

    st.title("🚀 Depo Sayım")

    # --- SAYFA SEÇİMİ (TEK KONTROL NOKTASI) ---
    sayfa = st.radio(
        "İşlem Seçin",
        ["🟢 Sayım Başlat", "📥 Sayım Okut", "📊 Rapor"],
        horizontal=True
    )

    # =========================================================
    # 🟢 SAYIM BAŞLAT (AYRI SAYFA)
    # =========================================================
    if sayfa == "🟢 Sayım Başlat":

        st.subheader("🟢 Yeni Sayım Belgesi")

        if st.button("📄 Sayım Başlat"):
            belge_no = f"SYM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            st.session_state['sayim_info'] = {
                "Belge": belge_no,
                "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                "Durum": "AÇIK"
            }
            st.success(f"Oluşturuldu: {belge_no}")

        st.markdown("---")
        st.subheader("🔒 Açık Sayımları Kapat")

        if not st.session_state['sayim_db'].empty:

            if "Durum" not in st.session_state['sayim_db'].columns:
                st.session_state['sayim_db']["Durum"] = "AÇIK"

            aciklar = st.session_state['sayim_db'][
                st.session_state['sayim_db']["Durum"] == "AÇIK"
            ]

            if not aciklar.empty:
                sec = st.selectbox("Açık Sayım Seç", aciklar["Oturum"].unique())

                if st.button("Kapat"):
                    st.session_state['sayim_db'].loc[
                        st.session_state['sayim_db']["Oturum"] == sec, "Durum"
                    ] = "KAPALI"

                    veritabani.update_data("sayim", st.session_state['sayim_db'])
                    st.success(f"{sec} kapatıldı")
                    st.rerun()

    # =========================================================
    # 📥 SAYIM OKUT (AYRI SAYFA)
    # =========================================================
    elif sayfa == "📥 Sayım Okut":

        st.subheader("📥 Sayım Okutma")

        if not st.session_state['sayim_db'].empty:
            belgeler = st.session_state['sayim_db']["Oturum"].dropna().unique()

            if len(belgeler) > 0:
                sec_belge = st.selectbox("Sayım Belgesi", belgeler)
                st.session_state['sayim_info']["Belge"] = sec_belge
                st.info(f"Aktif Belge: {sec_belge}")

        st.markdown("### 📍 Veri Girişi")

        st.selectbox(
            "Ürün",
            katalog,
            key="sec_box",
            on_change=urun_secildi
        )

        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("Kod", key="manual_s_kod").upper().strip()
            s_lot = st.text_input("Lot", key="s_lot").upper().strip()
        with c2:
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = st.selectbox("Durum", ["Kullanılabilir", "Hasarlı", "Karantina"])

        s_adres = st.text_input("Adres").upper()

        if st.button("➕ Ekle"):
            if s_adres and s_kod:
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": datetime.now().strftime("%d.%m.%Y"),
                    "Oturum": st.session_state['sayim_info'].get("Belge", "MANUEL"),
                    "Adres": s_adres,
                    "Kod": s_kod,
                    "Lot": s_lot,
                    "Miktar": s_mik,
                    "Durum": s_dur
                })
                st.rerun()

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Bekleyenler")

            for i, item in enumerate(st.session_state['gecici_sayim_listesi']):
                c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,1,0.5])
                c1.write(item["Adres"])
                c2.write(item["Kod"])
                c3.write(item["Lot"])
                c4.write(item["Miktar"])
                c5.write(item["Durum"])

                if c6.button("🗑️", key=f"del_{i}"):
                    st.session_state['gecici_sayim_listesi'].pop(i)
                    st.rerun()

            if st.button("💾 Kaydet"):
                df_new = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                df_all = pd.concat([st.session_state['sayim_db'], df_new], ignore_index=True)

                veritabani.update_data("sayim", df_all)

                st.session_state['sayim_db'] = df_all
                st.session_state['gecici_sayim_listesi'] = []

                st.success("Kaydedildi")
                st.rerun()

    # =========================================================
    # 📊 RAPOR (AYRI SAYFA)
    # =========================================================
    elif sayfa == "📊 Rapor":

        st.subheader("📊 Sayım Raporu")

        if not st.session_state['sayim_db'].empty and not df_stok.empty:

            gerekli = ['Adres', 'Kod', 'İsim', 'Miktar']

            if all(col in df_stok.columns for col in gerekli):

                sistem = df_stok[gerekli].copy()
                sistem.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]

                sayilan = (
                    st.session_state['sayim_db']
                    .groupby(['Adres', 'Kod'])['Miktar']
                    .sum()
                    .reset_index()
                )

                sayilan.columns = ["Adres", "Kod", "Sayılan_Miktar"]

                final = pd.merge(sistem, sayilan, on=['Adres','Kod'], how='outer').fillna(0)
                final["FARK"] = final["Sayılan_Miktar"] - final["Sistem_Miktarı"]

                st.dataframe(final, use_container_width=True)

                c1, c2, c3 = st.columns(3)
                c1.metric("Sistem", int(final["Sistem_Miktarı"].sum()))
                c2.metric("Sayılan", int(final["Sayılan_Miktar"].sum()))
                c3.metric("Fark", int(final["FARK"].sum()))
