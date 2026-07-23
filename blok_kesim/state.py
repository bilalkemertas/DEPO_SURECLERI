"""
Blok Kesim State Yönetimi
"""
import streamlit as st
import pandas as pd
from typing import Dict, List


def init_blok_kesim_state():
    """Streamlit session state'ini başlat"""
    if 'eslesme_df' not in st.session_state:
        st.session_state.eslesme_df = None


class BlokKesimState:
    """State'i yönet"""

    PAGE = 'blok_kesim_page'
    MATCHING_DF = 'eslesme_df'
    WORK_ORDERS = 'operator_work_orders'
    CURRENT_WO_IDX = 'current_work_order_idx'

    PAGE_MENU = 'menu'
    PAGE_PLAN = 'plan'
    PAGE_KESIM_MENU = 'kesim_menu'
    PAGE_KESIM = 'kesim'
    PAGE_RAPOR = 'rapor'

    @staticmethod
    def init() -> None:
        if BlokKesimState.PAGE not in st.session_state:
            st.session_state[BlokKesimState.PAGE] = BlokKesimState.PAGE_MENU
        if BlokKesimState.MATCHING_DF not in st.session_state:
            st.session_state[BlokKesimState.MATCHING_DF] = pd.DataFrame()
        if BlokKesimState.WORK_ORDERS not in st.session_state:
            st.session_state[BlokKesimState.WORK_ORDERS] = []
        if BlokKesimState.CURRENT_WO_IDX not in st.session_state:
            st.session_state[BlokKesimState.CURRENT_WO_IDX] = None

    @staticmethod
    def set_page(page: str) -> None:
        st.session_state[BlokKesimState.PAGE] = page

    @staticmethod
    def get_page() -> str:
        return st.session_state.get(BlokKesimState.PAGE, BlokKesimState.PAGE_MENU)

    @staticmethod
    def set_matching_df(df: pd.DataFrame) -> None:
        st.session_state[BlokKesimState.MATCHING_DF] = df

    @staticmethod
    def get_matching_df() -> pd.DataFrame:
        return st.session_state.get(BlokKesimState.MATCHING_DF, pd.DataFrame())

    @staticmethod
    def add_work_order(work_order: Dict) -> None:
        st.session_state[BlokKesimState.WORK_ORDERS].append(work_order)

    @staticmethod
    def get_work_orders() -> List[Dict]:
        return st.session_state.get(BlokKesimState.WORK_ORDERS, [])

    @staticmethod
    def remove_work_order(idx: int) -> None:
        orders = BlokKesimState.get_work_orders()
        if 0 <= idx < len(orders):
            orders.pop(idx)

    @staticmethod
    def clear_work_orders() -> None:
        st.session_state[BlokKesimState.WORK_ORDERS] = []

    @staticmethod
    def navigate_to(page: str, clear_work_orders: bool = False) -> None:
        BlokKesimState.set_page(page)
        if clear_work_orders:
            BlokKesimState.clear_work_orders()
        st.rerun()


class Messages:
    """UI Metinleri"""

    HOME_TITLE = "🧱 Blok ve Rulo Sünger Kesim Otomasyonu"
    PLAN_BUTTON = "📋 PLAN & İŞ EMRİ YÜKLE"
    KESIM_BUTTON = "🧱 KESİM OPERASYONU"
    RAPOR_BUTTON = "📊 KESİM RAPORLARI"
    PLAN_NO_PLAN = "ℹ️ Kesim planı bulunamadı."
    KESIM_NO_PLAN = "⚠️ Drive'da kesim planı bulunamadı."
    ERROR_NO_SELECTION = "❌ Lütfen en az bir plaka seçiniz!"
    ERROR_HEIGHT_MISMATCH = "❌ Farklı yükseklikteki plakalar seçildi!"
