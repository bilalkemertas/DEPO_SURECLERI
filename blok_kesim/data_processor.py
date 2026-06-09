import re
import pandas as pd

def ayikla_karakter_ve_olcu(text):
    """
    Zırhlı Ayıklama Motoru: Gelen metinden boy, en, kalınlık ve kalite karakterini ayıklar.
    Asla None dönmez.
    """
    default_return = {"boy": 0.0, "en": 0.0, "kalinlik": 0.0, "karakter": str(text) if text else ""}
    if pd.isna(text) or str(text).strip() == "":
        return default_return
        
    t = str(text).upper().replace(",", ".").strip()
    
    # 3'lü ölçü kombinasyonunu ara (Örn: 200X100X3.5 veya 188x88x18,5)
    olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
    
    if olcu_uzun:
        try:
            boy = float(olcu_uzun.group(1))
            en = float(olcu_uzun.group(2))
            kalinlik = float(olcu_uzun.group(3))
            start_idx = olcu_uzun.start()
            karakter = t[:start_idx].strip()
            return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}
        except Exception:
            return default_return
            
    return default_return

def parse_ozellik(text):
    """
    Kalite kelimelerini ve DNS (yoğunluk) bilgisini ayıklar.
    """
    if pd.isna(text) or str(text).strip() == "":
        return {"dns": None, "kelimeler": set()}
    t = str(text).upper().strip()
    
    dns_match = re.search(r'(\d+)\s*DNS', t)
    
    # Gereksiz kelimeleri temizle
    temiz_t = re.sub(r'\d+\s*DNS', '', t)
    temiz_t = re.sub(r'\d+(?:\.\d+)?\s*[Xx]\s*\d+(?:\.\d+)?(?:\s*[Xx]\s*\d+(?:\.\d+)?)?', '', temiz_t)
    
    kelimeler = set([w.strip() for w in re.split(r'[\s\+\-\*\/,;\.]', temiz_t) if len(w.strip()) > 1])
    
    # Agresif filtre kelimelerini ele
    yasakli = {"SUNGER", "PU", "BLOK", "PLAKA", "TAKOZ", "RULO", "NORMAL", "DUZ"}
    kelimeler = kelimeler.difference(yasakli)
    
    return {
        "dns": int(dns_match.group(1)) if dns_match else None,
        "kelimeler": kelimeler
    }

def plaka_sayisi_hesapla(plaka, blok):
    """
    Plaka ebatlarının ham blok ölçülerine göre verimini hesaplar.
    """
    if not plaka or not blok: 
        return 0
    if plaka.get('boy', 0) == 0 or plaka.get('en', 0) == 0: 
        return 0
        
    adet_boy_1 = int(blok.get('boy', 0) // plaka['boy'])
    adet_en_1  = int(blok.get('en', 0) // plaka['en'])
    verim_1 = adet_boy_1 * adet_en_1
    
    # Alternatif yön (90 derece döndürülmüş) kontrolü
    adet_boy_2 = int(blok.get('boy', 0) // plaka['en'])
    adet_en_2  = int(blok.get('en', 0) // plaka['boy'])
    verim_2 = adet_boy_2 * adet_en_2
    
    return max(verim_1, verim_2)

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0
