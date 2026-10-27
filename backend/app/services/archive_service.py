"""
Layanan Manajemen Arsip Internal Dokumen SSEB-AI.

Mengatur penyimpanan dan pengelompokan otomatis setiap file PDF dan DOCX
yang digenerate atau didownload ke dalam subdirektori internal masing-masing:
- direktori-nota_dinas/
- direktori-telaah_staff/
- direktori-kka_sesko/
- direktori-lapju/
- direktori-surat_biasa/
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any

from ..config import settings

logger = logging.getLogger(__name__)

# Pemetaan kategori dokumen ke nama subdirektori internal
ARCHIVE_DIRECTORIES: Dict[str, str] = {
    "nota_dinas": "direktori-nota_dinas",
    "telaah_staff": "direktori-telaah_staff",
    "telaahan_staf": "direktori-telaah_staff",
    "kka_sesko": "direktori-kka_sesko",
    "kka_seskoal": "direktori-kka_sesko",
    "kka": "direktori-kka_sesko",
    "lapju": "direktori-lapju",
    "surat_biasa": "direktori-surat_biasa",
    "surat": "direktori-surat_biasa",
}

# Daftar subdirektori internal resmi
ALL_ARCHIVE_DIRS: List[str] = [
    "direktori-nota_dinas",
    "direktori-telaah_staff",
    "direktori-kka_sesko",
    "direktori-lapju",
    "direktori-surat_biasa",
]


def detect_doc_type_from_filename(filename: str) -> str:
    """
    Mendeteksi tipe naskah dinas berdasarkan prefix atau nama file.
    """
    name = Path(filename).name.lower()
    if name.startswith("nota_dinas"):
        return "nota_dinas"
    elif name.startswith("telaahan_staf") or name.startswith("telaah_staff"):
        return "telaah_staff"
    elif name.startswith("kka_") or "kka" in name:
        return "kka_sesko"
    elif name.startswith("lapju_") or "lapju" in name:
        return "lapju"
    elif name.startswith("surat_") or "surat" in name:
        return "surat_biasa"
    return "surat_biasa"


def get_archive_dir(doc_type_or_dir_name: str) -> Path:
    """
    Mengambil path subdirektori internal untuk tipe naskah tertentu,
    sekaligus memastikan direktorinya sudah dibuat di disk.
    """
    dir_name = ARCHIVE_DIRECTORIES.get(doc_type_or_dir_name.lower(), doc_type_or_dir_name)
    if dir_name not in ALL_ARCHIVE_DIRS:
        # Fallback jika string tidak cocok langsung
        detected = detect_doc_type_from_filename(doc_type_or_dir_name)
        dir_name = ARCHIVE_DIRECTORIES.get(detected, "direktori-surat_biasa")

    target_dir = settings.OUTPUT_DIR / dir_name
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def init_archive_directories() -> None:
    """
    Membuat seluruh folder direktori internal jika belum ada di dalam settings.OUTPUT_DIR.
    """
    for dir_name in ALL_ARCHIVE_DIRS:
        (settings.OUTPUT_DIR / dir_name).mkdir(parents=True, exist_ok=True)


def archive_file(source_path: Path, doc_type: Optional[str] = None) -> Optional[Path]:
    """
    Menyimpan otomatis file PDF atau DOCX ke direktori internal sesuai tipe dokumen.
    Jika source_path ada di disk, file akan disalin ke direktori target yang sesuai.
    """
    if not source_path or not source_path.exists() or not source_path.is_file():
        logger.warning(f"[ARCHIVE] File sumber tidak ditemukan untuk diarsipkan: {source_path}")
        return None

    if not doc_type:
        doc_type = detect_doc_type_from_filename(source_path.name)

    target_dir = get_archive_dir(doc_type)
    dest_path = target_dir / source_path.name

    try:
        shutil.copy2(source_path, dest_path)
        logger.info(f"[ARCHIVE] Berhasil menyimpan file ke direktori internal '{target_dir.name}': {dest_path.name}")
        return dest_path
    except Exception as e:
        logger.error(f"[ARCHIVE] Gagal menyalin file {source_path} ke {dest_path}: {e}")
        return None


def ensure_archived_on_download(file_path: Path) -> Optional[Path]:
    """
    Memastikan bahwa file yang didownload sudah tersimpan di subdirektori internalnya.
    """
    if not file_path or not file_path.exists():
        return None
    # Jika file sudah berada di dalam subdirektori internal, tidak perlu disalin ulang
    parent_name = file_path.parent.name
    if parent_name in ALL_ARCHIVE_DIRS:
        return file_path
    return archive_file(file_path)


def find_file_in_output_or_archive(candidates: List[str]) -> Optional[Path]:
    """
    Mencari file naskah (PDF/DOCX) di root settings.OUTPUT_DIR
    serta di seluruh subdirektori internal bertipe dokumen.
    """
    # 1. Cek langsung di root OUTPUT_DIR
    for filename in candidates:
        candidate_path = settings.OUTPUT_DIR / filename
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path

    # 2. Cek di setiap subdirektori internal
    for dir_name in ALL_ARCHIVE_DIRS:
        sub_dir = settings.OUTPUT_DIR / dir_name
        if not sub_dir.exists():
            continue
        for filename in candidates:
            candidate_path = sub_dir / filename
            if candidate_path.exists() and candidate_path.is_file():
                return candidate_path

    return None


def sync_existing_output_files() -> Dict[str, int]:
    """
    Menyinkronkan dan mengelompokkan file-file naskah yang sudah ada
    di root settings.OUTPUT_DIR ke masing-masing subdirektori internal.
    """
    init_archive_directories()
    stats = {d: 0 for d in ALL_ARCHIVE_DIRS}

    if not settings.OUTPUT_DIR.exists():
        return stats

    for file_path in settings.OUTPUT_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".pdf", ".docx"]:
            # Abaikan file khusus non-naskah jika ada
            if file_path.name.startswith("_") or file_path.name.startswith("."):
                continue
            doc_type = detect_doc_type_from_filename(file_path.name)
            archived = archive_file(file_path, doc_type)
            if archived:
                target_dir_name = ARCHIVE_DIRECTORIES.get(doc_type, "direktori-surat_biasa")
                stats[target_dir_name] += 1

    return stats


def get_archive_summary() -> Dict[str, Any]:
    """
    Mengambil ringkasan status file pada seluruh subdirektori internal.
    """
    init_archive_directories()
    summary: Dict[str, Any] = {}
    for dir_name in ALL_ARCHIVE_DIRS:
        folder = settings.OUTPUT_DIR / dir_name
        files = [f for f in folder.iterdir() if f.is_file()]
        pdf_files = [f.name for f in files if f.suffix.lower() == ".pdf"]
        docx_files = [f.name for f in files if f.suffix.lower() == ".docx"]
        sorted_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
        summary[dir_name] = {
            "path": str(folder),
            "total_files": len(files),
            "pdf_count": len(pdf_files),
            "docx_count": len(docx_files),
            "recent_files": [f.name for f in sorted_files[:10]]
        }
    return summary
