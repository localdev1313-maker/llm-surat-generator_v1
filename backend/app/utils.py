from datetime import datetime
from typing import List

BULAN_ID: List[str] = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

def format_tanggal_indonesia(dt: datetime = None) -> str:
    """
    Format tanggal ke dalam format bahasa Indonesia, contoh: '20 Agustus 2026'
    """
    if dt is None:
        dt = datetime.now()
    nama_bulan = BULAN_ID[dt.month - 1]
    return f"{dt.day} {nama_bulan} {dt.year}"

def format_tanggal_lokasi(lokasi: str = "Jakarta", dt: datetime = None) -> str:
    """
    Format lokasi dan tanggal, contoh: 'Jakarta, 20 Agustus 2026'
    """
    return f"{lokasi}, {format_tanggal_indonesia(dt)}"
