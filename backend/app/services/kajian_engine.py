import logging
from typing import Dict, Any, List, Optional

from ..config import settings
from .ollama_client import chat as ollama_chat
from .rag_service import rag_engine
from .guardrail_kajian import (
    validate_telaahan_staf,
    validate_kka_studi_kasus,
    validate_kka_analisis_moe,
    validate_kka_pemecahan_masalah
)
from ..schemas.kajian import (
    KajianCategory,
    KKAModelType,
    KajianGenerateRequest
)

logger = logging.getLogger(__name__)


def _call_ollama(system_prompt: str, user_prompt: str) -> str:
    """
    Helper pemanggil Ollama lokal secara deterministik.

    Memakai klien bersama (ollama_client) sehingga host/timeout mengikuti env
    OLLAMA_HOST/OLLAMA_TIMEOUT — sebelumnya fungsi ini hardcode localhost + 10s
    yang membuat bagian kajian hampir selalu timeout dan diam-diam fallback.
    """
    return ollama_chat(system_prompt, user_prompt)


# ── 1. TELAAHAN STAF GENERATOR ──

def generate_telaahan_staf(req: KajianGenerateRequest) -> Dict[str, Any]:
    """Menyusun 6 pasal baku Telaahan Staf KEP/868/2022 Contoh 26."""
    judul = req.judul_atau_topik
    p_in = req.input_persoalan or judul
    pr_in = req.input_praanggapan or "Terdapat potensi risiko operasional jika persoalan tidak diselesaikan."
    f_in = req.input_fakta or "Data lapangan menunjukkan kebutuhan mendesak tindakan taktis."
    a_in = req.input_analisis or "Analisis mempertimbangkan efektivitas, efisiensi, dan kendala logistik."
    k_in = req.input_kesimpulan or "Diperlukan langkah terpadu sebagai opsi cara bertindak terbaik."
    s_in = req.input_saran or "Disarankan pimpinan menyetujui pelaksanaan rencana tindak lanjut."

    # Grounding RAG
    rag_ctx = ""
    if settings.RAG_ENABLED:
        matches = rag_engine.search(f"telaahan staf {judul} {p_in}", top_k=2)
        if matches:
            rag_ctx = "REFERENSI:\n" + "\n".join([f"- {m['title']}: {m['content_snippet'][:200]}" for m in matches])

    sys_p = (
        "Anda adalah Perwira Staf Ahli Tata Naskah Dinas TNI yang bertugas menyusun naskah TELAAHAN STAF "
        "berdasarkan KEP/868/IX/2022 Contoh 26. Tuliskan teks dalam 1 paragraf formal militer (2-4 kalimat) "
        "yang padat, lugas, dan bebas halusinasi tanpa markdown atau tanda bintang.\n"
        "ATURAN SINGKATAN (MUTLAK): Pertahankan singkatan PERSIS seperti pada input — "
        "DILARANG menguraikan, menerjemahkan, atau menafsirkan singkatan "
        "(contoh: KRI tetap ditulis 'KRI', bukan dijabarkan).\n"
        "ATURAN KONSISTENSI (MUTLAK): Seluruh pasal WAJIB konsisten dengan JUDUL, PERSOALAN, "
        "dan FAKTA yang diberikan; DILARANG memasukkan sistem/teknologi/program yang tidak "
        "disebut dalam input.\n"
        "ATURAN REFERENSI (MUTLAK): JANGAN menyebut nama/judul dokumen referensi, daftar "
        "dokumen, atau kata 'dummy' di dalam naskah — referensi hanya untuk grounding isi."
    )

    # Pasal 1: Persoalan
    p_out = _call_ollama(
        sys_p,
        f"{rag_ctx}\nSusun Pasal 1 (Persoalan) untuk Judul: {judul}. Inti persoalan: {p_in}."
    ) or f"Persoalan utama terkait {p_in} yang memerlukan petunjuk dan keputusan pimpinan guna kelancaran pelaksanaan tugas."

    # Pasal 2: Praanggapan
    pr_out = _call_ollama(
        sys_p,
        f"Susun Pasal 2 (Praanggapan). Asumsi dasar: {pr_in}. Konteks: {p_out}"
    ) or f"Praanggapan bahwa apabila persoalan {p_in} tidak segera ditangani secara terstruktur, maka dapat memengaruhi kesiapsiagaan operasional."

    # Pasal 3: Fakta
    f_out = _call_ollama(
        sys_p,
        f"Susun Pasal 3 (Fakta/Data yang Memengaruhi). Fakta: {f_in}. Konteks persoalan: {p_out}"
    ) or f"Berdasarkan data dan fakta lapangan saat ini, {f_in}, sehingga menuntut percepatan koordinasi lintas fungsi."

    # Pasal 4: Analisis — judul ditanam agar analisis tidak menyimpang ke topik lain
    a_out = _call_ollama(
        sys_p,
        f"Susun Pasal 4 (Analisis) untuk JUDUL: {judul}. Analisis pengaruh fakta ({f_out}) dan praanggapan ({pr_out}). Fokus analisis: {a_in}."
    ) or f"Melalui analisis komprehensif, pengaruh fakta dan praanggapan menunjukkan bahwa opsi tindakan yang diusulkan memiliki keunggulan efektivitas tinggi serta meminimalkan risiko hambatan teknis."

    # Pasal 5: Kesimpulan
    k_out = _call_ollama(
        sys_p,
        f"Susun Pasal 5 (Kesimpulan) untuk JUDUL: {judul}. Tetapkan 1 cara bertindak terbaik berdasarkan analisis: {a_out}."
    ) or f"Berdasarkan hasil kupasan analisis, disimpulkan bahwa penetapan cara bertindak terpadu merupakan pilihan terbaik yang paling feasible dan efektif."

    # Pasal 6: Saran
    s_out = _call_ollama(
        sys_p,
        f"Susun Pasal 6 (Saran) untuk JUDUL: {judul}. Rumuskan usulan tindakan konkret untuk pimpinan berdasarkan kesimpulan: {k_out}. Saran: {s_in}."
    ) or f"Disarankan kepada pimpinan kiranya berkenan menyetujui langkah-langkah implementasi strategis guna mengatasi persoalan secara menyeluruh."

    raw = {
        "persoalan": p_out,
        "praanggapan": pr_out,
        "fakta": f_out,
        "analisis": a_out,
        "kesimpulan": k_out,
        "saran": s_out
    }
    return validate_telaahan_staf(raw)


# ── 2. KKA MODEL STUDI KASUS (OMSP) ──

def generate_kka_studi_kasus(req: KajianGenerateRequest) -> Dict[str, Any]:
    """Menyusun KKA Model Studi Kasus berpedoman Perdan Seskoal 2020."""
    topik = req.judul_atau_topik
    pra_in = req.input_kronologis_pra or "Kondisi awal sebelum peristiwa terjadi menunjukkan dinamika situasi normal dan kesiapsiagaan awal satuan."
    kej_in = req.input_kronologis_kejadian or "Saat peristiwa terjadi, terjadi eskalasi cepat yang menuntut respon taktis dan pengerahan unsur segera."
    pasca_in = req.input_kronologis_pasca or "Pasca peristiwa, dilaksanakan tahapan konsolidasi, evaluasi dampak, dan penutupan operasi penanganan."
    
    rag_ctx = ""
    if settings.RAG_ENABLED:
        matches = rag_engine.search(f"kertas karya acuan studi kasus OMSP {topik}", top_k=2)
        if matches:
            rag_ctx = "REFERENSI KKA SESKOAL:\n" + "\n".join([f"- {m['title']}: {m['content_snippet'][:200]}" for m in matches])

    sys_p = (
        "Anda adalah Perwira Pembimbing Karya Tulis Seskoal yang menyusun Kertas Karya Acuan (KKA) "
        "Model Studi Kasus berlandaskan Perdan Seskoal 2020 dan Doktrin OMSP. Gunakan bahasa ilmiah militer formal."
    )

    # 1. Latar Belakang & Kronologis
    lb_prompt = f"{rag_ctx}\nSusun Latar Belakang Umum (1-2 paragraf) untuk Studi Kasus: {topik}."
    lb_umum = _call_ollama(sys_p, lb_prompt) or f"Kajian studi kasus mengenai {topik} merupakan telaah mendalam terhadap pembelajaran peristiwa guna meningkatkan pemahaman operasional dan kapabilitas personel TNI Angkatan Laut."

    k_pra = _call_ollama(sys_p, f"Susun Kronologis Pra-Kejadian untuk {topik}. Input: {pra_in}") or pra_in
    k_kej = _call_ollama(sys_p, f"Susun Kronologis Saat Kejadian untuk {topik}. Input: {kej_in}") or kej_in
    k_pasca = _call_ollama(sys_p, f"Susun Kronologis Pasca-Kejadian untuk {topik}. Input: {pasca_in}") or pasca_in

    # 2. Analisis Kejadian & Evaluasi Positif/Negatif
    analisis = _call_ollama(
        sys_p,
        f"Susun Analisis Kejadian penanganan {topik} menggunakan asas-asas OMSP (Proporsional, Objective, Kesatuan Komando, Keamanan, Legitimasi, Keterpaduan)."
    ) or f"Penanganan peristiwa {topik} ditinjau dari asas OMSP menunjukkan penerapan prinsip kesatuan komando dan keterpaduan antar instansi yang efektif dalam memitigasi dampak di lapangan."

    h_pos = _call_ollama(sys_p, f"Sebutkan 3 hal positif/keberhasilan penanganan {topik}.") or "Kecepatan mobilisasi unsur SAR, koordinasi lintas sektoral yang solid, dan kepemimpinan lapangan yang adaptif."
    h_neg = _call_ollama(sys_p, f"Sebutkan 3 hal negatif/kendala penanganan {topik}.") or "Keterbatasan peralatan deteksi dini, kendala jaring komunikasi pada fase awal, dan tantangan distribusi logistik medan berat."

    # 3. Manfaat 3 Aspek (Edukatif, Inspiratif, Instruktif) & Penutup
    m_edu = _call_ollama(sys_p, f"Uraikan Manfaat Aspek Edukatif bagi TNI AL dari studi kasus {topik}.") or "Memberikan pelajaran berharga bagi kurikulum pendidikan dan latihan kesiapsiagaan operasi kemanusiaan prajurit."
    m_insp = _call_ollama(sys_p, f"Uraikan Manfaat Aspek Inspiratif bagi TNI AL dari studi kasus {topik}.") or "Menginspirasi modernisasi teknologi surveillance maritim dan rancang bangun posko kendali darurat terpadu."
    m_inst = _call_ollama(sys_p, f"Uraikan Manfaat Aspek Instruktif bagi TNI AL dari studi kasus {topik}.") or "Menjadi landasan penerbitan petunjuk taktis dan prosedur standar operasi (SOP) pengerahan unsur dalam OMSP."

    kesimpulan = _call_ollama(sys_p, f"Susun Kesimpulan Studi Kasus {topik}.") or f"Studi kasus penanganan {topik} membuktikan bahwa kesiapan doktrin, interoperabilitas, dan soliditas prajurit merupakan kunci keberhasilan penugasan OMSP."
    saran = _call_ollama(sys_p, f"Susun Saran tindak lanjut bagi pimpinan terkait {topik}.") or "Disarankan peningkatan frekuensi latihan bersama OMSP antar satuan dan pemutakhiran peralatan komunikasi taktis maritim."

    raw = {
        "topik": topik,
        "latar_belakang_umum": lb_umum,
        "kronologis_pra": k_pra,
        "kronologis_kejadian": k_kej,
        "kronologis_pasca": k_pasca,
        "analisis_kejadian": analisis,
        "hal_positif": h_pos,
        "hal_negatif": h_neg,
        "manfaat_edukatif": m_edu,
        "manfaat_inspiratif": m_insp,
        "manfaat_instruktif": m_inst,
        "kesimpulan": kesimpulan,
        "saran": saran
    }
    return validate_kka_studi_kasus(raw)


# ── 3. KKA MODEL ANALISIS & PENGAMBILAN KEPUTUSAN (MoE) ──

def generate_kka_analisis_moe(req: KajianGenerateRequest) -> Dict[str, Any]:
    """Menyusun KKA Model Analisis Pemilihan Alternatif Terbaik (MoE)."""
    topik = req.judul_atau_topik
    DEFAULT_OPSI1 = "Kapal Patroli Cepat (KPC)"
    DEFAULT_OPSI2 = "Pesawat Patroli Maritim (MPA)"
    opsi1 = req.input_alutsista_opsi_1 or DEFAULT_OPSI1
    opsi2 = req.input_alutsista_opsi_2 or DEFAULT_OPSI2
    # Tabel spesifikasi teknis nyata (24 Nm, 46 Juta US$, dst.) HANYA valid
    # untuk pasangan contoh baku KPC vs MPA. Bila pengguna mengganti salah
    # satu/kedua opsi, tabel itu jadi fabrikasi (spesifikasi KPC/MPA dicetak
    # seolah milik alutsista lain) - guardrail_kajian akan mengisi placeholder
    # netral "Data belum diinput" untuk kasus itu.
    is_opsi_baku = (opsi1 == DEFAULT_OPSI1 and opsi2 == DEFAULT_OPSI2)

    sys_p = (
        "Anda adalah Dosen Iptek Seskoal yang menyusun KKA Model Analisis kuantitatif "
        "Metode Measurement of Effectiveness (MoE) berpedoman pada Perdan Seskoal 2020."
    )

    lb = _call_ollama(
        sys_p,
        f"Susun Latar Belakang KKA Analisis mengenai: {topik}. Mengapa perlu pemilihan alternatif antara {opsi1} dan {opsi2}."
    ) or f"Dinamika keamanan laut dan keterbatasan anggaran menuntut pemilihan alutsista yang paling optimal antara {opsi1} dan {opsi2} guna penegakan kedaulatan di perairan yurisdiksi nasional."

    an_umum = f"Dalam rangka menentukan alutsista terbaik untuk {topik}, dilakukan analisis komparasi multi-kriteria antara {opsi1} dan {opsi2} menggunakan metode Measurement of Effectiveness (MoE)."

    pembahasan = (
        f"Proses analisis menggunakan 3 kriteria utama Level 1: Kemampuan (bobot 0.4), Kehandalan (bobot 0.4), dan Harga (bobot 0.2). "
        f"Pada Level 2, kriteria dijabarkan ke sub-kriteria spesifik: Pendeteksian (0.4), Pengidentifikasian (0.3), Penindakan (0.3), "
        f"Kecepatan (0.4), Manuver (0.3), dan Endurance (0.3). Perhitungan skor dilakukan dengan mengalikan bobot hierarki terhadap nilai kinerja."
    )

    # Tidak ada input parameter kinerja/bobot numerik nyata dari pengguna untuk
    # opsi1/opsi2 (hanya label teks) — sistem TIDAK BOLEH mengarang skor
    # presisi (mis. "0.648"/"0.668") seolah-olah itu hasil kalkulasi MoE
    # sungguhan, karena akan selalu sama persis untuk pasangan opsi apa pun
    # yang dimasukkan pengguna. Uraian kualitatif digenerate via LLM per opsi
    # yang benar-benar diinput; fallback deterministik ditulis netral tanpa
    # angka spesifik yang tidak berdasar data.
    perhitungan = _call_ollama(
        sys_p,
        f"Susun uraian kualitatif Perhitungan/Pembandingan MoE antara {opsi1} dan {opsi2} untuk {topik} "
        f"berdasarkan kriteria Kemampuan, Kehandalan, dan Harga. JANGAN mengarang angka skor numerik presisi "
        f"karena data kinerja aktual tidak tersedia — uraikan secara kualitatif keunggulan/kelemahan relatif tiap opsi."
    ) or (
        f"Perbandingan kualitatif antara {opsi1} dan {opsi2} dilakukan pada kriteria Kemampuan, Kehandalan, "
        f"dan Harga sesuai kerangka MoE. Skor kuantitatif presisi memerlukan data kinerja dan bobot penilaian riil "
        f"yang belum diinput — pengambilan keputusan berikut bersifat kualitatif berbasis kriteria di atas."
    )

    keputusan = _call_ollama(
        sys_p,
        f"Susun Pengambilan Keputusan berdasarkan perbandingan kualitatif antara {opsi1} dan {opsi2} untuk {topik}, "
        f"tanpa mengarang skor numerik presisi."
    ) or (
        f"Berdasarkan perbandingan kualitatif kriteria Kemampuan, Kehandalan, dan Harga, pimpinan disarankan "
        f"menetapkan pilihan antara {opsi1} dan {opsi2} setelah verifikasi data kinerja dan anggaran riil kedua opsi."
    )

    kesimpulan = _call_ollama(
        sys_p,
        f"Susun Kesimpulan analisis pemilihan alternatif antara {opsi1} dan {opsi2} untuk {topik}."
    ) or f"Pemilihan antara {opsi1} dan {opsi2} untuk {topik} perlu didasarkan pada verifikasi data kinerja dan anggaran riil, mengacu kerangka kriteria MoE di atas."
    saran = _call_ollama(
        sys_p,
        f"Susun Saran tindak lanjut bagi pimpinan terkait pemilihan {opsi1} atau {opsi2}."
    ) or f"Disarankan kepada pimpinan untuk melengkapi data kinerja dan anggaran riil {opsi1} dan {opsi2} sebelum menetapkan keputusan pengadaan final."

    raw = {
        "topik": topik,
        "opsi_1": opsi1,
        "opsi_2": opsi2,
        "latar_belakang": lb,
        "analisis_umum": an_umum,
        "pembahasan_moe": pembahasan,
        "perhitungan_moe": perhitungan,
        "pengambilan_keputusan": keputusan,
        "kesimpulan": kesimpulan,
        "saran": saran
    }
    if is_opsi_baku:
        # Tabel contoh ilustratif KPC vs MPA - hanya valid untuk pasangan baku ini.
        raw["tabel_parameter"] = [
            {"parameter": "Kemampuan Pendeteksian", "opsi1": "24 Nm", "opsi2": "60 Nm", "ket": "Maks Radar"},
            {"parameter": "Kemampuan Pengidentifikasian", "opsi1": "10 Nm", "opsi2": "15 Nm", "ket": "Visual"},
            {"parameter": "Kemampuan Penindakan", "opsi1": "Meriam Kal 57 & 20", "opsi2": "Nihil", "ket": "Senjata Kapal"},
            {"parameter": "Kecepatan Maksimal", "opsi1": "20 Knots", "opsi2": "395 Km/jam", "ket": "Kehandalan"},
            {"parameter": "Endurance", "opsi1": "10 Hari", "opsi2": "11 Jam", "ket": "Operasional"},
            {"parameter": "Estimasi Harga per Unit", "opsi1": "46 Juta US$", "opsi2": "23 Juta US$", "ket": "Ekonomis"},
        ]
    return validate_kka_analisis_moe(raw)


# ── 4. KKA MODEL PEMECAHAN MASALAH (SOM) ──

def generate_kka_pemecahan_masalah(req: KajianGenerateRequest) -> Dict[str, Any]:
    """Menyusun KKA Model Pemecahan Masalah Strategis (Metode SOM)."""
    judul = req.judul_atau_topik
    pokok = req.input_pokok_masalah or f"Kesenjangan antara kondisi saat ini dengan kondisi yang diharapkan dalam {judul}."
    p_list = req.input_permasalahan_list or [
        "Kemampuan teknologi dan kapabilitas SDM pengawak masih terbatas.",
        "Dukungan alokasi anggaran pemeliharaan dan operasi belum mencukupi.",
        "Sinergi regulasi dan koordinasi lintas instansi belum terintegrasi secara optimal."
    ]

    sys_p = (
        "Anda adalah Perwira Staf Seskoal yang menyusun KKA Model Pemecahan Masalah "
        "berdasarkan Metode SOM (Subyek, Obyek, Metoda) Perdan Seskoal 2020."
    )

    p_umum = _call_ollama(
        sys_p,
        f"Susun Pemecahan Masalah Umum untuk Judul: {judul}. Pokok Masalah: {pokok}."
    ) or f"Upaya pemecahan masalah {judul} dilaksanakan melalui pendekatan kesisteman yang mengintegrasikan aspek regulasi, pembinaan SDM, dan tata kelola anggaran."

    sol_items = []
    for idx, p_item in enumerate(p_list, 1):
        p_item = (p_item or "").strip()
        if not p_item:
            continue
        kata_pertama = p_item.split()[0]
        sol_items.append({
            "persoalan": p_item,
            "pembahasan": f"Mengoptimalkan peran pemangku kepentingan melalui langkah terencana guna menuntaskan persoalan {p_item.lower()}",
            "subyek": "Mabes TNI AL dan Komando Utama Terkait",
            "obyek": f"Komponen {kata_pertama} dan Kesiapan Satuan",
            "metoda": "Regulasi, Edukasi, Kerjasama, dan Pengawasan Melekat"
        })

    kesimpulan = f"Pemecahan persoalan {judul} dapat tercapai melalui harmonisasi peran Subyek, ketepatan sasaran Obyek, dan penerapan Metoda SOM secara terukur."
    saran = "Disarankan penyusunan petunjuk kerja teknis bersama dan alokasi anggaran prioritas untuk mendukung percepatan program."

    raw = {
        "judul": judul,
        "pokok_masalah": pokok,
        "permasalahan_list": p_list,
        "pemecahan_umum": p_umum,
        "pemecahan_persoalan_list": sol_items,
        "kesimpulan": kesimpulan,
        "saran": saran
    }
    return validate_kka_pemecahan_masalah(raw)


# ── MAIN DISPATCHER ──

def process_kajian_generation(req: KajianGenerateRequest) -> Dict[str, Any]:
    """Orkestrator utama pembangkitan draf kajian berdasarkan kategori dan model."""
    if req.kategori == KajianCategory.TELAAHAN_STAF:
        return generate_telaahan_staf(req)
    
    # KKA SESKOAL
    kka_type = req.kka_model or KKAModelType.STUDI_KASUS
    if kka_type == KKAModelType.STUDI_KASUS:
        return generate_kka_studi_kasus(req)
    elif kka_type == KKAModelType.ANALISIS_MOE:
        return generate_kka_analisis_moe(req)
    elif kka_type == KKAModelType.PEMECAHAN_MASALAH:
        return generate_kka_pemecahan_masalah(req)
    else:
        return generate_kka_studi_kasus(req)
