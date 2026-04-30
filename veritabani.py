import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# MERKEZİ ZAMAN YÖNETİMİ (UTC+3 TÜRKİYE)
# ==========================================
def get_now():
    """Tüm sistem için merkezi Türkiye Saati (UTC+3) üretir."""
    return datetime.now() + timedelta(hours=3)

def get_now_str():
    """Loglama için formatlanmış zaman metni döner (Örn: 30.04.2026 14:00)."""
    return get_now().strftime("%d.%m.%Y %H:%M")

def get_local_time():
    """Eski fonksiyonlarla uyumluluk için (Y-m-d formatı)."""
    return get_now().strftime("%Y-%m-%d %H:%M")

# ==========================================
# VERİ BAĞLANTI MOTORLARI
# ==========================================
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def get_sheet_url():
    return st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        conn = get_conn()
        df = conn.read(spreadsheet=get_sheet_url(), worksheet=worksheet_name, ttl=0)
        df.columns = df.columns.str.strip()
        
        # Kodları string yapıp sonlarındaki .0'ları silerek eşleşme sorunlarını çözüyoruz
        if 'Kod' in df.columns:
            df['Kod'] = df['Kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        if 'kod' in df.columns:
            df['kod'] = df['kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
            
        return df.fillna("-")
    except:
        return pd.DataFrame()

def update_data(worksheet_name, data):
    conn = get_conn()
    conn.update(spreadsheet=get_sheet_url(), worksheet=worksheet_name, data=data)

def get_katalog():
    df = get_internal_data("Urun_Listesi")
    if df.empty: df = get_internal_data("ürün listesi")
    if df.empty: df = get_internal_data("Ürün Listesi")
    
    if not df.empty and 'kod' in df.columns and 'isim' in df.columns:
        df['Arama'] = df['kod'].astype(str) + " | " + df['isim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    
    df_stok = get_internal_data("Stok")
    if not df_stok.empty and 'Kod' in df_stok.columns and 'İsim' in df_stok.columns:
        df_stok['Arama'] = df_stok['Kod'].astype(str) + " | " + df_stok['İsim'].astype(str)
        return sorted(df_stok['Arama'].unique().tolist())
            
    return []
