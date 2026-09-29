"""
Konfigurasi terpusat aplikasi SSEB AI Surat Generator.

Semua nilai dapat dioverride lewat environment variable atau file
``backend/.env`` (dimuat otomatis via python-dotenv bila terpasang).

Kebijakan keamanan (lihat PROGRESS.md §5 dan CHECKLIST.md):
- Fail-fast autentikasi parsial: AUTH_USERNAME / AUTH_PASSWORD harus diset
  KEDUANYA. Salah satu saja terisi = server MENOLAK start (RuntimeError),
  karena konfigurasi setengah matang berarti API tanpa perlindungan.
- AUTH_REQUIRE=1 (default): auth WAJIB aktif — kredensial tidak lengkap =
  menolak start (fail-closed). Set AUTH_REQUIRE=0 secara sadar untuk mode
  pengembangan lokal dengan API terbuka.
- Koersi env numerik aman: nilai salah format fallback ke default + warning,
  bukan mematikan server (konsisten dengan ollama_client._env_float).
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Muat backend/.env secara otomatis (opsional — hanya bila python-dotenv ada).
try:
    from dotenv import load_dotenv

    _ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
    if _ENV_FILE.exists():
        load_dotenv(_ENV_FILE)
except ImportError:  # pragma: no cover - dotenv tidak terpasang, env murni dipakai
    pass


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        logger.warning("Nilai %s=%r tidak valid di env/.env — memakai default %s", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError:
        logger.warning("Nilai %s=%r tidak valid di env/.env — memakai default %s", name, raw, default)
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Kumpulan konfigurasi runtime — dibaca sekali saat proses start."""

    def __init__(self) -> None:
        # ── Direktori ──
        # PROJECT_ROOT = akar repo (berisi extracted_kep868.txt dsb.)
        self.PROJECT_ROOT: Path = Path(
            _env_str("PROJECT_ROOT") or Path(__file__).resolve().parents[2]
        )
        self.DOCS_DIR: Path = Path(_env_str("DOCS_DIR") or self.PROJECT_ROOT / "docs")
        self.TEMPLATE_DIR: Path = Path(__file__).resolve().parent / "templates"
        self.STATIC_DIR: Path = Path(__file__).resolve().parent.parent / "static"
        self.KNOWLEDGE_DIR: Path = Path(__file__).resolve().parent / "knowledge"
        self.OUTPUT_DIR: Path = Path(
            _env_str("OUTPUT_DIR") or Path(__file__).resolve().parent.parent / "output"
        )

        # Direktori output dibuat saat startup agar render PDF pertama tidak
        # gagal (folder output/ tidak ikut ter-commit).
        try:
            self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:  # disk penuh / permission — log, jangan crash
            logger.warning("Tidak dapat membuat direktori %s: %s", self.OUTPUT_DIR, e)

        # ── Render PDF ──
        # Path wkhtmltopdf; kosongkan untuk memakai binary dari PATH sistem.
        self.WKHTMLTOPDF_PATH: str = _env_str("WKHTMLTOPDF_PATH")

        # ── Autentikasi Basic HTTP ──
        self.AUTH_USERNAME: str = _env_str("AUTH_USERNAME")
        self.AUTH_PASSWORD: str = _env_str("AUTH_PASSWORD")
        # AUTH_REQUIRE=1 (default) = fail-closed: tanpa kredensial lengkap server
        # menolak start. Set 0 hanya untuk pengembangan lokal yang disengaja.
        self.AUTH_REQUIRE: bool = _env_bool("AUTH_REQUIRE", True)

        partial = bool(self.AUTH_USERNAME) != bool(self.AUTH_PASSWORD)
        if partial:
            raise RuntimeError(
                "Konfigurasi autentikasi tidak lengkap: AUTH_USERNAME dan "
                "AUTH_PASSWORD harus diset KEDUANYA di env/backend/.env "
                "(salah satu terisi = server menolak start)."
            )
        if self.AUTH_REQUIRE and not self.auth_enabled:
            raise RuntimeError(
                "Autentikasi WAJIB aktif (AUTH_REQUIRE=1) tetapi AUTH_USERNAME/"
                "AUTH_PASSWORD kosong. Set keduanya di env/backend/.env, atau "
                "set AUTH_REQUIRE=0 secara sadar untuk mode dev tanpa auth "
                "(TIDAK disarankan untuk data dinas)."
            )

        # ── Ollama / LLM ──
        self.OLLAMA_MODEL: str = _env_str("OLLAMA_MODEL", "llama3.1")
        self.OLLAMA_NUM_CTX: int = _env_int("OLLAMA_NUM_CTX", 8192)
        self.OLLAMA_TEMPERATURE: float = _env_float("OLLAMA_TEMPERATURE", 0.1)
        self.OLLAMA_TOP_P: float = _env_float("OLLAMA_TOP_P", 0.9)
        self.OLLAMA_TOP_K: int = _env_int("OLLAMA_TOP_K", 40)
        self.OLLAMA_REPEAT_PENALTY: float = _env_float("OLLAMA_REPEAT_PENALTY", 1.15)
        self.OLLAMA_NUM_PREDICT: int = _env_int("OLLAMA_NUM_PREDICT", 1500)
        # Rasio budget context window untuk input (system+user+RAG) vs num_ctx.
        self.CONTEXT_BUDGET_RATIO: float = _env_float("CONTEXT_BUDGET_RATIO", 0.75)

        # ── RAG ──
        self.RAG_ENABLED: bool = _env_bool("RAG_ENABLED", True)
        self.RAG_TOP_K: int = _env_int("RAG_TOP_K", 4)
        self.MAX_RAG_CONTEXT_TOKENS: int = _env_int("MAX_RAG_CONTEXT_TOKENS", 1800)
        self.RAG_INDEX_CACHE: Path = Path(
            _env_str("RAG_INDEX_CACHE") or self.KNOWLEDGE_DIR / "rag_index.json"
        )

        # ── Telegram Bot ──
        self.TELEGRAM_BOT_TOKEN: str = _env_str("TELEGRAM_BOT_TOKEN")

        # ── CORS ──
        # Daftar origin frontend yang diizinkan, dipisah koma. Default mengizinkan
        # halaman yang disajikan server sendiri; ["*"] + credentials adalah kombinasi
        # yang salah secara spesifikasi dan dilarang di sini.
        self.CORS_ORIGINS: list[str] = [
            o.strip()
            for o in _env_str(
                "CORS_ALLOW_ORIGINS",
                "http://localhost:8001,http://127.0.0.1:8001",
            ).split(",")
            if o.strip()
        ]

    @property
    def auth_enabled(self) -> bool:
        """Basic Auth aktif hanya bila kedua kredensial terisi."""
        return bool(self.AUTH_USERNAME) and bool(self.AUTH_PASSWORD)


settings = Settings()
