import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI VE MOBİL CSS ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    .stDataFrame { width: 100% !important; overflow-x: auto !important; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
        .row-font { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
if 'page' not in st.session_state: st.session_state.page = 'home'
if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = None

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                if u_raw.strip().lower() in users and str(users[u_raw.strip().lower()]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_raw.lower()
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# --- 3. BAĞLANTI VE YARDIMCI FONKSİYONLAR ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty: return dict(zip(df['Kod'].astype(str), df['İsim'].astype(str)))
    return {}

# Hareket Loglama Fonksiyonu (Stok ekranı için eklendi)
def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = get_internal_data("Sayfa1")
        yeni_log = pd.DataFrame([{
            "Tarih": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), 
            "İşlem": str(islem), "Adres": str(adres).upper(), "Malzeme Kodu": str(kod).upper(), 
            "Malzeme Adı": isim, "Miktar": float(miktar), "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

# --- 4. ANA EKRAN (NAVİGASYON) ---
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

# --- 5. STOK İŞLEMLERİ EKRANI (GERİ EKLENDİ) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("📦 Stok Giriş / Çıkış ve Transfer")
    
    t1, t2 = st.tabs(["🔄 Giriş / Çıkış", "🚚 Adres Transfer"])
    kod_map = get_kod_map()

    with t1:
        with st.container(border=True):
            adr = st.text_input("📍 Adres").upper()
            arama_tipi = st.radio("Arama Yöntemi:", ["📦 Koda Göre", "📝 İsme Göre"], horizontal=True, key="stok_arama")
            
            if arama_tipi == "📦 Koda Göre":
                kod = st.selectbox("📦 Kod Seçin", [""] + sorted(list(kod_map.keys())), key="stok_kod")
                isim = kod_map.get(kod, "")
            else:
                isim_map = {v: k for k, v in kod_map.items() if str(v).strip() != ""}
                isim = st.selectbox("📝 Ürün Adı Seçin", [""] + sorted(list(isim_map.keys())), key="stok_isim")
                kod = isim_map.get(isim, "")
            
            st.caption(f"Seçilen Ürün: **{kod}** - {isim}")
            mik = st.number_input("Miktar", min_value=0.0, step=1.0, key="stok_mik")
            
            col_g, col_c = st.columns(2)
            if col_g.button("📥 GİRİŞ YAP", type="primary", use_container_width=True):
                if adr and kod and mik > 0:
                    log_movement("GİRİŞ", adr, kod, isim, mik)
                    st.success("Stok Girişi Loglara Kaydedildi!"); st.rerun()
                else: st.warning("Adres, Kod ve Miktar zorunludur!")
            
            if col_c.button("📤 ÇIKIŞ YAP", type="primary", use_container_width=True):
                if adr and kod and mik > 0:
                    log_movement("ÇIKIŞ", adr, kod, isim, mik)
                    st.success("Stok Çıkışı Loglara Kaydedildi!"); st.rerun()
                else: st.warning("Adres, Kod ve Miktar zorunludur!")

    with t2:
        with st.container(border=True):
            eski_adr = st.text_input("📍 Eski Adres (Çıkış)").upper()
            yeni_adr = st.text_input("📍 Yeni Adres (Giriş)").upper()
            
            arama_tipi_t = st.radio("Arama Yöntemi:", ["📦 Koda Göre", "📝 İsme Göre"], horizontal=True, key="trans_arama")
            if arama_tipi_t == "📦 Koda Göre":
                t_kod = st.selectbox("📦 Kod Seçin", [""] + sorted(list(kod_map.keys())), key="trans_kod")
                t_isim = kod_map.get(t_kod, "")
            else:
                isim_map_t = {v: k for k, v in kod_map.items() if str(v).strip() != ""}
                t_isim = st.selectbox("📝 Ürün Adı Seçin", [""] + sorted(list(isim_map_t.keys())), key="trans_isim")
                t_kod = isim_map_t.get(t_isim, "")
            
            t_mik = st.number_input("Transfer Miktarı", min_value=0.0, step=1.0, key="trans_mik")
            
            if st.button("🚚 TRANSFERİ GERÇEKLEŞTİR", type="primary", use_container_width=True):
                if eski_adr and yeni_adr and t_kod and t_mik > 0:
                    log_movement("ÇIKIŞ", eski_adr, t_kod, t_isim, t_mik)
                    log_movement("GİRİŞ", yeni_adr, t_kod, t_isim, t_mik)
                    st.success(f"{t_kod} ürünü {eski_adr}'den {yeni_adr}'ye transfer edildi!"); st.rerun()
                else: st.warning("Tüm alanların doldurulması zorunludur!")

# --- 6. ÜRETİM HAZIRLIK EKRANI (GERİ EKLENDİ) ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("🏭 Üretim Hazırlık")
    st.info("💡 Üretim İş Emri Excel dosyanızı buraya yükleyerek içeriklerini görüntüleyebilirsiniz.")
    
    uploaded_file = st.file_uploader("📂 İş Emri Exceli / CSV Yükle", type=["xlsx", "xls", "csv"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'): 
                df_uretim = pd.read_csv(uploaded_file)
            else: 
                df_uretim = pd.read_excel(uploaded_file)
            st.success(f"✅ Dosya Yüklendi: {uploaded_file.name}")
            st.dataframe(df_uretim, use_container_width=True)
        except Exception as e:
            st.error(f"Dosya okuma hatası: {e}")

# --- 7. SAYIM SİSTEMİ EKRANI ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): st.session_state.page = 'home'; st.rerun()
    st.title("⚖️ Sayım İşlemleri Ekranı")
    
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım Raporu"])
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "İncelemede"]

    with st_tab1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres", key="sayim_adr").upper()
            arama_tipi = st.radio("Arama Yöntemi:", ["📦 Koda Göre", "📝 İsme Göre"], horizontal=True, key="sayim_tip")
            
            if arama_tipi == "📦 Koda Göre":
                s_kod = st.selectbox("📦 Kod Seçin", [""] + sorted(list(kod_map.keys())), key="sayim_kod")
                st.caption(f"Ürün Adı: {kod_map.get(s_kod, 'Seçilmedi')}")
            else:
                isim_map = {v: k for k, v in kod_map.items() if str(v).strip() != ""}
                s_isim = st.selectbox("📝 Ürün Adı Seçin", [""] + sorted(list(isim_map.keys())), key="sayim_isim")
                s_kod = isim_map.get(s_isim, "")
                st.caption(f"Ürün Kodu: {s_kod if s_kod else 'Seçilmedi'}")
            
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0, key="sayim_mik")
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari, key="sayim_dur")
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user, "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""), "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast("Eklendi")
                else: st.warning("Adres ve Ürün seçimi zorunludur!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyenler")
            h_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
            h_cols[0].write("**Adres**"); h_cols[1].write("**Kod**"); h_cols[2].write("**Ürün**")
            h_cols[3].write("**Mik.**"); h_cols[4].write("**Durum**"); h_cols[5].write("**Sil**")
            st.markdown("---")

            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_cols = st.columns([1, 1.2, 1.5, 0.7, 1, 0.6])
                r_cols[0].write(item['Adres'])
                r_cols[1].write(item['Kod'])
                r_cols[2].markdown(f"<p class='row-font'>{item['Ürün Adı'][:15]}</p>", unsafe_allow_html=True)
                r_cols[3].write(str(item['Miktar']))
                r_cols[4].write(item['Durum'])
                
                if st.session_state.delete_confirm == idx:
                    c_del, c_esc = r_cols[5].columns(2)
                    if c_del.button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx)
                        st.session_state.delete_confirm = None
                        st.rerun()
                    if c_esc.button("❌", key=f"esc_{idx}"):
                        st.session_state.delete_confirm = None
                        st.rerun()
                else:
                    if r_cols[5].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx
                        st.rerun()
            
            if st.button("📤 SAYIMI KAYDET", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.success("Drive güncellendi!"); st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Filtreler", expanded=True):
                    col_f1, col_f2 = st.columns(2)
                    col_f3, col_f4 = st.columns(2)
                    
                    f_t = col_f1.selectbox("📅 Tarih", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    sel_k = col_f2.multiselect("📦 Kod", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = col_f3.multiselect("📍 Adres", sorted(df_s_db["Adres"].unique().tolist()))
                    if "Durum" in df_s_db.columns:
                        durum_listesi = sorted(df_s_db["Durum"].astype(str).unique().tolist())
                    else:
                        durum_listesi = durum_opsiyonlari
                    sel_d = col_f4.multiselect("🛠️ Durum", durum_listesi)

                act = df_s_db.copy()
                if f_t != "Tümü": act = act[act["Tarih"] == f_t]
                if sel_k: act = act[act["Kod"].isin(sel_k)]
                if sel_a: act = act[act["Adres"].isin(sel_a)]
                if sel_d: act
