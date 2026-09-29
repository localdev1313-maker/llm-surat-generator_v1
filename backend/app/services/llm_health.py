"""
Pelacak degradasi LLM per-permintaan (request-scoped).

Ketika Ollama gagal/timeout dan layanan beralih ke teks templat standar,
service memanggil `record_llm_warning()`. Router memulai scope dengan
`start_llm_request_scope()` sebelum pemanggilan, lalu membaca hasilnya lewat
`collect_llm_warnings()` dan menyertakannya pada respons API sehingga klien
(Android/web/Telegram) dapat memberi tahu pengguna bahwa output berasal dari
templat, bukan hasil generasi AI.

ContextVar dipakai agar aman terhadap permintaan konkuren: asyncio.to_thread
menyalin context ke worker thread, sehingga warning yang dicatat di dalam
thread tetap terbaca oleh endpoint yang menunggunya.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import List, Optional

_active_warnings: ContextVar = ContextVar("llm_warnings", default=None)


def start_llm_request_scope() -> None:
    """Mulai pengumpulan warning untuk satu request (dipanggil router/handler)."""
    _active_warnings.set([])


def record_llm_warning(message: str) -> None:
    """Catat degradasi LLM; no-op jika dipanggil di luar scope request."""
    warnings: Optional[List[str]] = _active_warnings.get()
    if warnings is not None:
        warnings.append(message)


def collect_llm_warnings() -> List[str]:
    """Ambil salinan daftar warning degradasi untuk request ini."""
    warnings: Optional[List[str]] = _active_warnings.get()
    return list(warnings) if warnings else []
