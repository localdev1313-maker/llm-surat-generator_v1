import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Pola-pola markdown atau simbol liar yang sering muncul dari LLM
_MARKDOWN_CLEAN_PATTERNS = [
    (re.compile(r'\*\*([^*]+)\*\*'), r'\1'),      # Hapus bold **text**
    (re.compile(r'__([^_]+)__'), r'\1'),          # Hapus bold __text__
    (re.compile(r'\*([^*]+)\*'), r'\1'),          # Hapus italic *text*
    (re.compile(r'#+\s*'), ''),                   # Hapus heading ###
    (re.compile(r'```[a-zA-Z]*'), ''),            # Hapus code block fences
    (re.compile(r'```'), ''),
    (re.compile(r'^\s*[-*•]\s*', re.MULTILINE), ''), # Hapus bullet points liar
]

_PASAL_TITLES = {
    "persoalan": "Persoalan.",
    "praanggapan": "Praanggapan.",
    "fakta": "Fakta/Data yang Memengaruhi.",
    "analisis": "Analisis.",
    "kesimpulan": "Kesimpulan.",
    "saran": "Saran."
}

def sanitize_text(text: str) -> str:
    """
    Membersihkan teks dari markdown formatting liar, bullet point acak, dan spasi berlebih.
    """
    if not text:
        return ""
    
    cleaned = text.strip()
    for pattern, repl in _MARKDOWN_CLEAN_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    
    # Hapus kutip ganda/tunggal di awal & akhir string
    cleaned = cleaned.strip('"`\'')
    
    # Rapikan spasi ganda dan multiple newline
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    return cleaned.strip()


def validate_and_sanitize_telaahan_staf(pasal_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Memvalidasi dan membersihkan ke-6 pasal Telaahan Staf sesuai standar KEP/868/IX/2022.
    Memastikan setiap pasal terisi, bebas markdown liar, dan diakhiri tanda titik.
    """
    sanitized = {}
    for key in ["persoalan", "praanggapan", "fakta", "analisis", "kesimpulan", "saran"]:
        raw_val = pasal_dict.get(key, "").strip()
        
        # Hapus jika LLM mengulang judul pasal di dalam isi (misal "Persoalan. Dalam rangka...")
        prefix_pattern = re.compile(
            rf'^(?:{key}|persoalan|praanggapan|fakta(?:\/data yang memengaruhi)?|analisis|kesimpulan|saran)\s*[:\.\-]\s*',
            re.IGNORECASE
        )
        cleaned = prefix_pattern.sub('', raw_val)
        cleaned = sanitize_text(cleaned)
        
        # Fallback jika kosong
        if not cleaned:
            if key == "persoalan":
                cleaned = "Peningkatan efektivitas dan kesiapan operasional satuan."
            elif key == "praanggapan":
                cleaned = "Dukungan sumber daya dan regulasi yang memadai akan mempercepat pencapaian sasaran tugas pokok."
            elif key == "fakta":
                cleaned = "Kondisi sarana prasarana dan tuntutan tugas saat ini memerlukan penyesuaian strategi yang terukur."
            elif key == "analisis":
                cleaned = "Penerapan langkah sistematis memberikan keunggulan efisiensi waktu dan optimalisasi kapabilitas personel."
            elif key == "kesimpulan":
                cleaned = "Langkah penguatan kapasitas dan modernisasi metode kerja merupakan pilihan bertindak terbaik."
            elif key == "saran":
                cleaned = "Disarankan kepada pimpinan untuk menyetujui rencana aksi dan penerbitan petunjuk pelaksanaan terkait."
        
        # Pastikan diakhiri titik
        if not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
            
        sanitized[key] = cleaned
        
    return sanitized
