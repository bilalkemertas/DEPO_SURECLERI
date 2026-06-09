import streamlit as st

def init_blok_kesim_state():
    """
    Blok kesim modülü için gerekli tüm session_state değişkenlerini güvenli bir şekilde başlatır.
    """
    if 'eslesme_df' not in st.session_state:
        st.session_state.eslesme_df = None
        
    if 'main_data' not in st.session_state:
        st.session_state.main_data = None
        
    if 'har_data' not in st.session_state:
        st.session_state.har_data = None

    if 'stok_data' not in st.session_state:
        st.session_state.stok_data = None

    if 'clear_form' not in st.session_state:
        st.session_state.clear_form = False
