import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- FORM TEMİZLEME (SADE VE HATASIZ) ---
def clear_form():
    keys = [
        "s_kod", "s_lot", "s_mik",
        "src_adr", "dst_adr", "sec"
    ]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK DOLDUR ---
def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec.split(" | ")[0]

def goster():
    # --- LİSTE STATE ---
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- MESAJ GÖSTER ---
    if st.session_state.get("ekleme_ok"):
        st.success("Kalem listeye eklendi")
        del st.session_state["ekleme_ok"]

    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        clear_form()
        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()

    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")

    with st.container(border=True):

        move_type = st.selectbox(
            "İşlem Tipi:",
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"],
            key="move_type"
        )

        katalog = veritabani.get_katalog()

        sec = st.selectbox(
            "🔍 Ürün Seç:",
            ["+ MANUEL GİRİŞ"] + katalog,
            key="sec",
            on_change=urun_secildi
        )

        c1, c2 = st.columns(2)

        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()

        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox(
                "Durum:",
                ["Kullanılabilir", "Hasarlı", "Karantina"],
                key="s_dur"
            )

        st.markdown("---")

        src_adr = "-"
        dst_adr = "-"

        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()

        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()

        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()

        # --- LİSTEYE EKLE ---
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):

            if not s_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                kalem = {
                    "İşlem": move_type,
                    "Kod": s_kod,
                    "İsim": sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" and len(sec.split(" | ")) > 1 else "MANUEL ÜRÜN",
                    "Miktar": s_mik,
                    "Lot": s_lot,
                    "Durum": s_dur,
                    "Kaynak": src_adr,
                    "Hedef": dst_adr
                }

                st.session_state.gecici_liste.append(kalem)

                st.session_state["ekleme_ok"] = True

                # FORM TEMİZLE
                clear_form()

                st.rerun()

    # --- LİSTE GÖRÜNTÜ ---
    if st.session_state.gecici_liste:

        st.markdown("### 📋 Bekleyen Kalemler")

        for i, item in enumerate(st.session_state.gecici_liste):

            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']}"):

                st.write(f"Ürün: {item['İsim']}")
                st.write(f"Lot: {item['Lot']}")
                st.write(f"Durum: {item['Durum']}")
                st.write(f"Rota: {item['Kaynak']} ➜ {item['Hedef']}")

                if st.button("🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        st.divider()

        # --- TOPLU KAYDET ---
        if st.button("🚀 VERİTABANINA AKTAR", use_container_width=True, type="primary"):

            df_stok = veritabani.get_internal_data("Stok")
            df_hareketler = veritabani.get_internal_data("Hareketler")

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            personel = st.session_state.user if "user" in st.session_state else "Sistem"

            df_stok['Kod'] = df_stok['Kod'].astype(str).str.upper().str.strip()
            df_stok['Adres'] = df_stok['Adres'].astype(str).str.upper().str.strip()
            df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)

            count = 0

            for satir in st.session_state.gecici_liste:

                hareket = {
                    "Tarih": now,
                    "İşlem": satir["İşlem"],
                    "Kod": satir["Kod"],
                    "İsim": satir["İsim"],
                    "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"],
                    "Personel": personel,
                    "Durum": satir["Durum"],
                    "Lot": satir["Lot"],
                    "Kaynak_Adres": satir["Kaynak"],
                    "Hedef_Adres": satir["Hedef"]
                }

                df_hareketler = pd.concat([df_hareketler, pd.DataFrame([hareket])], ignore_index=True)
                count += 1

            veritabani.update_data("Hareketler", df_hareketler)

            st.session_state.gecici_liste = []
            st.session_state["islem_basarili"] = True
            st.session_state["mesaj"] = f"{count} kayıt işlendi"

            st.cache_data.clear()
            st.rerun()
