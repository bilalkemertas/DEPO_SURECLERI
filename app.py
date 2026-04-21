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

# --- 4. YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=30)
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
        if not match.empty: return match.iloc[0]['İsim']
    return ""

def log_movement(islem, adres, kod, isim, miktar):
    """Her türlü stok hareketini Drive Sayfa1'e kaydeder."""
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        if not isim: isim = find_name_by_code(kod)
        yeni_log = pd.DataFrame([{
            "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "İşlem": is_type if 'is_type' in locals() else islem,
            "Adres": adres,
            "Malzeme Kodu": kod,
            "Malzeme Adı": isim,
            "Miktar": miktar,
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

def update_stock_record(kod, isim, adres, miktar, is_increase=True):
    """Stok tablosunu günceller ve 0 olanları siler."""
    if not isim: isim = find_name_by_code(kod)
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres)
    
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: stok_df.loc[mask, 'Miktar'] -= float(miktar)
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": "ADET", "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)
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
    if st.button("⬅️ ANA MENÜ", key="nav_s"): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 Giriş/Çıkış", "🔄 Transfer", "🔍 Stok Sorgu"])
    stok_df_all, katalog_list = get_katalog()
    
    with t1:
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"], key="st_is_t")
        secim = st.selectbox("Hızlı Seçim:", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_is_s")
        k_init = secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else ""
        i_init = secim.split(" | ")[1] if secim != "+ MANUEL GİRİŞ" else ""
        kod = st.text_input("Stok Kodu:", value=k_init, key="st_is_k").strip().upper()
        isim = st.text_input("Stok Adı:", value=i_init if i_init else find_name_by_code(kod), key="st_is_i").strip().upper()
        adr = st.text_input("Adres:", value="GENEL", key="st_is_a").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, key="st_is_q")
        if st.button("KAYDET", use_container_width=True, type="primary", key="st_is_btn"):
            if is_type == "ÇIKIŞ":
                stok_df = get_internal_data("Stok")
                mev = stok_df[(stok_df['Kod']==kod) & (stok_df['Adres']==adr)]['Miktar'].sum()
                if mev < qty: st.error(f"Yetersiz Stok! Mevcut: {mev}"); st.stop()
            guncel_isim = update_stock_record(kod, isim, adr, qty, is_increase=(is_type == "GİRİŞ"))
            log_movement(is_type, adr, kod, guncel_isim, qty)
            st.success("İşlem Kaydedildi!")

    with t2:
        e_adr = st.text_input("Nereden:", key="st_tr_f").strip().upper()
        y_adr = st.text_input("Nereye:", key="st_tr_t").strip().upper()
        t_sec = st.selectbox("Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_tr_s")
        tk = t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else ""
        ti = t_sec.split(" | ")[1] if t_sec != "+ MANUEL GİRİŞ" else ""
        t_kod = st.text_input("Ürün Kodu:", value=tk, key="st_tr_k").strip().upper()
        t_qty = st.number_input("Miktar:", min_value=0.1, key="st_tr_q")
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary", key="st_tr_btn"):
            stok_df = get_internal_data("Stok")
            mev = stok_df[(stok_df['Kod']==t_kod) & (stok_df['Adres']==e_adr)]['Miktar'].sum()
            if mev >= t_qty:
                if not ti: ti = find_name_by_code(t_kod)
                update_stock_record(t_kod, ti, e_adr, t_qty, is_increase=False)
                update_stock_record(t_kod, ti, y_adr, t_qty, is_increase=True)
                log_movement("TRANSFER ÇIKIŞ", e_adr, t_kod, ti, t_qty)
                log_movement("TRANSFER GİRİŞ", y_adr, t_kod, ti, t_qty)
                st.success("Transfer Başarılı!")
            else: st.error(f"Kaynakta Stok Yok! Mevcut: {mev}")

    with t3:
        search = st.text_input("🔍 Stok Sorgula:", key="st_sq_in").strip().upper()
        if not stok_df_all.empty:
            df_v = stok_df_all.copy()
            if search: df_v = df_v[df_v['Kod'].str.contains(search, na=False) | df_v['İsim'].str.contains(search, na=False)]
            st.dataframe(df_v[["Adres", "Kod", "İsim", "Miktar"]], use_container_width=True, hide_index=True)

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ", key="nav_u"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")
    with st.expander("📥 İş Emri Yükle", expanded=False):
        f = st.file_uploader("Excel Seç:", type=["xlsx"], key="u_f")
        if f:
            try:
                eno = f.name.split('.')[0]
                df_r = pd.read_excel(f, sheet_name="HAZIRLIK", skiprows=3).ffill()
                kc = next((c for c in df_r.columns if "STOK KOD" in str(c).upper()), None)
                ac = next((c for c in df_r.columns if "STOK AD" in str(c).upper()), None)
                mc = next((c for c in df_r.columns if "TOTAL" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                if kc and ac and mc:
                    df_f = df_r[[kc, ac, mc]].copy()
                    df_f.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                    df_f.insert(0, "İş Emri", eno)
                    df_f["Hazırlanan Adet"] = 0
                    if st.button(f"'{eno}' Kaydet", key="u_save"):
                        old = get_internal_data("Is_Emirleri")
                        conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                        st.success("İş Emri Kaydedildi!"); st.cache_data.clear()
            except Exception as e: st.error(f"Hata: {e}")

    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        s = st.selectbox("İş Emri Seç:", ["Seçiniz..."] + sorted(df_e["İş Emri"].unique().tolist()), key="u_s")
        if s != "Seçiniz...":
            df_sub = df_e[df_e["İş Emri"] == s].copy()
            df_d = df_sub[["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]].copy()
            df_d["Alınan Adres"] = "GENEL"
            ed = st.data_editor(df_d, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"], hide_index=True, use_container_width=True, key="u_ed")
            if st.button("HAZIRLIĞI ONAYLA", key="u_btn"):
                for i, r in ed.iterrows():
                    fark = float(r["Hazırlanan Adet"]) - float(df_sub.loc[i, "Hazırlanan Adet"])
                    if fark > 0:
                        update_stock_record(r["Stok Kodu"], r["Stok Adı"], r["Alınan Adres"], fark, is_increase=False)
                        log_movement(f"{s} ÜRETİM ÇIKIŞ", r["Alınan Adres"], r["Stok Kodu"], r["Stok Adı"], fark)
                        df_e.at[i, "Hazırlanan Adet"] = r["Hazırlanan Adet"]
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_e)
                st.success("Üretim Çıkışları İşlendi!"); st.cache_data.clear(); st.rerun()

# --- 8. RAPORLAR (YENİ SEKME EKLENDİ) ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ", key="nav_r"): go_home(); st.rerun()
    st.subheader("📊 Merkezi Raporlar")
    rt1, rt2, rt3 = st.tabs(["🏠 Stok Durumu", "🏭 Hazırlık Takibi", "📜 Hareket Arşivi"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            df_h['%'] = (pd.to_numeric(df_h['Hazırlanan Adet']) / pd.to_numeric(df_h['İhtiyaç Miktarı']) * 100).round(1)
            st.dataframe(df_h, use_container_width=True, hide_index=True)
    with rt3:
        st.write("📜 **Stok Hareketleri Detayı**")
        hareketler = get_internal_data("Sayfa1")
        if not hareketler.empty:
            # En son hareketi en üstte gösterelim
            st.dataframe(hareketler.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
