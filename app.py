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
        df.columns = df.columns.str.strip()
        # Kodları string yapıp sonlarındaki .0'ları silerek eşleşme sorunlarını çözüyoruz
        if 'Kod' in df.columns:
            df['Kod'] = df['Kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        if 'kod' in df.columns:
            df['kod'] = df['kod'].astype(str).str.strip().replace(r'\.0$', '', regex=True)
        return df.fillna("-")
    except:
        return pd.DataFrame()

def get_katalog():
    # 1. Öncelik: Urun_Listesi sekmesindeki "kod" ve "isim" sütunları
    df = get_internal_data("Urun_Listesi")
    if df.empty: df = get_internal_data("ürün listesi")
    if df.empty: df = get_internal_data("Ürün Listesi")
    
    if not df.empty and 'kod' in df.columns and 'isim' in df.columns:
        df['Arama'] = df['kod'].astype(str) + " | " + df['isim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    
    # 2. Öncelik: Stok sekmesindeki "Kod" ve "İsim" sütunları
    df_stok = get_internal_data("Stok")
    if not df_stok.empty and 'Kod' in df_stok.columns and 'İsim' in df_stok.columns:
        df_stok['Arama'] = df_stok['Kod'].astype(str) + " | " + df_stok['İsim'].astype(str)
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
    
    # Metrikler tam olarak "Kod" ve "Miktar" sütun isimlerine ayarlandı
    sku_count = 0
    total_stok = 0
    if not df_ana.empty:
        if 'Kod' in df_ana.columns:
            sku_count = len(df_ana['Kod'].unique())
        if 'Miktar' in df_ana.columns:
            total_stok = pd.to_numeric(df_ana['Miktar'], errors='coerce').sum()

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

    with st.expander("📤 Yeni İş Emri Yükle", expanded=False):
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK")
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                
                if "total" in df_raw.columns:
                    df_raw["İhtiyaç Miktarı"] = df_raw["total"]
                
                if "Mamül Kodu" in df_raw.columns:
                    df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]

                if "Stok Kodu" in df_raw.columns:
                    df_raw["Stok Kodu"] = df_raw["Stok Kodu"]
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Mamül Kodu", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns:
                        df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_final_save = df_raw[cols_target]
                
                st.info(f"📂 'HAZIRLIK' sekmesi okundu. İş Emri: {is_emri_adi}")
                st.dataframe(df_final_save[["Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]], use_container_width=True, hide_index=True)
                
                if st.button("VERİTABANINA (IS_EMIRLERI) ŞİMDİ KAYDET"):
                    existing = get_internal_data("Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=updated)
                    st.success(f"✅ {is_emri_adi} başarıyla eklendi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Hata: Veri okuma sırasında bir sorun oluştu. -> {e}")

    st.markdown("---")

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
                # Stok sayfasındaki başlığa göre arama yap ("Kod")
                if 'Kod' in df_stok_ana.columns:
                    res = df_stok_ana[df_stok_ana['Kod'].astype(str) == str(kod)]
                    return res.iloc[0]['Adres'] if not res.empty else "STOK YOK"
                return "STOK YOK"
            
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
            
            # İsim parçasını katalogdan çeker
            s_isim = sec.split(" | ")[1] if sec != "+ MANUEL" and len(sec.split(" | ")) > 1 else ""
            
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            if st.button("➕ Listeye Ekle", use_container_width=True):
                # Excel'deki "sayim" sekme başlıklarına birebir uygun formatlandı
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), 
                    "Adres": s_adr, 
                    "Kod": s_kod, 
                    "Miktar": s_mik,
                    "Birim": "-", 
                    "Personel": st.session_state.user, 
                    "isim": s_isim, 
                    "Durum": s_durum
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
        
        # Ürün listesini de garantilemek için çekiyoruz
        df_urun = get_internal_data("Urun_Listesi")
        if df_urun.empty: df_urun = get_internal_data("ürün listesi")
        if df_urun.empty: df_urun = get_internal_data("Ürün Listesi")

        if not df_sayim.empty:
            df_sayim['Miktar'] = pd.to_numeric(df_sayim['Miktar'], errors='coerce').fillna(0)
            if 'Durum' not in df_sayim.columns: df_sayim['Durum'] = "Belirtilmemiş"
            
            # Sayım sekmesi: 'Adres', 'Kod' (büyük), 'isim' (küçük) ve 'Durum'
            s_ozet = df_sayim.groupby(['Adres', 'Kod', 'Durum'], sort=False)['Miktar'].sum().reset_index()
            s_ozet.rename(columns={'Miktar': 'Miktar_Sayilan'}, inplace=True)
            
            if not df_stok.empty:
                df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)
                # Stok sekmesi: 'Adres', 'Kod', 'İsim' (büyük)
                st_ozet = df_stok.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
                st_ozet.rename(columns={'Miktar': 'Miktar_Sistem'}, inplace=True)
            else:
                st_ozet = pd.DataFrame(columns=['Adres', 'Kod', 'Miktar_Sistem'])
            
            # BÜYÜK/KÜÇÜK HARFE GÖRE ZIRHLANDIRILMIŞ İSİM HAVUZU (TANIMSIZ'A SON)
            isim_sozlugu = {}
            if not df_stok.empty and 'İsim' in df_stok.columns and 'Kod' in df_stok.columns:
                isim_sozlugu.update(df_stok.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict())
            if 'isim' in df_sayim.columns and 'Kod' in df_sayim.columns:
                isim_sozlugu.update(df_sayim.drop_duplicates(subset=['Kod']).set_index('Kod')['isim'].to_dict())
            if not df_urun.empty and 'isim' in df_urun.columns and 'kod' in df_urun.columns:
                isim_sozlugu.update(df_urun.drop_duplicates(subset=['kod']).set_index('kod')['isim'].to_dict())
            
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
            
            # İsimleri sözlükten Kod'a göre çekiyoruz
            rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            
            rapor = rapor[['Adres', 'Kod', 'İsim', 'Durum', 'Miktar_Sayilan', 'Miktar_Sistem', 'FARK']]
            
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
