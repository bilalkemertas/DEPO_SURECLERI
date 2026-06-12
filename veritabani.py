import pandas as pd
import gspread
import requests
import base64
import json
import streamlit as st
from io import StringIO
"""
Veritabanı İşlemleri
====================

Google Drive (veritabani modülü) ile veri yükleme ve kaydetme.
"""

import streamlit as st
import math
import os
from blok_kesim.data_processor import DataCleaner


def load_sheet(sheet_name: str, conn=None) -> pd.DataFrame:
    """
    Drive'dan veri yükle
    
    Args:
        sheet_name: Sayfa adı (örn: "Stok", "Hareketler", "Sunger_Kesim")
        conn: Veritabanı bağlantısı (isteğe bağlı)
    
    Returns:
        DataFrame (boş ise boş DataFrame döner)
    """
    try:
        import veritabani
        
        try:
            df = veritabani.get_internal_data(sheet_name)
        except AttributeError:
            try:
                df = veritabani.get_data(sheet_name, conn) if conn else veritabani.get_data(sheet_name)
            except Exception as e:
                st.warning(f"⚠️ '{sheet_name}' yükleme hatası: {e}")
                df = None
        
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
        else:
            # Varsayılan boş DataFrame döndür
            if sheet_name == "Sunger_Kesim":
                return pd.DataFrame(columns=[
                    'Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Blok Kodu', 'Blok Adı', 
                    'Plaka Adet', 'Blok Adet', 'Üretilen Plaka Miktarı', 'Kesilen Blok Miktarı'
                ])
            elif sheet_name == "Stok":
                return pd.DataFrame(columns=[
                    'Adres', 'Kod', 'Malzeme_Adi', 'Miktar', 'Birim'
                ])
            elif sheet_name == "Hareketler":
                return pd.DataFrame(columns=[
                    'Tarih', 'İşlem', 'Adres', 'Kod', 'Malzeme_Adi', 'Miktar', 'Birim'
                ])
            else:
                return pd.DataFrame()
    
    except ImportError:
        st.error("❌ 'veritabani' modülü bulunamadı!")
        return pd.DataFrame()


def save_sheet(sheet_name: str, df: pd.DataFrame, conn=None) -> bool:
    """
    Drive'a veri kaydet
    
    Args:
        sheet_name: Sayfa adı
        df: Kaydedilecek DataFrame
        conn: Veritabanı bağlantısı (isteğe bağlı)
    
    Returns:
        Başarılı mı?
    """
    try:
        import veritabani
        
        # DataFrame'i temizle (NaN ve Inf'ler)
        df_clean = DataCleaner.clean_dataframe(df)
        
        success = False
        try:
            veritabani.update_data(sheet_name, df_clean)
            success = True
        except TypeError:
            try:
                veritabani.update_data(sheet_name, df_clean, conn)
                success = True
            except Exception as e:
                st.error(f"❌ '{sheet_name}' kaydedilirken hata: {e}")
        except Exception as e:
            st.error(f"❌ '{sheet_name}' kaydedilirken hata: {e}")
        
        return success
    
    except ImportError:
        st.error("❌ 'veritabani' modülü bulunamadı!")
        return False


def load_matching_matrix() -> pd.DataFrame:
    """
    Eşleştirme matrisini dosyadan yükle
    
    Önce XLSX, sonra CSV dene.
    
    Returns:
        Eşleştirme matris DataFrame
    """
    # XLSX dene
    if os.path.exists("eslesme_matrisi.xlsx"):
        try:
            df = pd.read_excel("eslesme_matrisi.xlsx", dtype=str)
            if not df.empty:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            pass
    
    # CSV dene (Türkçe karakter korumalı)
    if os.path.exists("eslesme_matrisi.csv"):
        encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
        separators = [';', ',', '\t']
        
        for sep in separators:
            for enc in encodings:
                try:
                    df = pd.read_csv("eslesme_matrisi.csv", dtype=str, encoding=enc, sep=sep)
                    if len(df.columns) > 1:  # Doğru ayrıştırıldı
                        df.columns = [str(c).strip() for c in df.columns]
                        return df
                except Exception:
                    continue
        
        # Son çare - UTF-8 ile oku
        try:
            df = pd.read_csv("eslesme_matrisi.csv", dtype=str, encoding='utf-8')
            if not df.empty:
                df.columns = [str(c).strip() for c in df.columns]
                return df
        except Exception:
            pass
    
    st.warning("⚠️ 'eslesme_matrisi.xlsx' veya 'eslesme_matrisi.csv' dosyası bulunamadı!")
    return pd.DataFrame()


def detect_excel_header_row(df_raw: pd.DataFrame) -> int:
    """
    Excel dosyasında başlık satırını tespit et
    
    Args:
        df_raw: Başlıksız DataFrame (header=None ile okunmuş)
    
    Returns:
        Başlık satırı indeksi (0-based)
    """
    for i in range(min(20, len(df_raw))):
        row_str = " ".join(str(val).upper() for val in df_raw.iloc[i].values if pd.notna(val))
        
        # Başlık satırının kriterleri
        has_column_names = any(k in row_str for k in [
            'SİPARİŞ', 'SIPARIS', 'STOK', 'PLAKA', 'KOD', 'ÜRÜN', 'URUN', 'TANIM', 'MALZEME'
        ])
        has_quantity = any(k in row_str for k in [
            'MİKTAR', 'MIKTAR', 'ADET', 'QTY'
        ])
        
        if has_column_names and has_quantity:
            return i
    
    return 0  # Varsayılan olarak ilk satır
