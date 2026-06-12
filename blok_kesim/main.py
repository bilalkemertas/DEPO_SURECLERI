"""
Blok & Rulo Sünger Kesim Otomasyonu
Modüler mimari ile optimize edilmiş ana yürütücü.
"""

import streamlit as st
import pandas as pd
import math
from datetime import datetime

# GÖRELİ (RELATIVE) IMPORTLAR - Döngüsel bağımlılığı (circular import) çözer
from .state import init_blok_kesim_state
from .matching import load_local_eslesme_matrisi, karakter_match
from .database import fetch_live_data, update_stock_and_logs
from .data_processor import ayikla_karakter_ve_olcu, plaka_sayisi_hesapla, safe_float

# Dış modül importu
import veritabani

def run_blok_kesim(conn):
    """
    Ana blok kesim işlem ekranı
    """
    # 1. State Yönetim Mekanizmasını Başlat
    init_blok_kesim_state()
    
    # 2. Yerel Eşleşme Matrisini Belleğe Al (Cache Koruma)
    if 'eslesme_df' not in st.session_state or st.session_state.eslesme_df is None:
        st.session_state.eslesme_df = load_local_eslesme_matrisi()
    
    # 3. Veritabanından Stok ve Hareketler Verilerini Çek
    stok_df, har_df = fetch_live_data()
    if stok_df.empty:
        st.warning("⚠️ Stok verisi veritabanından yüklenemedi veya tablo boş.")
        return
    
    st.subheader("🧱 Blok & Rulo Sünger Kesim Otomasyonu")
    
    # --- ARAYÜZ MANTIĞI ---
    # İş emri yükleme ve barkod okutma gibi operasyonel kısım
    # ... mevcut mantığınla devam eder ...
