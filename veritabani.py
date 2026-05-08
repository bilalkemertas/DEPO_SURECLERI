import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64
import json
import streamlit as st
from io import StringIO

# --- 1. GÜVENLİK VE AYARLAR ---
# GitHub Ayarları
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO_OWNER = "bilalkemertas"
REPO_NAME = "depo_surecleri"
GITHUB_FILE_PATH = "data/hafiza.csv"

# Google Drive Ayarları
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# --- 2. BAĞLANTI KURULUMU ---
try:
    # Senin paylaştığın secrets formatına ( [connections.gsheets] ) tam uyum:
    gcp_info = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(gcp_info, scopes=SCOPE)
    client = gspread.authorize(creds)
    # Drive'daki ana dosyanın adı
    sheet = client.open("Depo_Veritabani")
except Exception as e:
    st.error(f"⚠️ Bağlantı Hatası: {e}")

# --- 3. GITHUB (HAFIZA) FONKSİYONLARI ---

def get_github_data():
    """GitHub'daki hafiza.csv dosyasını okur."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()
        decoded_data = base64.b64decode(content['content']).decode('utf-8')
        return pd.read_csv(StringIO(decoded_data))
    else:
        # Dosya yoksa şablon döner
        return pd.DataFrame(columns=['SAS_No', 'Parti No', 'Malzeme Kodu', 'Teslimat Miktarı'])

def update_github_data(df, commit_message="Veri guncellendi"):
    """GitHub'daki hafiza.csv dosyasını günceller."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    csv_content = df.to_csv(index=False)
    encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": commit_message,
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    response = requests.put(url, headers=headers, data=json.dumps(payload))
    return response.status_code in [200, 201]

# --- 4. GOOGLE DRIVE (ANA VERİ) FONKSİYONLARI ---

def get_internal_data(sheet_name):
    """Drive üzerindeki herhangi bir sekmeyi (Stok, Satin_Alma vb.) DataFrame olarak çeker."""
    try:
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def update_data(sheet_name, df):
    """Drive üzerindeki tabloyu tamamen günceller."""
    try:
        worksheet = sheet.worksheet(sheet_name)
        worksheet.clear()
        # NaN değerleri boş stringe çevir (Google Sheet hatası almamak için)
        df_filled = df.fillna("")
        worksheet.update([df_filled.columns.values.tolist()] + df_filled.values.tolist())
        return True
    except Exception as e:
        st.error(f"Güncelleme hatası: {e}")
        return False

def get_katalog():
    """Drive'daki Katalog sekmesinden ürün listesini çeker."""
    df = get_internal_data("Katalog")
    if not df.empty:
        return (df['Kod'].astype(str) + " | " + df['İsim'].astype(str)).tolist()
    return []
