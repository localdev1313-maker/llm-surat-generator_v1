import re
import html as _html
import logging
from typing import Dict, Any, List, Tuple

from .llm_health import record_llm_warning

logger = logging.getLogger(__name__)


# ── Kamus singkatan baku TNI ──
# LLM kerap MENGARANG ekspansi singkatan institusi (kasus nyata: KRI ->
# "Kapal Rudal Induk" / "Kapal Rendra Indonesia"). Ekspansi salah di output
# dikoreksi OTOMATIS ke ekspansi baku + dicatat sebagai warning degradasi.
# Format: SINGKATAN -> (ekspansi baku, {kata-kepala sah untuk pola "Ekspansi (SINGKATAN)"}).
SINGKATAN_BAKU: Dict[str, Tuple[str, set]] = {
    "KRI": ("Kapal Perang Republik Indonesia", {"Kapal"}),
    "TNI": ("Tentara Nasional Indonesia", {"Tentara"}),
    "TNIAL": ("Tentara Nasional Indonesia", {"Tentara"}),
    "AL": ("Angkatan Laut", {"Angkatan"}),
    "MABESAL": ("Markas Besar Angkatan Laut", {"Markas"}),
    "LANTAMAL": ("Pangkalan Utama Angkatan Laut", {"Pangkalan"}),
    "KOLATL": ("Komando Latihan Angkatan Laut", {"Komando"}),
    "SESKO": ("Sekolah Staf dan Komando", {"Sekolah"}),
    "SESKOAL": ("Sekolah Staf dan Komando", {"Sekolah"}),
    "AAL": ("Akademi Angkatan Laut", {"Akademi"}),
    "ARMATIM": ("Komando Armada Timur", {"Komando", "Armada"}),
    "ARMABAR": ("Komando Armada Barat", {"Komando", "Armada"}),
    "KORMAR": ("Korps Marinir", {"Korps"}),
    "PUSPEN": ("Pusat Personel", {"Pusat"}),
    "ASOPS": ("Asisten Operasi", {"Asisten"}),
}


def _norm_teks(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def perbaiki_ekspansi_singkatan(text: str) -> str:
    """
    Koreksi otomatis ekspansi singkatan institusi yang dikarang LLM.

    Pola A: "Kapal Rudal Induk (KRI)"  -> "Kapal Perang Republik Indonesia (KRI)"
            (hanya bila kata-kepala kandidat cocok — mencegah salah ganti
             frasa lain yang kebetulan mendahului kurung)
    Pola B: "KRI (Kapal Rudal Induk)"  -> "KRI (Kapal Perang Republik Indonesia)"
    Setiap koreksi dicatat ke saluran llm_warning agar klien tahu naskah
    telah disunting guardrail.
    """
    if not text:
        return text

    hasil = text
    for singkatan, (baku, head_kata) in SINGKATAN_BAKU.items():

        def _ganti_pola_a(m):
            kandidat = m.group(1).strip()
            kata = kandidat.split()
            # Cari run terpanjang yang DIMULAI kata-kepala (mis. "Kesiapan
            # Pangkalan Utama (LANTAMAL)" -> ekspansi = "Pangkalan Utama",
            # "Kesiapan" adalah kata pendahulu yang harus dipertahankan).
            awal = next((i for i, w in enumerate(kata) if w in head_kata), None)
            if awal is None:
                return m.group(0)
            ekspansi = " ".join(kata[awal:])
            if _norm_teks(ekspansi) == _norm_teks(baku) or len(kata) - awal > 6:
                return m.group(0)
            record_llm_warning(
                f"Halusinasi ekspansi singkatan dikoreksi: "
                f"'{ekspansi} ({singkatan})' -> '{baku} ({singkatan})'."
            )
            return " ".join(kata[:awal] + baku.split()) + f" ({singkatan})"

        hasil = re.sub(
            rf"\b([A-Z][A-Za-z]+(?:\s+[A-Z][a-z]+){{1,5}})\s*\(\b{singkatan}\b\)",
            _ganti_pola_a,
            hasil,
        )

        def _ganti_pola_b(m):
            kandidat = m.group(1).strip()
            if _norm_teks(kandidat) == _norm_teks(baku):
                return m.group(0)
            record_llm_warning(
                f"Halusinasi ekspansi singkatan dikoreksi: "
                f"'{singkatan} ({kandidat})' -> '{singkatan} ({baku})'."
            )
            return f"{singkatan} ({baku})"

        hasil = re.sub(
            rf"\b{singkatan}\s*\(([^)]{{3,90}})\)",
            _ganti_pola_b,
            hasil,
        )

    return hasil


def escape_custom_html(value):
    """
    Escape rekursif untuk semua nilai teks kustom yang dikirim klien untuk
    jalur *_custom (sections_custom / konten_custom / isi_custom_list) - jalur
    ini melewati LLM dan seluruh sanitizer guardrail lain, lalu dirender
    langsung oleh Jinja2 Template(autoescape=False) ke HTML yang dicetak
    wkhtmltopdf dengan enable-local-file-access aktif. Tanpa escape ini,
    markup seperti <iframe src="file://..."> tercetak apa adanya ke PDF resmi
    (local file inclusion / SSRF). \n tetap utuh sehingga replace('\\n','<br>')
    yang dijalankan sesudahnya masih berfungsi.
    """
    if isinstance(value, str):
        return _html.escape(value)
    if isinstance(value, list):
        return [escape_custom_html(v) for v in value]
    if isinstance(value, dict):
        return {k: escape_custom_html(v) for k, v in value.items()}
    return value


def clean_military_text(text: str) -> str:
    """
    Membersihkan teks dari markdown liar, bullet points, prefix judul ganda,
    dan spasi berlebih untuk dokumen militer formal.
    Sekalian mengoreksi ekspansi singkatan yang dikarang LLM (lihat
    perbaiki_ekspansi_singkatan) — satu titik pemeriksaan untuk seluruh
    validator kajian.
    """
    if not text:
        return ""

    # Hapus heading markdown (#, ##, ###)
    cleaned = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Hapus bold/italic markdown (**text**, *text*, __text__, _text_)
    cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)
    cleaned = re.sub(r'__([^_]+)__', r'\1', cleaned)

    # Hapus bullet points liar (- , * , + ) di awal baris
    cleaned = re.sub(r'^\s*[-*+]\s+', '', cleaned, flags=re.MULTILINE)

    # Rapikan spasi ganda dan baris kosong berlebihan
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    # Koreksi halusinasi ekspansi singkatan institusi
    cleaned = perbaiki_ekspansi_singkatan(cleaned)

    return cleaned.strip()


def validate_telaahan_staf(sections: Dict[str, Any]) -> Dict[str, str]:
    """Validasi dan sanitasi 6 pasal Telaahan Staf KEP/868 Contoh 26."""
    keys = ["persoalan", "praanggapan", "fakta", "analisis", "kesimpulan", "saran"]
    validated = {}
    
    for k in keys:
        raw_val = sections.get(k, "")
        if isinstance(raw_val, list):
            raw_val = " ".join([str(x) for x in raw_val])
        cleaned = clean_military_text(str(raw_val))

        # 1) Lepas label meta ala LLM di awal: "Pasal 1", "Pasal 2 (Praanggapan):"
        cleaned = re.sub(
            r'^Pasal\s+\d+\s*(?:\([^)]*\))?\s*[:\-]?\s*', '', cleaned, flags=re.IGNORECASE
        ).strip()

        # 2) Lepas BARIS label pasal utuh ("3. Fakta/Data yang Memengaruhi.")
        #    hanya bila diikuti isi — mencegah sisa "/Data yang ..." seperti
        #    pada pembersih prefix inline lama.
        nl = cleaned.find('\n')
        if nl > 0:
            first_line, rest = cleaned[:nl].strip(), cleaned[nl + 1:].strip()
            if rest and len(first_line) < 90 and re.match(rf'^(?:\d+\.\s*)?{k}\b', first_line, re.IGNORECASE):
                cleaned = rest

        # 3) Lepas prefix nama pasal tersisa di awal teks
        cleaned = re.sub(rf'^(?:\d+\.\s*)?{k}\.?\s*[:\-\.]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
        
        if not cleaned:
            cleaned = f"Perumusan materi {k} yang telah disesuaikan dengan ketentuan kedinasan."
            
        validated[k] = cleaned
        
    return validated


def validate_kka_studi_kasus(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Validasi dan sanitasi KKA Model Studi Kasus (OMSP)."""
    text_fields = [
        "topik", "latar_belakang_umum", "kronologis_pra", "kronologis_kejadian",
        "kronologis_pasca", "analisis_kejadian", "hal_positif", "hal_negatif",
        "manfaat_edukatif", "manfaat_inspiratif", "manfaat_instruktif",
        "kesimpulan", "saran"
    ]
    validated = {}
    for f in text_fields:
        val = str(sections.get(f, ""))
        cleaned = clean_military_text(val)
        if not cleaned:
            cleaned = f"Uraian {f.replace('_', ' ')} sesuai dengan data penugasan lembar merah."
        validated[f] = cleaned
        
    # Daftar pustaka
    dp = sections.get("daftar_pustaka", [])
    if isinstance(dp, str):
        dp = [p.strip() for p in dp.split("\n") if p.strip()]
    if not dp:
        dp = [
            "Mabes TNI. 2022. Petunjuk Referensi Tata Tulis Militer di Lingkungan TNI (KEP/868/IX/2022). Jakarta: Mabes TNI.",
            "Sesko. 2020. Petunjuk Teknis Penulisan Kertas Karya Acuan Pendidikan Reguler Sesko. Jakarta: Sesko.",
            "Undang-Undang RI Nomor 34 Tahun 2004 tentang Tentara Nasional Indonesia. Jakarta."
        ]
    validated["daftar_pustaka"] = [clean_military_text(p) for p in dp]
    return validated


def validate_kka_analisis_moe(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Validasi dan sanitasi KKA Model Analisis & Pengambilan Keputusan (MoE)."""
    text_fields = [
        "topik", "latar_belakang", "analisis_umum", "pembahasan_moe",
        "perhitungan_moe", "pengambilan_keputusan", "kesimpulan", "saran"
    ]
    validated = {}
    for f in text_fields:
        val = str(sections.get(f, ""))
        cleaned = clean_military_text(val)
        if not cleaned:
            cleaned = f"Uraian materi {f.replace('_', ' ')} berdasarkan analisis komparatif sistematis."
        validated[f] = cleaned
        
    # opsi_1/opsi_2: label alternatif riil dari input pengguna (dipakai header
    # tabel di template) — bukan konstanta KPC/MPA baku.
    opsi_1 = str(sections.get("opsi_1") or "Opsi 1")
    opsi_2 = str(sections.get("opsi_2") or "Opsi 2")
    validated["opsi_1"] = opsi_1
    validated["opsi_2"] = opsi_2

    # Tabel parameter: TIDAK BOLEH default ke spesifikasi teknis KPC/MPA yang
    # spesifik (24 Nm, 46 Juta US$, dst.) — angka itu nyata untuk KPC/MPA tapi
    # jadi fabrikasi/halusinasi bila dicetak seolah-olah spesifikasi opsi lain
    # yang dimasukkan pengguna. Placeholder netral dipakai kecuali kajian_engine
    # sudah mengisi tabel_parameter sungguhan (mis. via sections_custom / opsi
    # default KPC-MPA persis).
    validated["tabel_parameter"] = sections.get("tabel_parameter", [
        {"parameter": p, "opsi1": "Data belum diinput", "opsi2": "Data belum diinput", "ket": "Perlu verifikasi data riil"}
        for p in (
            "Kemampuan Pendeteksian", "Kemampuan Pengidentifikasian", "Kemampuan Penindakan",
            "Kecepatan Maksimal", "Endurance", "Estimasi Harga per Unit",
        )
    ])

    validated["tabel_bobot_level1"] = sections.get("tabel_bobot_level1", [
        {"kriteria": "Kemampuan", "bobot": 0.4},
        {"kriteria": "Kehandalan", "bobot": 0.4},
        {"kriteria": "Harga", "bobot": 0.2}
    ])
    
    validated["tabel_bobot_level2"] = sections.get("tabel_bobot_level2", [
        {"sub_kriteria": "Pendeteksian", "bobot": 0.4},
        {"sub_kriteria": "Pengidentifikasian", "bobot": 0.3},
        {"sub_kriteria": "Penindakan", "bobot": 0.3},
        {"sub_kriteria": "Kecepatan Maksimal", "bobot": 0.4},
        {"sub_kriteria": "Manuvra (Sea State)", "bobot": 0.3},
        {"sub_kriteria": "Endurance", "bobot": 0.3}
    ])
    
    dp = sections.get("daftar_pustaka", [])
    if isinstance(dp, str):
        dp = [p.strip() for p in dp.split("\n") if p.strip()]
    if not dp:
        dp = [
            "Sesko. 2020. Petunjuk Teknis Penulisan Kertas Karya Acuan Pendidikan Reguler Sesko. Jakarta: Dep Iptek Sesko.",
            "Mabes TNI. 2020. Doktrin TNI Tri Dharma Eka Karma. Jakarta: Mabes TNI.",
            "Department of Defense. 2016. Measurement of Effectiveness (MoE) in Defense Acquisition. Washington D.C."
        ]
    validated["daftar_pustaka"] = [clean_military_text(p) for p in dp]
    return validated


def validate_kka_pemecahan_masalah(sections: Dict[str, Any]) -> Dict[str, Any]:
    """Validasi dan sanitasi KKA Model Pemecahan Masalah (SOM)."""
    validated = {
        "judul": clean_military_text(str(sections.get("judul", "OPTIMALISASI KESIAPAN OPERASIONAL SATUAN"))),
        "pokok_masalah": clean_military_text(str(sections.get("pokok_masalah", "Kesenjangan antara kesiapan alutsista dengan tuntutan penugasan operasional."))),
        "pemecahan_umum": clean_military_text(str(sections.get("pemecahan_umum", "Pemberdayaan potensi internal dan koordinasi lintas sektoral."))),
        "kesimpulan": clean_military_text(str(sections.get("kesimpulan", "Langkah strategis terpadu menjadi solusi paling feasible."))),
        "saran": clean_military_text(str(sections.get("saran", "Disarankan peningkatan alokasi pemeliharaan dan pelatihan intensif.")))
    }
    
    # Permasalahan list (minimal 3)
    p_list = sections.get("permasalahan_list", [])
    if isinstance(p_list, str):
        p_list = [x.strip() for x in p_list.split("\n") if x.strip()]
    if not p_list or len(p_list) < 3:
        p_list = [
            "Kemampuan bidang teknologi pengawak masih perlu ditingkatkan.",
            "Dukungan anggaran pemeliharaan dan logistik masih terbatas.",
            "Pemanfaatan produk industri strategis nasional belum optimal."
        ]
    validated["permasalahan_list"] = [clean_military_text(p) for p in p_list]
    
    # Pemecahan per persoalan (SOM)
    sol_list = sections.get("pemecahan_persoalan_list", [])
    if not sol_list or not isinstance(sol_list, list):
        sol_list = [
            {
                "persoalan": validated["permasalahan_list"][0],
                "pembahasan": "Meningkatkan kemampuan SDM melalui program pendidikan spesialisasi dan sertifikasi kompetensi berstandar militer.",
                "subyek": "Mabes TNI dan Komando Pembinaan Doktrin",
                "obyek": "Personel Teknisi dan Pengawak Alutsista",
                "metoda": "Edukasi, Latihan Terpadu, dan Kerjasama Industri"
            },
            {
                "persoalan": validated["permasalahan_list"][1],
                "pembahasan": "Melakukan penyesuaian skala prioritas anggaran pemeliharaan preventif dan optimalisasi skema pembiayaan bertahap.",
                "subyek": "Pemerintah dan Mabes TNI",
                "obyek": "Anggaran Pemeliharaan Alutsista",
                "metoda": "Regulasi, Efisiensi Anggaran, dan Koordinasi"
            },
            {
                "persoalan": validated["permasalahan_list"][2],
                "pembahasan": "Mendorong sinergi dan kontrak jangka panjang dengan industri pertahanan dalam negeri guna menjamin ketersediaan suku cadang.",
                "subyek": "Kementerian Pertahanan, Mabes TNI, dan BUMN Industri Pertahanan",
                "obyek": "Industri Strategis Nasional (Instranas)",
                "metoda": "Regulasi, Kerjasama Litbang, dan Sosialisasi"
            }
        ]
    validated["pemecahan_persoalan_list"] = sol_list
    
    dp = sections.get("daftar_pustaka", [])
    if isinstance(dp, str):
        dp = [p.strip() for p in dp.split("\n") if p.strip()]
    if not dp:
        dp = [
            "Sesko. 2020. Petunjuk Teknis Penulisan Kertas Karya Acuan Pendidikan Reguler Sesko. Jakarta: Sesko.",
            "Mabes TNI. 2020. Doktrin TNI Tri Dharma Eka Karma. Jakarta: Mabes TNI.",
            "Kementerian Pertahanan RI. 2015. Buku Putih Pertahanan Indonesia. Jakarta: Kemhan RI."
        ]
    validated["daftar_pustaka"] = [clean_military_text(p) for p in dp]
    
    return validated
