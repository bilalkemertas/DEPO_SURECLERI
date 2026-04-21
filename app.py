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

# --- 4. YARDIMCI FONKSİYONLAR (Hız İçin Önbellekleme Güçlendirildi) ---
@st.cache_data(ttl=30)
def urun_katalogu_getir():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        if not df.empty:
            df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
            df['İsim'] = df['İsim'].astype(str).str.strip().str.upper()
            # Hem liste hem de hızlı sorgulama için sözlük oluştur
            katalog_dict = dict(zip(df['Kod'], df['İsim']))
            isim_dict = dict(zip(df['İsim'], df['Kod']))
            arama_listesi = sorted((df['Kod'] + " | " + df['İsim']).unique().tolist())
            return ["+ MANUEL GİRİŞ"] + arama_listesi, katalog_dict, isim_dict
        return ["+ MANUEL GİRİŞ"], {}, {}
    except: return ["+ MANUEL GİRİŞ"], {}, {}

def get_stok_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)

def check_address_stock(kod, adres, miktar):
    df = get_stok_data()
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    current = df[(df['Kod'] == kod) & (df['Adres'] == adres)]['Miktar'].sum()
    return current >= miktar, current

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    try: stok_df = get_stok_data()
    except: stok_df = pd.DataFrame(columns=['Adres', 'Kod', 'İsim', 'Birim', 'Miktar'])
    
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

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
    st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (Hızlandırılmış Versiyon) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    t1, t2 = st.tabs(["📥 Giriş/Çıkış", "🔄 Transfer"])
    katalog_list, k_dict, i_dict = urun_katalogu_getir()
    
    with t1:
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        secim = st.selectbox("Ürün Seç (Hızlı Liste):", katalog_list)
        
        # Seçime göre veya girişe göre otomatik tamamlama
        init_kod = secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else ""
        init_isim = secim.split(" | ")[1] if secim != "+ MANUEL GİRİŞ" else ""
        
        kod = st.text_input("Stok Kodu:", value=init_kod).strip().upper()
        # Eğer isim boşsa ve kod katalogda varsa anında çek (Hafızadan)
        if kod in k_dict and not init_isim:
            isim = k_dict[kod]
        else:
            isim = st.text_input("Stok Adı:", value=init_isim).strip().upper()

        adr = st.text_input("Adres:", value="GENEL").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, value=1.0)
        
        if st.button("İŞLEMİ KAYDET", use_container_width=True, type="primary"):
            if is_type == "ÇIKIŞ":
                ok, mevcut = check_address_stock(kod, adr, qty)
                if not ok:
                    st.error(f"Yetersiz Stok! Mevcut: {mevcut}")
                    st.stop()
            update_stock_record(kod, isim, adr, "ADET", qty, is_increase=(is_type == "GİRİŞ"))
            st.success("Başarılı!"); st.cache_data.clear()

    with t2:
        e_adr = st.text_input("Nereden:").strip().upper()
        y_adr = st.text_input("Nereye:").strip().upper()
        t_sec = st.selectbox("Ürün Seç:", katalog_list, key="t_sec")
        
        t_kod_init = t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else ""
        t_isim_init = t_sec.split(" | ")[1] if t_sec != "+ MANUEL GİRİŞ" else ""
        
        t_kod = st.text_input("Ürün Kodu:", value=t_kod_init, key="tk").strip().upper()
        if t_kod in k_dict and not t_isim_init:
            t_isim = k_dict[t_kod]
        else:
            t_isim = st.text_input("Ürün Adı:", value=t_isim_init, key="ti").strip().upper()
            
        t_qty = st.number_input("Miktar:", min_value=0.1, key="tq")
        
        if st.button("TRANSFER ET", use_container_width=True, type="primary"):
            ok, mevcut = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                update_stock_record(t_kod, t_isim, e_adr, "ADET", t_qty, is_increase=False)
                update_stock_record(t_kod, t_isim, y_adr, "ADET", t_qty, is_increase=True)
                st.success("Transfer Başarılı!"); st.cache_data.clear()
            else: st.error(f"Kaynakta stok yok! Mevcut: {mevcut}")

# --- 7. ÜRETİM HAZIRLIK (Saha Hızı Modu) ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Malzeme Hazırlama")
    
    try:
        df_all = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
        emirler = ["Seçiniz..."] + sorted(df_all["İş Emri"].unique().tolist())
    except: emirler = ["Seçiniz..."]

    secim = st.selectbox("Hazırlanacak İş Emri:", emirler)
    
    if secim != "Seçiniz...":
        df_sub = df_all[df_all["İş Emri"] == secim].copy()
        if "Alınan Adres" not in df_sub.columns:
            df_sub["Alınan Adres"] = "GENEL"
        
        st.info("Tablodan 'Alınan Adres' ve 'Hazırlanan Adet' sütunlarını güncelleyin.")
        edited = st.data_editor(
            df_sub, 
            disabled=["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"], 
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("LİSTEYİ ONAYLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
            islem_listesi = []
            for idx, row in edited.iterrows():
                fark = float(row["Hazırlanan Adet"]) - float(df_sub.loc[idx, "Hazırlanan Adet"])
                if fark > 0:
                    ok, mevcut = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                    if not ok:
                        st.error(f"❌ DUR! {row['Stok Adı']} için {row['Alınan Adres']} rafında yeterli stok yok!")
                        st.stop()
                    islem_listesi.append((row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], fark))
            
            for k, i, a, f in islem_listesi:
                update_stock_record(k, i, a, "ADET", f, is_increase=False)
            
            db_save = edited.drop(columns=["Alınan Adres"]) if "Alınan Adres" in edited.columns else edited
            df_all.update(db_save)
            conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_all)
            st.success("Stoklar Güncellendi!"); st.cache_data.clear(); st.rerun()

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Güncel Durum Raporu")
    st.write("🏠 Adres Bazlı Mevcut Stok")
    st.dataframe(get_stok_data(), use_container_width=True, hide_index=True)
    st.write("🏭 İş Emri Hazırlık Durumu")
    st.dataframe(conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0), use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
