"""
Barcode Kontrol - Duplicate ve geçerlilik doğrulaması
teslim_alma.py'nin 'kabul' sayfasında kullanılacak
"""

import logging
from typing import Dict, Optional, Tuple, List

from .config import (
    BARCODE_NORMALIZE_STRIP_DECIMALS,
    MIKTAR_TOLERANSI_YUZDE,
    TAMAMLANMA_EŞIK_YUZDE,
    SAS_STATUS_ACIK,
    SAS_STATUS_KISMI,
    SAS_STATUS_TAMAMLANDI,
    SATIN_ALMA_COLUMNS,
)

logger = logging.getLogger(__name__)


class BarcodeKontrol:
    """Barcode doğrulaması ve duplicate kontrol"""
    
    @staticmethod
    def barcode_normalizasyon_yap(barcode: str) -> str:
        """
        Barcode'u normalize et (strip, .0 kaldır vb)
        
        Args:
            barcode: Ham barcode string
            
        Dönüş:
            str: Normalize edilmiş barcode
        """
        if not barcode:
            return ""
        
        barcode = str(barcode).strip()
        
        # .0 suffix'ini kaldır (Google Sheets sayısal type coercion)
        if BARCODE_NORMALIZE_STRIP_DECIMALS and barcode.endswith('.0'):
            barcode = barcode[:-2]
        
        return barcode
    
    @staticmethod
    def barcode_duplicate_kontrol(
        barcode: str,
        satin_alma_verisi: List[Dict],
        hareketler_verisi: List[Dict]
    ) -> Tuple[bool, str]:
        """
        Barcode'un daha önce teslim alınıp alınmadığını kontrol et.
        
        Args:
            barcode: Taranan barcode (Parti No)
            satin_alma_verisi: Satin_Alma sayfasından veriler
            hareketler_verisi: Hareketler sayfasından veriler
            
        Dönüş:
            Tuple[bool, str]:
                - True: Duplicate (uyarı verecek)
                - False: İlk kez (OK)
                - Mesaj: Detay bilgisi
        """
        
        barcode = BarcodeKontrol.barcode_normalizasyon_yap(barcode)
        
        if not barcode:
            return False, "❌ Boş barcode"
        
        # Satin_Alma'da ara
        for satir in satin_alma_verisi:
            tarkodisi = satir.get(SATIN_ALMA_COLUMNS['tedarikci_barkoodu'], '')
            tarkodisi = BarcodeKontrol.barcode_normalizasyon_yap(tarkodisi)
            
            if tarkodisi == barcode:
                durumu = satir.get(SATIN_ALMA_COLUMNS['status'], 'Bilinmiyor')
                
                if durumu == SAS_STATUS_TAMAMLANDI:
                    msg = f"⚠️ Bu barkod tamamen teslim alındı (Durum: {durumu})"
                    logger.warning(msg)
                    return True, msg
                
                elif durumu == SAS_STATUS_KISMI:
                    msg = f"⚠️ Bu barkod kısmen teslim alındı (Durum: {durumu})"
                    logger.warning(msg)
                    return True, msg
                
                else:  # Durum: "Açık"
                    msg = f"✅ Barcode geçerli (Durum: {durumu})"
                    logger.info(msg)
                    return False, msg
        
        # Hareketler'de de ara (ekstra kontrol)
        for satir in hareketler_verisi:
            tarkodisi = satir.get(SATIN_ALMA_COLUMNS['tedarikci_barkoodu'], '')
            tarkodisi = BarcodeKontrol.barcode_normalizasyon_yap(tarkodisi)
            
            if tarkodisi == barcode:
                tarih = satir.get('Tarih', 'Bilinmiyor')
                msg = f"⚠️ Bu barkod {tarih}'de teslim alındı"
                logger.warning(msg)
                return True, msg
        
        # Bulunamadı
        msg = "❌ Bu barkod Satın Alma'da bulunamadı"
        logger.error(msg)
        return False, msg
    
    @staticmethod
    def barcode_ile_sas_satiri_bul(
        barcode: str,
        satin_alma_verisi: List[Dict]
    ) -> Optional[Dict]:
        """
        Barcode'dan SAS satırını bulup detaylarını döndür.
        
        Args:
            barcode: Taranan barcode (Parti No)
            satin_alma_verisi: Satin_Alma sayfasından veriler
            
        Dönüş:
            Dict: SAS satırı detayları
            None: Bulunamadı
        """
        
        barcode = BarcodeKontrol.barcode_normalizasyon_yap(barcode)
        
        for satir in satin_alma_verisi:
            tarkodisi = satir.get(SATIN_ALMA_COLUMNS['tedarikci_barkoodu'], '')
            tarkodisi = BarcodeKontrol.barcode_normalizasyon_yap(tarkodisi)
            
            if tarkodisi == barcode:
                sas_satiri = {
                    'sas_no': satir.get(SATIN_ALMA_COLUMNS['siparis_no']),
                    'tedarikci': satir.get(SATIN_ALMA_COLUMNS['tedarikci']),
                    'stok_kodu': satir.get(SATIN_ALMA_COLUMNS['stok_kodu']),
                    'stok_adi': satir.get(SATIN_ALMA_COLUMNS['stok_adi']),
                    'siparisi_m3': satir.get(SATIN_ALMA_COLUMNS['siparisi_miktari']),
                    'siparisi_adet': satir.get(SATIN_ALMA_COLUMNS['adet']),
                    'siparisi_parti': satir.get(SATIN_ALMA_COLUMNS['parti']),
                    'gelen_m3': satir.get(SATIN_ALMA_COLUMNS['gelen_miktari']),
                    'gelen_adet': satir.get('Gelen Adet', 0),
                    'gelen_parti': satir.get('Gelen Parti', 0),
                    'durumu': satir.get(SATIN_ALMA_COLUMNS['status']),
                    'barcode_verisi': satir.get('Barcode Verisi'),
                    'kaynak_satir': satir
                }
                
                logger.info(f"✓ Barcode {barcode} → SAS {sas_satiri['sas_no']}")
                return sas_satiri
        
        logger.error(f"❌ Barcode {barcode} bulunamadı")
        return None
    
    @staticmethod
    def teslim_alinacak_miktar_dogrula(
        sas_satiri: Dict,
        gelen_m3: float,
        gelen_adet: int,
        gelen_parti: int
    ) -> Tuple[bool, List[str]]:
        """
        Gelen miktar vs Sipariş miktarını doğrula.
        
        Args:
            sas_satiri: SAS satırı
            gelen_m3: Gelen m³
            gelen_adet: Gelen Adet
            gelen_parti: Gelen Parti
            
        Dönüş:
            Tuple[bool, List]:
                - True/False: Geçerli mi?
                - Uyarı/hata mesajları
        """
        
        uyarilar = []
        
        siparisi_m3 = float(sas_satiri.get('siparisi_m3', 0))
        siparisi_adet = int(sas_satiri.get('siparisi_adet', 0))
        siparisi_parti = int(sas_satiri.get('siparisi_parti', 0))
        
        # m³ kontrol
        if gelen_m3 > siparisi_m3:
            msg = f"⚠️ Gelen m³ ({gelen_m3}) > Sipariş m³ ({siparisi_m3})"
            uyarilar.append(msg)
            logger.warning(msg)
        
        eksik_yuzde = ((siparisi_m3 - gelen_m3) / siparisi_m3 * 100) if siparisi_m3 > 0 else 0
        if eksik_yuzde > MIKTAR_TOLERANSI_YUZDE:
            msg = f"⚠️ Gelen m³ sipariş'ten %{eksik_yuzde:.1f} az"
            uyarilar.append(msg)
            logger.warning(msg)
        
        # Adet kontrol
        if gelen_adet > siparisi_adet:
            msg = f"⚠️ Gelen Adet ({gelen_adet}) > Sipariş Adet ({siparisi_adet})"
            uyarilar.append(msg)
            logger.warning(msg)
        
        if gelen_adet < siparisi_adet:
            msg = f"ℹ️ Gelen Adet ({gelen_adet}) < Sipariş Adet ({siparisi_adet})"
            uyarilar.append(msg)
            logger.info(msg)
        
        # Parti kontrol
        if gelen_parti > siparisi_parti:
            msg = f"⚠️ Gelen Parti ({gelen_parti}) > Sipariş Parti ({siparisi_parti})"
            uyarilar.append(msg)
            logger.warning(msg)
        
        if gelen_parti < siparisi_parti:
            msg = f"ℹ️ Gelen Parti ({gelen_parti}) < Sipariş Parti ({siparisi_parti})"
            uyarilar.append(msg)
            logger.info(msg)
        
        # Geçerli mi?
        gecerli = len(uyarilar) == 0 or all('ℹ️' in u for u in uyarilar)
        
        return gecerli, uyarilar
    
    @staticmethod
    def sas_durumu_hesapla(
        siparisi_m3: float,
        siparisi_adet: int,
        gelen_toplam_m3: float,
        gelen_toplam_adet: int
    ) -> str:
        """
        SAS durumunu hesapla.
        
        Args:
            siparisi_m3: Sipariş m³
            siparisi_adet: Sipariş Adet
            gelen_toplam_m3: Şimdiye kadar gelen m³
            gelen_toplam_adet: Şimdiye kadar gelen Adet
            
        Dönüş:
            str: 'Açık' | 'Kısmi Tamamlandı' | 'Tamamlandı'
        """
        
        if gelen_toplam_m3 <= 0:
            logger.info(f"SAS durumu: {SAS_STATUS_ACIK}")
            return SAS_STATUS_ACIK
        
        m3_oran = gelen_toplam_m3 / siparisi_m3 if siparisi_m3 > 0 else 0
        adet_oran = gelen_toplam_adet / siparisi_adet if siparisi_adet > 0 else 0
        
        # Tamamlandı: her ikisi de eşik üstünde
        if m3_oran >= (TAMAMLANMA_EŞIK_YUZDE / 100) and adet_oran >= (TAMAMLANMA_EŞIK_YUZDE / 100):
            logger.info(f"SAS durumu: {SAS_STATUS_TAMAMLANDI} (m3: %{m3_oran*100:.1f}, adet: %{adet_oran*100:.1f})")
            return SAS_STATUS_TAMAMLANDI
        
        # Kısmi: en az biri received
        if gelen_toplam_m3 > 0 or gelen_toplam_adet > 0:
            logger.info(f"SAS durumu: {SAS_STATUS_KISMI}")
            return SAS_STATUS_KISMI
        
        logger.info(f"SAS durumu: {SAS_STATUS_ACIK}")
        return SAS_STATUS_ACIK


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("✓ Barcode Kontrol modülü hazır")
