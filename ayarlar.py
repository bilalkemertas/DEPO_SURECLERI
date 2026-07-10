import streamlit as st

def page_ayarlar():
    """Tüm sayfalarda geçerli olacak kurumsal, kompakt ve endüstriyel WMS arayüz ayarları"""
    
    st.markdown("""
    <style>
    /* 1. KATI 12 PUNTO KURALI VE ENDÜSTRİYEL FONT */
    html, body, [class*="css"], p, span, div, label, input, select, button {
        font-size: 11pt !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* BAŞLIKLAR MAKSİMUM 12 PUNTO (Şık ve net) */
    h1, h2, h3, .erp-title { 
        font-size: 12pt !important; 
        font-weight: bold !important;
        margin-top: 4px !important; 
        margin-bottom: 6px !important; 
        padding: 0 !important;
        color: #0b3c5d !important;
    }

    /* 2. EKRAN BOŞLUKLARINI SIFIRA YAKIN TUT (Scroll eziyetini bitirir) */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    /* ÜST VE ALT STANDART MENÜLERİ GİZLE */
    header {visibility: hidden; height: 0 !important;}
    footer {visibility: hidden; height: 0 !important;}
    [data-testid="stHeader"] {display: none !important;}

    /* SATIR ARASI GEREKSİZ SARKMALARI ÖNLE */
    [data-testid="stVerticalBlock"] { gap: 0.4rem !important; }

    /* 3. KOMPAKT STANDART BUTONLAR */
    .stButton>button {
        width: 100% !important;
        border-radius: 4px !important;
        border: 1px solid #11caa0 !important;
        font-size: 11pt !important;
        font-weight: bold !important;
        height: 35px !important; /* Standart basılabilir terminal yüksekliği */
        padding: 0px 5px !important;
        transition: all 0.2s ease;
        background-color: #ffffff !important;
        color: #0b3c5d !important;
    }
    
    .stButton>button:hover {
        background-color: #11caa0 !important;
        color: white !important;
    }
    
    /* 4. MİNİMALİST SIK_ŞIK HEADER DÜZENİ */
    .erp-header {
        background-color: #0b3c5d;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .erp-user { margin: 0; font-size: 10pt !important; opacity: 0.95; }

    /* 5. VERİ SIKIŞTIRILMIŞ METRİK KUTULARI */
    .stMetric {
        background-color: #f8f9fa;
        padding: 6px !important;
        border-radius: 4px;
        border-left: 4px solid #11caa0;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 12pt !important;
        font-weight: bold !important;
    }
    .stMetric [data-testid="stMetricLabel"] {
        font-size: 9pt !important;
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
    <div style='text-align: center; color: #a0aec0; font-size: 9pt; margin-top: 20px; padding-top: 5px; border-top: 1px solid #e2e8f0;'>
        🚀 Bilal Kemertaş | BRN 2026
    </div>
    """, unsafe_allow_html=True)
