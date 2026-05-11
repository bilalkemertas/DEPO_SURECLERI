import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- ÜRÜN SEÇİLDİĞİNDE KODU DOLDUR (FIX) ---
def urun_secildi():
    sec_val = st.session_state.get("sec_box")
    if sec_val:
        # "KOD | İSİM" yapısından kodu ayır ve s_kod state'ine mühürle
        st.session_state["s_kod"] = sec_val.split(" | ")[0]
    else:
        st.session_state["s_kod"] = ""

def goster():
    # --- VERİ ÇEKME ---
    df_stok = veritabani.get_internal_data("Stok")
    df_har = veritabani.get_internal_data("Hareketler")
    
    # Katalog verisini çek (Urun_Listesi öncelikli)
    df_k = veritabani.get_internal_data("Urun_Listesi")
    if df_k.empty: df_k = veritabani.get_internal_data("Katalog")
    
    # Kolonları temizle
    df_k.columns = [str(c).strip() for c in df_k.columns]
    
    # Listeyi oluştur (Hata payı yok)
    if not df_k.empty and 'Kod' in df_k.columns and 'İsim' in df_k.columns:
        katalog = (df_k['Kod'].astype(str) + " | " + df_k['İsim'].astype(str)).tolist()
    else:
        katalog = []

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri")
    
    # DEBUG (Geliştirme bitince silinebilir)
    # st.write(f"Katalog Uzunluk: {len(katalog)}")

    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        
        # --- MODERN SELECTBOX (FIX) ---
        st.selectbox(
            "🔍 Ürün Seç:", 
            options=katalog,
            index=None,
            placeholder="Ürün seçmek için tıklayın...",
            key="sec_box",
            on_change=urun_secildi
        )
        
        c1, c2 = st.columns(2)
        with c1:
            # value parametresini sildik, yönetimi key="s_kod" devraldı
            st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        
        # ADRES YÖNETİMİ
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
            kod_val = st.session_state.get("s_kod", "")
            if kod_val and s_mik > 0:
                sec_v = st.session_state.get("sec_box")
                # İsim belirle
                isim = sec_v.split(" | ")[1] if sec_v and " | " in sec_v else "MANUEL ÜRÜN"
                
                st.session_state.gecici_liste.append({
                    "İşlem": move_type, "Kod": kod_val, "İsim": isim,
                    "Miktar": s_mik, "Lot": st.session_state.get("s_lot", ""), 
                    "Durum": s_dur, "Kaynak": src_adr, "Hedef": dst_adr
                })
                # Formu temizle
                st.session_state["s_kod"] = ""
                st.session_state["s_lot"] = ""
                st.session_state["s_mik"] = 0.0
                st.session_state["sec_box"] = None # Selectbox'ı placeholder'a döndürür
                st.rerun()

    # BEKLEYEN LİSTE GÖRÜNÜMÜ
    if st.session_state.gecici_liste:
        st.markdown("### 📋 Bekleyen Hareketler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Adres:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i); st.rerun()

        if st.button("🚀 VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
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
                    sm = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    dm = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if sm.any():
                        df_stok.loc[sm, 'Miktar'] = max(0, df_stok.loc[sm, 'Miktar'].values[0] - satir["Miktar"])
                        if dm.any(): df_stok.loc[dm, 'Miktar'] += satir["Miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)

                # Hareket Kaydı
                df_har = pd.concat([df_har, pd.DataFrame([{
                    "Tarih": zaman, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                    "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"], "Personel": "Bilal", "Durum": satir["Durum"], "Lot": satir["Lot"]
                }])], ignore_index=True)

            veritabani.update_data("Stok", df_stok)
            veritabani.update_data("Hareketler", df_har)
            st.session_state.gecici_liste = []
            st.success("✅ Tüm işlemler başarıyla kaydedildi!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
