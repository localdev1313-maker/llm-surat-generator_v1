"""
Konfigurasi pusat aplikasi SSEB-AI (Singleton).

Semua setting dibaca dari environment variable / file .env sehingga mudah
di-override tanpa mengubah source code. File ini diimpor oleh hampir
seluruh modul backend (security, routers, services, pdf_service, dll.)
melalui: ``from ..config import settings`` / ``from .config import settings``.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env ──────────────────────────────────────────────────────────────
# Cari .env di folder backend/ (satu level di atas app/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)


def _env(key: str, default: str = "") -> str:
    """Ambil env variable dengan default."""
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


class _Settings:
    """Objek konfigurasi global — diinstansiasi sekali saat import."""

    # ── Path ────────────────────────────────────────────────────────────────
    PROJECT_ROOT: Path = _BACKEND_DIR.parent  # root repo (llm-surat-generator_android_version_v1/)
    BACKEND_DIR: Path = _BACKEND_DIR
    STATIC_DIR: Path = Path(_env("STATIC_DIR", str(_BACKEND_DIR / "static")))
    TEMPLATE_DIR: Path = Path(_env("TEMPLATE_DIR", str(_BACKEND_DIR / "app" / "templates")))
    OUTPUT_DIR: Path = Path(_env("OUTPUT_DIR", str(_BACKEND_DIR / "output")))
    DOCS_DIR: Path = Path(_env("DOCS_DIR", str(PROJECT_ROOT / "fine-tune-dokumen")))
    KNOWLEDGE_DIR: Path = Path(_env("KNOWLEDGE_DIR", str(_BACKEND_DIR / "app" / "knowledge")))

    # ── RAG ──────────────────────────────────────────────────────────────────
    RAG_ENABLED: bool = _env_bool("RAG_ENABLED", True)
    RAG_TOP_K: int = _env_int("RAG_TOP_K", 3)
    RAG_INDEX_CACHE: Path = Path(_env("RAG_INDEX_CACHE", str(_BACKEND_DIR / "output" / "rag_index.json")))
    MAX_RAG_CONTEXT_TOKENS: int = _env_int("MAX_RAG_CONTEXT_TOKENS", 2000)
    CONTEXT_BUDGET_RATIO: float = _env_float("CONTEXT_BUDGET_RATIO", 0.6)

    # ── Ollama LLM ──────────────────────────────────────────────────────────
    OLLAMA_MODEL: str = _env("OLLAMA_MODEL", "qwen2.5:14b")
    OLLAMA_HOST: str = _env("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_TIMEOUT: float = _env_float("OLLAMA_TIMEOUT", 180.0)
    OLLAMA_NUM_CTX: int = _env_int("OLLAMA_NUM_CTX", 8192)
    OLLAMA_TEMPERATURE: float = _env_float("OLLAMA_TEMPERATURE", 0.1)
    OLLAMA_TOP_P: float = _env_float("OLLAMA_TOP_P", 0.9)
    OLLAMA_TOP_K: int = _env_int("OLLAMA_TOP_K", 40)
    OLLAMA_REPEAT_PENALTY: float = _env_float("OLLAMA_REPEAT_PENALTY", 1.1)
    OLLAMA_NUM_PREDICT: int = _env_int("OLLAMA_NUM_PREDICT", 1024)

    # ── PDF (wkhtmltopdf) ───────────────────────────────────────────────────
    WKHTMLTOPDF_PATH: str = _env("WKHTMLTOPDF_PATH", r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

    # ── HTTP Basic Auth ─────────────────────────────────────────────────────
    AUTH_USERNAME: str = _env("AUTH_USERNAME", "")
    AUTH_PASSWORD: str = _env("AUTH_PASSWORD", "")

    @property
    def auth_enabled(self) -> bool:
        """Auth aktif hanya bila KEDUA kredensial diset."""
        return bool(self.AUTH_USERNAME.strip() and self.AUTH_PASSWORD.strip())

    # ── Telegram Bot ────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = _env("TELEGRAM_BOT_TOKEN", "")

    # ── Server ──────────────────────────────────────────────────────────────
    PORT: int = _env_int("PORT", 8001)

    def __init__(self):
        # Pastikan direktori output ada
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.STATIC_DIR.mkdir(parents=True, exist_ok=True)


# Singleton — seluruh modul mengimpor objek ini
settings = _Settings()
