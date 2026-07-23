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


def update_stock_and_logs(stok_df, mevcut_hareket_df, yeni_hareket_df):
    """
    Güncellenen stok tablosunu ve eklenen yeni hareket satırını veritabanına işler.

    NOT: main.py bu fonksiyonu 3 parametreyle çağırıyor
    (stok_df, st.session_state.har_data, yeni_log) - imza buna göre düzeltildi.
    """
    try:
        veritabani.update_data("Stok", stok_df)

        # Mevcut hareketleri (parametre olarak gelen) yenisiyle birleştirip kaydet
        if mevcut_hareket_df is None or mevcut_hareket_df.empty:
            mevcut_hareket_df = veritabani.get_internal_data("Hareketler")
        updated_har = pd.concat([mevcut_hareket_df, yeni_hareket_df], ignore_index=True)
        veritabani.update_data("Hareketler", updated_har)
        return True
    except Exception as e:
        st.error(f"Yazma Hatası: {e}")
        return False
