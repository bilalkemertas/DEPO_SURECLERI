import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- FORM TEMİZLEME ---
def clear_form():
    st.session_state.reset_form = True

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK DOLDUR ---
def urun_secildi():
    val = st.session_state.get("sec_box")
    if val and val != "+ MANUEL GİRİŞ":
        # Katalog formatı: "KOD | İSİM" ise ilk parçayı al
        st.session_state.s_kod = val.split(" | ")[0]
    else:
        st.session_state.s_kod = ""

def goster():
    # --- 1. SAYFA AÇILIR AÇILMAZ VERİLERİ MÜHÜRLE (KRİTİK) ---
    if "full_stok_data" not in st.session_state:
        st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
    
    if "full_hareketler_data" not in st.session_state:
        st.session_state.full_hareketler_data = veritabani.get_internal_data("Hareketler")
    
    # "Urun_Listesi" sekmesindeki taze veriyi çekip session_state'e alıyoruz
    if "katalog_verisi" not in st.session_state:
        try:
            # Urun_Listesi sekmesinden Kod ve İsimleri çekip liste yapıyoruz
            df_katalog = veritabani.get_internal_data("Urun_Listesi")
            if not df_katalog.empty:
                # Kod | İsim formatında birleştiriyoruz
                st.session_state.katalog_verisi = (df_katalog['Kod'].astype(str) + " | " + df_katalog['İsim'].astype(str)).tolist()
            else:
                st.session_state.katalog_verisi = []
        except:
            st.session_state.katalog_verisi = []

    # --- TOPLU LİSTE BAŞLATMA ---
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- FORM SIFIRLAMA ---
    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "src_adr", "dst_adr", "sec_box"]:
            if k in st.session_state:
                if k == "s_mik": st.session_state[k] = 0.0
                elif k == "sec_box": st.session_state[k] = "+ MANUEL GİRİŞ"
                else: st.session_state[k] = ""
        st.session_state.reset_form = False

    if st.button("⬅️ ANA MENÜ"): 
        # Belleği temizleyerek çık ki bir sonraki girişte taze veri çeksin
        for k in ["full_stok_data", "full_hareketler_data", "katalog_verisi"]:
            if k in st.session_state: del st.session_state[k]
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")
    
    with st.container(border=True):
        move_type = st.selectbox(
            "İşlem Tipi:", 
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], 
            key="move_type"
        )
        
        # --- LİSTEYİ SESSION STATE'DEN ÇEK (ANINDA GELİR) ---
        katalog_listesi = st.session_state.get("katalog_verisi", [])
        
        st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog_listesi, 
            key="sec_box",
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
            current_kod = st.session_state.get("s_kod", "")
            if not current_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                urun_ismi = "MANUEL ÜRÜN"
                current_sec = st.session_state.get("sec_box")
                if current_sec and current_sec != "+ MANUEL GİRİŞ" and " | " in current_sec:
                    urun_ismi = current_sec.split(" | ")[1]

                kalem = {
                    "İşlem": move_type, "Kod": current_kod,
                    "İsim": urun_ismi,
                    "Miktar": s_mik, "Lot": st.session_state.get("s_lot", ""), 
                    "Durum": s_dur, "Kaynak": src_adr, "Hedef": dst_adr
                }
                st.session_state.gecici_liste.append(kalem)
                clear_form()
                st.rerun()

    # --- GEÇİCİ LİSTE VE VERİTABANI İŞLEME AYNI KALDI ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Adres:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Satırı Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        if st.button("🚀 TÜM HAREKETLERİ VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            df_stok = st.session_state.full_stok_data
            df_hareketler = st.session_state.full_hareketler_data
            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            personel = st.session_state.user if 'user' in st.session_state else "Bilal"
            
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
            
            for k in ["full_stok_data", "full_hareketler_data", "katalog_verisi"]:
                if k in st.session_state: del st.session_state[k]
                
            st.session_state.gecici_liste = []
            st.success("✅ İşlemler başarıyla kaydedildi!")
            st.rerun()

    st.markdown("---")
    col_sign2 = st.columns([3, 1])[1]
    with col_sign2:
        st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
