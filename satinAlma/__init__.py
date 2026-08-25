"""
Satın Alma - Gmail Modülü
Safaş tedarikçisinden mail ile gelen Excel dosyalarını parse edip
otomatik SAS (Satın Alma Siparişi) oluşturmak için
"""

__version__ = "1.0.0"
__author__ = "BRN WMS"

from .gmail_agent import get_latest_safas_attachment, get_safas_emails_last_n_days
from .excel_parser import parse_safas_excel, enrich_rows_with_lookups, validate_parsed_rows
from .sas_creator import (
    get_last_sas_no,
    generate_next_sas_no,
    create_satin_alma_rows,
    prepare_sheet_append_data,
)
from .barcode_kontrol import check_barcode_duplicate, get_sas_by_barcode

__all__ = [
    "get_latest_safas_attachment",
    "get_safas_emails_last_n_days",
    "parse_safas_excel",
    "enrich_rows_with_lookups",
    "validate_parsed_rows",
    "get_last_sas_no",
    "generate_next_sas_no",
    "create_satin_alma_rows",
    "prepare_sheet_append_data",
    "check_barcode_duplicate",
    "get_sas_by_barcode",
]
