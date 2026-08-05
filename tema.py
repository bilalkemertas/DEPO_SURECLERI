"""
tema.py
────────────────────────────────────────────────────────────────
Merkezi SAP Fiori / Horizon esintili, turkuaz vurgulu arayüz teması.
Her modül (app.py, modul_sayim.py, modul_stok.py, teslim_alma.py, vb.)
bu dosyayı import edip aynı görünümü ve aynı bileşenleri kullanır.
Böylece CSS her yerde ayrı ayrı yazılmaz, TEK YERDEN yönetilir.

Kullanım (her modülün en üstünde):
    import tema
    tema.uygula()          # sayfa açılışında bir kez çağrılır

    tema.baslik_bari("Depo Sayım", st.session_state.get('kullanici_adi', ''))
    tema.kpi_satiri([("SKU Çeşitliliği", 128), ("Toplam Stok", "12.450")])
    tema.durum_rozeti("Açık")      # veya "Tamamlandı" / "Bloke" / "Uyarı"
────────────────────────────────────────────────────────────────
"""

import streamlit as st

# ══════════════════════════════════════════════════════════════
# RENK PALETİ (SAP Fiori Horizon esintili, turkuaz ana renk)
# ══════════════════════════════════════════════════════════════
RENK = {
    "ana": "#0F828C",           # Turkuaz - ana marka rengi (buton, başlık barı)
    "ana_koyu": "#0B6169",      # Hover / vurgulu durum
    "ana_acik": "#E3F3F4",      # Açık turkuaz - arka plan vurgusu, seçili satır
    "yuzey": "#FFFFFF",         # Kart/panel arka planı
    "yuzey_gri": "#F5F7F8",     # Sayfa arka planı
    "kenarlik": "#D5DEE0",      # Kart/kutu kenarlığı
    "metin": "#1D2D32",         # Ana metin rengi
    "metin_soluk": "#6A7C80",   # İkincil metin (etiket, açıklama)
    "basari": "#1E8A44",        # Yeşil - Tamamlandı / Kullanılabilir
    "uyari": "#E9730C",         # Turuncu - İncelemede / Bekliyor
    "hata": "#BB0000",          # Kırmızı - Hasarlı / Hata
    "bilgi": "#0A6ED1",         # Mavi - bilgi mesajları
}

FONT = "'72', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"  # '72' = SAP'ın kendi fontu (varsa)


def uygula():
    """Sayfanın genel SAP Horizon/turkuaz temasını uygular. Her ekranın başında BİR KEZ çağrılır."""
    st.markdown(f"""
    <style>
    /* ── GENEL FONT VE ZEMİN ─────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: {FONT} !important;
        font-size: 11pt !important;
        color: {RENK["metin"]} !important;
    }}
    .stApp {{
        background-color: {RENK["yuzey_gri"]} !important;
    }}

    h1, h2, h3 {{
        font-weight: 700 !important;
        color: {RENK["metin"]} !important;
    }}

    .block-container {{
        padding: 1rem 1.2rem !important;
        max-width: 100% !important;
    }}
    header {{ visibility: hidden; height: 0 !important; }}
    footer {{ visibility: hidden; height: 0 !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}

    /* ── SATIR ARASI BOŞLUK (üst üste binmeyi önler) ─────────── */
    [data-testid="stVerticalBlock"] {{ gap: 0.6rem !important; }}
    .element-container {{ margin-bottom: 8px !important; }}

    /* ── İKON FONTU İSTİSNASI (ok/chevron ikonlarının bozulmaması) */
    [data-testid="stIconMaterial"],
    span[class*="material-symbols"],
    span[class*="material-icons"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }}

    /* ── KARTLAR / PANELLER (st.container(border=True)) ──────── */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {RENK["yuzey"]} !important;
        border: 1px solid {RENK["kenarlik"]} !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }}

    /* ── EXPANDER ─────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        border: 1px solid {RENK["kenarlik"]} !important;
        border-radius: 8px !important;
        background-color: {RENK["yuzey"]} !important;
    }}
    [data-testid="stExpander"] summary {{
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        line-height: 1.4 !important;
        padding: 8px 12px !important;
        font-weight: 600 !important;
        color: {RENK["ana"]} !important;
    }}
    [data-testid="stExpander"] summary p {{
        margin: 0 !important;
        white-space: normal !important;
    }}

    /* ── GİRİŞ ALANLARI (etiket kutunun ÜSTÜNDE - taşma yok) ──── */
    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stSelectbox"] label {{
        font-weight: 600 !important;
        color: {RENK["metin_soluk"]} !important;
        font-size: 10pt !important;
        margin-bottom: 2px !important;
    }}
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="select"] {{
        border-radius: 6px !important;
        border: 1px solid {RENK["kenarlik"]} !important;
    }}
    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus {{
        border-color: {RENK["ana"]} !important;
        box-shadow: 0 0 0 1px {RENK["ana"]} !important;
    }}

    /* ── BUTONLAR (Primary = turkuaz dolu, Secondary = turkuaz çerçeve) */
    button[kind="primary"], .stButton>button {{
        min-height: 42px !important;
        height: auto !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 11pt !important;
        line-height: 1.3 !important;
        white-space: normal !important;
        padding: 8px 14px !important;
        background-color: {RENK["ana"]} !important;
        color: #FFFFFF !important;
        border: 1px solid {RENK["ana"]} !important;
        transition: all 0.15s ease !important;
    }}
    button[kind="primary"]:hover, .stButton>button:hover {{
        background-color: {RENK["ana_koyu"]} !important;
        border-color: {RENK["ana_koyu"]} !important;
    }}
    button[kind="secondary"] {{
        min-height: 38px !important;
        height: auto !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
        background-color: {RENK["yuzey"]} !important;
        color: {RENK["ana"]} !important;
        border: 1px solid {RENK["ana"]} !important;
    }}
    button[kind="secondary"]:hover {{
        background-color: {RENK["ana_acik"]} !important;
    }}

    /* ── METRİK KUTULARI (KPI) ────────────────────────────────── */
    .stMetric {{
        background-color: {RENK["yuzey"]} !important;
        padding: 10px !important;
        border-radius: 8px !important;
        border-left: 4px solid {RENK["ana"]} !important;
        border-top: 1px solid {RENK["kenarlik"]} !important;
        border-right: 1px solid {RENK["kenarlik"]} !important;
        border-bottom: 1px solid {RENK["kenarlik"]} !important;
    }}
    .stMetric [data-testid="stMetricValue"] {{
        font-size: 16pt !important;
        font-weight: 700 !important;
        color: {RENK["ana"]} !important;
    }}
    .stMetric [data-testid="stMetricLabel"] {{
        font-size: 9pt !important;
        color: {RENK["metin_soluk"]} !important;
    }}

    /* ── ÜST BAŞLIK BARI (tema.baslik_bari ile kullanılır) ────── */
    .erp-header {{
        background-color: {RENK["ana"]};
        color: white;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .erp-title {{ margin: 0; font-size: 13pt !important; color: white !important; font-weight: 700 !important; letter-spacing: 0.3px; }}
    .erp-user {{ margin: 0; font-size: 9.5pt !important; color: white !important; opacity: 0.9; }}

    /* ── DURUM ROZETLERİ (tema.durum_rozeti ile kullanılır) ───── */
    .rozet {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 9pt;
        font-weight: 700;
    }}
    .rozet-basari {{ background-color: #E4F4E8; color: {RENK["basari"]}; }}
    .rozet-uyari {{ background-color: #FDEEDD; color: {RENK["uyari"]}; }}
    .rozet-hata {{ background-color: #FBE5E5; color: {RENK["hata"]}; }}
    .rozet-bilgi {{ background-color: {RENK["ana_acik"]}; color: {RENK["ana"]}; }}
    </style>
    """, unsafe_allow_html=True)


def baslik_bari(baslik: str, kullanici: str = ""):
    """Her ekranın en üstüne SAP tarzı turkuaz başlık barı basar."""
    kullanici_html = f'<p class="erp-user">👤 {kullanici}</p>' if kullanici else ""
    st.markdown(f"""
    <div class="erp-header">
        <p class="erp-title">🏢 {baslik}</p>
        {kullanici_html}
    </div>
    """, unsafe_allow_html=True)


def kpi_satiri(kpiler: list):
    """
    KPI kutularını yan yana basar.
    kpiler: [("Etiket", deger), ("Etiket2", deger2), ...]
    """
    cols = st.columns(len(kpiler))
    for col, (etiket, deger) in zip(cols, kpiler):
        with col:
            st.metric(etiket, deger)


def durum_rozeti(durum: str) -> str:
    """
    Durum metnine göre renkli HTML rozet üretir (st.markdown(..., unsafe_allow_html=True) ile basılmalı).
    Örnek: st.markdown(tema.durum_rozeti("Açık"), unsafe_allow_html=True)
    """
    eslesme = {
        "açık": "rozet-bilgi", "aktif": "rozet-bilgi", "kullanılabilir": "rozet-basari",
        "tamamlandı": "rozet-basari", "başarılı": "rozet-basari",
        "bekliyor": "rozet-uyari", "incelemede": "rozet-uyari", "beklemede": "rozet-uyari",
        "hasarlı": "rozet-hata", "bloke": "rozet-hata", "hata": "rozet-hata",
    }
    sinif = eslesme.get(str(durum).strip().lower(), "rozet-bilgi")
    return f'<span class="rozet {sinif}">{durum}</span>'


def imza_yazdir():
    """Sayfanın en altına standart imza şeridini basar."""
    st.markdown(f"""
    <div style='text-align: center; color: {RENK["metin_soluk"]}; font-size: 9pt; margin-top: 24px; padding-top: 8px; border-top: 1px solid {RENK["kenarlik"]};'>
        🚀 Bilal Kemertaş | BRN 2026
    </div>
    """, unsafe_allow_html=True)
