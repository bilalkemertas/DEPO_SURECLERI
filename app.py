import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
        .row-font { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None
if 'katalog_hafiza' not in st.session_state:
    st.session_state['katalog_hafiza'] = None
if 'page' not in st.session_state: 
    st.session_state.page = 'home'

# Üretim Hazırlık için Seçili Dosya Hafızası
if 'secili_is_emri' not in st.session_state:
    st.session_state.secili_is_emri = None

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# --- 3. NAVİGASYON FONKSİYONLARI ---
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_rapor(): st.session_state.page = 'rapor'
def go_sayim(): 
    st.cache_data.clear() 
    st.session_state['katalog_hafiza'] = None 
    st.session_state.page = 'sayim'

# --- 4. BAĞLANTI VE VERİ ÇEKME ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        df.columns = df.columns.str.strip()
        for col in ['Kod', 'kod']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame()

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

# --- 5. KATALOG VE HAFIZA YÖNETİMİ ---
def load_katalog_to_session():
    with st.spinner("📦 Katalog Hafızaya Alınıyor..."):
        df = get_internal_data("Urun_Listesi")
        if df.empty: df = get_internal_data("ürün listesi")
        if df.empty: df = get_internal_data("Ürün Listesi")
        
        final_list = []
        if not df.empty and 'kod' in df.columns and 'isim' in df.columns:
            temp_df = df.dropna(subset=['kod']).copy()
            temp_df['Arama'] = temp_df['kod'].astype(str) + " | " + temp_df['isim'].astype(str)
            final_list = sorted([str(x) for x in temp_df['Arama'].unique() if "nan" not in str(x).lower()])
        else:
            df_stok = get_internal_data("Stok")
            if not df_stok.empty and 'Kod' in df_stok.columns and 'İsim' in df_stok.columns:
                temp_stok = df_stok.dropna(subset=['Kod']).copy()
                temp_stok['Arama'] = temp_stok['Kod'].astype(str) + " | " + temp_stok['İsim'].astype(str)
                final_list = sorted([str(x) for x in temp_stok['Arama'].unique() if "nan" not in str(x).lower()])
        st.session_state['katalog_hafiza'] = final_list

def get_katalog():
    if st.session_state['katalog_hafiza'] is None:
        load_katalog_to_session()
    return st.session_state['katalog_hafiza']

# --- 6. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    df_ana = get_internal_data("Stok")
    m1, m2 = st.columns(2)
    sku_count = 0
    total_stok = 0
    if not df_ana.empty:
        if 'Kod' in df_ana.columns: sku_count = len(df_ana['Kod'].unique())
        if 'Miktar' in df_ana.columns: total_stok = pd.to_numeric(df_ana['Miktar'], errors='coerce').sum()
    m1.metric("SKU Çeşitliliği", sku_count)
    m2.metric("Toplam Stok", f"{total_stok:,.0f}")
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 RAPOR VE ARŞİV", use_container_width=True, type="primary", on_click=go_rapor)

# --- 7. ÜRETİM HAZIRLIK EKRANI (FULL VERSİYON) ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): 
        st.session_state.secili_is_emri = None
        go_home()
        st.rerun()
    
    st.subheader("🏭 Üretim Hazırlık Ekranı")
    
    # 1. Aşama: İş Emri Seçimi (Index)
    df_index = get_internal_data("Uretim_Index") # ERP'den gelen iş emri listesi
    if not df_index.empty:
        liste_is_emri = df_index['is_emri_no'].unique().tolist()
        secilen = st.selectbox("📋 Hazırlanacak İş Emrini Seçin:", ["Seçiniz..."] + liste_is_emri)
        
        if secilen != "Seçiniz...":
            st.session_state.secili_is_emri = secilen
            st.markdown(f"**Seçili İş Emri:** `{secilen}`")
            
            # 2. Aşama: Detay Listesi (Filtrelenmiş)
            df_detay = get_internal_data("Uretim_Detay")
            is_emri_verisi = df_detay[df_detay['is_emri_no'] == secilen]
            
            if not is_emri_verisi.empty:
                st.dataframe(is_emri_verisi[['urun_kodu', 'urun_adi', 'ihtiyac', 'hazirlanan']], 
                             use_container_width=True, hide_index=True)
                
                with st.expander("✅ Malzeme Hazırla"):
                    haz_kod = st.selectbox("Malzeme Seç:", is_emri_verisi['urun_kodu'].tolist())
                    haz_mik = st.number_input("Hazırlanan Adet:", min_value=1.0)
                    if st.button("HAZIRLIĞI ONAYLA"):
                        st.success("Hazırlık kaydedildi (Simülasyon)")
            else:
                st.warning("Bu iş emrine ait detay bulunamadı.")
    else:
        st.error("Üretim index listesi boş veya erişilemiyor.")

# --- 8. STOK HAREKETLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Stok Hareketleri")
    katalog = get_katalog()
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog)
        val_s_kod = sec.split(" | ", 1)[0].strip() if sec != "+ MANUEL GİRİŞ" else ""
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", value=val_s_kod, key=f"stok_kod_{sec}").upper()
            s_lot = st.text_input("🔢 Parti/Lot No:").upper()
        with c2:
            s_adr = st.text_input("📍 Adres:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
        s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            st.success("Kayıt Başarılı!")

# --- 9. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres:").upper()
            katalog = get_katalog() 
            sec = st.selectbox("🔍 Ürün Seç:", ["+ BARKOD / MANUEL GİRİŞ"] + katalog)
            
            if sec != "+ BARKOD / MANUEL GİRİŞ":
                parcalar = sec.split(" | ", 1)
                val_kod = parcalar[0].strip()
                val_isim = parcalar[1].strip() if len(parcalar) > 1 else ""
            else: val_kod, val_isim = "", ""
                
            c_kod, c_isim = st.columns(2)
            with c_kod:
                s_kod = st.text_input("📦 Malzeme Kodu:", value=val_kod, key=f"sayim_kod_{sec}").upper()
            with c_isim:
                s_isim = st.text_input("📝 Malzeme Adı:", value=val_isim, key=f"sayim_isim_{sec}").upper()
            
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                valid_codes = [k.split(" | ", 1)[0].upper().strip() for k in katalog]
                if not s_kod:
                    st.warning("⚠️ Lütfen kod giriniz!")
                elif s_kod not in valid_codes:
                    st.error(f"🛑 Hata: '{s_kod}' sistemde tanımlı değil!")
                else:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": get_local_time(), "Adres": s_adr, "Kod": s_kod, 
                        "Miktar": s_mik, "Personel": st.session_state.user, 
                        "isim": s_isim, "Durum": s_durum
                    })
                    st.toast("✅ Eklendi")
        
        # --- ONAYLI SİLME MEKANİZMASI ---
        if st.session_state['gecici_sayim_listesi']:
            st.markdown("---")
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                cols = st.columns([3, 1])
                cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
                
                if st.session_state.delete_confirm == idx:
                    c_del, c_esc = cols[1].columns(2)
                    if c_del.button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx)
                        st.session_state.delete_confirm = None
                        st.rerun()
                    if c_esc.button("❌", key=f"esc_{idx}"):
                        st.session_state.delete_confirm = None
                        st.rerun()
                else:
                    if cols[1].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx
                        st.rerun()
            
            if st.button("📤 VERİTABANINA GÖNDER", type="primary", use_container_width=True):
                eski = get_internal_data("sayim")
                yeni_df = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                guncel_df = pd.concat([eski, yeni_df], ignore_index=True) if not eski.empty else yeni_df
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=guncel_df)
                st.session_state['gecici_sayim_listesi'] = []
                st.rerun()

    with t2:
        st.markdown("#### 📊 Sadece Sayılan Ürünlerin Fark Raporu")
        df_stok = get_internal_data("Stok")
        df_sayim_db = get_internal_data("sayim")
        
        if df_sayim_db.empty:
            st.warning("Kayıtlı sayım bulunamadı.")
        else:
            # SADECE SAYILANLARI BAZ ALAN REFERANS
            pivot_sayim = df_sayim_db.groupby('Kod')['Miktar'].sum().reset_index()
            pivot_sayim.columns = ['Kod', 'Sayılan']
            
            pivot_stok = df_stok.groupby('Kod')['Miktar'].sum().reset_index()
            pivot_stok.columns = ['Kod', 'Sistem']
            
            # Left Join (Sadece sayılanlar)
            df_fark = pd.merge(pivot_sayim, pivot_stok, on='Kod', how='left').fillna(0)
            df_fark['Fark'] = df_fark['Sayılan'] - df_fark['Sistem']
            
            df_isimliler = get_internal_data("Urun_Listesi")
            if not df_isimliler.empty:
                df_fark = pd.merge(df_fark, df_isimliler[['kod', 'isim']], left_on='Kod', right_on='kod', how='left')
                df_fark = df_fark[['Adres', 'Kod', 'isim', 'Sistem', 'Sayılan', 'Fark']]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Sayılan SKU", len(df_fark))
            c2.metric("Toplam Sayılan", f"{df_fark['Sayılan'].sum():,.0f}")
            c3.metric("Toplam Fark", f"{df_fark['Fark'].sum():,.0f}")
            
            st.dataframe(df_fark, use_container_width=True, hide_index=True)

# --- 10. GENEL ARŞİV ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Genel Stok Arşivi")
    st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
