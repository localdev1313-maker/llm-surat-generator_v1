import logging
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .routers import surat, telaahan_staf, kajian, lapju
from .security import require_auth
from .services.telegram_bot import create_telegram_bot

logger = logging.getLogger(__name__)

telegram_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app
    try:
        if settings.TELEGRAM_BOT_TOKEN:
            logger.info("Memulai Bot Telegram di background...")
            telegram_app = create_telegram_bot()
            await telegram_app.initialize()
            await telegram_app.start()
            await telegram_app.updater.start_polling(drop_pending_updates=True)
            logger.info("Bot Telegram aktif dan siap melayani permintaan.")
        else:
            logger.warning(
                "TELEGRAM_BOT_TOKEN tidak diset (env/.env) — Bot Telegram dinonaktifkan."
            )
    except Exception as e:
        logger.warning(f"Tidak dapat memulai Bot Telegram saat startup: {e}")

    yield

    try:
        if telegram_app and telegram_app.updater and telegram_app.updater.running:
            logger.info("Menghentikan Bot Telegram...")
            await telegram_app.updater.stop()
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("Bot Telegram berhasil dihentikan.")
    except Exception as e:
        logger.warning(f"Error saat shutdown Bot Telegram: {e}")

app = FastAPI(
    title="Layanan Penyusunan Surat Elektronik Otomatis Terintegrasi AI",
    description="API generate surat formal dengan LLM lokal (Ollama) + PDF + Telegram Bot",
    version="1.2.0",
    lifespan=lifespan,
    # Saat auth aktif, dokumentasi API (/docs, /redoc, /openapi.json) dimatikan —
    # ketiganya tidak melewati include_router sehingga require_auth tidak melindunginya.
    docs_url=None if settings.auth_enabled else "/docs",
    redoc_url=None if settings.auth_enabled else "/redoc",
    openapi_url=None if settings.auth_enabled else "/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend).
# PENGECUALIAN SAJI YANG SENGAJA: /static tetap publik (tanpa auth) agar halaman
# login frontend web dapat dimuat; semua endpoint data tetap terlindungi.
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Include router — SELURUH endpoint API dilindungi Basic Auth bila
# AUTH_USERNAME/AUTH_PASSWORD diset (lihat app/security.py).
api_dependencies = [Depends(require_auth)]
app.include_router(surat.router, dependencies=api_dependencies)
app.include_router(telaahan_staf.router, dependencies=api_dependencies)
app.include_router(kajian.router, dependencies=api_dependencies)
app.include_router(lapju.router, dependencies=api_dependencies)

@app.get("/api/health")
async def health_check():
    """Endpoint status kesehatan server — SELALU terbuka (tanpa auth) agar
    tombol Tes Koneksi aplikasi dapat memverifikasi jaringan sebelum login."""
    return {"status": "ok", "version": "2.0.0-alpha"}

@app.get("/api/auth/verify", dependencies=[Depends(require_auth)])
async def verify_auth():
    """Verifikasi kredensial untuk layar login aplikasi Android.
    Mengembalikan 200 bila kredensial valid / auth nonaktif; 401 bila salah."""
    return {"status": "ok", "authenticated": True}

if not settings.auth_enabled:
    logger.warning(
        "AUTH_USERNAME/AUTH_PASSWORD tidak diset — API TANPA AUTENTIKASI. "
        "Set keduanya di env/.env untuk melindungi endpoint (disarankan)."
    )
else:
    logger.info("Autentikasi HTTP Basic aktif untuk seluruh endpoint API.")

@app.get("/")
async def read_index():
    """Sajikan halaman utama (index.html) dari folder static."""
    return FileResponse(settings.STATIC_DIR / "index.html")