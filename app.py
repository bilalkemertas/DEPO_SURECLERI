if st.session_state['page'] == 'main':
    st.subheader("Uygulama Menüsü")
    st.write("") # Layout düzeni için boşluk
    
    # --- 1. SATIR BUTONLARI ---
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦\nMal Kabul"):
            st.session_state['page'] = 'mal_kabul'
            st.rerun()
        if st.button("📦\nRaporlar"):
            st.session_state['page'] = 'rapor'
            st.rerun()
        if st.button("📦\nSayim"):
            st.session_state['page'] = 'sayim'
            st.rerun()
            
    with col2:
        if st.button("✂️\nBlok & Rulo Kesim"):
            st.session_state['page'] = 'blok_kesim'
            st.rerun()

    st.write("") # Satırlar arası boşluk

    # --- 2. SATIR BUTONLARI ---
    col3, col4 = st.columns(2)
    
    with col3:
        # Buraya eski uygulmandaki diğer modülün adını yazabilirsin
        if st.button("🔄\nÜretim Hazırlık (Kitleme)"):
            st.session_state['page'] = 'uretim_hazirlik' # Kendi sayfa değişkenini yaz
            st.rerun()
            
    with col4:
        # Buraya diğer modülün adını yazabilirsin
        if st.button("📊\nDepo Sayım & Envanter"):
            st.session_state['page'] = 'depo_sayim' # Kendi sayfa değişkenini yaz
            st.rerun()
