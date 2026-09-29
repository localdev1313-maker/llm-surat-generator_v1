from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field

# Catatan: field llm_degraded/llm_warnings pada respons menandai apakah generasi
# LLM gagal/timeout dan output memakai templat standar (lihat services/llm_health).
# Klien dapat memakainya untuk memberi peringatan kepada pengguna.

class SuratRequest(BaseModel):
    jenis_surat: str
    nama_pengirim: str
    alamat_pengirim: str
    nama_penerima: str
    alamat_penerima: str
    perihal: str
    isi_ringkas: str
    template_style: Optional[str] = "formal"
    bahasa: Optional[str] = "id"
    konten_custom: Optional[str] = None  # Jika diisi, gunakan teks ini langsung tanpa memanggil LLM

class SuratResponse(BaseModel):
    id: str
    konten_surat: str
    # Hanya NAMA BERKAS (bukan path absolut server) — tidak membocorkan
    # struktur direktori filesystem ke klien.
    file_path: str
    download_url: str
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)

class NotaDinasPoinItem(BaseModel):
    teks: str
    sub_poin: Optional[List[str]] = None

class NotaDinasRequest(BaseModel):
    kop_utama: Optional[str] = "PUSAT SIBER PERTAHANAN"
    kop_sub: Optional[str] = "SATUAN BAWAH"
    nomor_surat: str
    kepada: str
    dari: str
    perihal: str
    dasar: Optional[str] = ""  # setiap baris satu dasar
    isi_ringkas_1: Optional[str] = ""  # untuk web form lama
    isi_ringkas_2: Optional[str] = ""
    isi_ringkas_3: Optional[str] = ""
    isi_ringkas_4: Optional[str] = ""
    isi_ringkas_5: Optional[str] = ""
    isi_ringkas: Optional[List[Union[str, Dict[str, Any], NotaDinasPoinItem]]] = None  # poin & sub-poin
    isi_custom_list: Optional[List[Union[str, Dict[str, Any], NotaDinasPoinItem]]] = None  # Paragraf hasil edit pengguna
    konten_custom: Optional[str] = None  # Teks naskah lengkap hasil edit pengguna
    nama_pejabat: Optional[str] = "Budi Santoso, S.E., M.M."  # penandatangan nota dinas
    jabatan_pejabat: Optional[str] = "Komandan Satuan Penindak"
    pangkat_pejabat: Optional[str] = ""  # misal: Kolonel Laut (E) NRP 12345/P
    tembusan: Optional[List[str]] = None  # daftar pejabat tembusan
    jenis_penutup: Optional[str] = "perhatian"  # "periksa" (atasan) atau "perhatian" (sejajar/bawahan)

class DraftSuratResponse(BaseModel):
    perihal: str
    konten_draft: str
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)

class DraftNotaDinasResponse(BaseModel):
    perihal: str
    nomor_surat: str
    dasar_list: List[str]
    isi_list: List[Dict[str, Any]]
    konten_gabungan: str
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)

# Re-export Telaahan Staf Schemas
from .schemas.telaahan_staf import (
    TelaahanStafPasal,
    TelaahanStafInput,
    DraftTelaahanStafResponse,
    TelaahanStafOutput,
    TelaahanStafRenderRequest
)
from .schemas.kajian import (
    KajianCategory,
    KKAModelType,
    TelaahanStafSections,
    KKAStudiKasusSections,
    KKAAnalisisMoESections,
    KKAPemecahanMasalahSections,
    KajianGenerateRequest,
    KajianDraftResponse,
    KajianRenderPDFRequest,
    KajianGenerateResponse
)
from .schemas.lapju import (
    JenisTandaTangan,
    ItemKegiatanLapju,
    LapjuTotalsModel,
    LapjuGenerateRequest,
    LapjuDraftResponse,
    LapjuGenerateResponse
)