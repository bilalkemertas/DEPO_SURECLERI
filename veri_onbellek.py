"""
veri_onbellek.py
────────────────────────────────────────────────────────────────
Tüm ekranlar için ORTAK, session_state tabanlı veri önbelleği.

Neden bu dosya var:
- Google Sheets bir "sorgulanabilir veritabanı" değil, her okuma/yazma
  ayrı bir ağ isteği. Bir ekranın 4 sekmeye ihtiyacı varsa, bunları
  sırayla okumak 4 ayrı bekleme demek.
- Bu dosya, bir modülün ihtiyaç duyduğu sekmeleri AYNI ANDA (paralel)
  okur - toplam bekleme süresi 4 okumanın TOPLAMI değil, EN YAVAŞ
  OLANI kadar olur (2-4 kat hızlanma).
- Süre sınırı (TTL) YOKTUR. Veri, o modül bu tarayıcı oturumunda ilk
  kez açıldığında BİR KEZ okunur ve session_state'te kalır. Kullanıcı
  ne kadar yavaş yazarsa yazsın tekrar okuma yapılmaz.
- Sadece şu 3 durumda yeniden okunur:
    1) O modül bu oturumda ilk kez açıldığında,
    2) Kendi kaydımızı yaptıktan hemen sonra (zorla=True),
    3) Kullanıcı elle "🔄 Yenile" butonuna bastığında.
- Sadece o an aktif olan ekranın modülü çağrıldığı için (app.py zaten
  sadece seçili sayfayı çağırıyor), ziyaret edilmemiş ekranların
  verisi HİÇ çekilmez - "önce görülen ekrana öncelik" doğal olarak
  sağlanır.

Kullanım (her modülün goster()/run() fonksiyonunun en üstünde):
    import veri_onbellek as vo

    veri = vo.modul_verisi_yukle(conn, "stok", ["Stok", "Urun_Listesi"])
    df_stok = veri["Stok"]
    df_urun = veri["Urun_Listesi"]

    # Bir şey kaydettikten hemen sonra taze veri için:
    vo.modul_verisi_yukle(conn, "stok", ["Stok", "Urun_Listesi"], zorla=True)

    # Elle "Yenile" butonunda:
    if st.button("🔄 Yenile"):
        vo.modul_verisi_yukle(conn, "stok", ["Stok", "Urun_Listesi"], zorla=True)
        st.rerun()
────────────────────────────────────────────────────────────────
"""

import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st


def _tek_sekme_oku(conn, tablo_adi, deneme=3):
    """Tek bir sekmeyi okur, geçici hatalarda birkaç kez dener."""
    son_hata = None
    for i in range(deneme):
        try:
            df = conn.read(worksheet=tablo_adi, ttl=0)
            return (df.copy() if df is not None else pd.DataFrame()), None
        except Exception as e:
            son_hata = e
            if i == deneme - 1:
                return pd.DataFrame(), son_hata
            time.sleep(random.uniform(0.2, 0.5))
    return pd.DataFrame(), son_hata


def paralel_oku(conn, tablo_listesi):
    """
    Birden fazla sekmeyi AYNI ANDA (paralel iş parçacıklarıyla) okur.
    Sekmeler birbirinden bağımsız ağ istekleri olduğu için bu, toplam
    bekleme süresini ciddi şekilde düşürür. Hata alan bir sekme
    diğerlerini etkilemez, sadece o sekme için hata gösterilir.
    """
    sonuc = {}
    hatalar = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(tablo_listesi)))) as havuz:
        gorevler = {havuz.submit(_tek_sekme_oku, conn, t): t for t in tablo_listesi}
        for gorev in as_completed(gorevler):
            tablo_adi = gorevler[gorev]
            try:
                df, hata = gorev.result()
                sonuc[tablo_adi] = df
                hatalar[tablo_adi] = hata
            except Exception as e:
                sonuc[tablo_adi] = pd.DataFrame()
                hatalar[tablo_adi] = e

    for tablo_adi, hata in hatalar.items():
        if hata is not None:
            st.error(f"❌ '{tablo_adi}' sekmesi okunamadı! Hata: {hata}")
            st.warning(
                f"Kontrol et: Google Sheets dosyanda '{tablo_adi}' adında bir sekme "
                "gerçekten var mı? Sekme adı büyük/küçük harf dahil BİREBİR aynı olmalı."
            )

    return sonuc


def modul_verisi_yukle(conn, modul_anahtari, tablo_listesi, zorla=False):
    """
    Bir modülün ihtiyaç duyduğu tüm sekmeleri PARALEL okuyup
    session_state'te tutar. Süre sınırı yoktur - sadece olay bazlı
    yenilenir (bkz. dosya başındaki açıklama).
    """
    cache_anahtari = f"_veri_onbellek_{modul_anahtari}"
    if zorla or cache_anahtari not in st.session_state:
        st.session_state[cache_anahtari] = paralel_oku(conn, tablo_listesi)
    return st.session_state[cache_anahtari]


def onbellek_temizle(modul_anahtari):
    """Belirli bir modülün önbelleğini temizler (bir sonraki okumada taze veri gelir)."""
    cache_anahtari = f"_veri_onbellek_{modul_anahtari}"
    if cache_anahtari in st.session_state:
        del st.session_state[cache_anahtari]
