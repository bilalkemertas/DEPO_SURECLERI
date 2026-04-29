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
        for col in ['Kod', 'kod', 'Adres', 'adres', 'İş Emri']:
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
    sku_count, total_stok = 0, 0
    if not df_ana.empty:
        sku_count = len(df_ana['Kod'].unique())
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

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): 
        st.session_state.secili_is_emri = None
        go_home(); st.rerun()
    
    st.subheader("🏭 Üretim Hazırlık Ekranı")

    with st.expander("📤 Yeni İş Emri Yükle", expanded=False):
        uploaded_file = st.file_uploader("Excel dosyasını seçin:", type=['xlsx', 'xls'])
        if uploaded_file:
            try:
                # "hazırlık" sekmesini oku
                df_uploaded_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK")
                df_uploaded_raw.columns = [c.strip() for c in df_uploaded_raw.columns]
                
                # "total" sütununu "İhtiyaç Miktarı" yap
                if "total" in df_uploaded_raw.columns:
                    df_uploaded_raw["İhtiyaç Miktarı"] = df_uploaded_raw["total"]
                
                is_emri_adi_f = uploaded_file.name.rsplit('.', 1)[0]
                df_uploaded_raw['İş Emri'] = is_emri_adi_f
                
                # Standart 9 Kolon Yapısı (Mamül Adı, Stok Kodu ve Stok Adı Excel'den geliyor)
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Mamül Kodu", "Birim"]
                
                for c in cols_target:
                    if c not in df_uploaded_raw.columns:
                        df_uploaded_raw[c] = 0 if "Adet" in c or "Miktar" in c else ""
                
                df_save = df_uploaded_raw[cols_target]
                
                st.info(f"📂 'hazırlık' sekmesi okundu. İş Emri: {is_emri_adi_f}")
                st.dataframe(df_save, use_container_width=True, hide_index=True)
                
                if st.button("VERİTABANINA (IS_EMIRLERI) ŞİMDİ KAYDET"):
                    eski_veri = get_internal_data("Is_Emirleri")
                    guncel_veri = pd.concat([eski_veri, df_save], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=guncel_veri)
                    st.success(f"✅ {is_emri_adi_f} veritabanına başarıyla eklendi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e:
                st.error(f"Hata: Veri okuma sırasında bir sorun oluştu. -> {e}")

    st.markdown("---")
    
    df_is_emirleri = get_internal_data("Is_Emirleri")
    if not df_is_emirleri.empty:
        liste_is_emri = sorted(df_is_emirleri['İş Emri'].unique().tolist(), reverse=True)
        secilen = st.selectbox("📋 İş Emri Seçin:", ["Seçiniz..."] + liste_is_emri)
        
        if secilen != "Seçiniz...":
            st.session_state.secili_is_emri = secilen
            is_emri_verisi = df_is_emirleri[df_is_emirleri['İş Emri'].astype(str) == str(secilen)].copy()
            
            if not is_emri_verisi.empty:
                st.markdown(f"#### 🛠️ {secilen} Nolu Toplama Listesi")
                
                # PATRON TALİMATI: Ürün Kodu kaldırıldı, Mamül Adı, Stok Kodu ve Stok Adı eklendi
                hazirlik_df = is_emri_verisi[["Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]].copy()
                
                edited_df = st.data_editor(
                    hazirlik_df,
                    column_config={
                        "Mamül Adı": st.column_config.TextColumn("Mamül Adı", disabled=True),
                        "Stok Kodu": st.column_config.TextColumn("Stok Kodu", disabled=True),
                        "Stok Adı": st.column_config.TextColumn("Stok Adı", disabled=True),
                        "İhtiyaç Miktarı": st.column_config.NumberColumn("İhtiyaç", disabled=True),
                        "Hazırlanan Adet": st.column_config.NumberColumn("Toplanan", min_value=0)
                    },
                    use_container_width=True, hide_index=True, key="prod_prep_editor"
                )
                
                if st.button("MİKTARLARI VERİTABANINA İŞLE", use_container_width=True, type="primary"):
                    df_all = get_internal_data("Is_Emirleri")
                    df_others = df_all[df_all['İş Emri'].astype(str) != str(secilen)]
                    is_emri_verisi["Hazırlanan Adet"] = edited_df["Hazırlanan Adet"].values
                    final_df = pd.concat([df_others, is_emri_verisi], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=final_df)
                    st.success("✅ Veritabanı güncellendi!")
                    st.cache_data.clear(); st.rerun()
            else:
                st.warning(f"'{secilen}' detayları bulunamadı.")
    else: st.warning("Sistemde kayıtlı iş emri bulunamadı. Lütfen Excel yükleyin.")

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
            if move_type == "GİRİŞ": s_hedef_adr = st.text_input("📍 Hedef Adres:").upper()
            elif move_type == "ÇIKIŞ": s_kaynak_adr = st.text_input("📍 Kaynak Adres:").upper()
            elif move_type == "İÇ TRANSFER":
                s_kaynak_adr = st.text_input("📍 Kaynak Adres:").upper()
                s_hedef_adr = st.text_input("📍 Hedef Adres:").upper()
            s_mik = st.number_input("Miktar:", min_value=0.0)
        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            st.success(f"{move_type} İşlemi Başarıyla Kaydedildi!")

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
                val_kod, val_isim = parcalar[0].strip(), parcalar[1].strip()
            else: val_kod, val_isim = "", ""
            c_kod, c_isim = st.columns(2)
            with c_kod: s_kod = st.text_input("📦 Malzeme Kodu:", value=val_kod, key=f"sayim_kod_{sec}").upper()
            with c_isim: s_isim = st.text_input("📝 Malzeme Adı:", value=val_isim, key=f"sayim_isim_{sec}").upper()
            s_mik = st.number_input("Sayılan Miktar:", min_value=0.0, step=1.0)
            s_durum = st.selectbox("🛠️ Stok Durumu:", ["Kullanılabilir", "Hasarlı", "İncelemede"])
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), "Adres": s_adr, "Kod": s_kod, 
                    "Miktar": s_mik, "Personel": st.session_state.user, "isim": s_isim, "Durum": s_durum
                })
                st.toast("✅ Eklendi")
        
        if st.session_state['gecici_sayim_listesi']:
            st.markdown("---")
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                cols = st.columns([3, 1])
                cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']}")
                if st.session_state.delete_confirm == idx:
                    if cols[1].button("✅", key=f"conf_{idx}"):
                        st.session_state['gecici_sayim_listesi'].pop(idx)
                        st.session_state.delete_confirm = None; st.rerun()
                else:
                    if cols[1].button("🗑️", key=f"del_{idx}"):
                        st.session_state.delete_confirm = idx; st.rerun()
            
            if st.button("📤 VERİTABANINA GÖNDER", type="primary", use_container_width=True):
                eski = get_internal_data("sayim")
                yeni_df = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                guncel_df = pd.concat([eski, yeni_df], ignore_index=True) if not eski.empty else yeni_df
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=guncel_df)
                st.session_state['gecici_sayim_listesi'] = []; st.rerun()

    with t2:
        st.markdown("#### 📊 Adres Bazlı Sayım Fark Raporu")
        df_stok = get_internal_data("Stok")
        df_sayim_db = get_internal_data("sayim")
        
        if not df_sayim_db.empty:
            pivot_sayim = df_sayim_db.groupby(['Adres', 'Kod',])['Miktar'].sum().reset_index()
            pivot_sayim.columns = ['Adres', 'Kod', 'Sayılan']
            pivot_stok = df_stok.groupby(['Adres', 'Kod',])['Miktar'].sum().reset_index()
            pivot_stok.columns = ['Adres', 'Kod', 'Sistem']
            df_fark = pd.merge(pivot_sayim, pivot_stok, on=['Adres', 'Kod',], how='left').fillna(0)
            df_fark['Fark'] = df_fark['Sayılan'] - df_fark['Sistem']
            df_isimliler = get_internal_data("Urun_Listesi")
            if not df_isimliler.empty:
                df_fark = pd.merge(df_fark, df_isimliler[['kod', 'isim']], left_on='Kod', right_on='kod', how='left')
                df_fark = df_fark[['Adres', 'Kod', 'isim', 'Sistem', 'Sayılan', 'Fark']]

            with st.expander("🔍 Gelişmiş Filtreleme Paneli", expanded=True):
                c1, c2, c3 = st.columns(3)
                f_adr = c1.multiselect("📍 Adres Filtresi:", options=sorted(df_fark['Adres'].unique()))
                f_kod = c2.multiselect("📦 Kod Filtresi:", options=sorted(df_fark['Kod'].unique()))
                f_isim = c3.multiselect("📝 İsim Filtresi:", options=sorted(df_fark['isim'].dropna().unique()))

            if f_adr: df_fark = df_fark[df_fark['Adres'].isin(f_adr)]
            if f_kod: df_fark = df_fark[df_fark['Kod'].isin(f_kod)]
            if f_isim: df_fark = df_fark[df_fark['isim'].isin(f_isim)]

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("SKU Çeşitliliği", len(df_fark))
            m2.metric("Toplam Sayılan", f"{df_fark['Sayılan'].sum():,.0f}")
            m3.metric("Toplam Fark", f"{df_fark['Fark'].sum():,.0f}", delta=df_fark['Fark'].sum())
            st.dataframe(df_fark, use_container_width=True, hide_index=True)
        else: st.warning("Henüz sayım verisi yok.")

# --- 10. GENEL ARŞİV ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Genel Stok Arşivi")
    st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
