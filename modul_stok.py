import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK GÜNCELLE ---
def urun_secildi():
    sec_val = st.session_state.get("sec_box")
    if sec_val and sec_val != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec_val.split(" | ")[0]
    else:
        st.session_state.s_kod = ""

def goster():
    # --- 1. VERİLERİ İLK GİRİŞTE ÇEK ---
    if "full_stok_data" not in st.session_state:
        st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
    
    if "full_hareketler_data" not in st.session_state:
        st.session_state.full_hareketler_data = veritabani.get_internal_data("Hareketler")
    
    # Katalog verisini (Urun_Listesi) çek
    if "katalog_verisi" not in st.session_state:
        try:
            # Burası senin veritabanı yapına göre "Urun_Listesi" veya "Katalog" olmalı
            df_k = veritabani.get_internal_data("Urun_Listesi") 
            if df_k.empty: # Eğer Urun_Listesi boşsa Katalog'u dene
                df_k = veritabani.get_internal_data("Katalog")
            
            if not df_k.empty:
                st.session_state.katalog_verisi = (df_k['Kod'].astype(str) + " | " + df_k['İsim'].astype(str)).tolist()
            else:
                st.session_state.katalog_verisi = []
        except:
            st.session_state.katalog_verisi = []

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- ANA MENÜ BUTONU ---
    if st.button("⬅️ ANA MENÜ"): 
        for k in ["full_stok_data", "full_hareketler_data", "katalog_verisi"]:
            if k in st.session_state: del st.session_state[k]
        go_home(); st.rerun()
        
    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")
    
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        
        # --- ÜRÜN SEÇİM ALANI ---
        katalog = st.session_state.get("katalog_verisi", [])
        st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="sec_box",
            on_change=urun_secildi # Seçim değiştiğinde s_kod'u günceller
        )
        
        c1, c2 = st.columns(2)
        with c1:
            # s_kod'u session_state üzerinden takip ediyoruz
            st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        
        # --- ADRES YÖNETİMİ ---
        src_adr, dst_adr = "-", "-"
        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()
        elif move_type == "ÇIKIŞ":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
        elif move_type == "İÇ TRANSFER":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
            with a2: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            kod = st.session_state.get("s_kod", "")
            if not kod or s_mik <= 0:
                st.error("Eksik bilgi veya miktar!")
            else:
                sec_v = st.session_state.get("sec_box", "")
                isim = sec_v.split(" | ")[1] if " | " in sec_v else "MANUEL ÜRÜN"
                
                st.session_state.gecici_liste.append({
                    "İşlem": move_type, "Kod": kod, "İsim": isim,
                    "Miktar": s_mik, "Lot": st.session_state.get("s_lot", ""), 
                    "Durum": s_dur, "Kaynak": src_adr, "Hedef": dst_adr
                })
                # Formu temizle
                st.session_state.s_kod = ""; st.session_state.s_lot = ""; st.session_state.s_mik = 0.0
                st.session_state.sec_box = "+ MANUEL GİRİŞ"
                st.rerun()

    # --- BEKLEYEN İŞLEMLER ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Yol:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i); st.rerun()

        if st.button("🚀 TÜMÜNÜ KAYDET", use_container_width=True, type="primary"):
            df_stok = st.session_state.full_stok_data
            df_hareketler = st.session_state.full_hareketler_data
            zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for satir in st.session_state.gecici_liste:
                # Stok Güncelleme
                if satir["İşlem"] == "GİRİŞ":
                    m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if m.any(): df_stok.loc[m, 'Miktar'] += satir["Miktar"]
                    else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)
                
                elif satir["İşlem"] == "ÇIKIŞ":
                    m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    if m.any(): df_stok.loc[m, 'Miktar'] = max(0, df_stok.loc[m, 'Miktar'].values[0] - satir["Miktar"])
                
                elif satir["İşlem"] == "İÇ TRANSFER":
                    s_m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    d_m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if s_m.any():
                        df_stok.loc[s_m, 'Miktar'] = max(0, df_stok.loc[s_m, 'Miktar'].values[0] - satir["Miktar"])
                        if d_m.any(): df_stok.loc[d_m, 'Miktar'] += satir["Miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)

                # Hareket Kaydı
                df_hareketler = pd.concat([df_hareketler, pd.DataFrame([{
                    "Tarih": zaman, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                    "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"], "Personel": "Bilal", "Durum": satir["Durum"], "Lot": satir["Lot"]
                }])], ignore_index=True)

            veritabani.update_data("Stok", df_stok)
            veritabani.update_data("Hareketler", df_hareketler)
            st.session_state.gecici_liste = []
            # Hafızayı boşalt ki taze veri çekilsin
            del st.session_state.full_stok_data; del st.session_state.full_hareketler_data
            st.success("✅ İşlemler başarıyla kaydedildi!"); st.rerun()

    st.markdown("---")
    st.markdown("<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
