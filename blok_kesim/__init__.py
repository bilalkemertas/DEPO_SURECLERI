"""
Blok ve Rulo Sünger Kesim Otomasyonu
=====================================

Ana paket.
"""

from blok_kesim.state import state, Messages
from blok_kesim.main import run_blok_kesim

__version__ = "2.0.0"
__all__ = ["BlokKesimState", "Messages", "run_blok_kesim"]
