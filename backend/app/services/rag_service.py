import os
import re
import json
import math
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import docx
except ImportError:
    docx = None

from ..config import settings

logger = logging.getLogger(__name__)

# Stopwords umum bahasa Indonesia untuk pembersihan teks pencarian
ID_STOPWORDS = {
    "yang", "di", "dan", "dari", "ke", "ini", "itu", "untuk", "pada", "adalah",
    "sebagai", "dengan", "atau", "oleh", "juga", "akan", "telah", "dapat",
    "kami", "kita", "mereka", "anda", "saya", "dia", "dalam", "atas", "karena",
    "secara", "tentang", "maka", "tersebut", "antara", "setiap", "agar", "bisa"
}


def _tokenize(text: str) -> List[str]:
    """Tokenisasi teks menjadi kata-kata bersih untuk pencarian semantik."""
    text_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    tokens = [t.strip() for t in text_clean.split() if len(t.strip()) > 2]
    return [t for t in tokens if t not in ID_STOPWORDS]


def _estimate_tokens(text: str) -> int:
    """
    Estimasi jumlah token dari teks.
    Rasio umum Bahasa Indonesia: ~1 token per 3.5 karakter (lebih konservatif dari English).
    """
    return max(1, len(text) // 3)


class DocumentChunk:
    def __init__(self, doc_id: str, title: str, source_file: str, content: str,
                 perihal: str = "", dasar: str = "", isi_ringkas: str = "", doc_type: str = "nota_dinas"):
        self.doc_id = doc_id
        self.title = title
        self.source_file = source_file
        self.content = content
        self.perihal = perihal
        self.dasar = dasar
        self.isi_ringkas = isi_ringkas
        self.doc_type = doc_type
        self.tokens = _tokenize(f"{title} {perihal} {dasar} {content}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source_file": self.source_file,
            "content": self.content,
            "perihal": self.perihal,
            "dasar": self.dasar,
            "isi_ringkas": self.isi_ringkas,
            "doc_type": self.doc_type,
            "tokens": self.tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentChunk":
        chunk = cls(
            doc_id=data["doc_id"],
            title=data["title"],
            source_file=data["source_file"],
            content=data["content"],
            perihal=data.get("perihal", ""),
            dasar=data.get("dasar", ""),
            isi_ringkas=data.get("isi_ringkas", ""),
            doc_type=data.get("doc_type", "nota_dinas"),
        )
        chunk.tokens = data.get("tokens", _tokenize(chunk.content))
        return chunk


class RAGEngine:
    """
    Mesin RAG (Retrieval-Augmented Generation) Lokal untuk Tata Naskah Dinas.
    Mendukung indexing dokumen referensi DOCX, MD, TXT, dan pencarian semantik hybrid.
    Dilengkapi dengan context budget management dan anti-halusinasi enforcement.
    """

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.doc_freq: Dict[str, int] = {}
        self.total_docs: int = 0
        self.avg_doc_len: float = 0.0
        self.is_indexed: bool = False
        self.last_indexed_at: Optional[str] = None
        self._anti_hallucination_context: str = ""
        # Melindungi swap indeks saat reindex (worker thread) bersamaan dengan search()
        self._index_lock = threading.RLock()
        self._load_from_cache_or_build()
        self._load_anti_hallucination_rules()

    def _load_anti_hallucination_rules(self):
        """
        Muat aturan anti-halusinasi dari knowledge base.
        Konten ini SELALU disertakan di setiap prompt LLM.
        """
        anti_hal_path = settings.KNOWLEDGE_DIR / "aturan_anti_halusinasi.md"
        if anti_hal_path.exists():
            try:
                with open(anti_hal_path, "r", encoding="utf-8", errors="ignore") as f:
                    self._anti_hallucination_context = f.read().strip()
                logger.info("Aturan anti-halusinasi berhasil dimuat dari knowledge base.")
            except Exception as e:
                logger.warning(f"Gagal memuat aturan anti-halusinasi: {e}")

    def _extract_kep868_docx(self, file_path: Path) -> List[DocumentChunk]:
        """
        Ekstrak aturan wajib, format baku, dan kaidah penulisan dari dokumen master
        KEP/868/2022 Petunjuk Referensi Tata Tulis Militer di Lingkungan TNI.
        """
        if not docx:
            return []

        chunks = []
        try:
            # Chunk 1: Aturan & Struktur Baku Nota Dinas KEP-868 TNI
            nota_dinas_rule = (
                "ATURAN BAKU NOTA DINAS (KEP/868/2022 TNI):\n"
                "1. Definisi: Nota dinas adalah bentuk tulisan dinas (tuldis) yang memuat pemberitahuan, pernyataan, "
                "dan permintaan dari seorang pejabat kepada pejabat lain secara terbatas di lingkungan satker sendiri.\n"
                "2. Kelompok Kepala:\n"
                "   - Kop nama badan diletakkan di kiri atas dan diberi garis penutup selebar teks terpanjang.\n"
                "   - Tulisan 'NOTA DINAS' ditulis simetris di tengah dengan huruf kapital seluruhnya tanpa garis bawah.\n"
                "   - Penomoran: 'Nomor [Klasifikasi: B/R/SR]/ND-[No]/[Bulan Romawi]/[Tahun]/[Satker]'.\n"
                "   - Baris Kepada Yth, Dari, Perihal ditulis di tepi kiri dan diberi garis pemisah penutup.\n"
                "3. Kelompok Isi:\n"
                "   - '1. Dasar:' memuat landasan hukum atau surat rujukan (jika jamak, gunakan sub-poin a., b., dst.).\n"
                "   - '2.' Pembukaan: WAJIB diawali kalimat 'Sehubungan dasar tersebut, dengan ini disampaikan ...' "
                "atau 'Sehubungan dengan dasar tersebut di atas, dengan ini disampaikan ...'\n"
                "   - '3., 4., dst.' Poin Lanjutan: Menguraikan rincian substansi per poin secara spesifik dan terpisah tanpa mengulang pembuka.\n"
                "   - Nomor Terakhir (Penutup): 'Demikian disampaikan mohon menjadi perhatian.' atau 'Demikian mohon menjadi periksa.'\n"
                "4. Kelompok Penutup:\n"
                "   - Tempat dan tanggal pembuatan (misal: 'Jakarta, 22 Agustus 2026').\n"
                "   - Tajuk tanda tangan: Jabatan (di kanan bawah), spasi tanda tangan / QR Code, Nama Pejabat (Budi Santoso), Pangkat/NRP.\n"
                "   - Nota dinas tidak dibubuhi cap dinas fisik karena berlaku internal satker (dapat menggunakan verifikasi QR).\n"
                "5. Tipografi & Tata Letak: Font Arial 12pt, Spasi 1.25, Rata Kanan-Kiri (Justified)."
            )
            chunks.append(DocumentChunk(
                doc_id="KEP-868-NOTA-DINAS",
                title="Aturan Baku Nota Dinas TNI (KEP/868/2022)",
                source_file=file_path.name,
                content=nota_dinas_rule,
                perihal="Aturan Baku Nota Dinas TNI",
                dasar="Keputusan Panglima TNI Nomor KEP/868/2022",
                isi_ringkas=nota_dinas_rule,
                doc_type="aturan_wajib"
            ))

            # Chunk 2: Aturan & Struktur Baku Surat Resmi TNI KEP-868
            surat_rule = (
                "ATURAN BAKU SURAT RESMI/DINAS (KEP/868/2022 TNI):\n"
                "1. Definisi: Surat adalah bentuk tulisan dinas yang memuat pernyataan, permohonan, atau penyampaian "
                "kepada pihak internal maupun instansi eksternal.\n"
                "2. Susunan:\n"
                "   - Kepala: Kop nama instansi, Nomor surat, Klasifikasi (B/R/SR), Lampiran, Perihal, Alamat Tujuan.\n"
                "   - Isi: Paragraf pembuka naratif formal, paragraf isi/maksud surat, dan paragraf penutup.\n"
                "   - Penutup: Tanggal surat, Jabatan penandatangan, tanda tangan, nama pejabat, tembusan.\n"
                "3. Bahasa: Menggunakan bahasa Indonesia baku, santun, lugas, dan terstruktur tanpa singkatan yang tidak resmi."
            )
            chunks.append(DocumentChunk(
                doc_id="KEP-868-SURAT-DINAS",
                title="Aturan Baku Surat Resmi TNI (KEP/868/2022)",
                source_file=file_path.name,
                content=surat_rule,
                perihal="Aturan Baku Surat Dinas TNI",
                dasar="Keputusan Panglima TNI Nomor KEP/868/2022",
                isi_ringkas=surat_rule,
                doc_type="aturan_wajib"
            ))

            # Chunk 3: Kaidah Tata Tulis Militer & Ejaan Baku TNI KEP-868
            ttm_rule = (
                "KAIDAH TATA TULIS MILITER (TTM) TNI (KEP/868/2022):\n"
                "1. Penomoran Bertingkat: Angka Arab (1., 2.) -> Huruf Kecil (a., b.) -> Angka Berurung (1), 2)) -> Huruf Berurung (a), b)).\n"
                "2. Penggunaan Kata Penghubung Antar-Nomor:\n"
                "   - Nomor 1: Dasar hukum / rujukan.\n"
                "   - Nomor 2: Pembuka ('Sehubungan dasar tersebut, ...').\n"
                "   - Nomor 3, 4: Penjelasan/Substansi lanjutan ('Adapun...', 'Selanjutnya...', 'Guna mendukung...').\n"
                "   - Nomor Penutup: 'Demikian disampaikan mohon menjadi perhatian.'\n"
                "3. Setiap nomor paragraf merupakan satu kesatuan utuh yang diakhiri tanda titik (.) sebelum beralih ke nomor berikutnya."
            )
            chunks.append(DocumentChunk(
                doc_id="KEP-868-TATA-TULIS",
                title="Kaidah Tata Tulis Militer (TTM) TNI (KEP/868/2022)",
                source_file=file_path.name,
                content=ttm_rule,
                perihal="Kaidah Tata Tulis Militer TNI",
                dasar="Keputusan Panglima TNI Nomor KEP/868/2022",
                isi_ringkas=ttm_rule,
                doc_type="aturan_wajib"
            ))

            logger.info(f"Berhasil mengekstrak {len(chunks)} modul aturan master dari {file_path.name}")
        except Exception as e:
            logger.warning(f"Gagal memproses KEP-868 docx: {e}")

        return chunks

    def _extract_kep868_txt(self, file_path: Path) -> List[DocumentChunk]:
        """
        Ekstrak dan chunk file extracted_kep868.txt yang berisi teks lengkap
        KEP/868/2022 (185KB). Di-split per BAB/section untuk efisiensi retrieval.
        """
        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                full_text = f.read()

            if not full_text.strip():
                return chunks

            # Split per BAB (BAB I, BAB II, dst.)
            bab_pattern = re.compile(r'(BAB\s+[IVX]+\s*\n)', re.IGNORECASE)
            sections = bab_pattern.split(full_text)

            current_title = "KEP-868 Pendahuluan"
            current_content = []
            chunk_idx = 0

            for part in sections:
                part_stripped = part.strip()
                if bab_pattern.match(part):
                    # Simpan chunk sebelumnya
                    if current_content:
                        content_text = "\n".join(current_content).strip()
                        if len(content_text) > 100:  # Hanya chunk yang bermakna
                            # Potong chunk besar menjadi max ~2000 karakter
                            for sub_start in range(0, len(content_text), 2000):
                                sub_content = content_text[sub_start:sub_start + 2000]
                                if len(sub_content) > 50:
                                    chunks.append(DocumentChunk(
                                        doc_id=f"KEP-868-TXT-{chunk_idx:03d}",
                                        title=f"KEP/868/2022 - {current_title}",
                                        source_file=file_path.name,
                                        content=sub_content,
                                        perihal=current_title,
                                        dasar="Keputusan Panglima TNI Nomor KEP/868/2022",
                                        isi_ringkas=sub_content[:300],
                                        doc_type="aturan_referensi"
                                    ))
                                    chunk_idx += 1
                    current_title = part_stripped
                    current_content = []
                else:
                    current_content.append(part_stripped)

            # Simpan chunk terakhir
            if current_content:
                content_text = "\n".join(current_content).strip()
                if len(content_text) > 100:
                    for sub_start in range(0, len(content_text), 2000):
                        sub_content = content_text[sub_start:sub_start + 2000]
                        if len(sub_content) > 50:
                            chunks.append(DocumentChunk(
                                doc_id=f"KEP-868-TXT-{chunk_idx:03d}",
                                title=f"KEP/868/2022 - {current_title}",
                                source_file=file_path.name,
                                content=sub_content,
                                perihal=current_title,
                                dasar="Keputusan Panglima TNI Nomor KEP/868/2022",
                                isi_ringkas=sub_content[:300],
                                doc_type="aturan_referensi"
                            ))
                            chunk_idx += 1

            logger.info(f"Berhasil mengekstrak {len(chunks)} chunk dari {file_path.name}")
        except Exception as e:
            logger.warning(f"Gagal memproses KEP-868 txt: {e}")

        return chunks

    def _extract_docx(self, file_path: Path) -> Optional[DocumentChunk]:
        """Ekstrak konten dan struktur naskah dinas dari file DOCX."""
        if not docx:
            if not getattr(self, '_has_logged_docx_warning', False):
                logger.info("Modul python-docx tidak aktif, pembacaan file .docx dilewati (dokumen .md, .txt, dan .json tetap diindeks penuh).")
                self._has_logged_docx_warning = True
            return None

        try:
            doc = docx.Document(str(file_path))
            full_text = []
            perihal = ""
            dasar = ""
            isi_parts = []

            for p in doc.paragraphs:
                txt = p.text.strip()
                if not txt:
                    continue
                full_text.append(txt)

                txt_lower = txt.lower()
                if "perihal" in txt_lower and ":" in txt:
                    perihal = txt.split(":", 1)[1].strip()
                elif txt.startswith("1. Dasar") or "dasar:" in txt_lower:
                    dasar = txt
                elif txt.startswith("2.") or txt_lower.startswith("sehubungan dasar tersebut"):
                    isi_parts.append(txt)
                elif any(txt.startswith(f"{i}.") for i in range(3, 10)):
                    isi_parts.append(txt)

            # Cek juga di tabel jika ada
            for table in doc.tables:
                for row in table.rows:
                    row_txt = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if "perihal" in row_txt.lower() and not perihal:
                        for cell in row.cells:
                            if ":" in cell.text:
                                perihal = cell.text.split(":", 1)[1].strip()
                    full_text.append(row_txt)

            content = "\n".join(full_text)
            title = file_path.stem
            if not perihal:
                # Coba ambil judul dokumen sebagai perihal
                perihal = title.replace("Nota Dinas Dummy -", "").strip()

            return DocumentChunk(
                doc_id=file_path.stem,
                title=title,
                source_file=file_path.name,
                content=content,
                perihal=perihal,
                dasar=dasar,
                isi_ringkas="\n".join(isi_parts),
                doc_type="nota_dinas"
            )
        except Exception as e:
            logger.warning(f"Gagal ekstrak file DOCX {file_path.name}: {e}")
            return None

    def _extract_text_file(self, file_path: Path) -> Optional[DocumentChunk]:
        """Ekstrak file Markdown atau teks aturan."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if not content:
                return None

            return DocumentChunk(
                doc_id=file_path.stem,
                title=file_path.name,
                source_file=file_path.name,
                content=content,
                perihal="Aturan dan Pedoman Tata Naskah Dinas",
                doc_type="aturan"
            )
        except Exception as e:
            logger.warning(f"Gagal membaca teks file {file_path.name}: {e}")
            return None

    def index_all_documents(self, force: bool = False) -> int:
        """
        Pindai folder dokumen referensi dan buat indeks semantik BM25/TF-IDF.
        Termasuk indexing extracted_kep868.txt dari root project.

        Thread-safety: reindex berjalan di worker thread (asyncio.to_thread)
        sementara search() dibaca thread lain — akumulasi dilakukan ke list
        LOKAL lalu di-swap atomik di bawah lock agar pembaca tidak pernah
        melihat indeks kosong/parsial.
        """
        with self._index_lock:
            new_chunks: list = []
            doc_paths: List[Path] = []

            def _layak_indeks(p: Path) -> bool:
                # File latihan/dummy TIDAK boleh masuk knowledge base — pernah
                # dikutip AI ke naskah resmi ("...rekomendasi DAFTAR 50 NOTA DINAS
                # DUMMY"). DAFTAR_DOKUMEN.txt hanya daftar indeks, bukan materi.
                nama = p.name.lower()
                return "dummy" not in nama and nama != "daftar_dokumen.txt"

            # 1. Pindai folder fine-tune-dokumen
            if settings.DOCS_DIR.exists() and settings.DOCS_DIR.is_dir():
                doc_paths.extend(p for p in settings.DOCS_DIR.glob("*.docx") if _layak_indeks(p))
                doc_paths.extend(p for p in settings.DOCS_DIR.glob("*.txt") if _layak_indeks(p))
                doc_paths.extend(p for p in settings.DOCS_DIR.glob("*.md") if _layak_indeks(p))

            # 2. Pindai folder knowledge tambahan
            if settings.KNOWLEDGE_DIR.exists() and settings.KNOWLEDGE_DIR.is_dir():
                doc_paths.extend(list(settings.KNOWLEDGE_DIR.glob("*.md")))
                doc_paths.extend(list(settings.KNOWLEDGE_DIR.glob("*.txt")))
                doc_paths.extend(list(settings.KNOWLEDGE_DIR.glob("*.docx")))

            # 3. Index extracted_kep868.txt dari root project (file besar 185KB)
            kep868_txt_path = settings.PROJECT_ROOT / "extracted_kep868.txt"
            if kep868_txt_path.exists():
                kep868_txt_chunks = self._extract_kep868_txt(kep868_txt_path)
                new_chunks.extend(kep868_txt_chunks)
                logger.info(f"Indexed {len(kep868_txt_chunks)} chunks dari extracted_kep868.txt")

            # Hapus duplikat path
            unique_paths = list({p.resolve(): p for p in doc_paths}.values())

            for p in unique_paths:
                if "KEP-868" in p.name.upper():
                    kep_chunks = self._extract_kep868_docx(p)
                    new_chunks.extend(kep_chunks)
                elif p.suffix.lower() == ".docx":
                    chunk = self._extract_docx(p)
                    if chunk:
                        new_chunks.append(chunk)
                elif p.suffix.lower() in [".txt", ".md"]:
                    chunk = self._extract_text_file(p)
                    if chunk:
                        new_chunks.append(chunk)

            # Swap atomik: pembaca hanya melihat indeks lama-utuh atau baru-utuh
            self.chunks = new_chunks
            self._build_index_statistics()
            self._save_cache()

            logger.info(f"RAG Indexing selesai: {len(self.chunks)} dokumen referensi terindeks.")
            return len(self.chunks)


    def _build_index_statistics(self):
        """Hitung IDF (Inverse Document Frequency) untuk skoring relevansi."""
        self.total_docs = len(self.chunks)
        self.doc_freq = {}
        total_tokens = 0

        for chunk in self.chunks:
            total_tokens += len(chunk.tokens)
            unique_tokens = set(chunk.tokens)
            for t in unique_tokens:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1

        self.avg_doc_len = (total_tokens / self.total_docs) if self.total_docs > 0 else 1.0
        self.is_indexed = True
        self.last_indexed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _save_cache(self):
        """Simpan cache indeks ke disk dalam format JSON."""
        try:
            data = {
                "last_indexed_at": self.last_indexed_at,
                "total_docs": self.total_docs,
                "chunks": [c.to_dict() for c in self.chunks]
            }
            with open(settings.RAG_INDEX_CACHE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Gagal menyimpan cache RAG: {e}")

    def _load_from_cache_or_build(self):
        """Muat dari cache jika ada, atau buat baru."""
        if settings.RAG_INDEX_CACHE.exists():
            try:
                with open(settings.RAG_INDEX_CACHE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = [DocumentChunk.from_dict(d) for d in data.get("chunks", [])]
                self.last_indexed_at = data.get("last_indexed_at")
                self._build_index_statistics()
                if self.total_docs > 0:
                    logger.info(f"RAG dimuat dari cache: {self.total_docs} dokumen.")
                    return
            except Exception as e:
                logger.warning(f"Gagal memuat cache RAG: {e}. Melakukan re-index...")

        self.index_all_documents()

    def search(self, query: str, top_k: int = 3, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pencarian BM25 & Semantic Boosting untuk menemukan referensi dokumen paling relevan.

        Lock diambil agar pasangan chunks+statistik selalu konsisten meski
        reindex berjalan di thread lain.
        """
        with self._index_lock:
            return self._search_locked(query, top_k=top_k, doc_type=doc_type)

    def _search_locked(self, query: str, top_k: int = 3, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_indexed or not self.chunks:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        k1 = 1.5
        b = 0.75
        scored_results = []

        for chunk in self.chunks:
            if doc_type and chunk.doc_type != doc_type:
                continue

            score = 0.0
            doc_len = len(chunk.tokens)
            token_counts = {}
            for t in chunk.tokens:
                token_counts[t] = token_counts.get(t, 0) + 1

            for qt in query_tokens:
                tf = token_counts.get(qt, 0)
                if tf == 0:
                    continue

                df = self.doc_freq.get(qt, 1)
                # BM25 IDF formulation
                idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

                # BM25 Term Weight
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)

                # Semantic Boost jika kata kunci ada di perihal/judul
                if qt in chunk.perihal.lower() or qt in chunk.title.lower():
                    score += 2.5

            if score > 0:
                scored_results.append((score, chunk))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_results[:top_k]

        return [
            {
                "score": round(s, 3),
                "title": c.title,
                "source_file": c.source_file,
                "perihal": c.perihal,
                "dasar": c.dasar,
                "isi_ringkas": c.isi_ringkas,
                "content_snippet": c.content[:400] + ("..." if len(c.content) > 400 else ""),
                "doc_type": c.doc_type
            }
            for s, c in top_matches
        ]

    def _trim_context_to_budget(self, context: str, budget_tokens: int) -> str:
        """
        Pangkas context RAG agar tidak melebihi budget token.
        Prioritas: aturan wajib dipertahankan, contoh dokumen dipangkas terlebih dahulu.
        """
        estimated = _estimate_tokens(context)
        if estimated <= budget_tokens:
            return context

        logger.warning(
            f"RAG context ({estimated} est. tokens) melebihi budget ({budget_tokens} tokens). "
            f"Memangkas contoh dokumen..."
        )

        # Split menjadi blok-blok: aturan wajib vs contoh referensi
        blocks = context.split("\n\nCONTOH REFERENSI")
        if len(blocks) > 1:
            # Pertahankan aturan wajib, pangkas contoh
            trimmed = blocks[0]
            if _estimate_tokens(trimmed) <= budget_tokens:
                return trimmed + "\n\nInstruksi: Patuhi format baku KEP/868/2022 di atas dan gunakan gaya bahasa militer formal.\n"

        # Jika masih terlalu besar, potong dari belakang
        lines = context.split("\n")
        result_lines = []
        running_tokens = 0
        for line in lines:
            line_tokens = _estimate_tokens(line)
            if running_tokens + line_tokens > budget_tokens:
                break
            result_lines.append(line)
            running_tokens += line_tokens

        return "\n".join(result_lines) + "\n"

    def get_relevant_context(self, query: str, top_k: int = 2) -> str:
        """
        Menghasilkan blok konteks referensi terformat yang menggabungkan:
        1. BATASAN ANTI-HALUSINASI (selalu disertakan).
        2. Aturan Wajib KEP/868/2022 (Tata Tulis Militer TNI).
        3. Contoh Dokumen Serupa dari Knowledge Base Instansi.

        Context dipangkas otomatis agar tidak melebihi budget token.
        """
        if not settings.RAG_ENABLED:
            return ""

        context_blocks = []

        # 0. SELALU sertakan batasan anti-halusinasi di AWAL context
        if self._anti_hallucination_context:
            context_blocks.append("=== BATASAN KETAT GENERATOR AI (WAJIB DIPATUHI) ===")
            # Ambil hanya bagian kritis (larangan dan diperbolehkan, tanpa contoh panjang)
            anti_hal_lines = self._anti_hallucination_context.split("\n")
            critical_lines = []
            in_critical = False
            for line in anti_hal_lines:
                if "LARANGAN MUTLAK" in line or "DIPERBOLEHKAN" in line or "PENANGANAN INFORMASI" in line:
                    in_critical = True
                elif line.startswith("## CONTOH"):
                    in_critical = False  # Skip contoh panjang untuk hemat token
                if in_critical:
                    critical_lines.append(line)
            if critical_lines:
                context_blocks.append("\n".join(critical_lines))
            else:
                # Fallback: sertakan ringkasan larangan
                context_blocks.append(
                    "LARANGAN: Dilarang mengarang nama, jabatan, nomor regulasi, tanggal, angka, "
                    "atau fakta apapun yang TIDAK diberikan dalam data input pengguna."
                )

        # 1. Selalu sertakan Aturan Wajib KEP-868
        kep868_rules = [c for c in self.chunks if "KEP-868" in c.doc_id or c.doc_type == "aturan_wajib"]
        if kep868_rules:
            context_blocks.append("\nPEDOMAN & ATURAN WAJIB TATA NASKAH DINAS MILITER (KEP/868/2022 TNI):")
            for r in kep868_rules[:3]:
                context_blocks.append(f"- {r.title}:\n{r.content}")

        # 2. Tambahkan pencarian dokumen contoh relevan
        matches = self.search(query, top_k=top_k)
        doc_matches = [m for m in matches if m.get("doc_type") not in ["aturan", "aturan_wajib"]]

        if doc_matches:
            context_blocks.append("\nCONTOH REFERENSI KOSAKATA & REDAKSI DARI DOKUMEN SERUPA:")
            for idx, m in enumerate(doc_matches[:2], 1):
                sample_isi = m['isi_ringkas'] if m['isi_ringkas'] else m['content_snippet']
                clean_sample = "\n".join([line for line in sample_isi.split("\n") if line.strip()][:3])
                context_blocks.append(f"[{idx}] Perihal: {m['perihal']}\n{clean_sample}")

        context_blocks.append("\nInstruksi: Patuhi format baku KEP/868/2022 di atas dan gunakan gaya bahasa militer formal.")
        full_context = "\n\n".join(context_blocks) + "\n\n"

        # Pangkas context agar tidak melebihi budget token
        max_rag_tokens = settings.MAX_RAG_CONTEXT_TOKENS
        full_context = self._trim_context_to_budget(full_context, max_rag_tokens)

        return full_context

    def get_nota_dinas_context(self, perihal: str, pengirim: str, penerima: str) -> str:
        """
        Variant khusus get_relevant_context untuk Nota Dinas.
        Menghasilkan context yang lebih spesifik untuk pembuatan paragraf nota dinas.
        Selalu menyertakan aturan anti-halusinasi dan aturan nota dinas KEP-868.
        """
        if not settings.RAG_ENABLED:
            return ""

        query = f"nota dinas {perihal}"
        context_blocks = []

        # 0. Batasan anti-halusinasi (ringkasan ketat)
        context_blocks.append(
            "BATASAN KETAT: Anda HANYA boleh mengembangkan poin yang diberikan menjadi kalimat formal. "
            "DILARANG mengarang nama orang, jabatan, unit kerja, nomor peraturan, tanggal, angka, "
            "atau fakta apapun yang TIDAK ada dalam data input. "
            "Jika informasi tidak lengkap, tulis secara umum tanpa mengarang detail."
        )

        # 1. Aturan nota dinas KEP-868
        nota_rules = [c for c in self.chunks if c.doc_id == "KEP-868-NOTA-DINAS" or c.doc_id == "KEP-868-TATA-TULIS"]
        if nota_rules:
            context_blocks.append("ATURAN NOTA DINAS (KEP/868/2022):")
            for r in nota_rules[:2]:
                context_blocks.append(r.content)

        # 2. Contoh dokumen serupa (terbatas untuk hemat token)
        matches = self.search(query, top_k=2)
        doc_matches = [m for m in matches if m.get("doc_type") == "nota_dinas"]
        if doc_matches:
            context_blocks.append("CONTOH REDAKSI NOTA DINAS SERUPA:")
            for m in doc_matches[:1]:  # Hanya 1 contoh untuk hemat token
                sample = m['isi_ringkas'][:200] if m['isi_ringkas'] else m['content_snippet'][:200]
                context_blocks.append(f"Perihal: {m['perihal']}\n{sample}")

        full_context = "\n\n".join(context_blocks) + "\n\n"

        # Pangkas agar muat dalam budget (nota dinas per-paragraf, budget lebih kecil)
        nota_budget = min(settings.MAX_RAG_CONTEXT_TOKENS, 1500)  # Lebih ringkas per paragraf
        return self._trim_context_to_budget(full_context, nota_budget)


    def get_status(self) -> Dict[str, Any]:
        """Status terkini sistem RAG untuk API dan Bot."""
        return {
            "is_enabled": settings.RAG_ENABLED,
            "is_indexed": self.is_indexed,
            "total_documents": len(self.chunks),
            "last_indexed_at": self.last_indexed_at,
            "knowledge_path": str(settings.DOCS_DIR),
            "anti_hallucination_loaded": bool(self._anti_hallucination_context),
            "context_budget_ratio": settings.CONTEXT_BUDGET_RATIO,
            "max_rag_context_tokens": settings.MAX_RAG_CONTEXT_TOKENS,
            "sample_titles": [c.title for c in self.chunks[:5]]
        }


# Inisialisasi singleton RAGEngine
rag_engine = RAGEngine()
