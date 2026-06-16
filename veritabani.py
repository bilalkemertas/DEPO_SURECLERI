import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st


def connect_gsheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )

    client = gspread.authorize(creds)
    return client.open_by_key(st.secrets["SHEET_ID"])


def get_internal_data(sheet_name):
    try:
        sh = connect_gsheet()
        worksheet = sh.worksheet(sheet_name)

        data = worksheet.get_all_records()

        if not data:
            return pd.DataFrame()

        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Veri okuma hatası: {e}")
        return pd.DataFrame()


def update_data(sheet_name, df):
    try:
        sh = connect_gsheet()

        try:
            worksheet = sh.worksheet(sheet_name)
        except:
            worksheet = sh.add_worksheet(title=sheet_name, rows="1000", cols="50")

        df_filled = df.fillna("")

        worksheet.clear()
        worksheet.update(
            [df_filled.columns.tolist()] + df_filled.values.tolist()
        )

        return True

    except Exception as e:
        st.error(f"Veri yazma hatası: {e}")
        return False


def get_data(sheet_name, conn=None):
    return get_internal_data(sheet_name)
