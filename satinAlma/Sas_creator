"""
SAS Oluşturucu - Otomatik SAS No üretimi ve Satin_Alma sayfasına yazma
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from .config import (
    SAS_STATUS_ACIK,
    STOK_BIRIM_M3,
    SATIN_ALMA_COLUMNS,
)

logger = logging.getLogger(__name__)


class SasOlusturucu:
    """SAS nesneleri oluştur ve Satin_Alma sayfasına yazacak format hazırla"""
    
    def __init__(self):
        self.sas_prefix = "SAS"
        self.sas_numara_uzunlugu = 7  # SAS-0000001
    
    def son_sas_no_bul(self, satin_alma_verisi: List[Dict]) -> int:
        """
        Satin_Alma sayfasından son SAS No'yu bulup numarayı döndür.
        
        Args:
            satin_alma_verisi: Satin_Alma sayfasından çekilen tüm veriler
            
        Dönüş:
            int: Son SAS sayısı (örn: 1, 2, 100...)
        """
        if not satin_alma_verisi:
            return 0
        
        sas_numaralari = []
        
        for satir in satin_alma_verisi:
            sas_no = satir.get(SATIN_ALMA_COLUMNS['siparis_no'], '')
            
            if sas_no and str(sas_no).startswith(f'{self.sas_prefix}-'):
                try:
                    # "SAS-0000001" → 1
                    numara = int(str(sas_no).replace(f'{self.sas_prefix}-', ''))
                    sas_numaralari.append(numara)
                except ValueError:
                    continue
        
        if not sas_numaralari:
            return 0
        
        return max(sas_numaralari)
    
    def sonraki_sas_no_olustur(self, son_numara: int) -> str:
        """
        Son SAS numarasından sonraki SAS No'yu oluştur.
        
        Args:
            son_numara: Son SAS sayısı (örn: 1, 2, 100...)
            
        Dönüş:
            str: Sonraki SAS No (örn: "SAS-0000002")
        """
        sonraki = son_numara + 1
        formatted = f"{sonraki:0{self.sas_numara_uzunlugu}d}"
        sas_no = f"{self.sas_prefix}-{formatted}"
        
        logger.info(f"✓ Sonraki SAS No: {sas_no}")
        return sas_no
    
    def satin_alma_satirlari_olustur(
        self,
        ayristi_satırlar: List[Dict],
        baslangic_sas_no: str
    ) -> List[Dict]:
        """
        Ayrıştırılan Excel satırlarını Satin_Alma sayfası formatına dönüştür.
        
        Her Excel satırı = bir Satin_Alma satırı
        Tüm satırlar aynı SAS No ile (tek SAS = çok satır)
        
        Args:
            ayristi_satırlar: Excel ayrıştırıcıdan gelen satırlar
            baslangic_sas_no: Başlangıç SAS No (örn: "SAS-0000001")
            
        Dönüş:
            List[Dict]: Satin_Alma formatında satırlar
        """
        satin_alma_satirlari = []
        
        for satir in ayristi_satırlar:
            sas_satiri = {
                SATIN_ALMA_COLUMNS['siparis_no']: baslangic_sas_no,
                SATIN_ALMA_COLUMNS['tedarikci']: 'SAFAS',
                SATIN_ALMA_COLUMNS['tedarikci_barkoodu']: satir.get('parti_no'),
                SATIN_ALMA_COLUMNS['siparisi_miktari']: satir.get('hacim_m3'),
                SATIN_ALMA_COLUMNS['stok_kodu']: satir.get('stok_kodu'),
                SATIN_ALMA_COLUMNS['stok_adi']: satir.get('brn_urun_adi'),
                SATIN_ALMA_COLUMNS['gelen_miktari']: 0,  # Mal kabul yapılana kadar 0
                SATIN_ALMA_COLUMNS['birim']: STOK_BIRIM_M3,
                SATIN_ALMA_COLUMNS['adet']: satir.get('adet'),
                SATIN_ALMA_COLUMNS['parti']: 1,
                SATIN_ALMA_COLUMNS['status']: SAS_STATUS_ACIK,
                'Tarih': datetime.now().strftime('%d.%m.%Y'),
                'Gelen Adet': 0,
                'Gelen Parti': 0,
                'Barcode Verisi': satir.get('barcode_verisi'),
                'Excel Satir': satir.get('satir_index'),
            }
            
            satin_alma_satirlari.append(sas_satiri)
        
        logger.info(f"✓ {len(satin_alma_satirlari)} SAS satırı oluşturuldu")
        return satin_alma_satirlari
    
    def sayfaya_yazacak_veriyi_hazirla(self, satin_alma_satirlari: List[Dict]) -> List[List]:
        """
        Satin_Alma sayfasına append edilecek veriyi hazırla.
        gspread append_rows() formatı.
        
        Args:
            satin_alma_satirlari: Satin_Alma formatında satırlar
            
        Dönüş:
            List[List]: gspread append_rows() formatı
        """
        sayfa_verisi = []
        
        for satir in satin_alma_satirlari:
            satir_verisi = [
                satir.get(SATIN_ALMA_COLUMNS['siparis_no'], ''),
                satir.get(SATIN_ALMA_COLUMNS['tedarikci'], ''),
                satir.get(SATIN_ALMA_COLUMNS['tedarikci_barkoodu'], ''),
                satir.get(SATIN_ALMA_COLUMNS['siparisi_miktari'], ''),
                satir.get(SATIN_ALMA_COLUMNS['stok_kodu'], ''),
                satir.get(SATIN_ALMA_COLUMNS['stok_adi'], ''),
                satir.get(SATIN_ALMA_COLUMNS['gelen_miktari'], ''),
                satir.get(SATIN_ALMA_COLUMNS['birim'], ''),
                satir.get(SATIN_ALMA_COLUMNS['adet'], ''),
                satir.get(SATIN_ALMA_COLUMNS['parti'], ''),
                satir.get(SATIN_ALMA_COLUMNS['status'], ''),
            ]
            sayfa_verisi.append(satir_verisi)
        
        logger.info(f"✓ Sayfa yazma verisi hazırlandı ({len(sayfa_verisi)} satır)")
        return sayfa_verisi
    
    def satin_alma_satirlarini_dogrula(
        self,
        satin_alma_satirlari: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Satin_Alma satırlarını doğrula.
        
        Args:
            satin_alma_satirlari: Satin_Alma formatında satırlar
            
        Dönüş:
            Tuple[List, List]: (geçerli_satırlar, hata_satırları)
        """
        gecerli = []
        hatalar = []
        
        for idx, satir in enumerate(satin_alma_satirlari):
            satir_hatalari = []
            
            # Stok Kodu
            if not satir.get(SATIN_ALMA_COLUMNS['stok_kodu']):
                satir_hatalari.append('Stok Kodu boş')
            
            # Sipariş Miktarı
            siparisi_miktari = satir.get(SATIN_ALMA_COLUMNS['siparisi_miktari'], 0)
            if siparisi_miktari is None or siparisi_miktari <= 0:
                satir_hatalari.append('Sipariş Miktarı 0 veya boş')
            
            # Birim
            if not satir.get(SATIN_ALMA_COLUMNS['birim']):
                satir_hatalari.append('Birim boş')
            
            if satir_hatalari:
                hatalar.append({
                    'satir_index': idx,
                    'sas_no': satir.get(SATIN_ALMA_COLUMNS['siparis_no']),
                    'hatalar': satir_hatalari
                })
            else:
                gecerli.append(satir)
        
        logger.info(f"✓ {len(gecerli)} geçerli, {len(hatalar)} hatalı SAS satırı")
        return gecerli, hatalar
    
    def sas_ozeti_olustur(self, satin_alma_satirlari: List[Dict]) -> Dict:
        """
        Oluşturulan SAS için özet bilgi oluştur.
        
        Args:
            satin_alma_satirlari: Satin_Alma formatında satırlar
            
        Dönüş:
            Dict: SAS özeti
        """
        if not satin_alma_satirlari:
            return {}
        
        sas_no = satin_alma_satirlari[0].get(SATIN_ALMA_COLUMNS['siparis_no'])
        
        toplam_m3 = sum(
            satir.get(SATIN_ALMA_COLUMNS['siparisi_miktari'], 0)
            for satir in satin_alma_satirlari
        )
        toplam_adet = sum(
            satir.get(SATIN_ALMA_COLUMNS['adet'], 0)
            for satir in satin_alma_satirlari
        )
        toplam_parti = sum(
            satir.get(SATIN_ALMA_COLUMNS['parti'], 0)
            for satir in satin_alma_satirlari
        )
        
        ozet = {
            'sas_no': sas_no,
            'tedarikci': 'SAFAS',
            'satir_sayisi': len(satin_alma_satirlari),
            'toplam_m3': round(toplam_m3, 2),
            'toplam_adet': toplam_adet,
            'toplam_parti': toplam_parti,
            'durumu': SAS_STATUS_ACIK,
            'olusturulma_tarihi': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        logger.info(f"✓ SAS Özeti: {ozet['sas_no']} | {ozet['satir_sayisi']} satır | {ozet['toplam_m3']} m³")
        return ozet


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("✓ SAS Oluşturucu modülü hazır")
