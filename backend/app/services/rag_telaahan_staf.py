import logging
from typing import Dict, Any, Optional

from ..config import settings
from ..schemas.telaahan_staf import TelaahanStafInput, TelaahanStafPasal
from .guardrail import validate_and_sanitize_telaahan_staf, sanitize_text
from .ollama_client import chat as ollama_chat
from .rag_service import rag_engine, _estimate_tokens

logger = logging.getLogger(__name__)

def get_telaahan_staf_context(judul: str, persoalan: str) -> str:
    """
    Mengambil konteks grounding regulasi KEP/868/IX/2022 (Contoh 26) untuk Telaahan Staf.
    """
    context_blocks = [
        "=== PEDOMAN BAKU TELAAHAN STAF TNI (KEP/868/IX/2022 CONTOH 26) ===",
        "Telaahan Staf adalah naskah dinas pemecahan persoalan yang memuat analisis singkat, jelas, dan memberikan jalan keluar/pemecahan yang disarankan.",
        "Struktur wajib terdiri atas 6 pasal baku:",
        "1. Persoalan: pernyataan singkat dan jelas tentang persoalan yang akan dipecahkan.",
        "2. Praanggapan: dugaan beralasan berdasarkan data dan saling berhubungan, kemungkinan kejadian di masa depan.",
        "3. Fakta/Data yang Memengaruhi: landasan analisis dan fakta konkret pemecahan persoalan.",
        "4. Analisis: kupasan pengaruh praanggapan & fakta terhadap persoalan, hambatan, keuntungan & kerugian cara bertindak.",
        "5. Kesimpulan: intisari analisis dan penetapan 1 (satu) pilihan cara bertindak terbaik.",
        "6. Saran: usulan tindakan ringkas dan konkret untuk pimpinan mengatasi persoalan.",
        "\nATURAN BAHASA & ANTI-HALUSINASI:",
        "- Gunakan ragam Bahasa Indonesia militer baku, lugas, presisi, dan objektif.",
        "- DILARANG mengarang nomor regulasi, undang-undang, nama personel, pangkat fiktif, atau angka yang tidak ada dalam input data.",
        "- DILARANG menggunakan markdown bold (**), heading (##), atau bullet list liar."
    ]
    
    # Query knowledge base jika RAG aktif
    if settings.RAG_ENABLED:
        rag_query = f"telaahan staf {judul} {persoalan}"
        kb_matches = rag_engine.search(rag_query, top_k=2)
        if kb_matches:
            context_blocks.append("\nREFERENSI MATERI TERKAIT:")
            for m in kb_matches:
                if m.get("content_snippet"):
                    context_blocks.append(f"- {m['title']}: {m['content_snippet'][:250]}...")

    return "\n".join(context_blocks)


def _call_ollama_for_section(system_prompt: str, user_prompt: str) -> str:
    """Helper pemanggil Ollama (klien bersama); mengembalikan '' saat gagal untuk fallback templat."""
    return ollama_chat(system_prompt, user_prompt)


def generate_telaahan_staf_sections(input_data: TelaahanStafInput) -> Dict[str, str]:
    """
    Menyusun 6 pasal baku Telaahan Staf secara modular (Isolated Section Generation)
    berdasarkan input pengguna dan grounding regulasi KEP/868 Contoh 26.
    """
    # Jika user telah menyediakan pasal_custom lengkap, gunakan langsung
    if input_data.pasal_custom:
        return validate_and_sanitize_telaahan_staf(input_data.pasal_custom)

    rag_grounding = get_telaahan_staf_context(input_data.judul, input_data.input_persoalan)
    
    # Common system rule
    system_base = (
        "Anda adalah Perwira Staf Ahli Tata Naskah Militer Indonesia.\n"
        "Tugas Anda adalah merumuskan pasal Telaahan Staf sesuai KEP/868/IX/2022 (Contoh 26).\n"
        "Gunakan bahasa formal militer, ringkas, padat, lugas, tanpa basa-basi.\n"
        "ATURAN SINGKATAN (MUTLAK): Pertahankan singkatan PERSIS seperti pada input — "
        "DILARANG menguraikan, menerjemahkan, atau menafsirkan singkatan (contoh: KRI tetap 'KRI').\n"
        "ATURAN KONSISTENSI (MUTLAK): Pasal WAJIB konsisten dengan JUDUL, PERSOALAN, dan FAKTA; "
        "DILARANG memasukkan sistem/teknologi yang tidak disebut dalam input.\n"
        "ATURAN REFERENSI (MUTLAK): JANGAN menyebut nama/judul dokumen referensi, daftar "
        "dokumen, atau kata 'dummy' di dalam naskah — referensi hanya untuk grounding isi.\n"
        "DILARANG menuliskan judul pasal (seperti 'Persoalan.' atau '1.'), DILARANG menggunakan markdown (**bold**, ##heading, - bullet).\n"
        "Tulis langsung paragraf isi yang siap ditempatkan di dokumen resmi."
    )

    context_prompt = f"""\
{rag_grounding}

INFORMASI KAJIAN:
- Judul: {input_data.judul}
- Poin Persoalan: {input_data.input_persoalan}
- Data/Fakta Pendukung: {input_data.input_fakta}
- Usulan Saran/Solusi: {input_data.input_saran}
"""

    pasal_results = {}

    # 1. Generate Pasal: Persoalan
    p1_sys = f"{system_base}\nTUGAS: Rumuskan PASAL PERSOALAN dalam 2-3 kalimat lugas. Nyatakan persoalan inti yang dihadapi dan memerlukan pemecahan segera."
    p1_user = f"{context_prompt}\nInti input persoalan pengguna: {input_data.input_persoalan}\nRumuskan paragraf Persoalan:"
    p1_out = _call_ollama_for_section(p1_sys, p1_user)
    if not p1_out:
        p1_out = f"Kebutuhan perumusan langkah strategis dan terpadu dalam mengatasi {input_data.input_persoalan} guna menjamin kelancaran pelaksanaan tugas pokok satuan secara optimal."
    pasal_results["persoalan"] = p1_out

    # 2. Generate Pasal: Praanggapan
    p2_sys = f"{system_base}\nTUGAS: Rumuskan PASAL PRAANGGAPAN dalam 2-3 kalimat. Memuat dugaan beralasan dan kemungkinan perkembangan situasi di masa depan jika langkah pemecahan dilakukan."
    p2_user = f"{context_prompt}\nInput/arahan praanggapan pengguna: {input_data.input_praanggapan or 'Dukungan sumber daya, regulasi, dan koordinasi yang baik akan menjamin tercapainya sasaran.'}\nRumuskan paragraf Praanggapan:"
    p2_out = _call_ollama_for_section(p2_sys, p2_user)
    if not p2_out:
        p2_out = "Dukungan alokasi sumber daya yang memadai, penguatan regulasi operasional, serta sinergi antarunsur terkait diyakini mampu mengakselerasi penyelesaian persoalan dan meminimalisasi potensi hambatan di masa mendatang."
    pasal_results["praanggapan"] = p2_out

    # 3. Generate Pasal: Fakta/Data yang Memengaruhi
    p3_sys = f"{system_base}\nTUGAS: Rumuskan PASAL FAKTA/DATA YANG MEMENGARUHI dalam 2-4 kalimat formal. Landaskan HANYA pada fakta konkret yang diberikan pengguna."
    p3_user = f"{context_prompt}\nData/Fakta konkret dari pengguna:\n{input_data.input_fakta}\nRumuskan paragraf Fakta/Data yang Memengaruhi:"
    p3_out = _call_ollama_for_section(p3_sys, p3_user)
    if not p3_out:
        p3_out = f"Berdasarkan data dan evaluasi di lapangan, kondisi saat ini menunjukkan bahwa {input_data.input_fakta}. Kondisi ini secara langsung memengaruhi efektivitas pelaksanaan tugas kedinasan."
    pasal_results["fakta"] = p3_out

    # 4. Generate Pasal: Analisis
    p4_sys = f"{system_base}\nTUGAS: Rumuskan PASAL ANALISIS dalam 3-5 kalimat mendalam. Kupas pengaruh fakta dan praanggapan terhadap persoalan, pertimbangan hambatan, serta keuntungan dan kerugian cara bertindak."
    p4_user = f"{context_prompt}\nFokus arahan analisis pengguna: {input_data.input_analisis or 'Analisis efektivitas, efisiensi anggaran, keamanan operasional, dan keberlanjutan sistem.'}\nRumuskan paragraf Analisis:"
    p4_out = _call_ollama_for_section(p4_sys, p4_user)
    if not p4_out:
        p4_out = (
            f"Melalui penelaahan mendalam terhadap fakta yang ada, keterbatasan yang dihadapi dapat diatasi melalui penerapan langkah terstruktur dan terukur. "
            f"Alternatif tindakan ini memberikan keuntungan signifikan berupa efisiensi waktu, optimalisasi sumber daya yang ada, serta memitigasi risiko disrupsi operasional, "
            f"meskipun memerlukan koordinasi intensif pada tahap awal implementasi."
        )
    pasal_results["analisis"] = p4_out

    # 5. Generate Pasal: Kesimpulan
    p5_sys = f"{system_base}\nTUGAS: Rumuskan PASAL KESIMPULAN dalam 2-3 kalimat. Memuat intisari hasil analisis dan penetapan satu cara bertindak terbaik yang paling feasible."
    p5_user = f"{context_prompt}\nArahan kesimpulan pengguna: {input_data.input_kesimpulan or 'Langkah terintegrasi merupakan opsi terbaik yang paling efektif dan efisien.'}\nRumuskan paragraf Kesimpulan:"
    p5_out = _call_ollama_for_section(p5_sys, p5_user)
    if not p5_out:
        p5_out = (
            f"Berdasarkan hasil analisis terhadap persoalan dan fakta yang ada, disimpulkan bahwa penerapan langkah strategis terpadu "
            f"merupakan cara bertindak terbaik yang paling efektif, efisien, dan realistis untuk menyelesaikan permasalahan secara menyeluruh."
        )
    pasal_results["kesimpulan"] = p5_out

    # 6. Generate Pasal: Saran
    p6_sys = f"{system_base}\nTUGAS: Rumuskan PASAL SARAN dalam 2-3 kalimat ringkas dan jelas. Berikan usul tindakan konkret yang disarankan kepada pimpinan untuk mengatasi persoalan."
    p6_user = f"{context_prompt}\nUsulan saran/solusi pengguna: {input_data.input_saran}\nRumuskan paragraf Saran:"
    p6_out = _call_ollama_for_section(p6_sys, p6_user)
    if not p6_out:
        p6_out = f"Disarankan kepada pimpinan untuk berkenan menyetujui langkah tindak lanjut berupa {input_data.input_saran}, serta menerbitkan petunjuk teknis pelaksanaan sebagai pedoman operasional di satuan."
    pasal_results["saran"] = p6_out

    # Validasi dan bersihkan seluruh pasal
    return validate_and_sanitize_telaahan_staf(pasal_results)
