"""
Bot Telegram SSEB-AI — Layanan Penyusunan Surat Elektronik via Telegram.

Mendukung pembuatan:
- Surat Resmi (via /surat)
- Nota Dinas (via /notadinas)

Bot ini dapat dijalankan:
1. Standalone: ``python run_bot.py``
2. Embedded: otomatis start saat FastAPI server berjalan (lihat main.py lifespan)
"""

import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from ..config import settings

logger = logging.getLogger(__name__)

# ── Conversation states ─────────────────────────────────────────────────────
(
    MENU,
    # Surat biasa
    SURAT_JENIS, SURAT_PENGIRIM, SURAT_ALAMAT_PENGIRIM,
    SURAT_PENERIMA, SURAT_ALAMAT_PENERIMA, SURAT_PERIHAL, SURAT_ISI,
    # Nota Dinas
    NOTA_NOMOR, NOTA_KEPADA, NOTA_DARI, NOTA_PERIHAL, NOTA_DASAR, NOTA_ISI,
) = range(14)

# URL backend API (self-connect)
_API_BASE = f"http://127.0.0.1:{settings.PORT}"


# ── Helper ───────────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    """Header Basic Auth jika aktif."""
    if settings.auth_enabled:
        import base64
        cred = base64.b64encode(
            f"{settings.AUTH_USERNAME}:{settings.AUTH_PASSWORD}".encode()
        ).decode()
        return {"Authorization": f"Basic {cred}"}
    return {}


async def _call_api(endpoint: str, payload: dict) -> dict:
    """Panggil endpoint backend dan kembalikan JSON response."""
    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(
            f"{_API_BASE}/{endpoint}",
            json=payload,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()


# ── Command Handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler /start — tampilkan menu utama."""
    keyboard = [
        [InlineKeyboardButton("📄 Buat Surat Resmi", callback_data="surat")],
        [InlineKeyboardButton("📋 Buat Nota Dinas", callback_data="notadinas")],
    ]
    await update.message.reply_text(
        "🤖 *SSEB-AI — Bot Penyusunan Surat Elektronik*\n\n"
        "Selamat datang! Pilih jenis naskah yang ingin dibuat:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return MENU


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler /batal — batalkan percakapan."""
    await update.message.reply_text(
        "❌ Dibatalkan. Ketik /start untuk memulai kembali."
    )
    context.user_data.clear()
    return ConversationHandler.END


# ── Menu Callback ────────────────────────────────────────────────────────────

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "surat":
        await query.edit_message_text(
            "📄 *Buat Surat Resmi*\n\nMasukkan *jenis surat* "
            "(contoh: Surat Undangan, Surat Perintah, Surat Keterangan):",
            parse_mode="Markdown",
        )
        return SURAT_JENIS
    elif choice == "notadinas":
        await query.edit_message_text(
            "📋 *Buat Nota Dinas*\n\nMasukkan *Nomor Surat* "
            "(contoh: ND/123/IX/2026):",
            parse_mode="Markdown",
        )
        return NOTA_NOMOR
    return MENU


# ── Surat Biasa Flow ─────────────────────────────────────────────────────────

async def surat_jenis(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["jenis_surat"] = update.message.text.strip()
    await update.message.reply_text("👤 Masukkan *Nama Pengirim*:", parse_mode="Markdown")
    return SURAT_PENGIRIM

async def surat_pengirim(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["nama_pengirim"] = update.message.text.strip()
    await update.message.reply_text("🏢 Masukkan *Alamat Pengirim*:", parse_mode="Markdown")
    return SURAT_ALAMAT_PENGIRIM

async def surat_alamat_pengirim(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["alamat_pengirim"] = update.message.text.strip()
    await update.message.reply_text("👤 Masukkan *Nama Penerima*:", parse_mode="Markdown")
    return SURAT_PENERIMA

async def surat_penerima(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["nama_penerima"] = update.message.text.strip()
    await update.message.reply_text("🏢 Masukkan *Alamat Penerima*:", parse_mode="Markdown")
    return SURAT_ALAMAT_PENERIMA

async def surat_alamat_penerima(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["alamat_penerima"] = update.message.text.strip()
    await update.message.reply_text("📌 Masukkan *Perihal* surat:", parse_mode="Markdown")
    return SURAT_PERIHAL

async def surat_perihal(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["perihal"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 Masukkan *Poin-poin isi* surat (ringkas, bisa beberapa baris):",
        parse_mode="Markdown",
    )
    return SURAT_ISI

async def surat_isi(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["isi_ringkas"] = update.message.text.strip()
    await update.message.reply_text("⏳ Sedang menyusun surat dengan AI... Mohon tunggu.")

    try:
        payload = {
            "jenis_surat": ctx.user_data["jenis_surat"],
            "nama_pengirim": ctx.user_data["nama_pengirim"],
            "alamat_pengirim": ctx.user_data["alamat_pengirim"],
            "nama_penerima": ctx.user_data["nama_penerima"],
            "alamat_penerima": ctx.user_data["alamat_penerima"],
            "perihal": ctx.user_data["perihal"],
            "isi_ringkas": ctx.user_data["isi_ringkas"],
        }
        result = await _call_api("generate-surat", payload)

        konten = result.get("konten_surat", "(tidak ada konten)")
        download_url = result.get("download_url", "")

        msg = f"✅ *Surat berhasil dibuat!*\n\n{konten[:3000]}"
        if result.get("llm_degraded"):
            msg += "\n\n⚠️ _Catatan: AI sedang offline — teks menggunakan templat standar._"
        if download_url:
            msg += f"\n\n📥 Download PDF: `{_API_BASE}{download_url}`"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Gagal membuat surat via Telegram: {e}")
        await update.message.reply_text(f"❌ Gagal membuat surat: {e}")

    ctx.user_data.clear()
    await update.message.reply_text("Ketik /start untuk membuat surat baru.")
    return ConversationHandler.END


# ── Nota Dinas Flow ───────────────────────────────────────────────────────────

async def nota_nomor(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["nomor_surat"] = update.message.text.strip()
    await update.message.reply_text("👤 *Kepada* (pejabat tujuan):", parse_mode="Markdown")
    return NOTA_KEPADA

async def nota_kepada(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["kepada"] = update.message.text.strip()
    await update.message.reply_text("👤 *Dari* (pengirim/satuan):", parse_mode="Markdown")
    return NOTA_DARI

async def nota_dari(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["dari"] = update.message.text.strip()
    await update.message.reply_text("📌 Masukkan *Perihal* nota dinas:", parse_mode="Markdown")
    return NOTA_PERIHAL

async def nota_perihal(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["perihal"] = update.message.text.strip()
    await update.message.reply_text(
        "📜 Masukkan *Dasar* (satu per baris, misal peraturan/surat perintah):",
        parse_mode="Markdown",
    )
    return NOTA_DASAR

async def nota_dasar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["dasar"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 Masukkan *Poin-poin isi* nota dinas (satu poin per baris):",
        parse_mode="Markdown",
    )
    return NOTA_ISI

async def nota_isi(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    raw_isi = update.message.text.strip()
    poin_list = [line.strip() for line in raw_isi.split("\n") if line.strip()]
    isi_ringkas = [{"teks": p, "sub_poin": []} for p in poin_list]

    await update.message.reply_text("⏳ Sedang menyusun nota dinas dengan AI... Mohon tunggu.")

    try:
        payload = {
            "nomor_surat": ctx.user_data["nomor_surat"],
            "kepada": ctx.user_data["kepada"],
            "dari": ctx.user_data["dari"],
            "perihal": ctx.user_data["perihal"],
            "dasar": ctx.user_data["dasar"],
            "isi_ringkas": isi_ringkas,
        }
        result = await _call_api("generate-nota-dinas", payload)

        konten = result.get("konten_surat", "(tidak ada konten)")
        download_url = result.get("download_url", "")

        msg = f"✅ *Nota Dinas berhasil dibuat!*\n\n{konten[:3000]}"
        if result.get("llm_degraded"):
            msg += "\n\n⚠️ _Catatan: AI sedang offline — teks menggunakan templat standar._"
        if download_url:
            msg += f"\n\n📥 Download PDF: `{_API_BASE}{download_url}`"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Gagal membuat nota dinas via Telegram: {e}")
        await update.message.reply_text(f"❌ Gagal membuat nota dinas: {e}")

    ctx.user_data.clear()
    await update.message.reply_text("Ketik /start untuk membuat naskah baru.")
    return ConversationHandler.END


# ── Factory ──────────────────────────────────────────────────────────────────

def create_telegram_bot() -> Application:
    """Buat dan konfigurasi Application python-telegram-bot."""
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MENU: [CallbackQueryHandler(menu_callback)],
            # Surat biasa
            SURAT_JENIS: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_jenis)],
            SURAT_PENGIRIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_pengirim)],
            SURAT_ALAMAT_PENGIRIM: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_alamat_pengirim)],
            SURAT_PENERIMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_penerima)],
            SURAT_ALAMAT_PENERIMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_alamat_penerima)],
            SURAT_PERIHAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_perihal)],
            SURAT_ISI: [MessageHandler(filters.TEXT & ~filters.COMMAND, surat_isi)],
            # Nota Dinas
            NOTA_NOMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_nomor)],
            NOTA_KEPADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_kepada)],
            NOTA_DARI: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_dari)],
            NOTA_PERIHAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_perihal)],
            NOTA_DASAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_dasar)],
            NOTA_ISI: [MessageHandler(filters.TEXT & ~filters.COMMAND, nota_isi)],
        },
        fallbacks=[CommandHandler("batal", cmd_cancel)],
    )
    app.add_handler(conv_handler)

    logger.info("Bot Telegram SSEB-AI dikonfigurasi.")
    return app
