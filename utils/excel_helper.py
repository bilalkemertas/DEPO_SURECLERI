import pandas as pd
import streamlit as st

def oku_excel_akilli_baslik(file, sheet_name=0):
    """
    Excel dosyasını okur ve ilk satırlarda gerçek başlıkların nerede olduğunu 
    dinamik olarak bularak o satırı sütun başlığı (header) yapar.
    """
    # 1. Önce excel'i başlık tanımlamadan ham (raw) olarak oku (bütün satırlar veri gibi gelsin)
    df_raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
    
    # Başlık olabilecek kelime ipuçları
    hedef_kelimeler = [
        "sipariş", "stok", "plaka", "kod", "ad", "miktar", 
        "adet", "en", "boy", "barkod", "tedarikçi", "grup"
    ]
    
    en_iyi_satir_idx = 0
    en_yuksek_eslesme = 0
    
    # 2. İlk 15 satırı tara ve en çok hedef kelime içeren satırı başlık adayı seç
    tarama_limiti = min(15, len(df_raw))
    for idx in range(tarama_limiti):
        # Satırdaki değerleri küçük harfe çevirip temizle
        satir_degerleri = df_raw.iloc[idx].astype(str).str.lower().str.strip().tolist()
        
        # Bu satırda kaç tane aradığımız anahtar kelime geçiyor?
        eslesme_sayisi = 0
        for hucre in satir_degerleri:
            if any(anahtar in hucre for anahtar in hedef_kelimeler):
                eslesme_sayisi += 1
                
        # Eğer bu satır şimdiye kadarki en çok eşleşmeyi aldıysa başlık satırı budur
        if eslesme_sayisi > en_yuksek_eslesme:
            en_yuksek_eslesme = eslesme_sayisi
            en_iyi_satir_idx = idx

    # 3. Eğer hiç eşleşme bulamadıysak güvenli mod olarak ilk satırı (0) kullanalım
    if en_yuksek_eslesme == 0:
        st.warning("⚠️ Excel içinde standart başlık kelimeleri tespit edilemedi. Varsayılan olarak ilk satır okunuyor.")
        df_cleaned = pd.read_excel(file, sheet_name=sheet_name)
        return df_cleaned

    # 4. En iyi satırı bulduk! Şimdi o satırı kolon isimleri yapalım
    gercek_basliklar = df_raw.iloc[en_iyi_satir_idx].tolist()
    
    # Boş (NaN) başlıkları temizleyelim veya isimlendirelim
    temiz_basliklar = []
    for i, col in enumerate(gercek_basliklar):
        if pd.isna(col) or str(col).strip() == "" or str(col).lower() == "nan":
            temiz_basliklar.append(f"Unnamed_{i}")
        else:
            temiz_basliklar.append(str(col).strip())
            
    # Başlık satırının altındaki verileri alalım
    df_veri = df_raw.iloc[en_iyi_satir_idx + 1:].copy()
    df_veri.columns = temiz_basliklar
    df_veri = df_veri.reset_index(drop=True)
    
    # Kullanıcıya bilgi verelim (Streamlit arayüzünde çok şık durur)
    st.info(f"🎯 Başlık satırı otomatik olarak **{en_iyi_satir_idx + 1}. satırda** tespit edildi. Üstteki plan/tarih verileri temizlendi.")
    
    return df_veri


# --- KULLANIM ÖRNEĞİ (Streamlit Entegrasyonu) ---
def ornek_dosya_yukleme_ekrani():
    st.title("İş Emri Yükleme Ekranı")
    
    yuklenen_dosya = st.file_uploader("İş Emri Excel Dosyasını Seçin", type=["xlsx", "xls"])
    
    if yuklenen_dosya is not None:
        # Eski sistem: df = pd.read_excel(yuklenen_dosya) -> Bu hata veriyordu!
        # Yeni akıllı sistem:
        try:
            df = oku_excel_akilli_baslik(yuklenen_dosya, sheet_name=0)
            
            st.write("Eşleşen Yeni Tablonuz:")
            st.dataframe(df.head(10))
            
            # Sütun isimlerini kontrol et
            st.write("Okunan Sütunlar:", list(df.columns))
            
        except Exception as e:
            st.error(f"Excel okunurken bir hata oluştu: {e}")
