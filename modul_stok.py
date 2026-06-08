import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani
from decimal import Decimal, ROUND_HALF_UP

def go_home(): 
    st.session_state.page = 'home'

# --- ÜRÜN SEÇİLDİĞİNDE KODU DOLDUR ---
def urun_secildi():
    sec_val = st.session_state.get("sec_box")
    if sec_val:
        kod = str(sec_val).split(" | ")[0]
        st.session_state["manual_s_kod"] = kod

def normalize_dataframe(df):
    """DataFrame sütun adlarını ve veri tiplerini normalize et"""
    if df is None or df.empty:
        return df
    
    df.columns = [str(c).strip() for c in df.columns]
    
    # Miktar sütununu numeriğe dönüştür
    if 'Miktar' in df.columns:
        df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0.0)
    
    return df

def consolidate_stock(df):
    """Duplicate stok satırlarını birleştir (Kod + Adres + Durum bazında)"""
    if df is None or df.empty:
        return df
    
    df = normalize_dataframe(df)
    
    if 'Durum' in df.columns:
        df = df.groupby(['Kod', 'Adres', 'Durum'], as_index=False).agg({
            'İsim': 'first',
            'Miktar': 'sum'
        })
    else:
        df = df.groupby(['Kod', 'Adres'], as_index=False).agg({
            'İsim': 'first',
            'Miktar': 'sum'
        })
    
    return df

def float_equal_zero(value, tolerance=0.0001):
    """
    🔧 FLOAT PRECISION TUZAĞI ÇÖZÜMÜ
    
    Python'da 0.1 + 0.2 != 0.3 olabilir.
    Bu fonksiyon sayının etkili olarak sıfıra eşit olup olmadığını kontrol eder.
    """
    return abs(float(value)) < tolerance

def extract_stock_distributed(df_stok, kod, adres, miktar_cikis, durum="Kullanılabilir"):
    """
    🔧 DAĞITIMLI STOK DÜŞME ALGORITMASI (FIFO)
    
    Aynı kod + adres + durum'a sahip birden fazla satır varsa,
    FIFO (ilk satırdan başlayarak) dağıtarak düşür
    
    Return: (başarılı, kalan_miktar)
    """
    m = (df_stok['Kod'] == kod) & (df_stok['Adres'] == adres) & (df_stok['Durum'] == durum)
    
    if not m.any():
        return False, float(miktar_cikis)
    
    matching_indices = df_stok.loc[m].index.tolist()
    kalan = float(miktar_cikis)
    
    for idx in matching_indices:
        # 🔧 Float precision: <= 0.0001 kullanıyoruz
        if float_equal_zero(kalan):
            break
        
        mevcut = float(df_stok.at[idx, 'Miktar'])
        
        if mevcut >= kalan:
            df_stok.at[idx, 'Miktar'] = mevcut - kalan
            kalan = 0.0
        else:
            df_stok.at[idx, 'Miktar'] = 0.0
            kalan -= mevcut
    
    return True, kalan

def add_stock_distributed(df_stok, kod, isim, adres, miktar_giris, durum="Kullanılabilir"):
    """
    Stok ekleme (GİRİŞ)
    Varsa topla, yoksa yeni satır aç
    """
    m = (df_stok['Kod'] == kod) & (df_stok['Adres'] == adres) & (df_stok['Durum'] == durum)
    
    if m.any():
        idx = df_stok.loc[m].index[0]
        df_stok.at[idx, 'Miktar'] = float(df_stok.at[idx, 'Miktar']) + float(miktar_giris)
    else:
        new_row = pd.DataFrame([{
            "Kod": kod, 
            "İsim": isim, 
            "Adres": adres, 
            "Miktar": float(miktar_giris), 
            "Durum": durum
        }])
        df_stok = pd.concat([df_stok, new_row], ignore_index=True)
    
    return df_stok

def goster():
    # --- 🟢 KRİTİK: FORM SIFIRLAMA ---
    if st.session_state.get("clear_form"):
        st.session_state["manual_s_kod"] = ""
        st.session_state["sec_box"] = None
        st.session_state["s_lot"] = ""
        st.session_state["s_mik"] = 0.0
        st.session_state["clear_form"] = False

    # --- KATALOG HAFIZAYA AL (HIZ) ---
    if "katalog_hafiza" not in st.session_state or not st.session_state["katalog_hafiza"]:
        df_k = veritabani.get_internal_data("Urun_Listesi")
        if df_k is None or df_k.empty:
            df_k = veritabani.get_internal_data("Katalog")

        if df_k is None or df_k.empty:
            st.session_state["katalog_hafiza"] = []
        else:
            df_k.columns = [str(c).strip() for c in df_k.columns]
            k_col = 'Kod' if 'Kod' in df_k.columns else df_k.columns[0]
            n_col = None
            if 'İsim' in df_k.columns:
                n_col = 'İsim'
            elif 'İsimm' in df_k.columns:
                n_col = 'İsimm'
            else:
                n_col = df_k.columns[1] if len(df_k.columns) > 1 else 'Ad'
            
            ham_katalog = (df_k[k_col].astype(str) + " | " + df_k[n_col].astype(str)).tolist()
            st.session_state["katalog_hafiza"] = sorted(list(set(ham_katalog)))

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri")
    
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        
        st.selectbox(
            "🔍 Ürün Seç:", 
            options=st.session_state["katalog_hafiza"],
            index=None,
            placeholder="Ürün seçmek için tıklayın...",
            key="sec_box",
            on_change=urun_secildi
        )
        
        c1, c2 = st.columns(2)
        with c1:
            manual_kod = st.text_input("📦 Malzeme Kodu:", key="manual_s_kod")
            st.session_state["manual_s_kod"] = manual_kod.upper().strip()
            
            lot_no = st.text_input("🔢 Parti/Lot No:", key="s_lot")
            st.session_state["s_lot"] = lot_no.upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        
        # ADRES YÖNETİMİ (None standardı)
        src_adr, dst_adr = None, None
        a1, a2 = st.columns(2)
        if move_type == "GİRİŞ":
            with a1: 
                dst_input = st.text_input("📍 Hedef Adres:", key="dst_adr")
                dst_adr = dst_input.upper().strip() if dst_input.strip() else "UNKNOWN"
        elif move_type == "ÇIKIŞ":
            with a1: 
                src_input = st.text_input("📍 Kaynak Adres:", key="src_adr")
                src_adr = src_input.upper().strip() if src_input.strip() else "UNKNOWN"
        elif move_type == "İÇ TRANSFER":
            with a1: 
                src_input = st.text_input("📍 Kaynak Adres:", key="src_adr")
                src_adr = src_input.upper().strip() if src_input.strip() else "UNKNOWN"
            with a2: 
                dst_input = st.text_input("📍 Hedef Adres:", key="dst_adr")
                dst_adr = dst_input.upper().strip() if dst_input.strip() else "UNKNOWN"

        # --- LİSTEYE EKLEME ---
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            kod_final = st.session_state.get("manual_s_kod", "").strip()
            if kod_final and s_mik > 0:
                sec_v = st.session_state.get("sec_box")
                isim = str(sec_v).split(" | ")[1] if sec_v and " | " in str(sec_v) else "MANUEL ÜRÜN"
                
                st.session_state.gecici_liste.append({
                    "İşlem": move_type, 
                    "Kod": kod_final, 
                    "İsim": isim,
                    "Miktar": float(s_mik), 
                    "Lot": st.session_state.get("s_lot", "").strip(), 
                    "Durum": s_dur, 
                    "Kaynak": src_adr, 
                    "Hedef": dst_adr
                })
                
                st.session_state["clear_form"] = True
                st.rerun()

    # --- BEKLEYEN LİSTE ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 Bekleyen Hareketler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Yol:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        if st.button("🚀 VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            with st.spinner("Sunucu ile senkronize ediliyor. Lütfen bekleyin..."):
                
                try:
                    st.cache_data.clear()
                except Exception:
                    pass

                # ✅ EN GÜNCEL VERİ ÇEKİLİYOR
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                
                if df_stok is None or df_har is None:
                    st.error("❌ Veritabanı bağlantısı kurulamadı! İşlem durduruldu.")
                    st.stop()

                df_stok = normalize_dataframe(df_stok)
                df_har = normalize_dataframe(df_har)
                
                if df_stok.empty:
                    df_stok = pd.DataFrame(columns=["Kod", "İsim", "Adres", "Miktar", "Durum"])
                if df_har.empty:
                    df_har = pd.DataFrame(columns=["Tarih", "İşlem", "İş Emri", "Kod", "İsim", "Adres", "Miktar", "Personel", "Durum", "Lot"])

                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                aktif_user = (
                    st.session_state.get("username") or 
                    st.session_state.get("kullanici") or 
                    st.session_state.get("user") or 
                    st.session_state.get("user_name") or 
                    st.session_state.get("aktif_kullanici") or 
                    st.session_state.get("kullanici_adi") or 
                    "Sistem Kullanıcısı"
                )
                
                # 🔧 FIX: İşlem sayısını önceden kaydet
                islem_sayisi = len(st.session_state.gecici_liste)
                
                hata_listesi = []
                df_stok_temp = df_stok.copy()
                df_har_temp = df_har.copy()
                
                # ✅ TRANSACTION BAŞLANGICI (Ya Hep Ya Hiç)
                for satir in st.session_state.gecici_liste:
                    satir_miktar = float(satir.get("Miktar", 0))
                    satir_kod = satir["Kod"]
                    satir_isim = satir["İsim"]
                    satir_durum = satir["Durum"]
                    
                    if satir["İşlem"] == "GİRİŞ":
                        adres = satir["Hedef"] if satir["Hedef"] else "UNKNOWN"
                        df_stok_temp = add_stock_distributed(
                            df_stok_temp, satir_kod, satir_isim, adres, satir_miktar, satir_durum
                        )
                            
                    elif satir["İşlem"] == "ÇIKIŞ":
                        adres = satir["Kaynak"] if satir["Kaynak"] else "UNKNOWN"
                        
                        # 🔧 DAĞITIMLI ÇIKIŞ (Float precision ile)
                        basarili, kalan = extract_stock_distributed(
                            df_stok_temp, satir_kod, adres, satir_miktar, satir_durum
                        )
                        
                        if not basarili:
                            hata_listesi.append(f"❌ {satir_kod} ({satir_isim}) - {adres} adresinde stok bulunamadı!")
                            continue
                        
                        # 🔧 Float precision: tolerance=0.0001
                        if not float_equal_zero(kalan):
                            hata_listesi.append(f"⚠️ {satir_kod} - Yeterli stok yok! Eksik: {kalan:.2f}")
                            continue
                        
                    elif satir["İşlem"] == "İÇ TRANSFER":
                        src = satir["Kaynak"] if satir["Kaynak"] else "UNKNOWN"
                        dst = satir["Hedef"] if satir["Hedef"] else "UNKNOWN"
                        
                        # 🔧 DAĞITIMLI TRANSFER (Float precision ile)
                        basarili, kalan = extract_stock_distributed(
                            df_stok_temp, satir_kod, src, satir_miktar, satir_durum
                        )
                        
                        if not basarili:
                            hata_listesi.append(f"❌ {satir_kod} - {src} kaynak adresinde stok yok!")
                            continue
                        
                        if not float_equal_zero(kalan):
                            hata_listesi.append(f"⚠️ {satir_kod} - Kaynak adresinde yeterli stok yok!")
                            continue
                        
                        df_stok_temp = add_stock_distributed(
                            df_stok_temp, satir_kod, satir_isim, dst, satir_miktar, satir_durum
                        )

                    # Hareket geçmişi ekle
                    df_har_temp = pd.concat([df_har_temp, pd.DataFrame([{
                        "Tarih": zaman, 
                        "İşlem": satir["İşlem"], 
                        "İş Emri": "-", 
                        "Kod": satir_kod,
                        "İsim": satir_isim, 
                        "Adres": (satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"]) or "UNKNOWN",
                        "Miktar": satir_miktar, 
                        "Personel": aktif_user, 
                        "Durum": satir_durum, 
                        "Lot": satir["Lot"]
                    }])], ignore_index=True)

                # ✅ TRANSACTION SONUCU
                if hata_listesi:
                    st.error("❌ Hata nedeniyle hiçbir işlem kaydedilmedi (Transaction iptal):")
                    for hata in hata_listesi:
                        st.write(hata)
                else:
                    df_stok_temp = consolidate_stock(df_stok_temp)
                    
                    veritabani.update_data("Stok", df_stok_temp)
                    veritabani.update_data("Hareketler", df_har_temp)
                    st.session_state.gecici_liste = []
                    # 🔧 FIX: İşlem sayısını önceden kaydedilen değerden göster
                    st.success(f"✅ {islem_sayisi} işlem başarıyla kaydedildi!")
                    st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
