import streamlit as st
import veritabani
import pandas as pd
from datetime import datetime

def go_home(): 
    st.session_state.page = 'home'

# --- FORM TEMİZLEME ---
def clear_form():
    for key in [
        "s_kod", "s_lot", "s_mik", "s_dur",
        "src_adr", "dst_adr", "sec", "move_type"
    ]:
        if key in st.session_state:
            del st.session_state[key]

def goster():
    if st.button("⬅️ ANA MENÜ"): 
        go_home()
        st.rerun()
        
    st.subheader("📊 Stok Hareketleri")
    
    with st.container(border=True):
        move_type = st.selectbox(
            "İşlem Tipi:", 
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], 
            key="move_type"
        )
        
        katalog = veritabani.get_katalog()
        sec = st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="sec"
        )
        
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input(
                "📦 Malzeme Kodu:",
                value=st.session_state.get(
                    "s_kod",
                    sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else ""
                ),
                key="s_kod"
            ).upper().strip()
            
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox(
                "Durum:", 
                ["Kullanılabilir", "Hasarlı", "Karantina"], 
                key="s_dur"
            )

        st.markdown("---")
        
        src_adr = "-"
        dst_adr = "-"
        
        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()
        
        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()
        
        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()

        # --- KAYDET ---
        if st.button("HAREKETİ KAYDET", use_container_width=True, type="primary"):
            if not s_kod or s_mik <= 0:
                st.error("Lütfen Malzeme Kodu ve geçerli bir Miktar girin!")
                return

            df_stok = veritabani.get_internal_data("Stok")
            df_hareketler = veritabani.get_internal_data("Hareketler")
            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            personel = st.session_state.user if 'user' in st.session_state else "Sistem"
            
            df_stok['Kod'] = df_stok['Kod'].astype(str).str.strip().str.upper()
            df_stok['Adres'] = df_stok['Adres'].astype(str).str.strip().str.upper()
            df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)

            yeni_hareket_satiri = {
                "Tarih": islem_zamani,
                "İşlem": move_type,
                "İş Emri": "-",
                "Kod": s_kod,
                "İsim": sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" and len(sec.split(" | ")) > 1 else "MANUEL ÜRÜN",
                "Adres": dst_adr if move_type == "GİRİŞ" else src_adr,
                "Miktar": s_mik,
                "Personel": personel,
                "Durum": s_dur,
                "Lot": s_lot,
                "Kaynak_Adres": src_adr,
                "Hedef_Adres": dst_adr
            }

            success_stok = False
            
            if move_type == "GİRİŞ":
                mask = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == dst_adr)
                if mask.any():
                    df_stok.loc[mask, 'Miktar'] += s_mik
                else:
                    new_row = pd.DataFrame([{
                        "Kod": s_kod,
                        "İsim": yeni_hareket_satiri["İsim"],
                        "Adres": dst_adr,
                        "Miktar": s_mik,
                        "Durum": s_dur
                    }])
                    df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                success_stok = True

            elif move_type == "ÇIKIŞ":
                mask = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == src_adr)
                if mask.any():
                    mevcut = df_stok.loc[mask, 'Miktar'].values[0]
                    df_stok.loc[mask, 'Miktar'] = max(0, mevcut - s_mik)
                    success_stok = True
                else:
                    st.warning(f"{s_kod} kodu {src_adr} adresinde bulunamadı, hareket kaydedildi.")

            elif move_type == "İÇ TRANSFER":
                src_mask = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == src_adr)
                dst_mask = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == dst_adr)
                
                if src_mask.any():
                    mevcut_src = df_stok.loc[src_mask, 'Miktar'].values[0]
                    df_stok.loc[src_mask, 'Miktar'] = max(0, mevcut_src - s_mik)
                    
                    if dst_mask.any():
                        df_stok.loc[dst_mask, 'Miktar'] += s_mik
                    else:
                        new_row = pd.DataFrame([{
                            "Kod": s_kod,
                            "İsim": yeni_hareket_satiri["İsim"],
                            "Adres": dst_adr,
                            "Miktar": s_mik,
                            "Durum": s_dur
                        }])
                        df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                    
                    success_stok = True
                else:
                    st.error("Kaynak adreste ürün bulunamadı!")

            if success_stok or move_type == "ÇIKIŞ":
                veritabani.update_data("Stok", df_stok)
                yeni_log_df = pd.concat(
                    [df_hareketler, pd.DataFrame([yeni_hareket_satiri])],
                    ignore_index=True
                )
                veritabani.update_data("Hareketler", yeni_log_df)
                
                st.success(f"{move_type} işlemi kaydedildi!")
                st.cache_data.clear()
                
                # --- OTOMATİK TEMİZLE + RERUN ---
                clear_form()
                st.rerun()
