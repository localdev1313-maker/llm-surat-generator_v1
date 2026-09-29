"""
Bot Telegram SSEB AI — asisten pembuatan naskah dinas jarak jauh.

Dokumen kontrak fitur: DOKUMENTASI_LENGKAP §3.2 — wizard /surat & /notadinas,
pratinjau draf dengan inline keyboard (Setuju & Unduh PDF / Edit Redaksi /
Generate Ulang / Batalkan), pengiriman PDF langsung ke chat, serta perintah
kontrol RAG (/rag, /reindex, /carireferensi).

Keamanan:
- Bot TIDAK pernah membalas tanpa diminta; setiap aksi hanya melayani user
  yang mengaktifkan wizard sendiri (state per chat_id, tidak dibagikan).
- Tidak ada token/ kredensial yang dilog.
- Token dibaca dari settings.TELEGRAM_BOT_TOKEN (env/.env) — tidak hardcoded.
"""
import asyncio
import html
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ..config import settings
from ..models import NotaDinasRequest, SuratRequest
from ..services.llm_service import generate_isi_nota_dinas, generate_surat_content
from ..services.llm_health import start_llm_request_scope, collect_llm_warnings
from ..services.pdf_service import create_pdf_nota_dinas, create_pdf_surat
from ..utils import format_tanggal_indonesia, format_tanggal_lokasi

logger = logging.getLogger(__name__)

MENU_SETUJU = "ok"
MENU_EDIT = "edit"
MENU_REGEN = "regen"
MENU_BATAL = "cancel"


def _reply_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Setuju & Unduh PDF", callback_data=MENU_SETUJU),
                InlineKeyboardButton("📝 Edit Redaksi", callback_data=MENU_EDIT),
            ],
            [
                InlineKeyboardButton("🔄 Generate Ulang AI", callback_data=MENU_REGEN),
                InlineKeyboardButton("❌ Batalkan", callback_data=MENU_BATAL),
            ],
        ]
    )


def _fmt_preview(judul: str, teks: str, warnings: list) -> str:
    """Pratinjau draf di chat — HTML di-escape, peringatan degradasi AI ditampilkan."""
    badan = html.escape(teks)
    if warnings:
        catatan = "\n".join(f"⚠️ {html.escape(w)}" for w in warnings[:4])
        badan = f"<b>{html.escape(judul)}</b>\n\n{catatan}\n\n{badan}"
    else:
        badan = f"<b>{html.escape(judul)}</b>\n\n{badan}"
    return badan


class TelegramSuratBot:
    """Penyimpan state wizard per-chat + handler. Satu instance per proses."""

    def __init__(self) -> None:
        # chat_id -> {"stage": int, "data": {...}, "draft": {...}}
        self.sessions: Dict[int, Dict[str, Any]] = {}

    # ── Perintah umum ──
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "👋 Selamat datang di Bot Surat SSEB AI.\n\n"
            "Perintah tersedia:\n"
            "/surat —wizard surat resmi/umum\n"
            "/notadinas — wizard nota dinas\n"
            "/rag — status knowledge base\n"
            "/reindex — re-index dokumen referensi\n"
            "/carireferensi <kata kunci> — pencarian semantik arsip naskah"
        )

    async def cmd_rag(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from ..services.rag_service import rag_engine

        st = rag_engine.get_status()
        await update.message.reply_text(
            "📚 Status RAG:\n"
            f"- Aktif: {st.get('rag_enabled')}\n"
            f"- Dokumen terindeks: {st.get('total_documents', 0)}\n"
            f"- Chunk: {st.get('total_chunks', 0)}\n"
            f"- Index terakhir: {st.get('last_indexed_at') or '-'}"
        )

    async def cmd_reindex(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from ..services.rag_service import rag_engine

        await update.message.reply_text("♻️ Mengindeks ulang dokumen referensi…")
        total = await asyncio.to_thread(rag_engine.index_all_documents, force=True)
        await update.message.reply_text(
            f"✅ Selesai: {total} dokumen terindeks "
            f"(waktu: {rag_engine.last_indexed_at})."
        )

    async def cmd_cari(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from ..services.rag_service import rag_engine

        query = " ".join(context.args) if context.args else ""
        if not query:
            await update.message.reply_text("Format: /carireferensi <kata kunci>")
            return
        results = await asyncio.to_thread(rag_engine.search, query, 3)
        if not results:
            await update.message.reply_text("Tidak ada referensi cocok.")
            return
        lines = [f"🔎 Hasil untuk '{query}':"]
        for r in results:
            src = r.get("source_file", "?")
            snippet = (r.get("content") or "")[:220]
            lines.append(f"\n— {src}\n{snippet}…")
        await update.message.reply_text("\n".join(lines))

    # ── Wizard /surat ──
    SURAT_STEPS = [
        ("jenis", "Jenis surat? (mis: undangan, pemberitahuan)"),
        ("nama_pengirim", "Nama pengirim (penandatangan)?"),
        ("alamat_pengirim", "Alamat pengirim?"),
        ("nama_penerima", "Nama penerima?"),
        ("alamat_penerima", "Alamat penerima?"),
        ("perihal", "Perihal surat?"),
        ("isi_ringkas", "Poin-poin pokok isi surat (boleh beberapa baris):"),
    ]

    async def cmd_surat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions[update.effective_chat.id] = {"mode": "surat", "stage": 0, "data": {}}
        await self._ask(update, context)

    # ── Wizard /notadinas ──
    ND_STEPS = [
        ("nomor_surat", "Nomor nota dinas?"),
        ("kepada", "Kepada Yth.?"),
        ("dari", "Dari (unit pengirim)?"),
        ("perihal", "Perihal?"),
        ("dasar", "Dasar (satu baris per dasar, boleh kosong):"),
        ("isi_ringkas", "Poin-poin pokok isi (satu baris per poin):"),
    ]

    async def cmd_notadinas(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions[update.effective_chat.id] = {"mode": "nd", "stage": 0, "data": {}}
        await self._ask(update, context)

    async def _ask(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        s = self.sessions.get(update.effective_chat.id)
        if not s:
            return
        steps = self.SURAT_STEPS if s["mode"] == "surat" else self.ND_STEPS
        if s["stage"] < len(steps):
            _, pertanyaan = steps[s["stage"]]
            await update.message.reply_text(f"[{s['stage'] + 1}/{len(steps)}] {pertanyaan}")
        else:
            await self._generate_preview(update, context)

    async def on_wizard_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        s = self.sessions.get(chat_id)
        if not s:
            return
        # Mode edit redaksi: balasan teks = revisi draf, bukan jawaban wizard.
        if s.get("editing"):
            await self._apply_edit(update, context, s)
            return
        if "draft" in s:
            return  # menunggu keputusan tombol inline
        steps = self.SURAT_STEPS if s["mode"] == "surat" else self.ND_STEPS
        key, _ = steps[s["stage"]]
        s["data"][key] = (update.message.text or "").strip()
        s["stage"] += 1
        await self._ask(update, context)

    async def _build_draft(self, chat_id: int) -> tuple:
        """Susun draf via LLM dari data wizard. Mengembalikan (draft, preview, warnings)."""
        s = self.sessions[chat_id]
        if s["mode"] == "surat":
            req = SuratRequest(
                jenis_surat=s["data"].get("jenis", "resmi"),
                nama_pengirim=s["data"].get("nama_pengirim", ""),
                alamat_pengirim=s["data"].get("alamat_pengirim", ""),
                nama_penerima=s["data"].get("nama_penerima", ""),
                alamat_penerima=s["data"].get("alamat_penerima", ""),
                perihal=s["data"].get("perihal", ""),
                isi_ringkas=s["data"].get("isi_ringkas", ""),
            )
            start_llm_request_scope()
            konten = await asyncio.to_thread(generate_surat_content, req)
            warnings = collect_llm_warnings()
            draft = {"konten": konten, "req": req.model_dump()}
            return draft, (konten or "(isi kosong)"), warnings

        d = s["data"]
        req = NotaDinasRequest(
            nomor_surat=d.get("nomor_surat", ""),
            kepada=d.get("kepada", ""),
            dari=d.get("dari", ""),
            perihal=d.get("perihal", ""),
            dasar=d.get("dasar", ""),
            isi_ringkas=[ln for ln in d.get("isi_ringkas", "").splitlines() if ln.strip()],
        )
        start_llm_request_scope()
        isi_list = await asyncio.to_thread(generate_isi_nota_dinas, req)
        warnings = collect_llm_warnings()
        gabung = "\n\n".join(f"{2 + i}. {it.get('teks', '')}" for i, it in enumerate(isi_list))
        draft = {"isi_list": isi_list, "req": req.model_dump(mode="json")}
        return draft, (gabung or "(isi kosong)"), warnings

    async def _generate_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        await update.message.reply_text("🤖 AI sedang menyusun draf…")
        try:
            draft, teks_preview, warnings = await self._build_draft(chat_id)
        except Exception as e:
            logger.exception("Generasi draf bot gagal")
            await update.message.reply_text(f"❌ Gagal menyusun draf: {e.__class__.__name__}")
            self.sessions.pop(chat_id, None)
            return

        s = self.sessions[chat_id]
        s["draft"] = draft
        s["warnings"] = warnings
        await update.message.reply_text(
            _fmt_preview("DRAF NASKAH (pratinjau)", teks_preview, warnings),
            parse_mode=ParseMode.HTML,
            reply_markup=_reply_markup(),
        )

    # ── Tombol inline ──
    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        await q.answer()
        chat_id = update.effective_chat.id
        s = self.sessions.get(chat_id)
        if not s or "draft" not in s:
            await q.edit_message_text("Sesi draf sudah berakhir. Mulai lagi dengan /surat atau /notadinas.")
            return

        action = q.data
        if action == MENU_BATAL:
            self.sessions.pop(chat_id, None)
            await q.edit_message_text("❌ Draf dibatalkan.")
        elif action == MENU_REGEN:
            # Generate ulang pada data wizard yang sama (bukan hasil editan).
            await q.edit_message_text("🔄 AI menyusun ulang draf…")
            try:
                draft, teks_preview, warnings = await self._build_draft(chat_id)
            except Exception as e:
                logger.exception("Regenerasi draf bot gagal")
                await q.message.reply_text(f"❌ Gagal menyusun draf: {e.__class__.__name__}")
                self.sessions.pop(chat_id, None)
                return
            s["draft"] = draft
            s["warnings"] = warnings
            await q.message.reply_text(
                _fmt_preview("DRAF HASIL GENERATE ULANG", teks_preview, warnings),
                parse_mode=ParseMode.HTML,
                reply_markup=_reply_markup(),
            )
        elif action == MENU_EDIT:
            s["editing"] = True
            await q.edit_message_text(
                "✏️ Balas dengan TEKS REVISI lengkap. Setelah dikirim, pratinjau diperbarui."
            )
        elif action == MENU_SETUJU:
            await self._send_pdf(q, context, s)

    async def _apply_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
        s["editing"] = False
        teks_baru = (update.message.text or "").strip()
        if "draft" in s:
            if s["mode"] == "surat":
                s["draft"]["konten"] = teks_baru
            else:
                s["draft"]["isi_custom"] = teks_baru
        await update.message.reply_text(
            _fmt_preview("DRAF TERKINI (hasil edit)", teks_baru, s.get("warnings", [])),
            parse_mode=ParseMode.HTML,
            reply_markup=_reply_markup(),
        )

    async def _send_pdf(self, q: Any, context: ContextTypes.DEFAULT_TYPE, s: Dict[str, Any]) -> None:
        draft = s["draft"]
        surat_id = str(uuid.uuid4())
        try:
            if s["mode"] == "surat":
                req = SuratRequest(**draft["req"])
                konten = draft.get("isi_custom") or draft.get("konten", "")
                template_data = {
                    "nama_pengirim": req.nama_pengirim,
                    "alamat_pengirim": req.alamat_pengirim,
                    "nama_penerima": req.nama_penerima,
                    "alamat_penerima": req.alamat_penerima,
                    "perihal": req.perihal,
                    "tanggal": format_tanggal_indonesia(),
                    "nomor_surat": f"{surat_id[:8]}/SK/{datetime.now().strftime('%m/%Y')}",
                    "isi_surat": konten.replace("\n", "<br>"),
                }
                pdf_path = settings.OUTPUT_DIR / f"surat_{surat_id}.pdf"
                await asyncio.to_thread(create_pdf_surat, template_data, pdf_path)
            else:
                req = NotaDinasRequest(**dict(draft["req"]))
                now = datetime.now()
                if draft.get("isi_custom"):
                    # Hasil edit redaksi: satu blok teks bebas → satu poin isi.
                    isi_list = [{"teks": draft["isi_custom"], "sub_poin": []}]
                else:
                    isi_list = draft.get("isi_list", [])
                template_data = {
                    "kop_utama": req.kop_utama,
                    "kop_sub": req.kop_sub,
                    "nomor_surat": req.nomor_surat,
                    "kepada": req.kepada,
                    "dari": req.dari,
                    "perihal": req.perihal,
                    "dasar_list": [x.strip() for x in (req.dasar or "").splitlines() if x.strip()],
                    "isi_list": isi_list,
                    "tanggal_ttd": format_tanggal_lokasi("Jakarta", now),
                    "nama_pejabat": req.nama_pejabat,
                    "jabatan_pejabat": req.jabatan_pejabat,
                    "pangkat_pejabat": req.pangkat_pejabat,
                    "tembusan_list": req.tembusan or [],
                    "kalimat_penutup": "Demikian mohon menjadi periksa."
                    if req.jenis_penutup == "periksa"
                    else "Demikian disampaikan mohon menjadi perhatian.",
                }
                pdf_path = settings.OUTPUT_DIR / f"nota_dinas_{surat_id}.pdf"
                await asyncio.to_thread(create_pdf_nota_dinas, template_data, pdf_path)

            with open(pdf_path, "rb") as fh:
                await context.bot.send_document(chat_id=q.message.chat_id, document=fh)
            await q.edit_message_text("✅ Dokumen PDF terkirim. Terima kasih!")
            self.sessions.pop(q.message.chat_id, None)
        except Exception as e:
            logger.exception("Render/kirim PDF bot gagal")
            await q.edit_message_text(f"❌ Gagal mengirim PDF: {e.__class__.__name__}")


def create_telegram_bot() -> Application:
    """
    Bangun Application python-telegram-bot dengan seluruh handler terdaftar.

    Dipakai main.py (lifespan FastAPI, initialize/start/updater.start_polling)
    dan run_bot.py (Application.run_polling). Token dari settings (env) —
    tidak pernah di-hardcode maupun dilog.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum dikonfigurasi (env/.env).")

    builder = Application.builder().token(settings.TELEGRAM_BOT_TOKEN)
    try:
        app = builder.get_updates_read_timeout(30).build()
    except AttributeError:
        # API builder berubah antar versi PTB — fallback ke builder polos.
        app = builder.build()

    bot = TelegramSuratBot()

    app.add_handler(CommandHandler("start", bot.cmd_start))
    app.add_handler(CommandHandler("help", bot.cmd_start))
    app.add_handler(CommandHandler("surat", bot.cmd_surat))
    app.add_handler(CommandHandler("notadinas", bot.cmd_notadinas))
    app.add_handler(CommandHandler("rag", bot.cmd_rag))
    app.add_handler(CommandHandler("reindex", bot.cmd_reindex))
    app.add_handler(CommandHandler("carireferensi", bot.cmd_cari))
    app.add_handler(CallbackQueryHandler(bot.on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.on_wizard_message))

    logger.info("Bot Telegram dibangun (%d handler).", len(app.handlers[0]))
    return app
