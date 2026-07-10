import streamlit as st

def page_ayarlar():
    """Tüm sayfalarda geçerli olacak kurumsal, geniş ve ferah arayüz (UI) ayarları"""
    
    st.markdown("""
    <style>
    /* 1. EKRANI TAM GENİŞLİĞE YAY (Sıkışıklığı İptal Et) */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important; /* Ekranı zorla %100 genişletir */
    }

    /* 2. GEREKSİZ BOŞLUKLARI VE ÇİZGİLERİ TEMİZLE */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* 3. BUTONLARI KURUMSAL VE NİZAMİ YAP (Ne devasa ne de cüce) */
    .stButton>button {
        width: 100% !important;
        border-radius: 8px !important;
        border: 1px solid #11caa0 !important;
        font-size: 16px !important;
        font-weight: bold !important;
        height: 60px !important;
        transition: all 0.3s ease;
        background-color: #ffffff !important;
        color: #0b3c5d !important;
    }
    
    .stButton>button:hover {
        background-color: #11caa0 !important;
        color: white !important;
        border-color: #11caa0 !important;
    }
    
    /* 4. KURUMSAL HEADER DÜZENİ */
    .erp-header {
        background-color: #0b3c5d;
        color: white;
        padding: 15px 25px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .erp-title { margin: 0; font-size: 22px; font-weight: 700; }
    .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }

    /* 5. METRİK KUTULARI (Geniş ekran uyumlu) */
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        border-left: 5px solid #11caa0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

def session_kontrol():
    """Kritik state'lerin başlatılması"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if 'gecici_sayim_listesi' not in st.session_state:
        st.session_state['gecici_sayim_listesi'] = []
    if 'delete_confirm' not in st.session_state:
        st.session_state.delete_confirm = None

def imza_yazdir():
    """Tüm sayfalarda standart imza alanını en alt kısıma ince şerit olarak basar."""
    st.markdown("""
    <div style='text-align: center; color: #a0aec0; font-size: 12px; margin-top: 50px; padding-top: 10px; border-top: 1px solid #e2e8f0;'>
        🚀 Bilal Kemertaş | BRN 2026
    </div>
    """, unsafe_allow_html=True)
