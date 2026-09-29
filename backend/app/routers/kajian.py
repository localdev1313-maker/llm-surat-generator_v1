import asyncio
import re
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..schemas.kajian import (
    KajianCategory,
    KKAModelType,
    KajianGenerateRequest,
    KajianDraftResponse,
    KajianRenderPDFRequest,
    KajianGenerateResponse
)
from ..services.kajian_engine import process_kajian_generation
from ..services.llm_health import start_llm_request_scope, collect_llm_warnings
from ..services.pdf_service import create_pdf_kajian
from ..services.guardrail_kajian import clean_military_text
from ..utils import format_tanggal_indonesia

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/kajian",
    tags=["Kajian Dual-Mode"]
)

# Helper konversi bulan ke romawi
BULAN_ROMAWI = {
    1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI",
    7: "VII", 8: "VIII", 9: "IX", 10: "X", 11: "XI", 12: "XII"
}


def _get_auto_nomor_ts(satker: str = "PUSSIBER") -> str:
    now = datetime.now()
    bulan_rom = BULAN_ROMAWI.get(now.month, "VIII")
    satker_code = "".join([w[0] for w in satker.split() if w]).upper() or "SAT"
    return f"Nomor TS/01/{bulan_rom}/{now.year}/{satker_code}"


def _format_combined_text(kategori: KajianCategory, kka_model: Optional[KKAModelType], judul: str, sections: dict) -> str:
    """Format sections into combined text string for editor/preview."""
    if kategori == KajianCategory.TELAAHAN_STAF:
        lines = [
            f"TELAAHAN STAF TENTANG {judul.upper()}\n",
            f"1. Persoalan.\n{sections.get('persoalan', '')}\n",
            f"2. Praanggapan.\n{sections.get('praanggapan', '')}\n",
            f"3. Fakta/Data yang Memengaruhi.\n{sections.get('fakta', '')}\n",
            f"4. Analisis.\n{sections.get('analisis', '')}\n",
            f"5. Kesimpulan.\n{sections.get('kesimpulan', '')}\n",
            f"6. Saran.\n{sections.get('saran', '')}"
        ]
        return "\n".join(lines)
    
    # KKA Seskoal
    if kka_model == KKAModelType.STUDI_KASUS:
        lines = [
            f"KERTAS KARYA ACUAN - STUDI KASUS: {judul.upper()}\n",
            f"1. Topik: {sections.get('topik', judul)}\n",
            f"2. Latar Belakang:\n   a. Umum: {sections.get('latar_belakang_umum', '')}\n   b. Kronologis:",
            f"      1) Pra Kejadian: {sections.get('kronologis_pra', '')}",
            f"      2) Saat Kejadian: {sections.get('kronologis_kejadian', '')}",
            f"      3) Pasca Kejadian: {sections.get('kronologis_pasca', '')}\n",
            f"3. Analisis Kejadian:\n{sections.get('analisis_kejadian', '')}\n",
            f"4. Hal Positif dan Negatif:\n   a. Positif: {sections.get('hal_positif', '')}\n   b. Negatif: {sections.get('hal_negatif', '')}\n",
            f"5. Manfaat bagi TNI/TNI AL:\n   a. Edukatif: {sections.get('manfaat_edukatif', '')}\n   b. Inspiratif: {sections.get('manfaat_inspiratif', '')}\n   c. Instruktif: {sections.get('manfaat_instruktif', '')}\n",
            f"6. Penutup:\n   a. Kesimpulan: {sections.get('kesimpulan', '')}\n   b. Saran: {sections.get('saran', '')}"
        ]
        return "\n".join(lines)
    elif kka_model == KKAModelType.ANALISIS_MOE:
        lines = [
            f"KERTAS KARYA ACUAN - ANALISIS MoE: {judul.upper()}\n",
            f"1. Topik: {sections.get('topik', judul)}\n",
            f"2. Latar Belakang:\n{sections.get('latar_belakang', '')}\n",
            f"3. Analisis MoE:\n   a. Umum: {sections.get('analisis_umum', '')}\n   b. Pembahasan: {sections.get('pembahasan_moe', '')}\n   c. Perhitungan Skor:\n{sections.get('perhitungan_moe', '')}\n",
            f"4. Pengambilan Keputusan:\n{sections.get('pengambilan_keputusan', '')}\n",
            f"5. Penutup:\n   a. Kesimpulan: {sections.get('kesimpulan', '')}\n   b. Saran: {sections.get('saran', '')}"
        ]
        return "\n".join(lines)
    else:  # PEMECAHAN_MASALAH
        lines = [
            f"KERTAS KARYA ACUAN - PEMECAHAN MASALAH: {judul.upper()}\n",
            f"1. Judul: {sections.get('judul', judul)}\n",
            f"2. Pokok Masalah:\n{sections.get('pokok_masalah', '')}\n",
            f"3. Permasalahan:",
        ]
        for idx, p in enumerate(sections.get("permasalahan_list", []), 1):
            lines.append(f"   {chr(96+idx)}. {p}")
        lines.append(f"\n4. Pemecahan Permasalahan (SOM):\n   a. Umum: {sections.get('pemecahan_umum', '')}")
        for idx, item in enumerate(sections.get("pemecahan_persoalan_list", []), 1):
            lines.append(f"   {chr(97+idx)}. {item.get('persoalan', '')}: {item.get('pembahasan', '')} (S: {item.get('subyek','')}, O: {item.get('obyek','')}, M: {item.get('metoda','')})")
        lines.append(f"\n5. Penutup:\n   a. Kesimpulan: {sections.get('kesimpulan', '')}\n   b. Saran: {sections.get('saran', '')}")
        return "\n".join(lines)


@router.post("/draft", response_model=KajianDraftResponse)
async def draft_kajian(req: KajianGenerateRequest):
    """Generate draf kajian AI tanpa render PDF."""
    try:
        warnings = []
        if not req.sections_custom:
            # Generasi multi-bagian memanggil Ollama berkali-kali (blocking) — worker thread.
            start_llm_request_scope()
            sections = await asyncio.to_thread(process_kajian_generation, req)
            warnings = collect_llm_warnings()
        else:
            # sections_custom dipakai klien untuk PRATINJAU TEKS (bukan render
            # PDF) — simpan teks mentah; escaping terjadi otomatis di renderer
            # Jinja2 autoescape saat dokumen dicetak. Escape di sini membuat
            # entity &lt; &#x27; dst. tampil apa adanya di editor klien.
            sections = req.sections_custom
        nomor = req.nomor_naskah or (_get_auto_nomor_ts(req.kop_utama) if req.kategori == KajianCategory.TELAAHAN_STAF else None)
        combined = _format_combined_text(req.kategori, req.kka_model, req.judul_atau_topik, sections)

        return KajianDraftResponse(
            kategori=req.kategori,
            kka_model=req.kka_model,
            judul_atau_topik=req.judul_atau_topik,
            nomor_naskah=nomor,
            sections=sections,
            konten_gabungan=combined,
            konten_kajian=combined,
            lampiran_list=req.lampiran_list or [],
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        logger.error(f"Gagal menyusun draf kajian: {e}", exc_info=True)
        logger.error("Gagal menyusun draf kajian: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menyusun draf kajian. Periksa log server untuk detail.")


@router.post("/generate", response_model=KajianGenerateResponse)
async def generate_kajian(req: KajianGenerateRequest):
    """Generate draf kajian AI sekaligus merender dokumen PDF."""
    try:
        kajian_id = str(uuid.uuid4())
        warnings = []
        if not req.sections_custom:
            start_llm_request_scope()
            sections = await asyncio.to_thread(process_kajian_generation, req)
            warnings = collect_llm_warnings()
        else:
            # sections_custom masuk template render — Jinja2 autoescape menangani
            # escaping saat cetak; escape manual di sini hanya menghasilkan
            # entity ganda (&amp;lt;) tercetak di PDF.
            sections = req.sections_custom
        nomor = req.nomor_naskah or (_get_auto_nomor_ts(req.kop_utama) if req.kategori == KajianCategory.TELAAHAN_STAF else None)

        # Template context
        template_data = {
            "kop_utama": req.kop_utama,
            "kop_satuan_bawah": req.kop_satuan_bawah,
            "judul_atau_topik": req.judul_atau_topik.upper(),
            "nomor_naskah": nomor,
            "tempat": req.tempat,
            "tanggal": req.tanggal or format_tanggal_indonesia(),
            "nama_pejabat_atau_pasis": req.nama_pejabat_atau_pasis,
            "pangkat_korps_nrp": req.pangkat_korps_nrp or "",
            "jabatan": req.jabatan,
            "nomor_pasis": req.nomor_pasis,
            "kelompok_pasis": req.kelompok_pasis,
            "jenis_dan_tahun_pendidikan": req.jenis_dan_tahun_pendidikan,
            "sections": sections,
            "lampiran_list": req.lampiran_list or []
        }
        
        # Nama file
        prefix = "telaahan_staf" if req.kategori == KajianCategory.TELAAHAN_STAF else f"kka_{str(req.kka_model or 'studi_kasus').lower()}"
        filename = f"{prefix}_{kajian_id}.pdf"
        output_path = settings.OUTPUT_DIR / filename
        
        # Render PDF (blocking wkhtmltopdf) — worker thread.
        await asyncio.to_thread(
            create_pdf_kajian,
            kategori=req.kategori.value,
            kka_model=req.kka_model.value if req.kka_model else "STUDI_KASUS",
            template_data=template_data,
            output_path=output_path
        )

        combined = _format_combined_text(req.kategori, req.kka_model, req.judul_atau_topik, sections)

        return KajianGenerateResponse(
            status="success",
            message="Kajian berhasil dibuat",
            id=kajian_id,
            surat_id=kajian_id,
            kategori=req.kategori,
            kka_model=req.kka_model,
            judul_atau_topik=req.judul_atau_topik,
            konten_kajian=combined,
            file_path=output_path.name,
            download_url=f"/download/{kajian_id}",
            preview_pdf_url=f"/preview-pdf/{kajian_id}",
            sections=sections,
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        logger.error(f"Gagal generate kajian PDF: {e}", exc_info=True)
        logger.error("Gagal generate kajian PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal generate kajian PDF. Periksa log server untuk detail.")


def _strip_header_teks_gabungan(text: str, kategori: KajianCategory) -> str:
    """
    Hapus baris judul gabungan dari teks editor pratinjau. Template SUDAH
    mencetak kop + 'TELAAHAN STAF TENTANG' + nomor + judul; baris pertama teks
    gabungan ('TELAAHAN STAF TENTANG ...' / 'KERTAS KARYA ACUAN - ...') yang ikut
    tercetak membuat judul DOBEL di dokumen resmi (tertangkap trial di emulator).
    """
    if not text:
        return ""
    cleaned = text.strip()
    if kategori == KajianCategory.TELAAHAN_STAF:
        cleaned = re.sub(r"^TELAAHAN\s+STAF\s+TENTANG[^\n]*\n?", "", cleaned, count=1, flags=re.IGNORECASE)
    else:
        cleaned = re.sub(r"^KERTAS\s+KARYA\s+ACUAN[^\n]*\n?", "", cleaned, count=1, flags=re.IGNORECASE)
    # Tab pada teks editor (indentasi pasal) memicu overflow-clip wkhtmltopdf
    # pada mode pre-wrap — ganti dengan spasi.
    return cleaned.replace("\t", "    ").strip()


@router.post("/render-pdf", response_model=KajianGenerateResponse)
async def render_kajian_pdf(req: KajianRenderPDFRequest):
    """Render ulang PDF dari draf hasil editan teks manual."""
    try:
        kajian_id = str(uuid.uuid4())
        nomor = req.nomor_naskah or (_get_auto_nomor_ts(req.kop_utama) if req.kategori == KajianCategory.TELAAHAN_STAF else None)

        # Redaksi hasil editan pengguna menang atas sections baku; jika keduanya
        # kosong, tolak dengan 400 alih-alih merender dokumen resmi tanpa isi.
        # Teks mentah diteruskan apa adanya — Jinja2 autoescape menangani escaping
        # saat cetak (escape manual = entity ganda tercetak di PDF).
        konten_custom_clean = _strip_header_teks_gabungan(req.konten_custom or "", req.kategori)
        if not req.sections and not konten_custom_clean:
            raise HTTPException(
                status_code=400,
                detail="Sections kosong — susun draf kajian terlebih dahulu sebelum mencetak PDF."
            )

        template_data = {
            "kop_utama": req.kop_utama,
            "kop_satuan_bawah": req.kop_satuan_bawah,
            "judul_atau_topik": req.judul_atau_topik.upper(),
            "nomor_naskah": nomor,
            "tempat": req.tempat,
            "tanggal": req.tanggal or format_tanggal_indonesia(),
            "nama_pejabat_atau_pasis": req.nama_pejabat_atau_pasis,
            "pangkat_korps_nrp": req.pangkat_korps_nrp or "",
            "jabatan": req.jabatan,
            "nomor_pasis": req.nomor_pasis,
            "kelompok_pasis": req.kelompok_pasis,
            "jenis_dan_tahun_pendidikan": req.jenis_dan_tahun_pendidikan,
            "sections": req.sections,
            # Editan redaksi pengguna (editor pratinjau) — template merender ini
            # bila terisi; tanpa key ini editan diam-diam dibuang.
            "konten_custom": konten_custom_clean,
            "lampiran_list": req.lampiran_list or []
        }

        prefix = "telaahan_staf" if req.kategori == KajianCategory.TELAAHAN_STAF else f"kka_{str(req.kka_model or 'studi_kasus').lower()}"
        filename = f"{prefix}_{kajian_id}.pdf"
        output_path = settings.OUTPUT_DIR / filename

        await asyncio.to_thread(
            create_pdf_kajian,
            kategori=req.kategori.value,
            kka_model=req.kka_model.value if req.kka_model else "STUDI_KASUS",
            template_data=template_data,
            output_path=output_path
        )

        combined = _format_combined_text(req.kategori, req.kka_model, req.judul_atau_topik, req.sections)
        
        return KajianGenerateResponse(
            status="success",
            message="PDF Kajian berhasil dirender ulang dari editan",
            id=kajian_id,
            surat_id=kajian_id,
            kategori=req.kategori,
            kka_model=req.kka_model,
            judul_atau_topik=req.judul_atau_topik,
            konten_kajian=combined,
            file_path=output_path.name,
            download_url=f"/download/{kajian_id}",
            preview_pdf_url=f"/preview-pdf/{kajian_id}",
            sections=req.sections
        )
    except HTTPException:
        # Validasi input (mis. sections kosong) — teruskan apa adanya, jangan
        # diubah menjadi 500 oleh handler generik di bawah.
        raise
    except Exception as e:
        logger.error(f"Gagal render ulang kajian PDF: {e}", exc_info=True)
        logger.error("Gagal render ulang kajian PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal render ulang kajian PDF. Periksa log server untuk detail.")
