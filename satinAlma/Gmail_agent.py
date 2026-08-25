"""
Gmail Ajanı - Safaş tedarikçisinden gelen mail'leri oku
Sadece okuma yetkisi (read-only MCP)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

from .config import (
    TEDARIKCI_MAIL,
    TEDARIKCI_AD,
    GMAIL_MCP_ENABLED,
    GMAIL_MCP_SCOPE,
)

logger = logging.getLogger(__name__)


class GmailAjani:
    """Safaş mail'lerini oku ve dosya indir"""
    
    def __init__(self, enabled: bool = GMAIL_MCP_ENABLED):
        self.enabled = enabled
        self.tedarikci_mail = TEDARIKCI_MAIL
        self.tedarikci_ad = TEDARIKCI_AD
    
    def son_dosyayi_indir(self) -> Optional[Dict]:
        """
        Safaş mail'inden son Excel eki'ni indir.
        
        Dönüş:
            Dict: {
                'dosya_adi': str,
                'icerik': bytes,
                'alinma_tarihi': str,
                'durumu': 'BASARILI'|'HATA'
            }
            None: Mail bulunamadı
        """
        if not self.enabled:
            return {
                'durumu': 'AYAR_GEREKLI',
                'mesaj': 'Gmail MCP bağlantısı yapılandırılmamış',
                'yonergeler': self._kurulum_yonergelerini_getir()
            }
        
        try:
            # Production'da Gmail API çağrısı yapılacak
            logger.info(f"Safaş ({self.tedarikci_mail}) mail'inde son dosya aranıyor...")
            
            return {
                'durumu': 'HAZIR',
                'mesaj': 'Gmail MCP entegrasyonu tamamlanaması bekleniyor'
            }
        
        except Exception as e:
            logger.error(f"Gmail okuması hatası: {str(e)}")
            return {
                'durumu': 'HATA',
                'mesaj': str(e)
            }
    
    def son_n_gun_maillerini_getir(self, gun: int = 7) -> Dict:
        """
        Son N gün içindeki Safaş mail'lerini listele.
        
        Args:
            gun: Kaç gün geriye bakılacak (varsayılan: 7)
            
        Dönüş:
            Dict: {
                'durumu': str,
                'mail_sayisi': int,
                'mailler': List[Dict]
            }
        """
        if not self.enabled:
            return {
                'durumu': 'AYAR_GEREKLI',
                'mesaj': 'Gmail MCP bağlantısı yapılandırılmamış'
            }
        
        try:
            tarih_filtresi = (datetime.now() - timedelta(days=gun)).strftime("%Y/%m/%d")
            sorgu = f'from:{self.tedarikci_mail} after:{tarih_filtresi}'
            
            logger.info(f"Gmail sorgusu: {sorgu}")
            
            return {
                'durumu': 'HAZIR',
                'sorgu': sorgu,
                'yontem': 'Gmail API v1 - list()',
                'kapsam': ['gmail.readonly']
            }
        
        except Exception as e:
            logger.error(f"Mail listesi hatası: {str(e)}")
            return {
                'durumu': 'HATA',
                'mesaj': str(e)
            }
    
    def mail_meta_verisi_cikart(self, mail: Dict) -> Dict:
        """
        Mail başlıklarından meta veri çıkart.
        
        Args:
            mail: Gmail API mail nesnesi
            
        Dönüş:
            Dict: {
                'gonden': str,
                'alindigi_tarih': str,
                'baslik': str,
                'mail_id': str
            }
        """
        basliklar = mail.get('payload', {}).get('headers', [])
        
        meta = {
            'gonden': next(
                (b['value'] for b in basliklar if b['name'] == 'From'),
                'Bilinmiyor'
            ),
            'baslik': next(
                (b['value'] for b in basliklar if b['name'] == 'Subject'),
                '(Başlık yok)'
            ),
            'alindigi_tarih': next(
                (b['value'] for b in basliklar if b['name'] == 'Date'),
                'Bilinmiyor'
            ),
            'mail_id': mail.get('id'),
            'thread_id': mail.get('threadId'),
        }
        
        return meta
    
    def excel_eki_cikart(self, mail: Dict) -> Optional[Dict]:
        """
        Mail'den Excel dosyası eki'ni çıkart.
        
        Args:
            mail: Gmail API mail nesnesi
            
        Dönüş:
            Dict: {'dosya_adi': str, 'icerik': bytes}
            None: Excel eki'ni bulunamadı
        """
        parcalar = mail.get('payload', {}).get('parts', [])
        
        for parca in parcalar:
            dosya_adi = parca.get('filename', '')
            
            if dosya_adi.endswith(('.xlsx', '.xls')):
                if 'data' in parca.get('body', {}):
                    # Basit gömülü veri
                    dosya_verisi = parca['body']['data']
                    
                    import base64
                    icerik = base64.urlsafe_b64decode(dosya_verisi)
                    
                    return {
                        'dosya_adi': dosya_adi,
                        'icerik': icerik,
                        'boyut_byte': len(icerik)
                    }
                
                elif 'attachmentId' in parca.get('body', {}):
                    # Bağlı ek - sonra indirilecek
                    return {
                        'dosya_adi': dosya_adi,
                        'ek_id': parca['body']['attachmentId'],
                        'durumu': 'INDIRILMESI_GEREKLI'
                    }
        
        return None
    
    def _kurulum_yonergelerini_getir(self) -> List[str]:
        """Gmail MCP kurulum talimatlarını döndür"""
        return [
            "1. Google Workspace Yöneticisi → Güvenlik → API Kontrolü",
            "2. Gmail MCP kapsamı: gmail.readonly (sadece okuma)",
            "3. Yetkili kapsamlar: Gönderme yapılmayacak (yalnızca okuma)",
            "4. Streamlit secrets ayarları:",
            "   - gmail_mcp_enabled: true",
            "   - safas_mail: safas@safas.com.tr",
            "5. Servis hesabı JSON → .streamlit/secrets.toml"
        ]


def gmail_baglantiyi_test_et() -> Dict:
    """Gmail bağlantısını test et"""
    ajani = GmailAjani(enabled=GMAIL_MCP_ENABLED)
    
    return {
        'tedarikci': ajani.tedarikci_ad,
        'mail': ajani.tedarikci_mail,
        'baglanti_durumu': 'BAGLI' if ajani.enabled else 'BAGLANMADI',
        'kapsam': GMAIL_MCP_SCOPE,
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Test
    durum = gmail_baglantiyi_test_et()
    print(json.dumps(durum, indent=2, ensure_ascii=False))
