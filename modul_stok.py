import streamlit as st
import veritabani

def go_home(): 
    st.session_state.page = 'home'

def goster():
    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri")
    
    with st.container(border=True):
        # İşlem tipine göre dinamik alanlar yöneteceğiz
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        
        katalog = veritabani.get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog)
        
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            s_lot = st.text_input("🔢 Parti/Lot No:").upper()
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0)
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"])

        st.markdown("---")
        
        # --- DİNAMİK ADRES ALANLARI ZIRHI ---
        # İşlem tipine göre adres değişkenlerini tanımlıyoruz
        src_adr = "-"
        dst_adr = "-"
        
        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):").upper()
        
        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):").upper()
        
        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):").upper()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):").upper()

        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            # Veritabanı loglama için merkezi saati kullanıyoruz
            islem_zamani = veritabani.get_now_str()
            
            # Kayıt simülasyonu (Buraya veritabani.update_data entegrasyonu gelecek)
            st.success(f"✅ {move_type} işlemi başarıyla kaydedildi!")
            st.info(f"Zaman: {islem_zamani} | Ürün: {s_kod} | Kaynak: {src_adr} | Hedef: {dst_adr}")
