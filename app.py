import streamlit as st

# Yeni dosyalarımızı içeri aktarıyoruz
import ayarlar
import veritabani
import ana_sayfa
import modul_stok
import modul_uretim
import modul_sayim
import modul_rapor

# 1. Sayfa Görünümü ve Güvenlik Ayarları
ayarlar.page_ayarlar()
ayarlar.session_kontrol()
ayarlar.guvenlik_duvari()

# 2. Hangi sayfadaysak sadece o dosyadaki kodu çalıştır (Muazzam Hız ve Güvenlik)
if st.session_state.page == 'home':
    ana_sayfa.goster()
    
elif st.session_state.page == 'stok':
    modul_stok.goster()
    
elif st.session_state.page == 'uretim':
    modul_uretim.goster()
    
elif st.session_state.page == 'sayim':
    modul_sayim.goster()
    
elif st.session_state.page == 'rapor':
    modul_rapor.goster()

# Alt bilgi
st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
