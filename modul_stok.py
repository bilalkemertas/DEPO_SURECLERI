import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime
import re

def go_home(): 
    st.session_state.page = 'home'

# --- FORM TEMİZLEME ---
def clear_form():
    st.session_state.reset_form = True

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK DOLDUR ---
def urun_secildi():
    sec_val = st.session_state.get("sec")
    if sec_val and sec_val != "+ MANUEL GİRİŞ":
        # Katalogdan gelen "KOD | İSİM" yapısını ayırıp koda yazıyoruz
        st.session_state.s_kod = sec_val.split(" | ")[0]
    elif sec_val == "+ MANUEL GİRİŞ":
        st.session_state.s_kod = ""

def goster():
    # --- TOPLU LİSTE İÇİN SESSION STATE BAŞLATMA ---
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- FORM SIFIRLAMA ---
    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            if k in st.session_state:
                if k == "s_mik": st.session_state[k] = 0.0
                elif k == "sec": st.session_state[k] = "+ MANUEL GİRİŞ"
                else: st.session_state[k] = ""
        st.session_state.reset_form = False

    # --- KAYIT SONRASI MESAJ ---
    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        del st.session_state["islem_basarili"]
        if "mesaj" in st.session_state: del st.session_state["mesaj"]

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
        
        # KATALOG VERİSİNİ ÇEK
        try:
            katalog = veritabani.get_katalog()
        except:
            katalog = []

        # ÜRÜN SEÇİM LİSTESİ
        st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="sec",
            on_change=urun_secildi
        )
        
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
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
            with a1: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()
        
        elif move_type == "ÇIKIŞ":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
        
        elif move_type == "İÇ TRANSFER":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
            with a2: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            # State'den güncel değerleri al
            cur_kod = st.session_state.get("s_kod", "")
            cur_sec = st.session_state.get("sec", "+ MANUEL GİRİŞ")
            
            if not cur_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                kalem = {
                    "İşlem": move_type, 
                    "Kod": cur_kod,
                    "İsim": cur_sec.split(" | ")[1] if cur_sec != "+ MANUEL GİRİŞ" and " | " in cur_sec else "MANUEL ÜRÜN",
                    "Miktar": s_mik, 
                    "Lot": st.session_state.get("s_lot", ""), 
                    "Durum": s_dur, 
                    "Kaynak": st.session_state.get("src_adr", "-") if move_type != "GİRİŞ" else "-", 
                    "Hedef": st.session_state.get("dst_adr", "-") if move_type != "ÇIKIŞ" else "-"
                }
                st.session_state.gecici_liste.append(kalem)
                clear_form()
                st.rerun()

    # --- GEÇİCİ LİSTE GÖRÜNÜMÜ ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Adres:** {item['Kaynak']} ➡️ {item['Hedef']} | **Lot:** {item['Lot']} | **Durum:** {item['Durum']}")
                if st.button(f"🗑️ Satırı Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        if st.button("🚀 TÜM HAREKETLERİ VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            df_stok = veritabani.get_internal_data("Stok")
            df_hareketler = veritabani.get_internal_data("Hareketler")
            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            personel = st.session_state.user if 'user' in st.session_state else "Sistem"
            
            for satir in st.session_state.gecici_liste:
                if satir["İşlem"] == "GİRİŞ":
                    mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if mask.any(): df_stok.loc[mask, 'Miktar'] += satir["Miktar"]
                    else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)
                
                elif satir["İşlem"] == "ÇIKIŞ":
                    mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    if mask.any(): df_stok.loc[mask, 'Miktar'] = max(0, df_stok.loc[mask, 'Miktar'].values[0] - satir["Miktar"])
                
                elif satir["İşlem"] == "İÇ TRANSFER":
                    src_mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    dst_mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if src_mask.any():
                        df_stok.loc[src_mask, 'Miktar'] = max(0, df_stok.loc[src_mask, 'Miktar'].values[0] - satir["Miktar"])
                        if dst_mask.any(): df_stok.loc[dst_mask, 'Miktar'] += satir["Miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)

                df_hareketler = pd.concat([df_hareketler, pd.DataFrame([{
                    "Tarih": islem_zamani, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                    "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"], "Personel": personel, "Durum": satir["Durum"], "Lot": satir["Lot"]
                }])], ignore_index=True)

            veritabani.update_data("Stok", df_stok)
            veritabani.update_data("Hareketler", df_hareketler)
            st.session_state.gecici_liste = []
            st.success("✅ Tüm işlemler başarıyla kaydedildi!")
            st.rerun()

    # --- SAYFA SONU İMZASI ---
    st.markdown("---")
    col_sign1, col_sign2 = st.columns([3, 1])
    with col_sign2:
        st.markdown(
            """
            <div style='text-align: right;'>
                <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p>
                <p style='margin:0; font-size: 12px; color: gray;'>BRN 2026</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
