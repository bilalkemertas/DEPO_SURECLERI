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
            if "users" not in st.secrets:
                st.error("Secrets ayarlarında [users] bloğu bulunamadı!")
            else:
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

# --- 4. AKILLI ÖNBELLEK ---
@st.cache_data(ttl=60)
def get_internal_data(worksheet_name):
    return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
        df['İsim'] = df['İsim'].astype(str).str.strip().str.upper()
        df['Arama'] = df['Kod'] + " | " + df['İsim']
        return df, sorted(df['Arama'].unique().tolist())
    return pd.DataFrame(), ["+ MANUEL GİRİŞ"]

def check_address_stock(kod, adres, miktar):
    df = get_internal_data("Stok")
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    current = df[(df['Kod'] == kod) & (df['Adres'] == adres)]['Miktar'].sum()
    return current >= miktar, current

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    miktar = float(miktar)
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres) & (stok_df['Birim'] == birim)
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += miktar
        else: stok_df.loc[mask, 'Miktar'] -= miktar
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df[stok_df['Miktar'] >= 0])
    st.cache_data.clear()

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.write("")
    st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
    st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "🔍 Stok Sorgu"])
    stok_df_all, katalog_list = get_katalog()
    
    with t1:
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        secim = st.selectbox("Hızlı Seçim:", ["+ MANUEL GİRİŞ"] + katalog_list)
        kod_init = secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else ""
        isim_init = secim.split(" | ")[1] if secim != "+ MANUEL GİRİŞ" else ""
        kod = st.text_input("Stok Kodu:", value=kod_init).strip().upper()
        if kod and not isim_init and not stok_df_all.empty:
            match = stok_df_all[stok_df_all['Kod'] == kod]
            if not match.empty: isim_init = match.iloc[0]['İsim']
        isim = st.text_input("Stok Adı:", value=isim_init).strip().upper()
        adr = st.text_input("Adres:", value="GENEL").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1)
        if st.button("KAYDET", use_container_width=True, type="primary"):
            if is_type == "ÇIKIŞ":
                ok, mev = check_address_stock(kod, adr, qty)
                if not ok: st.error(f"Yetersiz Stok! Mevcut: {mev}"); st.stop()
            update_stock_record(kod, isim, adr, "ADET", qty, is_increase=(is_type == "GİRİŞ"))
            st.success("İşlem Başarılı!")

    with t2:
        e_adr = st.text_input("Nereden:").strip().upper()
        y_adr = st.text_input("Nereye:").strip().upper()
        t_sec = st.selectbox("Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog_list, key="tr_sec")
        tk = t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else ""
        ti = t_sec.split(" | ")[1] if t_sec != "+ MANUEL GİRİŞ" else ""
        t_kod = st.text_input("Ürün Kodu:", value=tk, key="tk_in").strip().upper()
        t_qty = st.number_input("Transfer Miktarı:", min_value=0.1)
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True, type="primary"):
            ok, mev = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                update_stock_record(t_kod, ti, e_adr, "ADET", t_qty, is_increase=False)
                update_stock_record(t_kod, ti, y_adr, "ADET", t_qty, is_increase=True)
                st.success("Transfer Başarılı!")
            else: st.error(f"Stok Yok! Mevcut: {mev}")

    with t3:
        search_query = st.text_input("🔍 Stoklarda Ara (Kod veya İsim):").strip().upper()
        if not stok_df_all.empty:
            df_display = stok_df_all.copy()
            if search_query:
                df_display = df_display[df_display['Kod'].str.contains(search_query) | df_display['İsim'].str.contains(search_query)]
            st.dataframe(df_display[["Adres", "Kod", "İsim", "Birim", "Miktar"]], use_container_width=True, hide_index=True)

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")
    
    with st.expander("📥 Yeni İş Emri Yükle (Excel)", expanded=False):
        uploaded_file = st.file_uploader("Dosya Seç:", type=["xlsx"])
        if uploaded_file:
            try:
                is_emri_no = uploaded_file.name.split('.')[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=3).ffill()
                k_c = next((c for c in df_raw.columns if "STOK KOD" in str(c).upper()), None)
                a_c = next((c for c in df_raw.columns if "STOK AD" in str(c).upper()), None)
                m_c = next((c for c in df_raw.columns if "TOTAL" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                u_a_c = next((c for c in df_raw.columns if "MAMÜL AD" in str(c).upper() or "ÜRÜN AD" in str(c).upper()), None)
                u_k_c = next((c for c in df_raw.columns if "MAMÜL KOD" in str(c).upper() or "ÜRÜN KOD" in str(c).upper()), None)
                
                if k_c and a_c and m_c:
                    df_final = df_raw[[k_c, a_c, m_c]].copy()
                    df_final.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                    df_final.insert(0, "Mamül Adı", df_raw[u_a_c] if u_a_c else "-")
                    df_final.insert(1, "Mamül Kodu", df_raw[u_k_c] if u_k_c else "-")
                    df_final.insert(0, "İş Emri", is_emri_no)
                    df_final["Hazırlanan Adet"] = 0
                    
                    if st.button(f"'{is_emri_no}' İş Emrini Kaydet"):
                        old = get_internal_data("Is_Emirleri")
                        conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_final], ignore_index=True))
                        st.success("İş Emri Kaydedildi!"); st.cache_data.clear()
            except Exception as e: st.error(f"Excel Okuma Hatası: {e}")

    df_emirler = get_internal_data("Is_Emirleri")
    if not df_emirler.empty:
        secim = st.selectbox("Hazırlanacak İş Emri:", ["Seçiniz..."] + sorted(df_emirler["İş Emri"].unique().tolist()))
        if secim != "Seçiniz...":
            df_sub = df_emirler[df_emirler["İş Emri"] == secim].copy()
            # UI Düzenlemesi: Mamül bilgilerini personelden sakla
            display_cols = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]
            df_display = df_sub[display_cols].copy()
            df_display["Alınan Adres"] = "GENEL"
            
            st.info("Miktarı ve rafı girip onaylayın.")
            edited = st.data_editor(df_display, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"], hide_index=True, use_container_width=True)
            
            if st.button("HAZIRLIĞI TAMAMLA VE STOKTAN DÜŞ"):
                success_flag = False
                for idx, row in edited.iterrows():
                    # Orijinal tablo (df_sub) üzerinden farkı bul
                    fark = float(row["Hazırlanan Adet"]) - float(df_sub.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        ok, mev = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                        if not ok:
                            st.error(f"❌ {row['Stok Adı']} için {row['Alınan Adres']} rafında stok yetersiz! (Mevcut: {mev})")
                            st.stop()
                        update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], "ADET", fark, is_increase=False)
                        # Veritabanı ana tablosunu (df_emirler) güncelle
                        df_emirler.at[idx, "Hazırlanan Adet"] = row["Hazırlanan Adet"]
                        success_flag = True
                
                if success_flag:
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_emirler)
                    st.success("Kayıt başarılı, stoklar güncellendi!"); st.cache_data.clear(); st.rerun()

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Merkezi Raporlar")
    r_t1, r_t2 = st.tabs(["🏠 Stok Raporu", "🏭 Hazırlık Raporu"])
    with r_t1:
        st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with r_t2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            df_h['%'] = (pd.to_numeric(df_h['Hazırlanan Adet']) / pd.to_numeric(df_h['İhtiyaç Miktarı']) * 100).round(1)
            st.dataframe(df_h, use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
