import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- KATALOG YÜKLEME FONKSİYONU (HER SEFERİNDE TAZE) ---
def load_katalog():
    try:
        # Veriyi çek
        df_k = veritabani.get_internal_data("Urun_Listesi")
        if df_k.empty:
            df_k = veritabani.get_internal_data("Katalog")

        if df_k.empty:
            return []

        # Kolon isimlerini temizle (Boşlukları sil)
        df_k.columns = [str(c).strip() for c in df_k.columns]

        # Kolon kontrolü
        if 'Kod' not in df_k.columns or 'İsim' not in df_k.columns:
            st.error(f"⚠️ Katalog Kolon Hatası! Mevcutlar: {list(df_k.columns)}")
            return []

        # Listeyi oluştur
        return (df_k['Kod'].astype(str) + " | " + df_k['İsim'].astype(str)).tolist()

    except Exception as e:
        st.error(f"❌ Katalog yüklenirken hata oluştu: {e}")
        return []

# --- ÜRÜN SEÇİLDİĞİNDE KODU DOLDUR ---
def urun_secildi():
    sec_val = st.session_state.get("sec_box")
    if sec_val and sec_val != "+ MANUEL GİRİŞ":
        st.session_state["s_kod"] = sec_val.split(" | ")[0]
    else:
        st.session_state["s_kod"] = ""

def goster():
    # --- 1. VERİLERİ HER RENDER'DA TAZELE (CACHE'İ KIR) ---
    if "full_stok_data" not in st.session_state:
        st.session_state.full_stok_data = veritabani.get_internal_data("Stok")
    
    if "full_hareketler_data" not in st.session_state:
        st.session_state.full_hareketler_data = veritabani.get_internal_data("Hareketler")
    
    # Kataloğu her seferinde yükle (Cache Bug Fix)
    katalog = load_katalog()

    # DEBUG: Kataloğu ekranda gizlice gör (Geliştirme sonrası silebilirsin)
    if not katalog:
        st.warning("⚠️ Katalog şu an boş veya çekilemedi!")
    
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.button("⬅️ ANA MENÜ"): 
        for k in ["full_stok_data", "full_hareketler_data"]:
            if k in st.session_state: del st.session_state[k]
        go_home(); st.rerun()
        
    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")
    
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        
        # --- ÜRÜN SEÇİM ALANI ---
        st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="sec_box",
            on_change=urun_secildi
        )
        
        c1, c2 = st.columns(2)
        with c1:
            # Otomatik dolum için value parametresi state'e bağlı
            s_kod = st.text_input(
                "📦 Malzeme Kodu:", 
                value=st.session_state.get("s_kod", ""),
                key="manual_input_kod"
            ).upper().strip()
            st.session_state["s_kod"] = s_kod # Manuel girişi de yakala
            
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
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
            if not st.session_state.get("s_kod") or s_mik <= 0:
                st.error("Eksik bilgi veya miktar!")
            else:
                sec_v = st.session_state.get("sec_box", "")
                isim = sec_v.split(" | ")[1] if " | " in sec_v else "MANUEL ÜRÜN"
                
                st.session_state.gecici_liste.append({
                    "İşlem": move_type, "Kod": st.session_state["s_kod"], "İsim": isim,
                    "Miktar": s_mik, "Lot": s_lot, "Durum": s_dur, "Kaynak": src_adr, "Hedef": dst_adr
                })
                # State temizliği
                st.session_state["s_kod"] = ""
                st.session_state["s_lot"] = ""
                st.session_state["s_mik"] = 0.0
                st.session_state["sec_box"] = "+ MANUEL GİRİŞ"
                st.rerun()

    # --- LİSTE GÖRÜNÜMÜ VE KAYIT ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Adres:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i); st.rerun()

        if st.button("🚀 TÜMÜNÜ KAYDET", use_container_width=True, type="primary"):
            df_st = st.session_state.full_stok_data
            df_hr = st.session_state.full_hareketler_data
            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            for satir in st.session_state.gecici_liste:
                if satir["İşlem"] == "GİRİŞ":
                    mask = (df_st['Kod'] == satir["Kod"]) & (df_st['Adres'] == satir["Hedef"])
                    if mask.any(): df_st.loc[mask, 'Miktar'] += satir["Miktar"]
                    else: df_st = pd.concat([df_st, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)
                
                elif satir["İşlem"] == "ÇIKIŞ":
                    mask = (df_st['Kod'] == satir["Kod"]) & (df_st['Adres'] == satir["Kaynak"])
                    if mask.any(): df_st.loc[mask, 'Miktar'] = max(0, df_st.loc[mask, 'Miktar'].values[0] - satir["Miktar"])
                
                elif satir["İşlem"] == "İÇ TRANSFER":
                    s_m = (df_st['Kod'] == satir["Kod"]) & (df_st['Adres'] == satir["Kaynak"])
                    d_m = (df_st['Kod'] == satir["Kod"]) & (df_st['Adres'] == satir["Hedef"])
                    if s_m.any():
                        df_st.loc[s_m, 'Miktar'] = max(0, df_st.loc[s_m, 'Miktar'].values[0] - satir["Miktar"])
                        if d_m.any(): df_st.loc[d_m, 'Miktar'] += satir["Miktar"]
                        else: df_st = pd.concat([df_st, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)

                df_hr = pd.concat([df_hr, pd.DataFrame([{
                    "Tarih": zaman, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                    "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"], "Personel": "Bilal", "Durum": satir["Durum"], "Lot": satir["Lot"]
                }])], ignore_index=True)

            veritabani.update_data("Stok", df_st)
            veritabani.update_data("Hareketler", df_hr)
            st.session_state.gecici_liste = []
            if "full_stok_data" in st.session_state: del st.session_state.full_stok_data
            if "full_hareketler_data" in st.session_state: del st.session_state.full_hareketler_data
            st.success("✅ Tüm işlemler başarıyla kaydedildi!"); st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
