from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TelaahanStafPasal(BaseModel):
    persoalan: str = Field(..., description="Pasal 1: Persoalan")
    praanggapan: str = Field(..., description="Pasal 2: Praanggapan")
    fakta: str = Field(..., description="Pasal 3: Fakta/Data yang Memengaruhi")
    analisis: str = Field(..., description="Pasal 4: Analisis")
    kesimpulan: str = Field(..., description="Pasal 5: Kesimpulan")
    saran: str = Field(..., description="Pasal 6: Saran")

class TelaahanStafInput(BaseModel):
    kop_utama: Optional[str] = "PUSAT KOMANDO OPERASI"
    kop_satuan_bawah: Optional[str] = "SATUAN BAWAH"
    judul: str = Field(..., description="Judul permasalahan telaahan staf (misal: PENGUATAN SISTEM KESIAPSIAGAAN OPERASIONAL)")
    nomor_naskah: Optional[str] = None  # Format: Nomor TS/01/V/2026

    # 6 Poin Masukan Materi Kajian
    input_persoalan: str = Field(..., description="Inti persoalan singkat yang akan dipecahkan")
    input_praanggapan: Optional[str] = ""
    input_fakta: str = Field(..., description="Poin data atau fakta konkret pendukung")
    input_analisis: Optional[str] = ""
    input_kesimpulan: Optional[str] = ""
    input_saran: str = Field(..., description="Usulan tindakan konkret untuk pimpinan")

    # Identitas & Penandatangan
    tempat: Optional[str] = "Jakarta"
    tanggal: Optional[str] = None
    nama_pejabat: str = "Budi Santoso, S.E., M.M."
    pangkat_korps_nrp: Optional[str] = "Kolonel Laut (E) NRP 12345/P"
    jabatan: str = "Komandan Satuan Penindak"

    # Lampiran
    lampiran_list: Optional[List[str]] = None

    # Custom teks jika sudah diedit manual
    konten_custom: Optional[str] = None
    pasal_custom: Optional[Dict[str, str]] = None

class DraftTelaahanStafResponse(BaseModel):
    judul: str
    nomor_naskah: Optional[str]
    pasal: TelaahanStafPasal
    konten_gabungan: str
    lampiran_list: List[str] = []
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)

class TelaahanStafOutput(BaseModel):
    id: str
    judul: str
    nomor_naskah: Optional[str]
    pasal: TelaahanStafPasal
    konten_gabungan: str
    file_path: str
    download_url: str
    download_docx_url: Optional[str] = None
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)

class TelaahanStafRenderRequest(BaseModel):
    kop_utama: Optional[str] = "PUSAT KOMANDO OPERASI"
    kop_satuan_bawah: Optional[str] = "SATUAN BAWAH"
    judul: str
    nomor_naskah: Optional[str] = None
    pasal: TelaahanStafPasal
    tempat: Optional[str] = "Jakarta"
    tanggal: Optional[str] = None
    nama_pejabat: str = "Budi Santoso, S.E., M.M."
    pangkat_korps_nrp: Optional[str] = "Kolonel Laut (E) NRP 12345/P"
    jabatan: str = "Komandan Satuan Penindak"
    lampiran_list: Optional[List[str]] = None
    konten_custom: Optional[str] = None
