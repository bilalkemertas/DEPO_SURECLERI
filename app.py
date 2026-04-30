# Bu fonksiyonu veritabani.py veya ortak bir yere koyabiliriz
def sayfa_ust_bilgi(emoji, baslik, geri_fonksiyonu):
    """Tüm ekranlarda standart küçük puntolu mobil başlık yapısı"""
    col_nav, col_text = st.columns([1, 5])
    with col_nav:
        if st.button("⬅️", key="global_back_btn"):
            geri_fonksiyonu()
            st.rerun()
    with col_text:
        st.markdown(f"""
            <div style='display: flex; align-items: center; margin-top: 5px;'>
                <span style='font-size: 20px; margin-right: 8px;'>{emoji}</span>
                <span style='font-size: 18px; font-weight: bold;'>{baslik}</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("---")
