import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64
import json
import streamlit as st

# --- AYARLAR ---
# GitHub Token'ını Streamlit Secrets'a eklemelisin (Setting -> Secrets)
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO_OWNER = "bilalkemertas" # Kendi GitHub kullanıcı adın
REPO_NAME = "depo_surecleri"  # Repo ismin
FILE_PATH = "data/hafiza.csv" # GitHub'daki dosya yolu

# --- GOOGLE DRIVE BAĞLANTISI (Mevcut Yapın) ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("DEPO_VERITABANI") # Senin ana dosya adın

# --- GITHUB FONKSİYONLARI ---

def get_github_data():
    """GitHub'dan CSV dosyasını çeker ve DataFrame döner."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content = response.json()
        decoded_data = base64.b64decode(content['content']).decode('utf-8')
        from io import StringIO
        return pd.read_csv(StringIO(decoded_data))
    else:
        # Dosya yoksa veya hata varsa boş şablon dön
        return pd.DataFrame(columns=['SAS_No', 'Parti No', 'Malzeme Kodu', 'Teslimat Miktarı'])

def update_github_data(df, commit_message="Veri guncellendi"):
    """DataFrame'i CSV'ye çevirip GitHub'a commit atar."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    # Önce mevcut dosyanın SHA değerini almamız lazım (GitHub kuralı)
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

# --- MEVCUT DRIVE FONKSİYONLARI (Kısaltmadan ekliyorum) ---

def get_internal_data(sheet_name):
    """Drive'daki diğer tabloları çeker (Stok, Hareketler vb.)"""
    worksheet = sheet.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def update_data(sheet_name, df):
    """Drive'daki tabloları günceller."""
    worksheet = sheet.worksheet(sheet_name)
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def get_katalog():
    """Ürün listesini döner."""
    df = get_internal_data("Katalog")
    return (df['Kod'] + " | " + df['İsim']).tolist()
