from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class JenisTandaTangan(str, Enum):
    LANGSUNG = "LANGSUNG"
    MEWAKILI = "MEWAKILI"

class ItemKegiatanLapju(BaseModel):
    no_urut: int = Field(default=1, description="Nomor urut kegiatan")
    nomor_dipa: str = Field(default="SP DIPA-012.01.1.678901/2025", description="Nomor DIPA")
    tanggal_dipa: str = Field(default="28 November 2024", description="Tanggal DIPA")
    nama_kegiatan: str = Field(..., description="Uraian Program/Kegiatan/KRO/RO/Komponen/Akun/Item")
    pagu_anggaran: float = Field(..., description="Pagu Anggaran DIPA dalam Rupiah")
    nilai_kontrak: Optional[float] = Field(default=0.0, description="Nilai Kontrak dalam Rupiah (0 jika belum kontrak)")
    nomor_kontrak: Optional[str] = Field(default="-", description="Nomor Surat Perjanjian / Kontrak")
    tanggal_kontrak: Optional[str] = Field(default="-", description="Tanggal Surat Perjanjian / Kontrak")
    tds: Optional[str] = Field(default="-", description="Target Deadline Selesai (TDS)")
    penyedia: Optional[str] = Field(default="-", description="Nama Perusahaan / Penyedia Barang Jasa")
    anggaran_terserap: Optional[float] = Field(default=0.0, description="Realisasi Anggaran Terserap dalam Rupiah")
    sisa_anggaran: Optional[float] = Field(default=0.0, description="Sisa Anggaran dalam Rupiah")
    persentase_fisik: int = Field(default=0, description="Persentase Kemajuan Fisik (0-100%)")
    persentase_admin: int = Field(default=0, description="Persentase Kemajuan Administrasi (0-100%)")
    keterangan_admin: Optional[List[str]] = Field(default_factory=list, description="Catatan tahapan administrasi")
    keterangan_fisik: Optional[List[str]] = Field(default_factory=list, description="Catatan tahapan fisik / pengiriman")

class LapjuTotalsModel(BaseModel):
    total_pagu: float = 0.0
    total_nilai_kontrak: float = 0.0
    total_anggaran_terserap: float = 0.0
    total_sisa_anggaran: float = 0.0
    rata_rata_fisik: float = 0.0
    rata_rata_admin: float = 0.0
    total_pagu_formatted: str = "Rp 0,00"
    total_nilai_kontrak_formatted: str = "Rp 0,00"
    total_terserap_formatted: str = "Rp 0,00"
    total_sisa_formatted: str = "Rp 0,00"

class LapjuGenerateRequest(BaseModel):
    kop_utama: str = Field(default="MARKAS BESAR ANGKATAN LAUT", description="Kop Utama")
    kop_satker: str = Field(default="DINAS PENGADAAN ANGKATAN LAUT", description="Kop Satuan Kerja Pelaksana")
    nomor_surat: Optional[str] = Field(default=None, description="Nomor Naskah Surat Pengantar Lapju")
    tempat: str = Field(default="Jakarta", description="Tempat penandatanganan")
    tanggal_surat: Optional[str] = Field(default=None, description="Tanggal lengkap surat pengantar")
    bulan: str = Field(default="April", description="Periode Bulan Pelaporan")
    tahun: int = Field(default=2025, description="Tahun Anggaran")
    klasifikasi: str = Field(default="Biasa", description="Klasifikasi Keamanan Surat")
    lampiran_keterangan: str = Field(default="Dua lembar", description="Keterangan jumlah lampiran")
    perihal: str = Field(default="Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa", description="Perihal Surat")
    kepada_yth: str = Field(default="Asisten Logistik Kasal", description="Pejabat Penerima Surat Pengantar")
    kota_tujuan: str = Field(default="Jakarta", description="Kota Tujuan Penerima")
    dasar_rujukan: str = Field(default="Surat Perintah Kasal Nomor Sprin/123/I/2025 tanggal 10 Januari 2025", description="Dasar rujukan pengiriman laporan")
    
    # Penandatangan & Jenis TTD
    jabatan_penandatangan: str = Field(default="Kepala Dinas Pengadaan Angkatan Laut", description="Jabatan Penandatangan")
    jenis_ttd: JenisTandaTangan = Field(default=JenisTandaTangan.MEWAKILI, description="Jenis TTD: LANGSUNG atau MEWAKILI")
    nama_penandatangan: str = Field(default="Budi Santoso, S.E., M.M.", description="Nama Lengkap Penandatangan & Gelar")
    pangkat_korps_nrp: str = Field(default="Laksamana Pertama TNI NRP 12345/P", description="Pangkat, Korps, dan NRP")
    
    # Tembusan & Paraf
    tembusan: List[str] = Field(
        default=[
            "Kepala Staf Angkatan Laut",
            "Wakil Kepala Staf Angkatan Laut",
            "Inspektur Jenderal Angkatan Laut",
            "Asisten Perencanaan dan Anggaran Kasal"
        ],
        description="Daftar Pejabat Tembusan"
    )
    daftar_paraf: Optional[List[Dict[str, str]]] = Field(
        default=[
            {"jabatan": "Paren", "paraf": ""},
            {"jabatan": "Ka TU", "paraf": ""}
        ],
        description="Tabel Paraf Koordinasi Internal"
    )
    
    items: List[ItemKegiatanLapju] = Field(..., description="Daftar kegiatan belanja modal (Tabel 13 Kolom)")
    konten_custom: Optional[str] = Field(default=None, description="Teks kustom surat pengantar hasil editan")

class LapjuDraftResponse(BaseModel):
    status: str = "success"
    nomor_surat: str
    tanggal_surat: str
    ringkasan_teks: str
    # Dua pasal formal surat pengantar — editor Android mengedit INI SAJA.
    # Sebelumnya editor memakai ringkasan_teks utuh (KOP+rekap) yang saat dicetak
    # menggantikan pasal resmi di PDF (badan surat berisi blok rekap mentah).
    pasal_list: List[str] = Field(default_factory=list)
    totals: LapjuTotalsModel
    items_processed: List[Dict[str, Any]]

class LapjuGenerateResponse(BaseModel):
    status: str = "success"
    message: str = "Laporan Kemajuan (Lapju) berhasil dibuat"
    id: str
    surat_id: str
    nomor_surat: str
    file_path: str  # hanya nama berkas, bukan path absolut server
    download_url: str
    preview_pdf_url: str
    totals: LapjuTotalsModel