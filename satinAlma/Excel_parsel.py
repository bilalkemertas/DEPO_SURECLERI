"""
Excel Ayrıştırıcı - Safaş Excel dosyasını parse et
Eşleşmeler sayfasından Stok Kodu bulunup barcode verisi oluştur
"""

import openpyxl
import io
import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .config import (
    HACIM_BOLENI,
    ESLESMELER_COLUMNS,
    TEDARIKCI_AD,
)

logger = logging.getLogger(__name__)


class ExcelAyrıştırıcı:
    """Safaş Excel dosyasını ayrıştır ve veri çıkart"""
    
    def __init__(self):
        self.tedarikci = TEDARIKCI_AD
    
    def safas_excel_ayristic(self, excel_bytes: bytes) -> Tuple[List[Dict], Dict]:
        """
        Safaş Excel dosyasını ayrıştır.
        
        Beklenen sütunlar:
        A: İrsaliye Numarası
        B: Teslimat No
        C: Sipariş Veren Adı
        D: Malzeme (Ürün Kodu)
        E: Malzeme Tanımı
        F: En Bilgisi (cm)
        G: Boy Bilgisi (cm)
        H: Yükseklik Bilgisi (cm)
        I: Parti içi adet
        J: Parti (Plaka No)
        
        Args:
            excel_bytes: Excel dosyası bytes
            
        Dönüş:
            Tuple[List[Dict], Dict]:
                - satırlar: Ayrıştırılan satırlar (barcode verisi içeren)
                - meta_veri: İrsaliye bilgileri
        """
        try:
            wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
            ws = wb.active
            
            satırlar = []
            meta_veri = {}
            
            for idx, satir in enumerate(ws.iter_rows(min_row=2, values_only=False), start=2):
                try:
                    # Sütunları oku
                    irsaliye_no = satir[0].value
                    teslimat_no = satir[1].value
                    siparis_veren = satir[2].value
                    urun_kodu = satir[3].value
                    urun_adi = satir[4].value
                    en = satir[5].value if satir[5].value else 0
                    boy = satir[6].value if satir[6].value else 0
                    yukseklik = satir[7].value if satir[7].value else 0
                    parti_ici_adet = int(satir[8].value) if satir[8].value else 0
                    parti_no = satir[9].value
                    
                    # Meta veri (ilk satırdan)
                    if idx == 2:
                        meta_veri = {
                            'irsaliye_no': irsaliye_no,
                            'teslimat_no': teslimat_no,
                            'siparis_veren': siparis_veren,
                            'birden_fazla_satir': False
                        }
                    
                    # Hacim hesapla: (En × Boy × Yükseklik) / 1,000,000 = m³
                    hacim_m3 = round(
                        (en * boy * yukseklik) / HACIM_BOLENI, 3
                    ) if en and boy and yukseklik else 0
                    
                    # Barcode verisi oluştur (mal kabul ekranında kullanılacak)
                    barcode_verisi = {
                        'urun_kodu': str(urun_kodu),
                        'boyutlar': f'{en}x{boy}x{yukseklik}',
                        'parti_no': str(parti_no),
                        'adet': parti_ici_adet,
                        'hacim_m3': hacim_m3,
                        'urun_adi': urun_adi,
                        'tarih': datetime.now().strftime('%d.%m.%Y'),
                        'tedarikci': self.tedarikci
                    }
                    
                    satir_verisi = {
                        'irsaliye_no': irsaliye_no,
                        'teslimat_no': teslimat_no,
                        'urun_kodu': str(urun_kodu),
                        'urun_adi': urun_adi,
                        'en_cm': en,
                        'boy_cm': boy,
                        'yukseklik_cm': yukseklik,
                        'hacim_m3': hacim_m3,
                        'parti_no': str(parti_no),
                        'adet': parti_ici_adet,
                        'barcode_verisi': barcode_verisi,
                        'stok_kodu': None,  # Lookup'tan gelecek
                        'brn_urun_adi': None,  # Lookup'tan gelecek
                        'satir_index': idx - 1  # 0-based
                    }
                    
                    satırlar.append(satir_verisi)
                
                except Exception as e:
                    logger.warning(f"Satır {idx} ayrıştırma hatası: {str(e)}")
                    continue
            
            # Meta veri: Birden fazla satır mı?
            meta_veri['birden_fazla_satir'] = len(satırlar) > 1
            meta_veri['satir_sayisi'] = len(satırlar)
            
            logger.info(f"✓ {len(satırlar)} satır başarıyla ayrıştırıldı")
            return satırlar, meta_veri
        
        except Exception as e:
            logger.error(f"Excel ayrıştırma hatası: {str(e)}")
            raise ValueError(f"Excel ayrıştırma başarısız: {str(e)}")
    
    def stok_kodu_bul(self, urun_kodu: str, eslesmeler_verisi: List[Dict]) -> Optional[Dict]:
        """
        Eşleşmeler sayfasından Stok Kodu + BRN Ürün Adı bulmasını yap.
        
        Args:
            urun_kodu: Ürün Kodu (D023190570STD000)
            eslesmeler_verisi: Eşleşmeler sayfasından çekilen veriler
            
        Dönüş:
            Dict: {'stok_kodu': str, 'brn_urun_adi': str}
            None: Eşleşme bulunamadı
        """
        if not eslesmeler_verisi:
            logger.warning("Eşleşmeler verisi boş")
            return None
        
        for esl in eslesmeler_verisi:
            if str(esl.get(ESLESMELER_COLUMNS['urun_kodu'], '')).strip() == str(urun_kodu).strip():
                sonuc = {
                    'stok_kodu': esl.get(ESLESMELER_COLUMNS['stok_kodu']),
                    'brn_urun_adi': esl.get(ESLESMELER_COLUMNS['brn_urun_adi'])
                }
                logger.info(f"✓ Ürün Kodu {urun_kodu} → Stok Kodu {sonuc['stok_kodu']}")
                return sonuc
        
        logger.warning(f"⚠️ Ürün Kodu {urun_kodu} eşleşmesi bulunamadı")
        return None
    
    def satırları_zenginleştir(self, satırlar: List[Dict], eslesmeler_verisi: List[Dict]) -> List[Dict]:
        """
        Satırları Eşleşmeler sayfasından lookup edilerek zenginleştir.
        
        Args:
            satırlar: Ayrıştırıcıdan gelen satırlar
            eslesmeler_verisi: Eşleşmeler sayfasından çekilen veriler
            
        Dönüş:
            List[Dict]: Lookup verisiyle zenginleştirilmiş satırlar
        """
        zenginlestirilmis = []
        
        for satir in satırlar:
            lookup_sonucu = self.stok_kodu_bul(satir['urun_kodu'], eslesmeler_verisi)
            
            if lookup_sonucu:
                satir['stok_kodu'] = lookup_sonucu['stok_kodu']
                satir['brn_urun_adi'] = lookup_sonucu['brn_urun_adi']
                satir['lookup_durumu'] = 'BASARILI'
            else:
                satir['lookup_durumu'] = 'BULUNAMADI'
                satir['stok_kodu'] = None
                satir['brn_urun_adi'] = None
            
            zenginlestirilmis.append(satir)
        
        return zenginlestirilmis
    
    def satırları_doğrula(self, satırlar: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Ayrıştırılan satırları doğrula. Hatalı satırları ayır.
        
        Args:
            satırlar: Ayrıştırılan satırlar
            
        Dönüş:
            Tuple[List, List]: (geçerli_satırlar, hata_satırları)
        """
        gecerli = []
        hatalar = []
        
        for satir in satırlar:
            satir_hatalari = []
            
            # Ürün Kodu
            if not satir.get('urun_kodu'):
                satir_hatalari.append('Ürün Kodu boş')
            
            # Parti No
            if not satir.get('parti_no'):
                satir_hatalari.append('Parti No boş')
            
            # Hacim
            if satir.get('hacim_m3', 0) == 0:
                satir_hatalari.append('Hacim 0 (boyutlar kontrol edin)')
            
            # Lookup durumu
            if satir.get('lookup_durumu') == 'BULUNAMADI':
                satir_hatalari.append(f'Stok Kodu bulunamadı ({satir.get("urun_kodu")})')
            
            if satir_hatalari:
                hatalar.append({
                    'satir_index': satir['satir_index'],
                    'urun_kodu': satir.get('urun_kodu'),
                    'hatalar': satir_hatalari,
                })
            else:
                gecerli.append(satir)
        
        logger.info(f"✓ {len(gecerli)} geçerli satır, {len(hatalar)} hatalı satır")
        return gecerli, hatalar


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("✓ Excel Ayrıştırıcı modülü hazır")
