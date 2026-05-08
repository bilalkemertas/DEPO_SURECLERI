import streamlit as st
import pandas as pd
import veritabani

def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_rapor(): st.session_state.page = 'rapor'
def go_sayim(): 
    st.cache_data.clear()
    st.session_state.page = 'sayim'

def goster():
    # --- İMZAYI SAYFAYA SABİTLEYEN CSS ---
    st.markdown("""
        <style>
        .footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: white;
            color: black;
            text-align: right;
            padding: 10px;
            padding-right: 30px;
            border-top: 1px solid #eee;
            z-index: 999;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    
    df_ana = veritabani.get_internal_data("Stok")
    m1, m2 = st.columns(2)
    
    sku_count, total_stok = 0, 0
    if not df_ana.empty:
        if 'Kod' in df_ana.columns: sku_count = len(df_ana['Kod'].unique())
        if 'Miktar' in df_ana.columns: total_stok = pd.to_numeric(df_ana['Miktar'], errors='coerce').sum()

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

    # --- SABİT İMZA ALANI ---
    st.markdown(
        """
        <div class="footer">
            <p style='margin:0; font-size: 14px; font-weight: bold; color: #1f77b4;'>🚀 Bilal Kemertaş</p>
            <p style='margin:0; font-size: 12px; color: gray;'>Logistics Solutions</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
