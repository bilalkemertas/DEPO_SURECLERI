import os
import pandas as pd
from .data_processor import parse_ozellik

def load_local_eslesme_matrisi():
    """
    Local'deki eslesme_matrisi.csv dosyasını çoklu encoding korumasıyla yükler.
    """
    csv_path = "eslesme_matrisi.csv"
    if os.path.exists(csv_path):
        encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
        for enc in encodings:
            try:
                df = pd.read_csv(csv_path, sep=';', encoding=enc)
                if not df.empty:
                    return df
            except:
                continue
    return pd.DataFrame()

def karakter_match(plaka, blok):
    """
    DNS ve kalite kelimeleri bazında esnek eşleşme kontrolü.
    """
    if not plaka or not blok: 
        return False
        
    p = parse_ozellik(plaka)
    b = parse_ozellik(blok)
    
    if p["dns"] is not None and b["dns"] is not None:
        if p["dns"] != b["dns"]: 
            return False
            
    ortak = p["kelimeler"].intersection(b["kelimeler"])
    if len(p["kelimeler"]) > 0 and len(b["kelimeler"]) > 0 and len(ortak) == 0:
        return False
        
    return True
