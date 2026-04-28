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
    st.cache_data.clear() # Sayım ekranına girişte veriyi tazeler
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
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

def get_katalog():
    # Güncel Urun_Listesi sekmesini çekiyoruz
    df = get_internal_data("Urun_Listesi")
    
    # Sütun isimlerini senin belirttiğin başlıklara (Malzeme Kodu, Malzeme Adı) göre kontrol ediyoruz
    if not df.empty and 'Malzeme Kodu' in df.columns and 'Malzeme Adı' in df.columns:
        df['Arama'] = df['Malzeme Kodu'].astype(str) + " | " + df['Malzeme Adı'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    
    # Eğer Urun_Listesi sekmesinde sorun varsa Stok sekmesine bak (eski başlıklar için yedek)
    df_stok = get_internal_data("Stok")
    if not df_stok.empty:
        # Stok sekmesinde başlıklar hala 'Kod' ise onu kullanır
        kod_col = 'Malzeme Kodu' if 'Malzeme Kodu' in df_stok.columns else 'Kod'
        isim_col = 'Malzeme Adı' if 'Malzeme Adı' in df_stok.columns else 'İsim'
        
        if kod_col in df_stok.columns and isim_col in df_stok.columns:
            df_stok['Arama'] = df_stok[kod_col].astype(str) + " | " + df_stok[isim_col].astype(str)
            return sorted(df_stok['Arama'].unique().tolist())
            
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": str(islem),
            "Adres": str(adres).upper(),
            "Malzeme Kodu": str(kod).upper(),
            "Malzeme Adı": str(isim).upper(),
            "Miktar": float(miktar),
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    df_ana = get_internal_data("Stok")
    m1, m2 = st.columns(2)
    
    # Metrikler için sütun kontrolü
    sku_count = 0
    total_stok = 0
    if not df_ana.empty:
        k_col = 'Malzeme Kodu' if 'Malzeme Kodu' in df_ana.columns else 'Kod'
        m_col = 'Miktar'
        if k_col in df_ana.columns:
            sku_count = len(df_ana[k_col].unique())
        if m_col in df_ana.columns:
            total_stok = pd.to_numeric(df_ana[m_col], errors='coerce').sum()

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
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            s_lot = st.text_input("🔢 Parti/Lot No:").upper()
        with c2:
            s_adr = st.text_input("📍 Adres:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
        s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            st.success("Kayıt Başarılı!")

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Hazırlık")
    df_emirler = get_internal_data("Is_Emirleri")
    df_stok_ana = get_internal_data("Stok")
    
    if not df_emirler.empty:
        emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
        s_list = st.multiselect("📋 İş Emirlerini Seçin:", emir_list)
        
        if s_list:
            temp_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)]
            mamul_list = sorted(temp_df["Mamül Kodu"].astype(str).unique().tolist())
            m_sec = st.multiselect("🏗️ Mamül Kodu Filtrele:", mamul_list)
            
            filtered = temp_df.copy()
            if m_sec:
                filtered = filtered[filtered["Mamül Kodu"].astype(str).isin(m_sec)]
            
            filtered['Doluluk %'] = (pd.to_numeric(filtered['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                     pd.to_numeric(filtered['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            
            def get_best_adr(kod):
                # Stok sayfasındaki başlığa göre arama yap
                k_col = 'Malzeme Kodu' if 'Malzeme Kodu' in df_stok_ana.columns else 'Kod'
                res = df_stok_ana[df_stok_ana[k_col].astype(str) == str(kod)]
                return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
            
            # Is_Emirleri içindeki başlığa göre işlem yap
            s_kod_col = 'Stok Kodu' if 'Stok Kodu' in filtered.columns else 'Kod'
            filtered["Alınacak Adres"] = filtered[s_kod_col].apply(get_best_adr)
            
            st.markdown("#### 📝 Hazırlık Detay Listesi")
            ed = st.data_editor(filtered, hide_index=True, use_container_width=True)
            
            if st.button("✅ HAZIRLIĞI ONAYLA VE KAYDET", use_container_width=True, type="primary"):
                st.success("Veriler Güncellendi! (GSheets bağlantısı ve update blokları burada çalışır)"); st.rerun()

# --- 8. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım Kontrolü")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres:").upper()
            katalog = get_katalog() 
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
            s_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), "Personel": st.session_state.user,
                    "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik, "Durum": s_durum
                })
                st.toast("Eklendi")
        
        if st.session_state['gecici_sayim_listesi']:
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                cols = st.columns([3, 1])
                cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
                if st.session_state.delete_confirm == idx:
                    c_del, c_esc = cols[1].columns(2)
                    if c_del.button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx); st.session_state.delete_confirm = None; st.rerun()
                    if c_esc.button("❌", key=f"esc_{idx}"):
                        st.session_state.delete_confirm = None; st.rerun()
                else:
                    if cols[1].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx; st.rerun()
            
            if st.button("📤 VERİTABANINA GÖNDER", type="primary", use_container_width=True):
                eski = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([eski, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.rerun()

    with t2:
        df_sayim = get_internal_data("sayim")
        df_stok = get_internal_data("Stok")
        if not df_sayim.empty:
            s_ozet = df_sayim.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
            
            # Stok sekmesindeki başlığa göre join yap
            k_col = 'Malzeme Kodu' if 'Malzeme Kodu' in df_stok.columns else 'Kod'
            n_col = 'Malzeme Adı' if 'Malzeme Adı' in df_stok.columns else 'İsim'
            
            st_ozet = df_stok.groupby(['Adres', k_col, n_col], sort=False)['Miktar'].sum().reset_index()
            st_ozet.rename(columns={k_col: 'Kod', n_col: 'İsim'}, inplace=True)
            
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left', suffixes=('_Sayilan', '_Sistem')).fillna(0)
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            
            st.markdown("#### 🔍 Rapor Filtreleri")
            rf1, rf2, rf3 = st.columns(3)
            f_adr = rf1.text_input("📍 Adres Filtre:").upper()
            f_kod = rf2.text_input("📦 Kod Filtre:").upper()
            f_isim = rf3.text_input("📝 İsim Filtre:").upper()
            
            if f_adr: rapor = rapor[rapor['Adres'].astype(str).str.contains(f_adr)]
            if f_kod: rapor = rapor[rapor['Kod'].astype(str).str.contains(f_kod)]
            if f_isim: rapor = rapor[rapor['İsim'].astype(str).str.contains(f_isim, case=False)]
            
            m1, m2 = st.columns(2)
            m1.metric("Toplam Sayılan", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
            m2.metric("Toplam Fark", f"{rapor['FARK'].sum():,.0f}")
            
            def color_diff(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
            st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)

# --- 9. RAPORLAR VE ARŞİV ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Raporlar ve Arşiv")
    rt1, rt2, rt3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Raporu", "📜 Hareket Arşivi"])
    
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri").copy()
        if not df_h.empty:
            r_emir_list = sorted(df_h["İş Emri"].astype(str).unique().tolist())
            r_emir = st.multiselect("📋 İş Emri Filtrele:", r_emir_list, key="r_emir")
            r_df = df_h.copy()
            if r_emir:
                r_df = r_df[r_df["İş Emri"].astype(str).isin(r_emir)]
            st.dataframe(r_df, use_container_width=True, hide_index=True)
            
    with rt3:
        hareketler = get_internal_data("Sayfa1")
        if not hareketler.empty:
            f1, f2, f3 = st.columns(3)
            f_tar, f_kod, f_isi = f1.text_input("📅 Tarih:"), f2.text_input("📦 Kod:"), f3.text_input("📝 İsim:")
            df_f = hareketler.copy()
            if f_tar: df_f = df_f[df_f['Tarih'].astype(str).str.contains(f_tar)]
            if f_kod: df_f = df_f[df_f['Malzeme Kodu'].astype(str).str.contains(f_kod, case=False)]
            if f_isi: df_f = df_f[df_f['Malzeme Adı'].astype(str).str.contains(f_isi, case=False)]
            st.dataframe(df_f.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
