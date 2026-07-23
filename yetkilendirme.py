"""
yetkilendirme.py
------------------
Basit rol tabanlı yetkilendirme (admin / operator).

st.secrets içindeki [roles] tablosundan kullanıcının rolünü okur;
app.py login akışında st.session_state['role'] içine yazılır.

secrets.toml örneği (.streamlit/secrets.toml):

    [users]
    bilal = "sifre123"
    ahmet = "sifre456"

    [roles]
    bilal = "admin"
    ahmet = "operator"

Bir kullanıcı [roles] tablosunda tanımlı değilse varsayılan rolü "operator"dur
(yani yeni kullanıcı eklerken rol belirtmeyi unutursan otomatik olarak kısıtlı kalır,
yanlışlıkla admin yetkisi verilmez).
"""
import streamlit as st

ADMIN = "admin"
OPERATOR = "operator"


def get_role() -> str:
    """Mevcut oturumun rolünü döner. Giriş yapılmadıysa 'operator' varsayılır."""
    return st.session_state.get("role", OPERATOR)


def is_admin() -> bool:
    return get_role() == ADMIN


def admin_only(mesaj: str = "🔒 Bu özellik sadece Admin kullanıcılar tarafından kullanılabilir.") -> bool:
    """
    Bir sayfanın/bloğun EN BAŞINDA çağır.
    Admin değilse uyarı basar ve False döner — çağıran taraf bu durumda
    geri kalan kodu çalıştırmamalı (if not admin_only(): return / st.stop()).
    Admin ise True döner, akış normal devam eder.
    """
    if not is_admin():
        st.warning(mesaj)
        return False
    return True


def role_badge():
    """Sidebar'da mevcut kullanıcının rolünü küçük bir rozet olarak gösterir."""
    rol = get_role()
    etiket = "👑 Admin" if rol == ADMIN else "🧑‍🔧 Operatör"
    st.sidebar.caption(f"Rol: {etiket}")
