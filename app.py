import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo", layout="centered", page_icon="📦")

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
    df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    if worksheet_name == "Is_Emirleri" and not df.empty:
        for col in ["Birim", "Mamül Kodu", "Mamül Adı"]:
            if col not in df.columns: df[col] = "ADET" if col == "Birim" else "-"
    return df

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

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def check_address_stock(kod, adres, miktar):
    df = get_internal_data("Stok")
    if adres == "STOK YOK": return False, 0
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    current = df[(df['Kod'] == kod) & (df['Adres'] == adres)]['Miktar'].sum()
    return current >= miktar, current

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": islem,
            "Adres": adres,
            "Malzeme Kodu": kod,
            "Malzeme Adı": isim if isim else find_name_by_code(kod),
            "Miktar": miktar,
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

def update_stock_record(kod, isim, adres, miktar, is_increase=True):
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    # Eğer adres STOK YOK ise ve giriş yapıyorsak GENEL rafa koyalım
    hedef_adres = "GENEL" if adres == "STOK YOK" else adres
    mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == hedef_adres)
    
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: stok_df.loc[mask, 'Miktar'] -= float(miktar)
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": hedef_adres, "Kod": kod, "İsim": isim if isim else find_name_by_code(kod), "Birim": "ADET", "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)
    st.cache_data.clear()
    return hedef_adres

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
        is_t = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"], key="st_is_t")
        sec = st.selectbox("Hızlı Seçim:", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_is_s")
        k_i = sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else ""
        i_i = sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" else ""
        kod = st.text_input("Stok Kodu:", value=k_i, key="st_is_k").strip().upper()
        isim = st.text_input("Stok Adı:", value=i_i if i_i else find_name_by_code(kod), key="st_is_i").strip().upper()
        adr = st.text_input("Adres:", value="GENEL", key="st_is_a").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, key="st_is_q")
        if st.button("KAYDET", use_container_width=True, type="primary", key="st_is_btn"):
            if is_t == "ÇIKIŞ":
                ok, mev = check_address_stock(kod, adr, qty)
                if not ok: st.error(f"Yetersiz Stok! Mevcut: {mev}"); st.stop()
            update_stock_record(kod, isim, adr, qty, is_increase=(is_t == "GİRİŞ"))
            log_movement(is_t, adr, kod, isim, qty)
            st.success("İşlem Başarılı!")

    with t2:
        e_adr = st.text_input("Nereden:", key="st_tr_f").strip().upper()
        y_adr = st.text_input("Nereye:", key="st_tr_t").strip().upper()
        t_sec = st.selectbox("Ürün Seç:", ["+ MANUEL GİRİŞ"] + katalog_list, key="st_tr_s")
        t_kod = st.text_input("Ürün Kodu:", value=t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else "", key="st_tr_k").strip().upper()
        t_qty = st.number_input("Miktar:", min_value=0.1, key="st_tr_q")
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary", key="st_tr_btn"):
            ok, mev = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                ti = find_name_by_code(t_kod)
                update_stock_record(t_kod, ti, e_adr, t_qty, is_increase=False)
                update_stock_record(t_kod, ti, y_adr, t_qty, is_increase=True)
                log_movement("TRANSFER ÇIKIŞ", e_adr, t_kod, ti, t_qty)
                log_movement("TRANSFER GİRİŞ", y_adr, t_kod, ti, t_qty)
                st.success("Transfer Başarılı!")
            else: st.error(f"Stok Yok! Mevcut: {mev}")

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
    with st.expander("📥 İş Emri Yükle"):
        f = st.file_uploader("Excel Seç:", type=["xlsx"], key="u_f")
        if f:
            try:
                eno = f.name.split('.')[0]
                df_r = pd.read_excel(f, sheet_name="HAZIRLIK", skiprows=3).ffill()
                kc = next((c for c in df_r.columns if "STOK KOD" in str(c).upper()), None)
                ac = next((c for c in df_r.columns if "STOK AD" in str(c).upper()), None)
                mc = next((c for c in df_r.columns if "TOTAL" in str(c).upper() or "MİKTAR" in str(c).upper()), None)
                bc = next((c for c in df_r.columns if "BİRİM" in str(c).upper()), None)
                uac = next((c for c in df_r.columns if "MAMÜL AD" in str(c).upper() or "ÜRÜN AD" in str(c).upper()), None)
                ukc = next((c for c in df_r.columns if "MAMÜL KOD" in str(c).upper() or "ÜRÜN KOD" in str(c).upper()), None)
                if kc and ac and mc:
                    df_f = df_r[[kc, ac, mc]].copy()
                    df_f.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                    df_f["Birim"] = df_r[bc].astype(str).str.upper() if bc else "ADET"
                    df_f.insert(0, "Mamül Adı", df_r[uac] if uac else "-")
                    df_f.insert(1, "Mamül Kodu", df_r[ukc] if ukc else "-")
                    df_f.insert(0, "İş Emri", eno); df_f["Hazırlanan Adet"] = 0
                    if st.button(f"'{eno}' Kaydet", key="u_s_b"):
                        old = get_internal_data("Is_Emirleri")
                        conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                        st.success("Kaydedildi!"); st.cache_data.clear()
            except Exception as e: st.error(f"Hata: {e}")

    df_emirler_master = get_internal_data("Is_Emirleri")
    if not df_emirler_master.empty:
        s = st.selectbox("İş Emri Seç:", ["Seçiniz..."] + sorted(df_emirler_master["İş Emri"].unique().tolist()), key="u_sel")
        if s != "Seçiniz...":
            df_is_emri = df_emirler_master[df_emirler_master["İş Emri"] == s].copy()
            df_prep = df_is_emri.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            
            stok_verisi = get_internal_data("Stok")
            stok_verisi['Miktar'] = pd.to_numeric(stok_verisi['Miktar'], errors='coerce').fillna(0)

            def get_best_address(kod):
                urun_raflari = stok_verisi[(stok_verisi['Kod'] == str(kod).strip().upper()) & (stok_verisi['Miktar'] > 0)]
                if urun_raflari.empty: return "STOK YOK"
                return urun_raflari.loc[urun_raflari['Miktar'].idxmin(), 'Adres']

            df_prep["Alınan Adres"] = df_prep["Stok Kodu"].apply(get_best_address)
            
            bt = df_prep.groupby('Birim')['İhtiyaç Miktarı'].sum()
            ozet = " | ".join([f"{m:.2f} {b}" for b, m in bt.items()])
            st.info(f"💡 Toplam {len(df_prep)} Kalem | {ozet}")
            
            ed = st.data_editor(df_prep, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim"], hide_index=True, use_container_width=True, key="u_ed")
            
            if st.button("HAZIRLIĞI ONAYLA", key="u_ok"):
                for idx, row in ed.iterrows():
                    fark = float(row["Hazırlanan Adet"]) - float(df_prep.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        # --- PATRONUN YENİ MANTIĞI: SANAL TAMAMLAMA ---
                        ok, mevcut = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                        
                        if not ok:
                            # Eksik olan miktar kadar sisteme "Otomatik Giriş" yap
                            eksik = fark - mevcut
                            hedef_adr = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], eksik, is_increase=True)
                            log_movement("OTOMATİK SİSTEM GİRİŞİ (HAZIRLIK)", hedef_adr, row["Stok Kodu"], row["Stok Adı"], eksik)
                            # Artık stokta 'fark' kadar ürün var, hazırlığa devam et
                        
                        # Hazırlık Çıkışını yap
                        adr_son = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], fark, is_increase=False)
                        log_movement(f"{s} ÜRETİM ÇIKIŞ", adr_son, row["Stok Kodu"], row["Stok Adı"], fark)
                        
                        # Master Tablo Dağıtımı
                        kalan = float(row["Hazırlanan Adet"])
                        mask = (df_emirler_master["İş Emri"] == s) & (df_emirler_master["Stok Kodu"] == row["Stok Kodu"])
                        for i in df_emirler_master[mask].index:
                            iht = float(df_emirler_master.at[i, "İhtiyaç Miktarı"])
                            val = iht if kalan >= iht else kalan
                            df_emirler_master.at[i, "Hazırlanan Adet"] = val
                            kalan -= val
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_emirler_master)
                st.success("Sanal tamamlama yapıldı ve hazırlık onaylandı!"); st.cache_data.clear(); st.rerun()

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ", key="n_r"): go_home(); st.rerun()
    st.subheader("📊 Merkezi Raporlar")
    rt1, rt2, rt3 = st.tabs(["🏠 Stok Durumu", "🏭 Hazırlık Takibi", "📜 Hareket Arşivi"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            summary = df_h.groupby('İş Emri')[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            summary['%'] = (summary['Hazırlanan Adet'] / summary['İhtiyaç Miktarı'] * 100).round(1)
            st.dataframe(summary, column_config={"%": st.column_config.ProgressColumn("İlerleme", format="%.1f%%", min_value=0, max_value=100)}, use_container_width=True, hide_index=True)
            st.divider()
            secilen = st.selectbox("Detay:", ["Seçiniz..."] + sorted(summary['İş Emri'].unique().tolist()), key="rep_s")
            if secilen != "Seçiniz...":
                detay = df_h[df_h['İş Emri'] == secilen].copy()
                st.dataframe(detay[["Mamül Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]], use_container_width=True, hide_index=True)
    
    with rt3:
        hareketler = get_internal_data("Sayfa1")
        if not hareketler.empty:
            c1, c2, c3 = st.columns(3)
            fk = c1.text_input("📦 Kod:", key="f_k").strip().upper()
            fi = c2.text_input("🏷️ İsim:", key="f_i").strip().upper()
            fa = c3.text_input("📍 Adres:", key="f_a").strip().upper()
            df_f = hareketler.copy()
            if fk: df_f = df_f[df_f['Malzeme Kodu'].astype(str).str.contains(fk, na=False)]
            if fi: df_f = df_f[df_f['Malzeme Adı'].astype(str).str.contains(fi, na=False)]
            if fa: df_f = df_f[df_f['Adres'].astype(str).str.contains(fa, na=False)]
            st.dataframe(df_f.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
