import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. GITHUB'DAKİ TÜM MODÜLLERİ İÇE AKTARIYORUZ
import teslim_alma
import blok_kesim
import modul_stok
import modul_uretim
import modul_sayim
import modul_rapor

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
st.set_page_config(page_title="BRN WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# Garantili, Simetrik ve Ayrıştırılmış CSS Tasarımı
st.markdown("""
    <style>
        .block-container { padding: 2rem !important; max-width: 1000px; margin: 0 auto; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* 1. SADECE ANA MENÜ KUTULARI İÇİN (Primary Butonlar) */
        button[kind="primary"] {
            height: 130px !important;
            width: 100% !important;
            border-radius: 12px !important;
            font-size: 18px !important;
            font-weight: bold !important;
            background-color: #ffffff !important;
            color: #0b3c5d !important;
            border: 2px solid #dcdcdc !important;
            transition: all 0.3s ease !important;
            white-space: pre-wrap !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
        }
        button[kind="primary"]:hover {
            background-color: #0b3c5d !important;
            color: #ffffff !important;
            border-color: #11caa0 !important;
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important;
        }
        
        /* 2. STANDART BUTONLAR İÇİN (Çıkış, Geri Dön, Giriş) */
        button[kind="secondary"] {
            height: 50px !important;
            border-radius: 8px !important;
            font-weight: bold !important;
            border: 1px solid #dcdcdc !important;
            color: #0b3c5d !important;
            transition: all 0.2s ease !important;
        }
        button[kind="secondary"]:hover {
            border-color: #11caa0 !important;
            color: #11caa0 !important;
            background-color: #f8f9fa !important;
        }
        
        /* Kurumsal Header */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .erp-title { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 1px; }
        .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }
        
        /* Login Ekranı Özel */
        .login-box {
            background-color: #ffffff;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            max-width: 400px;
            margin: 50px auto;
            text-align: center;
            border-top: 5px solid #0b3c5d;
        }
    </style>
""", unsafe_allow_html=True)

# Google Sheets Bağlantısı
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    conn = None 

# --- OTURUM (SESSION) YÖNETİMİ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'kullanici_adi' not in st.session_state:
    st.session_state['kullanici_adi'] = ""
if 'page' not in st.session_state:
    st.session_state['page'] = 'main'

# --- 1. KULLANICI GİRİŞ (LOGIN) EKRANI ---
if not st.session_state['logged_in']:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("<h2 style='color: #0b3c5d; margin-bottom: 20px;'>BRN WMS Giriş</h2>", unsafe_allow_html=True)
    
    kadi = st.text_input("Kullanıcı Adı", placeholder="Kullanıcı adınızı girin")
    sifre = st.text_input("Şifre", type="password", placeholder="Şifrenizi girin")
    
    # Giriş butonu standart (secondary) kalıyor
    if st.button("Sisteme Giriş Yap", use_container_width=True):
        if "users" in st.secrets:
            kullanici_listesi = st.secrets["users"]
            
            if kadi in kullanici_listesi and kullanici_listesi[kadi] == sifre: 
                st.session_state['logged_in'] = True
                st.session_state['kullanici_adi'] = kadi.capitalize() 
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")
        else:
            st.error("Sistem Hatası: Secrets içinde [users] bloğu bulunamadı.")
            
    st.markdown('</div>', unsafe_allow_html=True)

# --- 2. ANA UYGULAMA (GİRİŞ YAPILDIYSA) ---
else:
    # Kurumsal Üst Bilgi (Header)
    st.markdown(f"""
        <div class="erp-header">
            <p class="erp-title">BRN WMS Enterprise</p>
            <p class="erp-user">Aktif Kullanıcı: {st.session_state['kullanici_adi']}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- ANA MENÜ (TILE EKRANI) ---
    if st.session_state['page'] == 'main':
        st.subheader("Uygulama Menüsü")
        st.write("") 
        
        # 1. SATIR (use_container_width ve type="primary" ile simetri sağlandı)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📦\nMal Kabul", type="primary", use_container_width=True):
                st.session_state['page'] = 'mal_kabul'
                st.rerun()
        with col2:
            if st.button("✂️\nBlok & Rulo Kesim", type="primary", use_container_width=True):
                st.session_state['page'] = 'blok_kesim'
                st.rerun()
        with col3:
            if st.button("🏗️\nÜretim Hazırlık", type="primary", use_container_width=True):
                st.session_state['page'] = 'uretim'
                st.rerun()

        st.write("") # Boşluk
        
        # 2. SATIR
        col4, col5, col6 = st.columns(3)
        with col4:
            if st.button("📍\nStok & Adresleme", type="primary", use_container_width=True):
                st.session_state['page'] = 'stok'
                st.rerun()
        with col5:
            if st.button("📊\nDepo Sayım", type="primary", use_container_width=True):
                st.session_state['page'] = 'sayim'
                st.rerun()
        with col6:
            if st.button("📈\nRaporlar", type="primary", use_container_width=True):
                st.session_state['page'] = 'rapor'
                st.rerun()
                
        # Çıkış Yap Butonu (Standart boyutlarda solda duracak)
        st.divider()
        col_cikis, _ = st.columns([1, 4]) # Sola dayalı küçük buton için
        with col_cikis:
            if st.button("🚪 Güvenli Çıkış Yap", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['kullanici_adi'] = ""
                st.rerun()

    # --- MODÜL SAYFALARI YÖNLENDİRMELERİ ---

    elif st.session_state['page'] == 'mal_kabul':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        teslim_alma.run(conn)

    elif st.session_state['page'] == 'blok_kesim':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        blok_kesim.run_blok_kesim(conn)

    elif st.session_state['page'] == 'uretim':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        modul_uretim.goster() # Hatanın çözüldüğü kısım

    elif st.session_state['page'] == 'stok':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        modul_stok.run(conn) 

    elif st.session_state['page'] == 'sayim':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        modul_sayim.run(conn) 

    elif st.session_state['page'] == 'rapor':
        if st.button("⬅️ Ana Menüye Dön"):
            st.session_state['page'] = 'main'
            st.rerun()
        st.divider()
        modul_rapor.run(conn)
