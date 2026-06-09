import streamlit as st
import pandas as pd
import veritabani

def fetch_live_data():
    """
    Veritabanından Stok ve Hareketler tablolarını güncel olarak çeker.
    """
    try:
        stok_df = veritabani.get_internal_data("Stok")
        har_df = veritabani.get_internal_data("Hareketler")
        return stok_df, har_df
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
        return pd.DataFrame(), pd.DataFrame()

def update_stock_and_logs(stok_df, yeni_hareket_df):
    """
    Güncellenen stok tablosunu ve eklenen yeni hareket satırını veritabanına işler.
    """
    try:
        veritabani.update_data("Stok", stok_df)
        
        # Mevcut hareketleri çekip yenisini altına ekleyerek kaydet
        current_har = veritabani.get_internal_data("Hareketler")
        updated_har = pd.concat([current_har, yeni_hareket_df], ignore_index=True)
        veritabani.update_data("Hareketler", updated_har)
        return True
    except Exception as e:
        st.error(f"Yazma Hatası: {e}")
        return False
