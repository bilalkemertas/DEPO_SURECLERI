import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="BRN Depo Sayım v2.3", layout="wide")

# --- 1. VERİTABANI BAĞLANTISI ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_Stok_ana = conn.read(worksheet="Stok", ttl=0)
    
    # Veri Temizliği
    df_Stok_ana = df_Stok_ana.dropna(subset=["Kod", "İsim"])
    df_Stok_ana["Kod"] = df_Stok_ana["Kod"].astype(str).str.strip()
    df_Stok_ana["İsim"] = df_Stok_ana["İsim"].astype(str).str.strip()
    
    # Sözlükler
    kod_isim_dict = pd.Series(df_Stok_ana.İsim.values, index=df_Stok_ana.Kod).to_dict()
    isim_kod_dict = pd.Series(df_Stok_ana.Kod.values, index=df_Stok_ana.İsim).to_dict()
    
    kod_listesi = sorted(list(kod_isim_dict.keys()))
    ad_listesi = sorted(ad for ad in isim_kod_dict.keys())
    
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]
    
except Exception as e:
    st.error(f"Bağlantı hatası! Hata: {e}")
    st.stop()

# --- 2. GİRİŞ VE BELLEK SİSTEMİ ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'gecici_sayim_listesi' not in st.session_state:
    st.session_state['gecici_sayim_listesi'] = []

if not st.session_state['logged_in']:
    st.title("🔐 BRN Depo Girişi")
    user_id = st.text_input("Kullanıcı Adı")
    password = st.text_input("Şifre", type="password")
    if st.button("Giriş Yap"):
        if user_id in st.secrets["users"] and st.secrets["users"][user_id] == password:
            st.session_state['logged_in'] = True
            st.session_state['user_name'] = user_id
            st.rerun()
        else:
            st.error("Hatalı Giriş!")
    st.stop()

# --- 3. ANA UYGULAMA ---
st.sidebar.info(f"👤 Personel: {st.session_state['user_name']}")
if st.sidebar.button("Güvenli Çıkış"):
    st.session_state.clear()
    st.rerun()

st.title("🚀 Gelişmiş Sayım ve Durum Takibi")

# --- OTOMATİK SEÇİM STATE YÖNETİMİ ---
if 's_Kod' not in st.session_state: st.session_state['s_Kod'] = ""
if 's_Isim' not in st.session_state: st.session_state['s_Isim'] = ""

tab1, tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])

with tab1:
    st.subheader("📍 Yeni Veri Girişi")
    with st.container(border=True):
        col_adr, col_kod, col_isim, col_mik, col_durum = st.columns([1, 1.2, 1.8, 0.8, 1.2])
        
        with col_adr:
            s_adres = st.text_input("📍 Adres", key="adr_box").upper()
        
        with col_kod:
            new_kod = st.selectbox("📦 Ürün Kodu", [""] + kod_listesi, key="kod_sel")
            if new_kod != st.session_state['s_Kod']:
                st.session_state['s_Kod'] = new_kod
                st.session_state['s_Isim'] = kod_isim_dict.get(new_kod, "")
                st.rerun()
                
        with col_isim:
            new_isim = st.selectbox("📝 Ürün Adı", [""] + ad_listesi, key="isim_sel")
            if new_isim != st.session_state['s_Isim']:
                st.session_state['s_Isim'] = new_isim
                st.session_state['s_Kod'] = isim_kod_dict.get(new_isim, "")
                st.rerun()
        
        with col_mik:
            s_miktar = st.number_input("⚖️ Miktar", min_value=0.0, step=1.0, key="mik_box")
        with col_durum:
            s_durum = st.selectbox("🛠️ Ürün Durumu", durum_opsiyonlari, key="durum_box")
        
        if st.button("➕ Listeye Ekle", use_container_width=True):
            if s_adres and st.session_state['s_Kod']:
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": datetime.now().strftime("%d.%m.%Y"),
                    "Personel": st.session_state['user_name'],
                    "Adres": s_adres,
                    "Kod": st.session_state['s_Kod'],
                    "Ürün Adı": st.session_state['s_Isim'],
                    "Miktar": s_miktar,
                    "Durum": s_durum
                })
                st.toast(f"{st.session_state['s_Kod']} eklendi.")
            else:
                st.warning("Adres ve Kod/İsim alanları zorunludur!")

    # --- LİSTE VE KAYIT ---
    if st.session_state['gecici_sayim_listesi']:
        st.write("---")
        st.markdown("### 📥 Onay Bekleyen Sayımlar")
        df_temp = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
        st.dataframe(df_temp, use_container_width=True)
        
        if st.button("📤 DRIVE'A GÖNDER VE KAYDET", type="primary", use_container_width=True):
            df_db = conn.read(worksheet="sayim", ttl=0)
            df_son = pd.concat([df_db, df_temp], ignore_index=True)
            conn.update(worksheet="sayim", data=df_son)
            st.session_state['gecici_sayim_listesi'] = []
            st.rerun()

# --- TAB 2 ---
with tab2:
    st.subheader("🔍 Sayım ve Durum Analizi")
    try:
        df_sayim_db = conn.read(worksheet="sayim", ttl=0)
        if not df_sayim_db.empty:
            df_sayim_db["Tarih"] = df_sayim_db["Tarih"].astype(str).str[:10]
        
        sistem = df_Stok_ana[['Adres', 'Kod', 'İsim', 'Miktar']].copy()
        sistem.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]
        
        with st.expander("🛠️ Filtreler", expanded=True):
            f1, f2, f3, f4, f5 = st.columns(5)
            f_tarih = f1.selectbox("📅 Tarih", ["Hepsi"] + (sorted(df_sayim_db["Tarih"].unique().tolist(), reverse=True) if not df_sayim_db.empty else []))
            f_kod = f2.multiselect("📦 Kod", kod_listesi)
            f_ad = f3.multiselect("📝 Ürün Adı", ad_listesi)
            f_adr = f4.multiselect("📍 Adres", sorted(sistem["Adres"].unique().tolist()))
            f_durum = f5.multiselect("🛠️ Durum", durum_opsiyonlari)

        act_sayim = df_sayim_db.copy()
        if f_tarih != "Hepsi": act_sayim = act_sayim[act_sayim["Tarih"] == f_tarih]
        if f_durum: act_sayim = act_sayim[act_sayim["Durum"].isin(f_durum)]
        
        if not act_sayim.empty:
            s_ozet = act_sayim.groupby(['Adres', 'Kod', 'Durum'])['Miktar'].sum().reset_index()
            s_ozet.columns = ["Adres", "Kod", "Durum", "Sayılan_Miktar"]
        else:
            s_ozet = pd.DataFrame(columns=["Adres", "Kod", "Durum", "Sayılan_Miktar"])

        final_df = pd.merge(sistem, s_ozet, on=['Adres', 'Kod'], how='outer').fillna({"Sayılan_Miktar": 0, "Sistem_Miktarı": 0, "Durum": "Sayılmadı"})
        final_df['FARK'] = final_df['Sayılan_Miktar'] - final_df['Sistem_Miktarı']
        
        st.dataframe(final_df, use_container_width=True)
    except Exception as e:
        st.error(f"Rapor hatası: {e}")
