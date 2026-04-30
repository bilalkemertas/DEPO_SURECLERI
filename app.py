import streamlit as st
import pandas as pd
import modul_giris
import modul_cikis
import modul_hareket
import modul_sayim
import veritabani

# --- SAYFA AYARLARI VE MOBİL CSS ---
st.set_page_config(page_title="BRN Depo Otomasyonu", layout="centered")

st.markdown("""
    <style>
        /* Üst boşluğu azalt */
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        /* Buton puntolarını ve boşluklarını düzenle */
        div.stButton > button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
        /* Metriklerin alt boşluğunu daralt */
        [data-testid="stMetric"] { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- MOBİL UYUMLU BAŞLIK FONKSİYONU (MERKEZİ) ---
def mobil_baslik(emoji, metin):
    st.markdown(f"""
        <div style='display: flex; align-items: center; margin-bottom: 15px;'>
            <span style='font-size: 22px; margin-right: 10px;'>{emoji}</span>
            <span style='font-size: 19px; font-weight: bold; color: #1E3A8A;'>{metin}</span>
        </div>
    """, unsafe_allow_html=True)

# --- OTURUM YÖNETİMİ ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'user' not in st.session_state:
    st.session_state.user = "Depo_Yöneticisi" # Varsayılan kullanıcı (Patron)

# --- ANA MENÜ FONKSİYONLARI ---
def set_page(pname):
    st.session_state.page = pname

# ==========================================
# ANA SAYFA (NAVİGASYON)
# ==========================================
if st.session_state.page == 'home':
    mobil_baslik("🏢", "BRN Sleep Products - Depo")
    
    st.info(f"Hoş geldin Patron! Kullanıcı: {st.session_state.user}")
    st.markdown("---")
    
    # Menü Butonları (Büyük ve Mobil Uyumlu)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📥 ÜRÜN GİRİŞİ"): set_page('giris'); st.rerun()
        if st.button("📤 ÜRÜN ÇIKIŞI"): set_page('cikis'); st.rerun()
    with c2:
        if st.button("🔄 STOK HAREKET"): set_page('hareket'); st.rerun()
        if st.button("⚖️ SAYIM KONTROL"): set_page('sayim'); st.rerun()
    
    st.markdown("---")
    if st.button("📊 GÜNCEL STOK DURUMU"):
        st.subheader("📦 Mevcut Stok Özeti")
        df_stok = veritabani.get_internal_data("Stok")
        if not df_stok.empty:
            st.dataframe(df_stok, use_container_width=True, hide_index=True)
        else:
            st.warning("Stok verisi bulunamadı.")

# ==========================================
# MODÜL YÖNLENDİRMELERİ
# ==========================================
elif st.session_state.page == 'giris':
    modul_giris.goster()

elif st.session_state.page == 'cikis':
    modul_cikis.goster()

elif st.session_state.page == 'hareket':
    modul_hareket.goster()

elif st.session_state.page == 'sayim':
    modul_sayim.goster()
