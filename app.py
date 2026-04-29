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

# --- NAVİGASYON ---
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_sayim(): 
    st.cache_data.clear() 
    st.session_state.page = 'sayim'
def go_uretim(): st.session_state.page = 'uretim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI VE VERİ ÇEKME ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        df.columns = df.columns.str.strip()
        if 'Kod' in df.columns:
            df['Kod'] = df['Kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        if 'kod' in df.columns:
            df['kod'] = df['kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        return df
    except:
        return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Urun_Listesi")
    if df.empty: df = get_internal_data("ürün listesi")
    if df.empty: df = get_internal_data("Ürün Listesi")
    
    if not df.empty and 'kod' in df.columns and 'isim' in df.columns:
        temp_df = df.dropna(subset=['kod']).copy()
        temp_df['Arama'] = temp_df['kod'].astype(str) + " | " + temp_df['isim'].astype(str)
        # Karışık veri tiplerinden (NaN/Float) dolayı sorted çökmesin diye string koruması
        liste = [str(x) for x in temp_df['Arama'].unique() if "nan" not in str(x).lower()]
        return sorted(liste)
    
    df_stok = get_internal_data("Stok")
    if not df_stok.empty and 'Kod' in df_stok.columns and 'İsim' in df_stok.columns:
        temp_stok = df_stok.dropna(subset=['Kod']).copy()
        temp_stok['Arama'] = temp_stok['Kod'].astype(str) + " | " + temp_stok['İsim'].astype(str)
        liste = [str(x) for x in temp_stok['Arama'].unique() if "nan" not in str(x).lower()]
        return sorted(liste)
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

# --- 5. ANA EKRAN ---
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

# --- 6. STOK İŞLEMLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Stok Hareketleri")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        katalog = get_katalog()
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

# --- 8. SAYIM SİSTEMİ ---
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
                if val_isim.lower() in ["nan", "none", "-"]: val_isim = ""
            else: val_kod, val_isim = "", ""
                
            c_kod, c_isim = st.columns(2)
            with c_kod:
                s_kod = st.text_input("📦 Malzeme Kodu:", value=val_kod, key=f"sayim_kod_{sec}").upper()
            with c_isim:
                s_isim = st.text_input("📝 Malzeme Adı (İsim):", value=val_isim, key=f"sayim_isim_{sec}").upper()
            
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                valid_codes = [k.split(" | ", 1)[0].upper().strip() for k in katalog]
                if not s_kod:
                    st.warning("⚠️ Lütfen bir malzeme kodu giriniz!")
                elif s_kod not in valid_codes:
                    st.error(f"🛑 İŞLEM REDDEDİLDİ: '{s_kod}' kodlu ürün sistemde tanımlı değil!")
                else:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": get_local_time(), "Adres": s_adr, "Kod": s_kod, 
                        "Miktar": s_mik, "Birim": "-", "Personel": st.session_state.user, 
                        "isim": s_isim, "Durum": s_durum
                    })
                    st.toast("✅ Başarıyla Eklendi")
        
        # --- SİLME ONAYLI GEÇİCİ LİSTE ---
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
        st.info("Rapor verileri veritabanından çekiliyor...")

# --- 9. RAPORLAR VE ARŞİV ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Raporlar ve Arşiv")
    st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
