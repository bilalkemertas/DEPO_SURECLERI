import streamlit as st
import pandas as pd
from datetime import datetime
import veritabani

def go_home(): 
    st.session_state.page = 'home'

# --- ÜRÜN SEÇİLDİĞİNDE KODU DOLDUR ---
def urun_secildi():
    sec_val = st.session_state.get("sec_box")
    if sec_val:
        kod = str(sec_val).split(" | ")[0]
        st.session_state["manual_s_kod"] = kod

def goster():
    # --- 1. KRİTİK: FORM SIFIRLAMA ---
    if st.session_state.get("clear_form"):
        st.session_state["manual_s_kod"] = ""
        st.session_state["sec_box"] = None
        st.session_state["s_lot"] = ""
        st.session_state["s_mik"] = 0.0
        st.session_state["clear_form"] = False

    # --- 2. SADECE KATALOĞU HAFIZAYA AL (HIZ İÇİN) ---
    if "katalog_hafiza" not in st.session_state or not st.session_state["katalog_hafiza"]:
        df_k = veritabani.get_internal_data("Urun_Listesi")
        if df_k is None or df_k.empty:
            df_k = veritabani.get_internal_data("Katalog")

        if df_k is None or df_k.empty:
            st.session_state["katalog_hafiza"] = []
        else:
            df_k.columns = [str(c).strip() for c in df_k.columns]
            k_col = 'Kod' if 'Kod' in df_k.columns else df_k.columns[0]
            n_col = 'İsim' if 'İsimm' in df_k.columns or 'İsim' in df_k.columns else df_k.columns[1]
            ham_katalog = (df_k[k_col].astype(str) + " | " + df_k[n_col].astype(str)).tolist()
            st.session_state["katalog_hafiza"] = sorted(list(set(ham_katalog)))

    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- 3. ARAYÜZ ---
    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri")
    
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], key="move_type")
        
        # ÜRÜN SEÇİMİ
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
            st.text_input("📦 Malzeme Kodu:", key="manual_s_kod").upper().strip()
            st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        
        # ADRES YÖNETİMİ
        src_adr, dst_adr = "-", "-"
        a1, a2 = st.columns(2)
        if move_type == "GİRİŞ":
            with a1: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()
        elif move_type == "ÇIKIŞ":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
        elif move_type == "İÇ TRANSFER":
            with a1: src_adr = st.text_input("📍 Kaynak Adres:", key="src_adr").upper().strip()
            with a2: dst_adr = st.text_input("📍 Hedef Adres:", key="dst_adr").upper().strip()

        # --- LİSTEYE EKLEME ---
        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            kod_final = st.session_state.get("manual_s_kod", "")
            if kod_final and s_mik > 0:
                sec_v = st.session_state.get("sec_box")
                isim = str(sec_v).split(" | ")[1] if sec_v and " | " in str(sec_v) else "MANUEL ÜRÜN"
                
                st.session_state.gecici_liste.append({
                    "İşlem": move_type, "Kod": kod_final, "İsim": isim,
                    "Miktar": s_mik, "Lot": st.session_state.get("s_lot", ""), 
                    "Durum": s_dur, "Kaynak": src_adr, "Hedef": dst_adr
                })
                
                st.session_state["clear_form"] = True
                st.rerun()

    # --- 4. BEKLEYEN LİSTE VE KAYIT KISMI ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 Bekleyen Hareketler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Yol:** {item['Kaynak']} ➡️ {item['Hedef']}")
                if st.button(f"🗑️ Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        # --- KRİTİK ALAN: VERİTABANINA YAZMA (TÜM SORUNLARIN ÇÖZÜLDÜĞÜ YER) ---
        if st.button("🚀 VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            with st.spinner("Sunucu ile senkronize ediliyor. Lütfen bekleyin..."):
                
                # 1. ÖNBELLEK TEMİZLİĞİ: İki kullanıcı sorununun kökten çözümü!
                try:
                    st.cache_data.clear()
                except Exception:
                    pass

                # 2. EN GÜNCEL VERİYİ ŞİMDİ ÇEKİYORUZ!
                df_stok = veritabani.get_internal_data("Stok")
                df_har = veritabani.get_internal_data("Hareketler")
                
                # 3. BAĞLANTI KONTROLÜ (ESKİ KAYITLARI SİLME HATASININ ÇÖZÜMÜ)
                # Eğer bağlantı koparsa 'None' döner. Asla boş tablo oluşturmayıp işlemi durduruyoruz!
                if df_stok is None or df_har is None:
                    st.error("❌ Veritabanı bağlantısı kurulamadı! Önceki kayıtlarınızın silinmemesi için işlem durduruldu. Lütfen 5 saniye bekleyip tekrar tıklayın.")
                    st.stop()

                # 4. SÜTUN ZIRHLARI
                if df_stok.empty:
                    df_stok = pd.DataFrame(columns=["Kod", "İsim", "Adres", "Miktar", "Durum"])
                else:
                    df_stok.columns = [str(c).strip() for c in df_stok.columns]
                    
                if df_har.empty:
                    df_har = pd.DataFrame(columns=["Tarih", "İşlem", "İş Emri", "Kod", "İsim", "Adres", "Miktar", "Personel", "Durum", "Lot"])
                else:
                    df_har.columns = [str(c).strip() for c in df_har.columns]

                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                aktif_user = (
                    st.session_state.get("username") or 
                    st.session_state.get("kullanici") or 
                    st.session_state.get("user") or 
                    st.session_state.get("user_name") or 
                    st.session_state.get("aktif_kullanici") or 
                    "Bilal Kemertaş"
                )
                
                # 5. DÖNGÜ (TÜM LİSTEYİ GÜVENLE İŞLE)
                for satir in st.session_state.gecici_liste:
                    # Stok Güncellemesi
                    if satir["İşlem"] == "GİRİŞ":
                        m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                        if m.any(): df_stok.loc[m, 'Miktar'] += satir["Miktar"]
                        else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)
                    elif satir["İşlem"] == "ÇIKIŞ":
                        m = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                        if m.any(): df_stok.loc[m, 'Miktar'] = max(0, df_stok.loc[m, 'Miktar'].values[0] - satir["Miktar"])
                    elif satir["İşlem"] == "İÇ TRANSFER":
                        sm = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                        dm = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                        if sm.any():
                            df_stok.loc[sm, 'Miktar'] = max(0, df_stok.loc[sm, 'Miktar'].values[0] - satir["Miktar"])
                            if dm.any(): df_stok.loc[dm, 'Miktar'] += satir["Miktar"]
                            else: df_stok = pd.concat([df_stok, pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])], ignore_index=True)

                    # Hareket Geçmişine Ekleme (DÖNGÜNÜN İÇİNDE - GÜVENLİ)
                    yeni_hareket = pd.DataFrame([{
                        "Tarih": zaman, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                        "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                        "Miktar": satir["Miktar"], "Personel": aktif_user, "Durum": satir["Durum"], "Lot": satir["Lot"]
                    }])
                    df_har = pd.concat([df_har, yeni_hareket], ignore_index=True)

                # 6. EN SON TEK SEFERDE YAZ (VERİYİ YORMA)
                veritabani.update_data("Stok", df_stok)
                veritabani.update_data("Hareketler", df_har)
                
                # Temizlik ve Başarı
                st.session_state.gecici_liste = []
                st.success("✅ Tüm işlemler başarıyla kaydedildi!")
                st.rerun()

    st.markdown("---")
    st.markdown(f"<div style='text-align: right;'><b>🚀 Bilal Kemertaş</b><br><small>BRN 2026</small></div>", unsafe_allow_html=True)
