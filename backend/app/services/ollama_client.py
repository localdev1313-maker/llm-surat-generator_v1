"""
Klien Ollama bersama — satu sumber konfigurasi untuk seluruh layanan.

Konfigurasi dibaca dari environment:
- OLLAMA_HOST    : alamat server Ollama (default http://localhost:11434)
- OLLAMA_TIMEOUT : timeout HTTP per panggilan dalam detik (default 180)

Sebelumnya llm_service, rag_telaahan_staf, dan kajian_engine masing-masing
membuat kliennya sendiri dengan konfigurasi yang menyimpang (kajian_engine
bahkan hardcode localhost + timeout 10 detik via requests), sehingga perbaikan
konfigurasi hanya berlaku pada sebagian fitur. Semua layanan kini memakai
modul ini.
"""
import os
import logging
from typing import Optional

import ollama

from ..config import settings
from .llm_health import record_llm_warning

logger = logging.getLogger(__name__)

def _env_float(name: str, default: float) -> float:
    """Koersi env numerik aman — nilai salah format fallback ke default + warning."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        logger.warning("Nilai %s=%r tidak valid di env/.env — memakai default %s", name, raw, default)
        return default


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_TIMEOUT = _env_float("OLLAMA_TIMEOUT", 180.0)

client = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)


def default_chat_options() -> dict:
    """
    Opsi sampling standar dari settings (dapat dioverride via env):
    - num_ctx: kapasitas context window
    - temperature: 0.1 (deterministik, bebas halusinasi)
    - top_p / top_k / repeat_penalty: kontrol kualitas token
    - num_predict: batas panjang output token
    """
    return {
        "num_ctx": settings.OLLAMA_NUM_CTX,
        "temperature": settings.OLLAMA_TEMPERATURE,
        "top_p": settings.OLLAMA_TOP_P,
        "top_k": settings.OLLAMA_TOP_K,
        "repeat_penalty": settings.OLLAMA_REPEAT_PENALTY,
        "num_predict": settings.OLLAMA_NUM_PREDICT,
    }


def extract_content(response) -> str:
    """Ekstrak content dari response Ollama, support dict (0.1.x) dan object (0.2+)."""
    try:
        return response['message']['content'].strip()
    except (TypeError, KeyError, AttributeError):
        return response.message.content.strip()


def chat(system_prompt: str, user_prompt: str, options: Optional[dict] = None) -> str:
    """
    Panggil /api/chat secara sinkron; mengembalikan '' bila Ollama gagal/timeout.

    Kegagalan otomatis dicatat sebagai degradasi LLM (lihat llm_health) agar
    router dapat memberi tahu klien bahwa output berasal dari templat standar.
    """
    try:
        response = client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options=options if options is not None else default_chat_options(),
        )
        content = extract_content(response)
        if not content:
            logger.warning("Ollama merespons 200 tetapi konten kosong.")
            record_llm_warning(
                "Ollama mengembalikan konten kosong; bagian ini memakai templat standar."
            )
        return content
    except Exception as e:
        logger.warning(
            f"Ollama chat gagal (host={OLLAMA_HOST}, timeout={OLLAMA_TIMEOUT}s): {e}"
        )
        record_llm_warning(
            f"Ollama tidak merespons ({e.__class__.__name__}); "
            f"bagian ini memakai templat standar."
        )
        return ""
