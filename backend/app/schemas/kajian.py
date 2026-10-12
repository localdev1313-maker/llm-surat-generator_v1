from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class KajianCategory(str, Enum):
    TELAAHAN_STAF = "TELAAHAN_STAF"
    KKA_SESKOAL = "KKA_SESKOAL"


class KKAModelType(str, Enum):
    STUDI_KASUS = "STUDI_KASUS"
    ANALISIS_MOE = "ANALISIS_MOE"
    PEMECAHAN_MASALAH = "PEMECAHAN_MASALAH"


# ── Section Models ──

class TelaahanStafSections(BaseModel):
    persoalan: str = Field(..., description="Pasal 1: Persoalan")
    praanggapan: str = Field(..., description="Pasal 2: Praanggapan")
    fakta: str = Field(..., description="Pasal 3: Fakta/Data yang Memengaruhi")
    analisis: str = Field(..., description="Pasal 4: Analisis")
    kesimpulan: str = Field(..., description="Pasal 5: Kesimpulan")
    saran: str = Field(..., description="Pasal 6: Saran")


class KKAStudiKasusSections(BaseModel):
    topik: str
    latar_belakang_umum: str
    kronologis_pra: str
    kronologis_kejadian: str
    kronologis_pasca: str
    analisis_kejadian: str
    hal_positif: str
    hal_negatif: str
    manfaat_edukatif: str
    manfaat_inspiratif: str
    manfaat_instruktif: str
    kesimpulan: str
    saran: str
    daftar_pustaka: List[str] = Field(default_factory=list)


class KKAAnalisisMoESections(BaseModel):
    topik: str
    latar_belakang: str
    analisis_umum: str
    pembahasan_moe: str
    tabel_parameter: List[Dict[str, Any]] = Field(default_factory=list)
    tabel_bobot_level1: List[Dict[str, Any]] = Field(default_factory=list)
    tabel_bobot_level2: List[Dict[str, Any]] = Field(default_factory=list)
    perhitungan_moe: str
    pengambilan_keputusan: str
    kesimpulan: str
    saran: str
    daftar_pustaka: List[str] = Field(default_factory=list)


class KKAPemecahanMasalahSections(BaseModel):
    judul: str
    pokok_masalah: str
    permasalahan_list: List[str] = Field(default_factory=list)
    pemecahan_umum: str
    pemecahan_persoalan_list: List[Dict[str, str]] = Field(default_factory=list)
    kesimpulan: str
    saran: str
    daftar_pustaka: List[str] = Field(default_factory=list)


# ── Request & Response Models ──

class KajianGenerateRequest(BaseModel):
    kategori: KajianCategory = Field(default=KajianCategory.TELAAHAN_STAF, description="Kategori kajian: TELAAHAN_STAF atau KKA_SESKOAL")
    kka_model: Optional[KKAModelType] = Field(default=None, description="Sub-model KKA: STUDI_KASUS, ANALISIS_MOE, atau PEMECAHAN_MASALAH")
    
    # Metadata Dokumen
    kop_utama: str = Field(default="PUSAT KOMANDO OPERASI", description="Kop Nama Badan Utama")
    kop_satuan_bawah: str = Field(default="SATUAN BAWAH", description="Kop Sub Satuan / Divisi")
    judul_atau_topik: str = Field(..., description="Judul Kajian / Topik Permasalahan")
    nomor_naskah: Optional[str] = Field(default=None, description="Nomor Naskah TS / Penomoran Dokumen")
    tempat: str = Field(default="Jakarta", description="Tempat penetapan / tanda tangan")
    tanggal: Optional[str] = Field(default=None, description="Tanggal naskah (opsional)")
    
    # Data Personel / Pasis
    nama_pejabat_atau_pasis: str = Field(default="Budi Santoso, S.E., M.M.", description="Nama Lengkap Penandatangan / Pasis")
    pangkat_korps_nrp: Optional[str] = Field(default="Kolonel Laut (E) NRP 12345/P", description="Pangkat, Korps, dan NRP")
    jabatan: str = Field(default="Komandan Satuan Penindak", description="Tajuk Jabatan Penandatangan")
    nomor_pasis: Optional[str] = Field(default=None, description="Nomor Pasis Seskoal")
    kelompok_pasis: Optional[str] = Field(default=None, description="Kelompok Pasis Seskoal (contoh: Kelompok 1)")
    jenis_dan_tahun_pendidikan: Optional[str] = Field(default="PASIS DIKREG SESKOAL ANGKATAN KE-64 TP 2026", description="Jenis & TP Pendidikan")
    
    # Input Poin untuk Pembentukan Konten AI
    input_persoalan: Optional[str] = Field(default=None, description="Poin persoalan inti yang dihadapi")
    input_praanggapan: Optional[str] = Field(default=None, description="Dugaan beralasan / asumsi logis")
    input_fakta: Optional[str] = Field(default=None, description="Fakta lapangan dan data konkret pendukung")
    input_analisis: Optional[str] = Field(default=None, description="Arahan atau fokus analisis")
    input_kesimpulan: Optional[str] = Field(default=None, description="Arahan kesimpulan")
    input_saran: Optional[str] = Field(default=None, description="Usulan solusi / saran konkret")
    
    # Khusus KKA Studi Kasus
    input_kronologis_pra: Optional[str] = Field(default=None, description="Kronologi pra-kejadian")
    input_kronologis_kejadian: Optional[str] = Field(default=None, description="Kronologi saat kejadian")
    input_kronologis_pasca: Optional[str] = Field(default=None, description="Kronologi pasca-kejadian")
    
    # Khusus KKA Analisis MoE
    input_alutsista_opsi_1: Optional[str] = Field(default="Kapal Patroli Cepat (KPC)", description="Opsi Alternatif 1")
    input_alutsista_opsi_2: Optional[str] = Field(default="Pesawat Patroli Maritim (MPA)", description="Opsi Alternatif 2")
    
    # Khusus KKA Pemecahan Masalah
    input_pokok_masalah: Optional[str] = Field(default=None, description="Gap kondisi saat ini vs harapan")
    input_permasalahan_list: Optional[List[str]] = Field(default=None, description="Daftar 3 akar persoalan")
    
    # Lampiran & Kustomisasi
    lampiran_list: Optional[List[str]] = Field(default=None, description="Daftar lampiran dokumen")
    konten_custom: Optional[str] = Field(default=None, description="Teks draf utuh hasil editan pengguna")
    sections_custom: Optional[Dict[str, Any]] = Field(default=None, description="Dictionary bagian-bagian kustom")


class KajianDraftResponse(BaseModel):
    kategori: KajianCategory
    kka_model: Optional[KKAModelType] = None
    judul_atau_topik: str
    nomor_naskah: Optional[str] = None
    sections: Dict[str, Any]
    konten_gabungan: str
    konten_kajian: Optional[str] = None
    lampiran_list: List[str] = Field(default_factory=list)
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)


class KajianRenderPDFRequest(BaseModel):
    kategori: KajianCategory
    kka_model: Optional[KKAModelType] = None
    kop_utama: str = "PUSAT KOMANDO OPERASI"
    kop_satuan_bawah: str = "SATUAN BAWAH"
    judul_atau_topik: str
    nomor_naskah: Optional[str] = None
    tempat: str = "Jakarta"
    tanggal: Optional[str] = None
    nama_pejabat_atau_pasis: str = "Budi Santoso, S.E., M.M."
    pangkat_korps_nrp: Optional[str] = "Kolonel Laut (E) NRP 12345/P"
    jabatan: str = "Komandan Satuan Penindak"
    nomor_pasis: Optional[str] = None
    kelompok_pasis: Optional[str] = None
    jenis_dan_tahun_pendidikan: Optional[str] = "PASIS DIKREG SESKOAL ANGKATAN KE-64 TP 2026"
    sections: Dict[str, Any]
    lampiran_list: Optional[List[str]] = None
    konten_custom: Optional[str] = None


class KajianGenerateResponse(BaseModel):
    status: str = "success"
    message: str = "Kajian berhasil dibuat"
    id: str
    surat_id: Optional[str] = None
    kategori: KajianCategory
    kka_model: Optional[KKAModelType] = None
    judul_atau_topik: str
    konten_kajian: str
    file_path: str
    download_url: str
    preview_pdf_url: Optional[str] = None
    sections: Optional[Dict[str, Any]] = None
    llm_degraded: bool = False
    llm_warnings: List[str] = Field(default_factory=list)
