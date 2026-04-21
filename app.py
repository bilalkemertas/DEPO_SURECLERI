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
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { padding: 10px; font-size: 14px; }
    div[data-testid="stHorizontalBlock"]:first-of-type {
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
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
            try:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
            except: st.error("Secrets ayarları eksik!")
    st.stop()

# --- SAYFA NAVİGASYONU ---
if 'page' not in st.session_state:
    st.session_state.page = 'home'

def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=10)
def urun_katalogu_getir():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        if not df.empty:
            df['Kod'] = df['Kod'].fillna("KODSUZ").astype(str)
            df['İsim'] = df['İsim'].fillna("İSİMSİZ").astype(str)
            df['Arama'] = df['Kod'] + " | " + df['İsim']
            return ["+ YENİ / MANUEL GİRİŞ"] + sorted(df['Arama'].unique().tolist())
        return ["+ YENİ / MANUEL GİRİŞ"]
    except:
        return ["+ YENİ / MANUEL GİRİŞ"]

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    try:
        stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    except:
        stok_df = pd.DataFrame(columns=['Adres', 'Kod', 'İsim', 'Birim', 'Miktar'])
    
    miktar = float(miktar)
    if not stok_df.empty:
        stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
        mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres) & (stok_df['Birim'] == birim)
        if mask.any():
            if is_increase: stok_df.loc[mask, 'Miktar'] += miktar
            else: stok_df.loc[mask, 'Miktar'] -= miktar
        else:
            if is_increase:
                new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
                stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    else:
        if is_increase:
            stok_df = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
    
    stok_df = stok_df[stok_df['Miktar'] >= 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)

# --- 5. HEADER ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1: st.image("brn_logo.webp", width=55) 
with h2: st.markdown(f"<p style='text-align: center; margin: 0; font-size: 14px;'><b>👤 {st.session_state.user.upper()}</b></p>", unsafe_allow_html=True)
with h3: 
    if st.button("Çık", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.page = 'home'
        st.rerun()

st.divider()

# ========================================================
# --- EKRAN YÖNETİMİ ---
# ========================================================

# 🟢 ANA MENÜ 🟢
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.write("")
    
    c1, c2 = st.columns(2)
    with c1: st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
    with c2: st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    
    st.write("")
    st.button("📈 RAPORLAR (Üretim Durumu)", use_container_width=True, on_click=go_rapor)

# 🔵 STOK İŞLEMLERİ 🔵
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜYE DÖN", use_container_width=True): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])
    arama_listesi = urun_katalogu_getir()
    
    with t1:
        with st.container(border=True):
            is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
            adr = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
            secim = st.selectbox("🔍 Kayıtlı Ürün Ara:", arama_listesi, key="sec1")
            if secim == "+ YENİ / MANUEL GİRİŞ":
                kod = st.text_input("Kod:", key="b1").strip().upper()
                isim = st.text_input("İsim:", key="n1").strip().upper()
            else:
                bolunmus = str(secim).split(" | ")
                kod, isim = bolunmus[0].strip(), bolunmus[1].strip()
                st.text_input("Kod:", value=kod, disabled=True, key="b1_l")
                st.text_input("İsim:", value=isim, disabled=True, key="n1_l")
            c1, c2 = st.columns(2)
            with c1: unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="u1")
            with c2: qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="m1")
            if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
                if kod and isim:
                    log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                    yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": is_type, "Adres": adr, "Malzeme Kodu": kod, "Malzeme Adı": isim, "Birim": unit, "Miktar": qty, "Operatör": st.session_state.user}])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni]))
                    update_stock_record(kod, isim, adr, unit, qty, is_increase=(is_type == "GİRİŞ"))
                    st.success("Kaydedildi!"); st.cache_data.clear()
                else: st.error("Eksik bilgi!")

    with t2:
        with st.container(border=True):
            e_adr = st.text_input("Nereden:", key="ea2").strip().upper()
            y_adr = st.text_input("Nereye:", key="ya2").strip().upper()
            t_secim = st.selectbox("🔍 Ürün Ara:", arama_listesi, key="t_sec1")
            if t_secim == "+ YENİ / MANUEL GİRİŞ":
                t_kod = st.text_input("Kod:", key="b2").strip().upper()
                t_isim = st.text_input("İsim:", key="n2").strip().upper()
            else:
                t_b = str(t_secim).split(" | ")
                t_kod, t_isim = t_b[0].strip(), t_b[1].strip()
                st.text_input("Kod:", value=t_kod, disabled=True, key="b2_l"); st.text_input("İsim:", value=t_isim, disabled=True, key="n2_l")
            t_qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
            t_unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
            if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
                if t_kod and t_isim and y_adr and e_adr:
                    log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                    c_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": t_isim, "Birim": t_unit, "Miktar": t_qty, "Operatör": st.session_state.user}])
                    g_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", "Adres": y_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": t_isim, "Birim": t_unit, "Miktar": t_qty, "Operatör": st.session_state.user}])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, c_log, g_log]))
                    update_stock_record(t_kod, t_isim, e_adr, t_unit, t_qty, is_increase=False)
                    update_stock_record(t_kod, t_isim, y_adr, t_unit, t_qty, is_increase=True)
                    st.success("Transfer Kaydedildi!"); st.cache_data.clear()
                else: st.error("Eksik bilgi!")

    with t3:
        if st.button("🔄 SENKRONİZE ET", use_container_width=True):
            with st.spinner("Yükleniyor..."):
                st.cache_data.clear()
                raw = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
                if not raw.empty:
                    raw['Miktar'] = pd.to_numeric(raw['Miktar'], errors='coerce').fillna(0)
                    raw['Net'] = raw.apply(lambda x: x['Miktar'] if x['İşlem'] == 'GİRİŞ' else (-x['Miktar'] if x['İşlem'] == 'ÇIKIŞ' else 0), axis=1)
                    sumry = raw.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
                    sumry.columns = ['Adres', 'Kod', 'İsim', 'Birim', 'Miktar']
                    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=sumry[sumry['Miktar'] > 0])
                    st.success("Senkronize Edildi!")
        stok_data = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        st.dataframe(stok_data, use_container_width=True, hide_index=True)


# 🏭 ÜRETİM HAZIRLIK 🏭
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜYE DÖN", use_container_width=True): go_home(); st.rerun()
    st.markdown("<h4 style='text-align:center;'>🏭 Üretim Hazırlık Süreci</h4>", unsafe_allow_html=True)
    
    # --- 1. DOSYA YÜKLEME ---
    with st.expander("📥 Yeni İş Emri Yükle (Excel)", expanded=False):
        uploaded_file = st.file_uploader("Excel dosyasını seçin", type=["xlsx"])
        if uploaded_file:
            try:
                is_emri_no = uploaded_file.name.split('.')[0]
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                h_idx = 0
                for i, row in df_raw.iterrows():
                    if row.astype(str).str.contains("KOD", case=False, na=False).any():
                        h_idx = i; break
                df_p = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", skiprows=h_idx).ffill()
                
                # AKILLI SÜTUN BULUCU: Öncelik "STOK KODU" ve "STOK ADI", "MAMÜL" hariç.
                k_c = next((c for c in df_p.columns if "STOK KODU" in str(c).upper()), next((c for c in df_p.columns if "KOD" in str(c).upper()), None))
                a_c = next((c for c in df_p.columns if "STOK ADI" in str(c).upper()), next((c for c in df_p.columns if "AD" in str(c).upper() and "MAM" not in str(c).upper()), None))
                m_c = next((c for c in df_p.columns if "TOTAL" in str(c).upper() or "İHTİYAÇ" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                
                if not k_c or not a_c or not m_c:
                    st.error(f"HATA: Sütunlar eşleştirilemedi! Okunan başlıklar: {list(df_p.columns)}")
                    st.stop()
                
                df_f = df_p[[k_c, a_c, m_c]].copy()
                df_f.columns = ["Ürün Kodu", "Ürün Adı", "İhtiyaç Miktarı"]
                df_f.insert(0, "İş Emri", is_emri_no)
                df_f["Hazırlanan Adet"] = 0
                
                if st.button(f"'{is_emri_no}' İş Emrini Veritabanına İşle", type="primary", use_container_width=True):
                    old = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                    st.success(f"{is_emri_no} başarıyla sisteme kaydedildi! Aşağıdan hazırlığa başlayabilirsiniz."); st.cache_data.clear()
            except Exception as e: st.error(f"Hata: {e}")

    st.markdown("---")
    
    # --- 2. İŞ EMRİ SEÇİM ---
    try:
        df_all = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
        emirler_listesi = ["Seçiniz..."] + sorted(df_all["İş Emri"].unique().tolist())
    except: emirler_listesi = ["Seçiniz..."]

    secim = st.selectbox("📋 Hazırlanacak İş Emri Seçin:", emirler_listesi)
    
    if secim != "Seçiniz...":
        mask = df_all["İş Emri"] == secim
        df_sub = df_all[mask].copy()
        
        st.info("Aşağıdaki tabloda 'Hazırlanan Adet' sütununa çift tıklayarak miktarı girebilirsiniz.")
        edited = st.data_editor(df_sub, disabled=["İş Emri", "Ürün Kodu", "Ürün Adı", "İhtiyaç Miktarı"], hide_index=True, use_container_width=True)
        
        if st.button("Hazırlanan Miktarları Kaydet", type="primary"):
            df_all.update(edited) 
            conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_all)
            st.success("Miktarlar güncellendi!"); st.cache_data.clear()


# 📈 RAPORLAR EKRANI 📈
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜYE DÖN", use_container_width=True): go_home(); st.rerun()
    st.markdown("<h4 style='text-align:center;'>📈 Üretim Tamamlanma Raporları</h4>", unsafe_allow_html=True)
    
    try:
        df_all = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
        
        if df_all.empty:
            st.warning("Henüz sisteme yüklenmiş bir iş emri bulunmuyor.")
        else:
            # Rakamları hesaplanabilir hale getir
            df_all['İhtiyaç Miktarı'] = pd.to_numeric(df_all['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            df_all['Hazırlanan Adet'] = pd.to_numeric(df_all['Hazırlanan Adet'], errors='coerce').fillna(0)
            
            # --- 1. GENEL İŞ EMRİ ÖZETİ ---
            st.subheader("Tüm İş Emirleri (Genel Durum)")
            summary = df_all.groupby('İş Emri')[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            # Yüzde Hesaplama (Sıfıra bölünme hatasını engelle)
            summary['Tamamlanma Oranı (%)'] = summary.apply(lambda x: (x['Hazırlanan Adet'] / x['İhtiyaç Miktarı'] * 100) if x['İhtiyaç Miktarı'] > 0 else 0, axis=1)
            summary['Tamamlanma Oranı (%)'] = summary['Tamamlanma Oranı (%)'].round(1)
            
            # İlerleme Çubuğu (Progress Bar) ile Dataframe gösterimi
            st.dataframe(
                summary,
                column_config={
                    "Tamamlanma Oranı (%)": st.column_config.ProgressColumn(
                        "İlerleme %", format="%f%%", min_value=0, max_value=100
                    )
                },
                hide_index=True, use_container_width=True
            )
            
            st.markdown("---")
            
            # --- 2. SATIR BAZLI DETAY ÖZETİ ---
            st.subheader("🔍 Satır Bazlı Detay İnceleme")
            secilen_rapor = st.selectbox("Detayını görmek istediğiniz İş Emrini seçin:", ["Seçiniz..."] + sorted(summary['İş Emri'].tolist()))
            
            if secilen_rapor != "Seçiniz...":
                detay_df = df_all[df_all['İş Emri'] == secilen_rapor].copy()
                detay_df['Tamamlanma (%)'] = detay_df.apply(lambda x: (x['Hazırlanan Adet'] / x['İhtiyaç Miktarı'] * 100) if x['İhtiyaç Miktarı'] > 0 else 0, axis=1)
                detay_df['Tamamlanma (%)'] = detay_df['Tamamlanma (%)'].round(1)
                
                # Sadece gerekli sütunları göster
                gosterilecek_df = detay_df[['Ürün Kodu', 'Ürün Adı', 'İhtiyaç Miktarı', 'Hazırlanan Adet', 'Tamamlanma (%)']]
                
                st.dataframe(
                    gosterilecek_df,
                    column_config={
                        "Tamamlanma (%)": st.column_config.ProgressColumn(
                            "Satır İlerlemesi", format="%f%%", min_value=0, max_value=100
                        )
                    },
                    hide_index=True, use_container_width=True
                )
                
    except Exception as e:
        st.error(f"Rapor oluşturulurken bir hata meydana geldi: {e}")

# --- 7. İMZA ---
st.markdown("<br><br><div style='text-align: center; color: #888; font-size: 12px; border-top: 1px solid #eee;'><b>BRN SLEEP PRODUCTS</b><br>BİLAL KEMERTAŞ</div>", unsafe_allow_html=True)
