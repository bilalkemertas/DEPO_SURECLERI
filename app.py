import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    @media (max-width: 640px) { .stMetric { padding: 5px !important; } .row-font { font-size: 12px !important; } }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = None

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u = st.text_input("Kullanıcı:").strip().lower()
        p = st.text_input("Parola:", type="password").strip()
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets and u in st.secrets["users"] and str(st.secrets["users"][u]) == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
    st.stop()

# --- 3. BAĞLANTI VE FONKSİYONLAR ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def get_data(worksheet):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl=0)
    except: return pd.DataFrame()

def log_movement(islem, adr, kod, isim, mik):
    try:
        df = get_data("Sayfa1")
        new_row = pd.DataFrame([{"Tarih": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), 
                                 "İşlem": islem, "Adres": adr.upper(), "Malzeme Kodu": str(kod).upper(), 
                                 "Malzeme Adı": isim, "Miktar": float(mik), "Operatör": st.session_state.user}])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, new_row], ignore_index=True))
    except: pass

# --- 4. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 STOK HAREKETLERİ", use_container_width=True, type="primary"): st.session_state.page = 'stok'; st.rerun()
        if st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary"): st.session_state.page = 'uretim'; st.rerun()
    with c2:
        if st.button("📝 SAYIM EKRANLARI", use_container_width=True, type="primary"): st.session_state.page = 'sayim'; st.rerun()
        if st.button("📈 RAPORLAR", use_container_width=True, type="primary"): st.session_state.page = 'rapor'; st.rerun()
    if st.sidebar.button("Güvenli Çıkış"): st.session_state.clear(); st.rerun()

# --- 5. STOK HAREKETLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("🔄 Stok İşlemleri")
    kod_map = dict(zip(get_data("Stok")['Kod'].astype(str), get_data("Stok")['İsim'].astype(str)))
    
    with st.container(border=True):
        adr = st.text_input("📍 Adres").upper()
        tip = st.radio("Arama:", ["Kod", "İsim"], horizontal=True)
        if tip == "Kod":
            kod = st.selectbox("📦 Kod", [""] + sorted(list(kod_map.keys())))
            isim = kod_map.get(kod, "")
        else:
            im = {v: k for k, v in kod_map.items() if str(v).strip() != ""}
            isim = st.selectbox("📝 İsim", [""] + sorted(list(im.keys())))
            kod = im.get(isim, "")
        mik = st.number_input("Miktar", min_value=0.0, step=1.0)
        
        cg, cc = st.columns(2)
        if cg.button("📥 GİRİŞ", use_container_width=True):
            if adr and kod and mik > 0: log_movement("GİRİŞ", adr, kod, isim, mik); st.success("Kaydedildi"); st.rerun()
        if cc.button("📤 ÇIKIŞ", use_container_width=True):
            if adr and kod and mik > 0: log_movement("ÇIKIŞ", adr, kod, isim, mik); st.success("Kaydedildi"); st.rerun()

# --- 6. ÜRETİM HAZIRLIK (YENİLENEN EKRAN) ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("🏭 Üretim Hazırlık")
    
    file = st.file_uploader("📂 İş Emri Dosyasını Yükleyin", type=["xlsx", "xls", "csv"])
    if file:
        df_u = pd.read_excel(file) if file.name.endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        
        # İş Emri (Mamül) Seçimi
        mamul_listesi = df_u['Mamül Adı'].unique().tolist()
        secilen_is_emri = st.selectbox("🎯 Hazırlık Yapılacak İş Emrini Seçin", [""] + mamul_listesi)
        
        if secilen_is_emri:
            # Sadece hammaddeleri filtrele (Mamül adı ALV'de olmayacak)
            detay = df_u[df_u['Mamül Adı'] == secilen_is_emri][['Stok Kodu', 'Stok Adı', 'Miktar']].copy()
            detay.columns = ['Hammadde Kodu', 'Hammadde Adı', 'İhtiyaç']
            
            st.markdown(f"### 📋 {secilen_is_emri} - İhtiyaç Listesi")
            
            # Dinamik ALV Yapısı
            hazirlik_data = []
            for i, row in detay.iterrows():
                with st.expander(f"🛠️ {row['Hammadde Adı']}", expanded=True):
                    c1, c2, c3, c4 = st.columns([2, 1, 1.5, 1.5])
                    c1.write(f"**Kod:** {row['Hammadde Kodu']}\n\n**İhtiyaç:** {row['İhtiyaç']}")
                    h_mik = c2.number_input("Hazırlanan", min_value=0.0, key=f"mik_{i}")
                    h_adr = c3.text_input("Nereden Alındı?", key=f"adr_{i}").upper()
                    h_bir = c4.text_input("Taşıma Birimi (Palet/Koli)", key=f"bir_{i}")
                    
                    if h_mik > 0:
                        hazirlik_data.append({"Kod": row['Hammadde Kodu'], "Miktar": h_mik, "Adres": h_adr, "Birim": h_bir})
            
            if st.button("💾 HAZIRLIĞI TAMAMLA VE KAYDET", type="primary", use_container_width=True):
                st.success(f"{len(hazirlik_data)} kalem hammadde hazırlığı kaydedildi (Simülasyon).")

# --- 7. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("⚖️ Sayım Yönetimi")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])
    kod_map = dict(zip(get_data("Stok")['Kod'].astype(str), get_data("Stok")['İsim'].astype(str)))
    
    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres", key="s_adr").upper()
            s_kod = st.selectbox("📦 Kod", [""] + sorted(list(kod_map.keys())), key="s_kod")
            s_mik = st.number_input("Sayılan Miktar", min_value=0.0, key="s_mik")
            s_dur = st.selectbox("🛠️ Durum", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({"Tarih": datetime.now().strftime("%Y-%m-%d"), "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik, "Durum": s_dur})
                st.toast("Eklendi")

        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 DRIVE'A GÖNDER", type="primary", use_container_width=True):
                old = get_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([old, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.success("Kaydedildi!"); st.rerun()

    with t2:
        try:
            s_df = get_data("sayim"); st_df = get_data("Stok")
            if not s_df.empty:
                res = pd.merge(s_df.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index(), 
                               st_df.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index(), on=['Adres', 'Kod'], how='left', suffixes=('_Sayım', '_Sistem')).fillna(0)
                res['FARK'] = res['Miktar_Sayım'] - res['Miktar_Sistem']
                st.dataframe(res.style.map(lambda v: 'color:red' if v < 0 else 'color:green' if v > 0 else '', subset=['FARK']), use_container_width=True)
        except: st.info("Veri bekleniyor...")

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    t1, t2 = st.tabs(["📋 Güncel Stok", "📜 Hareket Arşivi"])
    with t1: st.dataframe(get_data("Stok"), use_container_width=True)
    with t2: st.dataframe(get_data("Sayfa1").iloc[::-1], use_container_width=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
