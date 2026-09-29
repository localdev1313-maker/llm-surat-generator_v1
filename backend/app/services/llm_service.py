import re
import html as _html
import logging
from fastapi import HTTPException
from ..config import settings
from ..models import SuratRequest, NotaDinasRequest
from .ollama_client import chat as ollama_chat
from .llm_health import record_llm_warning
from .rag_service import rag_engine, _estimate_tokens

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────────
# Pola-pola halusinasi umum yang harus dideteksi dalam output LLM
# ────────────────────────────────────────────────────────────────────────────────
_HALLUCINATION_PATTERNS = [
    # Nomor peraturan/undang-undang yang dikarang LLM
    re.compile(r'(?:Undang-Undang|UU|Peraturan Pemerintah|PP|Peraturan Presiden|Perpres|'
               r'Peraturan Menteri|Permen|Surat Edaran|SE|Instruksi Presiden|Inpres)'
               r'\s+(?:Nomor|No\.?)\s*\d+', re.IGNORECASE),
    # Tanggal spesifik yang dikarang (format "tanggal DD Bulan YYYY" atau "DD/MM/YYYY")
    re.compile(r'tanggal\s+\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|'
               r'Agustus|September|Oktober|November|Desember)\s+\d{4}', re.IGNORECASE),
    # Nama pangkat militer lengkap yang dikarang (misal "Kolonel Inf. Arif Budiman")
    # [^\S\n] = whitespace TANPA newline — mencegah regex mencocokkan lintas
    # paragraf sehingga "Mayor Andi\n\nSurabaya" tidak ditangkap sebagai satu entitas.
    re.compile(r'(?:Letnan|Kolonel|Brigadir|Mayor|Kapten|Sersan|Kopral)[^\S\n]+(?:Jenderal|'
               r'Inf\.|Kav\.|Armed\.|Mar\.|Laut|Udara)?[^\S\n]*[A-Z][a-z]+[^\S\n]+[A-Z][a-z]+', re.IGNORECASE),
]

# Kata-kata penghubung yang menandakan halusinasi eksplanatif berlebihan
_EXCESSIVE_EXPLANATION_MARKERS = [
    "sebagaimana diketahui bersama",
    "perlu diingatkan bahwa",
    "sebagai catatan penting",
    "penulis berpendapat",
    "menurut hemat kami",
    "tidak bisa dipungkiri",
    "pada kenyataannya",
    "secara filosofis",
]


def _check_context_budget(system_prompt: str, user_prompt: str) -> None:
    """
    Cek apakah total token input (system + user prompt) melebihi budget context window.
    Jika melebihi, log warning agar administrator mengetahui.
    """
    total_input_tokens = _estimate_tokens(system_prompt) + _estimate_tokens(user_prompt)
    budget = int(settings.OLLAMA_NUM_CTX * settings.CONTEXT_BUDGET_RATIO)

    if total_input_tokens > budget:
        logger.warning(
            f"⚠️ CONTEXT BUDGET OVERFLOW: Input ~{total_input_tokens} tokens "
            f"melebihi budget {budget} tokens ({settings.CONTEXT_BUDGET_RATIO*100:.0f}% dari {settings.OLLAMA_NUM_CTX}). "
            f"Output LLM mungkin terpotong atau mengabaikan instruksi awal. "
            f"Pertimbangkan menaikkan OLLAMA_NUM_CTX atau memangkas RAG context."
        )
    else:
        logger.debug(
            f"Context budget OK: ~{total_input_tokens}/{budget} tokens "
            f"({total_input_tokens/budget*100:.0f}% terpakai)"
        )


def _clean_paragraph(text: str) -> str:
    """Membersihkan nomor urut, penanda separator, atau tanda kutip yang tidak sengaja ter-generate."""
    cleaned = text.strip()
    # Hapus baris pemisah separator jika ada sisa
    cleaned = re.sub(r'={3,}.*$', '', cleaned).strip()
    # Hapus nomor di awal misal "1. ", "2. ", "a. ", "Paragraf 1:", "- "
    cleaned = re.sub(r'^(?:paragraf\s*\d+\s*[:\-]?|[0-9]+[\.)]|[a-zA-Z][\.)]|[\-\*•])\s*', '', cleaned, flags=re.IGNORECASE)
    # Hapus kutip berlebih di awal/akhir
    cleaned = cleaned.strip('"`\'')
    return cleaned.strip()


def _validate_output(text: str, user_input_data: dict, extra_context: str = "") -> str:
    """
    Validasi output LLM untuk mendeteksi dan menangani halusinasi.

    Checks:
    1. Deteksi pola halusinasi (nomor regulasi palsu, nama fiktif, dll.)
       - whitelist mencakup input pengguna + extra_context (RAG grounding)
    2. Deteksi output terlalu panjang (>500 kata = tanda halusinasi verbose)
    3. Deteksi kalimat eksplanatif berlebihan yang tidak relevan

    Jika terdeteksi, kembalikan teks yang sudah dibersihkan atau flag warning.
    """
    if not text or not text.strip():
        return text

    cleaned = text.strip()
    warnings = []
    reported: set = set()

    # 1. Cek pola halusinasi regulasi/nama fiktif
    # Whitelist: input pengguna + konteks RAG yang disuntikkan ke prompt yang sama —
    # sitasi SAH dari knowledge base tidak boleh dilaporkan sebagai halusinasi.
    user_combined = re.sub(
        r'\s+', ' ',
        " ".join(str(v) for v in user_input_data.values() if v) + " " + (extra_context or "")
    ).lower()

    for pattern in _HALLUCINATION_PATTERNS:
        matches = pattern.findall(cleaned)
        for match in matches:
            # Dedup: sitasi berulang tidak boleh menggandakan warning
            # Normalisasi whitespace: regex \s+ mencocokkan newline sehingga
            # match "Mayor Andi\n\nDi" tidak ditemukan di user_combined
            # yang hanya berisi "Mayor Andi" — tanpa normalisasi ini, nama
            # penerima yang sah salah ditandai sebagai halusinasi.
            key = re.sub(r'\s+', ' ', match).lower().strip()
            if key in reported:
                continue
            reported.add(key)
            # Cek apakah referensi ini berasal dari input pengguna / RAG context
            if key not in user_combined:
                warnings.append(f"Potensi halusinasi terdeteksi: '{match}'")
                logger.warning(f"⚠️ HALUSINASI TERDETEKSI dalam output LLM: '{match}' — "
                             f"tidak ditemukan dalam data input/konteks referensi.")
                record_llm_warning(
                    f"Terdeteksi potensi halusinasi '{match}' pada keluaran LLM "
                    f"— mohon periksa ulang naskah."
                )

    # 2. Cek output terlalu panjang (>500 kata per paragraf = tanda verbose halusinasi)
    word_count = len(cleaned.split())
    if word_count > 500:
        logger.warning(
            f"⚠️ Output LLM terlalu panjang ({word_count} kata). "
            f"Kemungkinan halusinasi verbose. Memotong ke 300 kata pertama."
        )
        record_llm_warning(
            "Keluaran LLM melebihi 500 kata dan dipotong otomatis — "
            "periksa ulang kelengkapan bagian ini."
        )
        words = cleaned.split()
        # Potong dan tambahkan penutup yang aman
        cleaned = " ".join(words[:300])
        # Pastikan berakhir dengan kalimat lengkap
        last_period = cleaned.rfind(".")
        if last_period > len(cleaned) // 2:
            cleaned = cleaned[:last_period + 1]

    # 3. Cek kalimat eksplanatif berlebihan
    lower_cleaned = cleaned.lower()
    for marker in _EXCESSIVE_EXPLANATION_MARKERS:
        if marker in lower_cleaned:
            logger.warning(f"⚠️ Kalimat eksplanatif berlebihan terdeteksi: '{marker}' — dihapus dari output.")
            # Hapus kalimat yang mengandung marker
            sentences = re.split(r'(?<=[.!?])\s+', cleaned)
            sentences = [s for s in sentences if marker not in s.lower()]
            cleaned = " ".join(sentences)

    # 4. Koreksi halusinasi ekspansi singkatan institusi (mis. KRI -> "Kapal Rudal Induk")
    from .guardrail_kajian import perbaiki_ekspansi_singkatan
    fixed = perbaiki_ekspansi_singkatan(cleaned)
    if fixed != cleaned:
        logger.warning("⚠️ Ekspansi singkatan salah dikoreksi guardrail singkatan baku.")
        cleaned = fixed

    if warnings:
        logger.info(f"Output LLM lulus validasi dengan {len(warnings)} warning(s).")

    return cleaned.strip()


def _strip_metadata_header(text: str) -> str:
    """
    Buang blok metadata yang ikut ditulis AI di AWAL isi surat ("Kepada Yth.",
    "Perihal: ...", "Nomor: ...", "Tanggal: ...", "Hal: ..."). Template SUDAH
    mencetak semuanya — duplikat membuat surat tampak memuat dua header.
    Berhenti pada baris substantif pertama.
    """
    if not text:
        return text
    # Anchor ke BARIS di posisi awal saja (bukan re.sub MULTILINE ke seluruh
    # dokumen) - sebelumnya pola ^/$ mencocokkan baris apa pun di mana pun
    # dalam teks, sehingga kalimat sah di tengah surat yang kebetulan diawali
    # "Tanggal:"/"Perihal:" dsb. ikut terhapus, bukan cuma blok header di awal.
    pola_baris = re.compile(
        r"^\s*(?:kepada\s+(?:yth\.?|yang\s+terhormat)|yth\.?|perihal\s*:|nomor\s*:|"
        r"tanggal\s*:|hal\s*:|lama\s*:|no\.?\s*:)\s*.*$",
        re.IGNORECASE,
    )
    lines = text.strip().split("\n")
    idx = 0
    while idx < len(lines) and pola_baris.match(lines[idx]):
        idx += 1
    return "\n".join(lines[idx:]).lstrip()


def generate_surat_content(request: SuratRequest) -> str:
    """
    Generate isi surat resmi/umum menggunakan Ollama dengan RAG context grounding,
    threshold optimal, dan validasi anti-halusinasi.
    """
    # Ambil referensi dari knowledge base RAG (termasuk aturan anti-halusinasi)
    rag_query = f"{request.perihal} {request.isi_ringkas}"
    rag_context = rag_engine.get_relevant_context(rag_query, top_k=settings.RAG_TOP_K)

    system_prompt = (
        "Anda adalah staf tata naskah dinas resmi dan profesional di instansi pemerintahan/militer Indonesia.\n"
        "TUGAS ANDA: Menyusun isi surat formal yang ringkas, baku, lugas, dan bebas dari kesalahan tata bahasa/ejaan.\n\n"
        "ATURAN ANTI-HALUSINASI (MUTLAK DIPATUHI):\n"
        "1. DILARANG KERAS mengarang nama orang, jabatan, unit kerja, pangkat, atau NRP yang TIDAK ada dalam data input.\n"
        "2. DILARANG KERAS menyebut nomor peraturan, undang-undang, keputusan, atau surat edaran yang TIDAK ada dalam data input.\n"
        "3. DILARANG KERAS mengarang tanggal, waktu, lokasi, atau angka spesifik yang TIDAK diberikan pengguna.\n"
        "4. Jika informasi tidak lengkap, tulis secara UMUM tanpa mengarang detail (gunakan: 'sesuai ketentuan yang berlaku', 'berdasarkan regulasi terkait').\n"
        "5. Gunakan kaidah Bahasa Indonesia baku (EYD/PUEBI).\n"
        "6. Tulis langsung paragraf isi surat tanpa menyertakan kop, nomor surat, tanggal, atau tanda tangan (karena elemen tersebut ditangani otomatis oleh sistem).\n"
        "7. Hindari penggunaan bullet points atau nomor urut kecuali sangat diperlukan.\n"
        "8. Tulis MAKSIMAL 3-4 paragraf pendek (2-3 kalimat per paragraf). Jangan bertele-tele.\n"
        "9. ATURAN ISI-SAHA (MUTLAK): yang Anda tulis adalah PARAGRAF ISI surat saja. "
        "Jangan menulis 'Kepada Yth.', alamat tujuan, 'Perihal: ...', 'Nomor: ...', atau "
        "'Tanggal: ...' — SEMUANYA sudah dicetak otomatis oleh sistem di luar isi. "
        "Mulailah langsung dengan salam pembuka isi (mis. 'Dengan hormat,')."
    )

    user_prompt = f"""\
{rag_context}
Rincian Surat yang akan dibuat:
- Jenis Surat: {request.jenis_surat}
- Nama Pengirim: {request.nama_pengirim}
- Alamat Pengirim: {request.alamat_pengirim}
- Nama Penerima: {request.nama_penerima}
- Alamat Penerima: {request.alamat_penerima}
- Perihal: {request.perihal}
- Poin-poin Pokok / Fakta:
{request.isi_ringkas}

INSTRUKSI FINAL: Tuliskan isi surat resmi secara lengkap berdasarkan HANYA poin-poin pokok di atas. JANGAN menambahkan fakta, nama, nomor regulasi, atau informasi yang TIDAK ada dalam poin-poin di atas.
"""

    # Cek context window budget sebelum memanggil LLM
    _check_context_budget(system_prompt, user_prompt)

    try:
        content = ollama_chat(system_prompt, user_prompt)
        if content:
            # Validasi output anti-halusinasi
            user_data = {
                "jenis_surat": request.jenis_surat,
                "nama_pengirim": request.nama_pengirim,
                "alamat_pengirim": request.alamat_pengirim,
                "nama_penerima": request.nama_penerima,
                "alamat_penerima": request.alamat_penerima,
                "perihal": request.perihal,
                "isi_ringkas": request.isi_ringkas,
            }
            content = _validate_output(content, user_data, extra_context=rag_context)
            # Buang header metadata yang ikut ditulis AI (Kepada Yth./Perihal/Nomor)
            content = _strip_metadata_header(content)
            # Kontrak keluaran: TEKS MENTAH (bukan entity HTML). Renderer PDF
            # (pdf_service._render_template) memakai Jinja2 autoescape=True, dan
            # konsumen JSON (editor klien) melakukan escaping sendiri — escape di
            # sini akan tampil sebagai '&lt;' di PDF/editor (double-escape).
            return content
    except Exception as e:
        logger.warning(f"Ollama generation warning (fallback will be used): {e}")

    # Fallback jika model LLM offline / timeout — kontrak sama dengan jalur LLM:
    # teks mentah; escaping dilakukan renderer PDF (autoescape) saat dicetak.
    return (
        f"Dengan hormat,\n\n"
        f"Sehubungan dengan perihal {request.perihal}, bersama ini kami sampaikan:\n\n"
        f"{request.isi_ringkas}\n\n"
        f"Demikian surat ini kami sampaikan, atas perhatian dan kerja sama yang baik diucapkan terima kasih."
    )

def _generate_single_nota_dinas_paragraph(
    poin: str,
    index: int,
    perihal: str,
    pengirim: str,
    penerima: str,
    rag_context: str = ""
) -> str:
    """
    Mengembangkan SATU poin ringkas menjadi SATU paragraf formal mandiri.
    - Index 0: Paragraf pengantar (Poin 1) diawali 'Sehubungan dasar tersebut, dengan ini disampaikan...'
    - Index > 0: Paragraf lanjutan (Poin 2, 3, dst) membahas poin spesifik tanpa mengulang pengantar.

    RAG context SELALU disertakan untuk grounding anti-halusinasi.
    """
    anti_hal_block = (
        "ATURAN ANTI-HALUSINASI (MUTLAK):\n"
        "- DILARANG mengarang nama orang, jabatan, unit kerja, pangkat, NRP, nomor regulasi, tanggal, atau angka yang TIDAK ada dalam poin yang diberikan.\n"
        "- Jika informasi tidak lengkap, tulis secara umum (gunakan: 'sesuai ketentuan yang berlaku', 'berdasarkan regulasi terkait').\n"
        "- HANYA kembangkan substansi dari poin yang diberikan, JANGAN menambahkan fakta baru.\n"
    )

    if index == 0:
        system_prompt = (
            "Anda adalah staf perumus naskah dinas resmi pada instansi pemerintah.\n"
            "TUGAS: Kembangkan SATU poin ringkasan berikut menjadi SATU paragraf pengantar formal bahasa Indonesia baku.\n\n"
            f"{anti_hal_block}\n"
            "ATURAN FORMAT:\n"
            "1. Paragraf WAJIB DIAWALI PERSIS dengan kalimat: \"Sehubungan dasar tersebut, dengan ini disampaikan ...\"\n"
            "2. HANYA bahas substansi dari poin yang diberikan (JANGAN membahas poin atau topik lain).\n"
            "3. DILARANG menambahkan nomor urut (seperti '1.', '2.'), bullet, salam pembuka/penutup, atau kalimat 'Demikian disampaikan'.\n"
            "4. Tulis dalam 2-3 kalimat formal yang padat dan jelas, diakhiri tanda titik (.)"
        )
    else:
        system_prompt = (
            "Anda adalah staf perumus naskah dinas resmi pada instansi pemerintah.\n"
            "TUGAS: Kembangkan SATU poin ringkasan berikut menjadi SATU paragraf formal lanjutan bahasa Indonesia baku.\n\n"
            f"{anti_hal_block}\n"
            "ATURAN FORMAT:\n"
            "1. DILARANG mengulang kalimat 'Sehubungan dasar tersebut'.\n"
            "2. Langsung jelaskan substansi poin ini secara formal dan lugas (misal diawali dengan: 'Adapun terkait...', 'Selanjutnya mengenai...', 'Guna mendukung hal tersebut...', dsb).\n"
            "3. HANYA bahas poin ini secara spesifik (JANGAN mengulang isi poin sebelumnya).\n"
            "4. DILARANG menambahkan nomor urut (seperti '1.', '2.'), bullet, salam pembuka/penutup, atau kalimat 'Demikian disampaikan'.\n"
            "5. Tulis dalam 2-3 kalimat formal yang padat dan jelas, diakhiri tanda titik (.)"
        )

    # User prompt DENGAN RAG context grounding
    user_prompt = ""
    if rag_context:
        user_prompt += f"{rag_context}\n"
    user_prompt += (
        f"Perihal: {perihal}\nPengirim: {pengirim}\nPenerima: {penerima}\n\n"
        f"Poin Ringkas yang harus dikembangkan:\n{poin}\n\n"
        f"INSTRUKSI FINAL: Tuliskan SATU paragraf resmi berdasarkan HANYA poin di atas. "
        f"JANGAN menambahkan informasi yang tidak ada dalam poin."
    )

    # Cek context window budget
    _check_context_budget(system_prompt, user_prompt)

    try:
        content = _clean_paragraph(ollama_chat(system_prompt, user_prompt))
        if content:
            # Validasi anti-halusinasi pada output paragraf
            user_data = {
                "perihal": perihal,
                "pengirim": pengirim,
                "penerima": penerima,
                "poin": poin,
            }
            content = _validate_output(content, user_data, extra_context=rag_context)

            if index == 0 and not content.lower().startswith("sehubungan dasar tersebut"):
                content = f"Sehubungan dasar tersebut, dengan ini disampaikan {content[0].lower() + content[1:]}"
            return content
    except Exception as e:
        logger.warning(f"Ollama paragraph {index + 1} warning: {e}")

    # Fallback yang aman jika model timeout / offline
    cleaned_p = _clean_paragraph(poin)
    if index == 0:
        if not cleaned_p.lower().startswith("sehubungan dasar tersebut"):
            return f"Sehubungan dasar tersebut, dengan ini disampaikan {cleaned_p[0].lower() + cleaned_p[1:]}."
        return cleaned_p
    else:
        return f"Adapun berkenaan dengan hal tersebut, {cleaned_p[0].lower() + cleaned_p[1:]}."

def generate_isi_nota_dinas(request: NotaDinasRequest) -> list:
    """
    Generate paragraf formal terpisah untuk setiap poin ringkasan pada Nota Dinas (poin 2, 3, 4, ...).
    Mendukung sub-poin (sub-items) bertingkat secara opsional sesuai standar KEP/868/2022.

    RAG context SELALU diinjeksi ke setiap paragraf untuk grounding anti-halusinasi.
    """
    # Ambil RAG context khusus nota dinas (termasuk aturan anti-halusinasi)
    rag_context = rag_engine.get_nota_dinas_context(
        perihal=request.perihal,
        pengirim=request.dari,
        penerima=request.kepada
    )

    logger.info(
        f"RAG context untuk Nota Dinas dimuat: {_estimate_tokens(rag_context)} est. tokens, "
        f"perihal='{request.perihal}'"
    )

    items = []
    if request.isi_ringkas and isinstance(request.isi_ringkas, list):
        for raw in request.isi_ringkas:
            if isinstance(raw, dict):
                teks = str(raw.get("teks", "")).strip()
                subs = [str(s).strip() for s in raw.get("sub_poin", []) if str(s).strip()]
                if teks or subs:
                    items.append({"teks": teks if teks else "Rincian sebagai berikut:", "sub_poin": subs})
            elif hasattr(raw, "teks"):
                teks = str(raw.teks).strip()
                subs = [str(s).strip() for s in (raw.sub_poin or []) if str(s).strip()]
                if teks or subs:
                    items.append({"teks": teks if teks else "Rincian sebagai berikut:", "sub_poin": subs})
            else:
                s = str(raw).strip()
                if s:
                    items.append({"teks": s, "sub_poin": []})
    else:
        for i in range(1, 6):
            val = getattr(request, f"isi_ringkas_{i}", "")
            if val and str(val).strip():
                items.append({"teks": str(val).strip(), "sub_poin": []})

    if not items:
        items = [{"teks": "Permohonan terkait.", "sub_poin": []}]

    results = []
    for idx, itm in enumerate(items):
        poin_text = itm["teks"]
        sub_list = itm["sub_poin"]

        para_text = _generate_single_nota_dinas_paragraph(
            poin=poin_text,
            index=idx,
            perihal=request.perihal,
            pengirim=request.dari,
            penerima=request.kepada,
            rag_context=rag_context  # RAG CONTEXT DIINJEKSI KE SETIAP PARAGRAF
        )

        # Standardisasi tanda baca militer (KEP-868: titik koma dan titik di akhir rincian)
        formatted_subs = []
        n_subs = len(sub_list)
        for s_idx, s_val in enumerate(sub_list):
            clean_s = re.sub(r'[\.,;]+$', '', s_val).strip()
            if s_idx == n_subs - 1:
                formatted_subs.append(f"{clean_s}.")
            elif s_idx == n_subs - 2 and n_subs > 1:
                formatted_subs.append(f"{clean_s}; dan")
            else:
                formatted_subs.append(f"{clean_s};")

        results.append({
            "teks": para_text,
            "sub_poin": formatted_subs
        })

    # Kontrak keluaran setara generate_surat_content: teks MENTAH — renderer
    # PDF autoescape, konsumen JSON meng-escape sendiri. (Dulu di-escape di
    # sini sehingga entity &lt; tercetak apa adanya di PDF.)
    return results