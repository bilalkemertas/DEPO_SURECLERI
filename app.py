import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
def go_uretim(): st.session_state.page = 'uretim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. AKILLI ÖNBELLEK VE YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=60)
def get_internal_data(worksheet_name):
    return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Kod'] = df['Kod'].fillna("").astype(str).str.strip().str.upper()
        df['İsim'] = df['İsim'].fillna("").astype(str).str.strip().str.upper()
        df['Arama'] = df['Kod'] + " | " + df['İsim']
        liste = [x for x in df['Arama'].unique() if "|" in str(x) and "nan" not in str(x).lower()]
        return df, sorted(liste)
    return pd.DataFrame(), []

def find_name_by_code(kod):
    df, _ = get_katalog()
    if not df.empty and kod:
        match = df[df['Kod'] == kod.strip().upper()]
        if not match.empty:
            return match.iloc[0]['İsim']
    return ""

def check_address_stock(kod, adres, miktar):
    df = get_internal_data("Stok")
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    current = df[(df['Kod'] == kod) & (df['Adres'] == adres)]['Miktar'].sum()
    return current >= miktar, current

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    if not isim or isim.strip() == "":
        isim = find_name_by_code(kod)
    
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres)
    
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: stok_df.loc[mask, 'Miktar'] -= float(miktar)
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df[stok_df['Miktar'] >= 0])
    st.cache_data.clear()
    return isim

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
    st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ", key="nav_home"): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "🔍 Stok Sorgu"])
    stok_df_all, katalog_list = get_katalog()
    
    with t1:
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"], key="st_type")
        secim = st.selectbox("Hızlı Seçim:", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_sec")
        k_init = secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else ""
        i_init = secim.split(" | ")[1] if secim != "+ MANUEL GİRİŞ" else ""
        
        kod = st.text_input("Stok Kodu:", value=k_init, key="st_kod").strip().upper()
        if kod and not i_init: i_init = find_name_by_code(kod)
            
        isim = st.text_input("Stok Adı:", value=i_init, key="st_isim").strip().upper()
        adr = st.text_input("Adres:", value="GENEL", key="st_adr").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, key="st_qty")
        
        if st.button("KAYDET", use_container_width=True, type="primary", key="st_save"):
            if is_type == "ÇIKIŞ":
                ok, mev = check_address_stock(kod, adr, qty)
                if not ok: st.error(f"Stok Yetersiz! Mevcut: {mev}"); st.stop()
            
            guncel_isim = update_stock_record(kod, isim, adr, "ADET", qty, is_increase=(is_type == "GİRİŞ"))
            
            log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
            yeni_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"), "İşlem": is_type, "Adres": adr, "Malzeme Kodu": kod, "Malzeme Adı": guncel_isim, "Miktar": qty, "Operatör": st.session_state.user}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
            st.success(f"Kaydedildi: {guncel_isim}")

    with t2:
        e_adr = st.text_input("Nereden:", key="tr_from").strip().upper()
        y_adr = st.text_input("Nereye:", key="tr_to").strip().upper()
        t_sec = st.selectbox("Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog_list, key="tr_sec")
        tk = t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else ""
        ti = t_sec.split(" | ")[1] if t_sec != "+ MANUEL GİRİŞ" else ""
        
        t_kod = st.text_input("Ürün Kodu:", value=tk, key="tr_kod").strip().upper()
        t_qty = st.number_input("Miktar:", min_value=0.1, key="tr_qty")
        
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True, type="primary", key="tr_save"):
            ok, mev = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                if not ti: ti = find_name_by_code(t_kod)
                update_stock_record(t_kod, ti, e_adr, "ADET", t_qty, is_increase=False)
                update_stock_record(t_kod, ti, y_adr, "ADET", t_qty, is_increase=True)
                st.success("Transfer Başarılı!")
            else: st.error(f"Stok Yok! Mevcut: {mev}")

    with t3:
        search = st.text_input("🔍 Stok Sorgula (Kod/İsim):", key="sq_input").strip().upper()
        if not stok_df_all.empty:
            df_view = stok_df_all.copy()
            if search:
                df_view = df_view[df_view['Kod'].str.contains(search, na=False) | df_view['İsim'].str.contains(search, na=False)]
            st.dataframe(df_view[["Adres", "Kod", "İsim", "Miktar"]], use_container_width=True, hide_index=True)

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ", key="nav_home_u"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")
    
    with st.expander("📥 Yeni İş Emri Yükle (Excel)", expanded=False):
        uploaded_file = st.file_uploader("Dosya Seç:", type=["xlsx"], key="u_file")
        if uploaded_file:
            try:
                is_emri_no = uploaded_file.name.split('.')[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=3).ffill()
                k_c = next((c for c in df_raw.columns if "STOK KOD" in str(c).upper()), None)
                a_c = next((c for c in df_raw.columns if "STOK AD" in str(c).upper()), None)
                m_c = next((c for c in df_raw.columns if "TOTAL" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                if k_c and a_c and m_c:
                    df_final = df_raw[[k_c, a_c, m_c]].copy()
                    df_final.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                    df_final.insert(0, "İş Emri", is_emri_no)
                    df_final["Hazırlanan Adet"] = 0
                    if st.button(f"'{is_emri_no}' Kaydet", key="u_save_btn"):
                        old = get_internal_data("Is_Emirleri")
                        conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_final], ignore_index=True))
                        st.success("Kaydedildi!"); st.cache_data.clear()
            except Exception as e: st.error(f"Hata: {e}")

    df_emirler = get_internal_data("Is_Emirleri")
    if not df_emirler.empty:
        secim = st.selectbox("İş Emri Seç:", ["Seçiniz..."] + sorted(df_emirler["İş Emri"].unique().tolist()), key="u_is_emri")
        if secim != "Seçiniz...":
            df_sub = df_emirler[df_emirler["İş Emri"] == secim].copy()
            df_display = df_sub[["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]].copy()
            df_display["Alınan Adres"] = "GENEL"
            edited = st.data_editor(df_display, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"], hide_index=True, use_container_width=True, key="u_editor")
            
            if st.button("HAZIRLIĞI ONAYLA", key="u_approve"):
                for idx, row in edited.iterrows():
                    fark = float(row["Hazırlanan Adet"]) - float(df_sub.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        ok, mev = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                        if not ok: st.error(f"{row['Stok Adı']} Yetersiz!"); st.stop()
                        update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], "ADET", fark, is_increase=False)
                        df_emirler.at[idx, "Hazırlanan Adet"] = row["Hazırlanan Adet"]
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_emirler)
                st.success("Hazırlık Kaydedildi!"); st.cache_data.clear(); st.rerun()

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ", key="nav_home_r"): go_home(); st.rerun()
    st.subheader("📊 Merkezi Raporlar")
    r_t1, r_t2 = st.tabs(["🏠 Stok Raporu", "🏭 Hazırlık Takibi"])
    with r_t1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with r_t2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            df_h['%'] = (pd.to_numeric(df_h['Hazırlanan Adet']) / pd.to_numeric(df_h['İhtiyaç Miktarı']) * 100).round(1)
            st.dataframe(df_h, use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
