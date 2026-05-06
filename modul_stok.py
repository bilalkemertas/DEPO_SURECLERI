import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

# ----------------------------
# NAVIGATION
# ----------------------------
def go_home():
    st.session_state.page = "home"


# ----------------------------
# SAFE FORM RESET
# (Streamlit-safe: ONLY delete keys)
# ----------------------------
def clear_form():

    keys_to_clear = [
        "s_kod",
        "s_lot",
        "s_mik",
        "src_adr",
        "dst_adr",
        "sec",
        "move_type",
        "s_dur"
    ]

    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]


# ----------------------------
# AUTO PRODUCT CODE FILL
# ----------------------------
def urun_secildi():
    sec = st.session_state.get("sec")

    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state["s_kod"] = sec.split(" | ")[0]


# ----------------------------
# MAIN SCREEN
# ----------------------------
def goster():

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # ---- success message after save ----
    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))

        clear_form()

        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

    # ---- home button ----
    if st.button("⬅️ ANA MENÜ"):
        go_home()
        st.rerun()

    st.subheader("📊 Stok Hareketleri")

    # ----------------------------
    # INPUT FORM
    # ----------------------------
    with st.container(border=True):

        move_type = st.selectbox(
            "İşlem Tipi",
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"],
            key="move_type"
        )

        katalog = veritabani.get_katalog()

        sec = st.selectbox(
            "Ürün Seç",
            ["+ MANUEL GİRİŞ"] + katalog,
            key="sec",
            on_change=urun_secildi
        )

        c1, c2 = st.columns(2)

        with c1:
            s_kod = st.text_input("Malzeme Kodu", key="s_kod")
            s_lot = st.text_input("Lot No", key="s_lot")

        with c2:
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox(
                "Durum",
                ["Kullanılabilir", "Hasarlı", "Karantina"],
                key="s_dur"
            )

        st.markdown("---")

        src_adr = "-"
        dst_adr = "-"

        c3, c4 = st.columns(2)

        if move_type == "GİRİŞ":
            with c3:
                dst_adr = st.text_input("Hedef Adres", key="dst_adr")

        elif move_type == "ÇIKIŞ":
            with c3:
                src_adr = st.text_input("Kaynak Adres", key="src_adr")

        elif move_type == "İÇ TRANSFER":
            with c3:
                src_adr = st.text_input("Kaynak Adres", key="src_adr")
            with c4:
                dst_adr = st.text_input("Hedef Adres", key="dst_adr")

        # ----------------------------
        # ADD TO LIST
        # ----------------------------
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):

            if not s_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:

                item = {
                    "İşlem": move_type,
                    "Kod": s_kod.strip().upper(),
                    "İsim": sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" and " | " in sec else "MANUEL ÜRÜN",
                    "Miktar": s_mik,
                    "Lot": s_lot,
                    "Durum": s_dur,
                    "Kaynak": src_adr,
                    "Hedef": dst_adr
                }

                st.session_state.gecici_liste.append(item)

                clear_form()
                st.rerun()

    # ----------------------------
    # PENDING LIST
    # ----------------------------
    if st.session_state.gecici_liste:

        st.markdown("### Bekleyen İşlemler")

        for i, item in enumerate(st.session_state.gecici_liste):

            with st.expander(f"{i+1}. {item['Kod']} | {item['Miktar']}"):

                st.write(f"İşlem: {item['İşlem']}")
                st.write(f"Ürün: {item['İsim']}")
                st.write(f"Lot: {item['Lot']}")
                st.write(f"Durum: {item['Durum']}")
                st.write(f"Rota: {item['Kaynak']} ➜ {item['Hedef']}")

                if st.button("Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        st.divider()

        # ----------------------------
        # SAVE ALL
        # ----------------------------
        if st.button("🚀 KAYDET", use_container_width=True, type="primary"):

            df_stok = veritabani.get_internal_data("Stok")
            df_hareketler = veritabani.get_internal_data("Hareketler")

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            user = st.session_state.get("user", "Sistem")

            df_stok["Kod"] = df_stok["Kod"].astype(str).str.upper().str.strip()
            df_stok["Adres"] = df_stok["Adres"].astype(str).str.upper().str.strip()
            df_stok["Miktar"] = pd.to_numeric(df_stok["Miktar"], errors="coerce").fillna(0)

            count = 0

            for r in st.session_state.gecici_liste:

                hareket = {
                    "Tarih": now,
                    "İşlem": r["İşlem"],
                    "Kod": r["Kod"],
                    "İsim": r["İsim"],
                    "Adres": r["Hedef"] if r["İşlem"] == "GİRİŞ" else r["Kaynak"],
                    "Miktar": r["Miktar"],
                    "Personel": user,
                    "Durum": r["Durum"],
                    "Lot": r["Lot"],
                    "Kaynak_Adres": r["Kaynak"],
                    "Hedef_Adres": r["Hedef"]
                }

                df_hareketler = pd.concat(
                    [df_hareketler, pd.DataFrame([hareket])],
                    ignore_index=True
                )

                count += 1

            veritabani.update_data("Hareketler", df_hareketler)

            st.session_state.gecici_liste = []
            st.session_state.islem_basarili = True
            st.session_state.mesaj = f"{count} kayıt işlendi"

            st.cache_data.clear()
            st.rerun()
