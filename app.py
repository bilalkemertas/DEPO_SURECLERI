import streamlit as st
import pandas as pd
import ana_sayfa
import modul_sayim
import modul_uretim
import modul_stok
import modul_rapor
import veritabani

# --- SAYFA AYARLARI VE MOBİL CSS ---
st.set_page_config(page_title="BRN Depo Otomasyonu", layout="centered")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        div.stButton > button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
        [data-testid="stMetric"] { background-color: #f8f9fa; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- MOBİL UYUMLU BAŞLIK FONKSİYONU ---
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
    st.session_state.user = "Depo_Yöneticisi"

# --- NAVİGASYON ---
def set_page(pname):
    st.session_state.page = pname

# ==========================================
# ANA SAYFA (NAVİGASYON)
# ==========================================
if st.session_state.page == 'home':
    mobil_baslik("🏢", "BRN Sleep Products - Depo")
    
    st.info(f"Kullanıcı: {st.session_state.user}")
    st.markdown("---")
    
    # Görseldeki dosya yapısına göre menü
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⚖️ SAYIM KONTROL"): set_page('sayim'); st.rerun()
        if st.button("⚙️ ÜRETİM SÜREÇLERİ"): set_page('uretim'); st.rerun()
    with c2:
        if st.button("📦 STOK YÖNETİMİ"): set_page('stok'); st.rerun()
        if st.button("📊 RAPORLAR"): set_page('rapor'); st.rerun()
    
    st.markdown("---")
    # Logo yükleme (Görselde brn_logo.webp var)
    try:
        st.image("brn_logo.webp", width=150)
    except:
        pass

# ==========================================
# MODÜL YÖNLENDİRMELERİ
# ==========================================
elif st.session_state.page == 'sayim':
    modul_sayim.goster()

elif st.session_state.page == 'uretim':
    modul_uretim.goster()

elif st.session_state.page == 'stok':
    modul_stok.goster()

elif st.session_state.page == 'rapor':
    modul_rapor.goster()
