import asyncio
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..schemas.telaahan_staf import (
    TelaahanStafInput,
    TelaahanStafOutput,
    DraftTelaahanStafResponse,
    TelaahanStafPasal,
    TelaahanStafRenderRequest
)
from ..services.rag_telaahan_staf import generate_telaahan_staf_sections
from ..services.llm_health import start_llm_request_scope, collect_llm_warnings
from ..services.pdf_service import create_pdf_telaahan_staf
from ..services.guardrail import validate_and_sanitize_telaahan_staf

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Telaahan Staf"])

def _format_telaahan_staf_gabungan(
    kop_utama: str,
    kop_sub: str,
    judul: str,
    nomor_naskah: str,
    pasal: Dict[str, str],
    tanggal_ttd: str,
    nama_pejabat: str,
    jabatan: str,
    pangkat: str,
    lampiran_list: list
) -> str:
    """Format teks lengkap telaahan staf untuk preview / editor."""
    lampiran_str = ""
    if lampiran_list:
        lampiran_str = "\n\nLampiran:\n" + "\n".join([f"{i+1}. {l}" for i, l in enumerate(lampiran_list)])

    nomor_str = f"\n{nomor_naskah}" if nomor_naskah else ""
    return (
        f"{kop_utama}\n{kop_sub}\n\n"
        f"TELAAHAN STAF TENTANG\n"
        f"{judul.upper()}{nomor_str}\n\n"
        f"Persoalan. {pasal.get('persoalan', '')}\n\n"
        f"Praanggapan. {pasal.get('praanggapan', '')}\n\n"
        f"Fakta/Data yang Memengaruhi. {pasal.get('fakta', '')}\n\n"
        f"Analisis. {pasal.get('analisis', '')}\n\n"
        f"Kesimpulan. {pasal.get('kesimpulan', '')}\n\n"
        f"Saran. {pasal.get('saran', '')}\n\n"
        f"{tanggal_ttd}\n"
        f"{jabatan},\n\n\n"
        f"{nama_pejabat}\n"
        f"{pangkat}"
        f"{lampiran_str}"
    )

@router.post("/draft-telaahan-staf", response_model=DraftTelaahanStafResponse)
async def draft_telaahan_staf(request: TelaahanStafInput):
    """
    Generate draf teks 6 pasal Telaahan Staf dengan AI tanpa membuat PDF (untuk live editor & pratinjau).
    """
    try:
        # Generasi 6 pasal memanggil Ollama berkali-kali (blocking) — worker thread.
        start_llm_request_scope()
        pasal_dict = await asyncio.to_thread(generate_telaahan_staf_sections, request)
        warnings = collect_llm_warnings()
        pasal_obj = TelaahanStafPasal(**pasal_dict)

        now = datetime.now()
        bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_ttd = f"{request.tempat or 'Jakarta'}, {now.day} {bulan_id[now.month - 1]} {now.year}"
        if request.tanggal:
            tanggal_ttd = f"{request.tempat or 'Jakarta'}, {request.tanggal}"

        lampiran_clean = [l.strip() for l in (request.lampiran_list or []) if l.strip()]

        konten_gabungan = _format_telaahan_staf_gabungan(
            kop_utama=request.kop_utama or "PUSAT SIBER PERTAHANAN",
            kop_sub=request.kop_satuan_bawah or "",
            judul=request.judul,
            nomor_naskah=request.nomor_naskah or "",
            pasal=pasal_dict,
            tanggal_ttd=tanggal_ttd,
            nama_pejabat=request.nama_pejabat,
            jabatan=request.jabatan,
            pangkat=request.pangkat_korps_nrp or "",
            lampiran_list=lampiran_clean
        )

        return DraftTelaahanStafResponse(
            judul=request.judul,
            nomor_naskah=request.nomor_naskah,
            pasal=pasal_obj,
            konten_gabungan=konten_gabungan,
            lampiran_list=lampiran_clean,
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        logger.error(f"Error in draft_telaahan_staf: {e}", exc_info=True)
        logger.error("Gagal menyusun draf telaahan staf: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menyusun draf telaahan staf. Periksa log server untuk detail.")


@router.post("/generate-telaahan-staf", response_model=TelaahanStafOutput)
async def generate_telaahan_staf(request: TelaahanStafInput):
    """
    Generate Telaahan Staf lengkap (AI Generation + Render PDF Baku KEP/868 Contoh 26).
    """
    try:
        surat_id = str(uuid.uuid4())
        start_llm_request_scope()
        pasal_dict = await asyncio.to_thread(generate_telaahan_staf_sections, request)
        warnings = collect_llm_warnings()
        pasal_obj = TelaahanStafPasal(**pasal_dict)

        now = datetime.now()
        bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_ttd = f"{request.tempat or 'Jakarta'}, {now.day} {bulan_id[now.month - 1]} {now.year}"
        if request.tanggal:
            tanggal_ttd = f"{request.tempat or 'Jakarta'}, {request.tanggal}"

        lampiran_clean = [l.strip() for l in (request.lampiran_list or []) if l.strip()]

        template_data = {
            'kop_utama': (request.kop_utama or "PUSAT SIBER PERTAHANAN").strip(),
            'kop_satuan_bawah': (request.kop_satuan_bawah or "").strip(),
            'judul': request.judul.strip().upper(),
            'nomor_naskah': (request.nomor_naskah or "").strip(),
            'pasal': pasal_dict,
            'tanggal_ttd': tanggal_ttd,
            'nama_pejabat': request.nama_pejabat.strip(),
            'jabatan_pejabat': request.jabatan.strip(),
            'pangkat_pejabat': (request.pangkat_korps_nrp or "").strip(),
            'lampiran_list': lampiran_clean,
        }

        pdf_filename = f"telaahan_staf_{surat_id}.pdf"
        pdf_path = settings.OUTPUT_DIR / pdf_filename
        await asyncio.to_thread(create_pdf_telaahan_staf, template_data, pdf_path)

        konten_gabungan = _format_telaahan_staf_gabungan(
            kop_utama=request.kop_utama or "PUSAT SIBER PERTAHANAN",
            kop_sub=request.kop_satuan_bawah or "",
            judul=request.judul,
            nomor_naskah=request.nomor_naskah or "",
            pasal=pasal_dict,
            tanggal_ttd=tanggal_ttd,
            nama_pejabat=request.nama_pejabat,
            jabatan=request.jabatan,
            pangkat=request.pangkat_korps_nrp or "",
            lampiran_list=lampiran_clean
        )

        return TelaahanStafOutput(
            id=surat_id,
            judul=request.judul,
            nomor_naskah=request.nomor_naskah,
            pasal=pasal_obj,
            konten_gabungan=konten_gabungan,
            file_path=pdf_path.name,
            download_url=f"/download/{surat_id}",
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        logger.error(f"Error in generate_telaahan_staf: {e}", exc_info=True)
        logger.error("Gagal membuat telaahan staf: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal membuat telaahan staf. Periksa log server untuk detail.")


@router.post("/render-telaahan-staf-pdf", response_model=TelaahanStafOutput)
async def render_telaahan_staf_pdf(request: TelaahanStafRenderRequest):
    """
    Render ulang PDF dari teks 6 pasal yang sudah diedit manual oleh pengguna.
    """
    try:
        surat_id = str(uuid.uuid4())
        
        # Validasi dan sanitasi input pasal yang diedit
        pasal_raw = {
            "persoalan": request.pasal.persoalan,
            "praanggapan": request.pasal.praanggapan,
            "fakta": request.pasal.fakta,
            "analisis": request.pasal.analisis,
            "kesimpulan": request.pasal.kesimpulan,
            "saran": request.pasal.saran
        }
        pasal_dict = validate_and_sanitize_telaahan_staf(pasal_raw)
        pasal_obj = TelaahanStafPasal(**pasal_dict)

        now = datetime.now()
        bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_ttd = f"{request.tempat or 'Jakarta'}, {now.day} {bulan_id[now.month - 1]} {now.year}"
        if request.tanggal:
            tanggal_ttd = f"{request.tempat or 'Jakarta'}, {request.tanggal}"

        lampiran_clean = [l.strip() for l in (request.lampiran_list or []) if l.strip()]

        # Redaksi hasil editan pengguna (dikirim klien sebagai konten_custom)
        # WAJIB menang atas pasal baku — tanpa ini editan di editor diam-diam
        # dibuang dan PDF dirender dari teks lama (bug: editan hilang senyap).
        # Teks mentah diteruskan apa adanya — Jinja2 autoescape menangani
        # escaping saat cetak (escape manual = entity ganda tercetak di PDF).
        konten_custom_clean = (request.konten_custom or "").strip()

        template_data = {
            'kop_utama': (request.kop_utama or "PUSAT SIBER PERTAHANAN").strip(),
            'kop_satuan_bawah': (request.kop_satuan_bawah or "").strip(),
            'judul': request.judul.strip().upper(),
            'nomor_naskah': (request.nomor_naskah or "").strip(),
            'pasal': pasal_dict,
            'konten_custom': konten_custom_clean,
            'tanggal_ttd': tanggal_ttd,
            'nama_pejabat': request.nama_pejabat.strip(),
            'jabatan_pejabat': request.jabatan.strip(),
            'pangkat_pejabat': (request.pangkat_korps_nrp or "").strip(),
            'lampiran_list': lampiran_clean,
        }

        pdf_filename = f"telaahan_staf_{surat_id}.pdf"
        pdf_path = settings.OUTPUT_DIR / pdf_filename
        await asyncio.to_thread(create_pdf_telaahan_staf, template_data, pdf_path)

        konten_gabungan = (
            konten_custom_clean if konten_custom_clean else _format_telaahan_staf_gabungan(
                kop_utama=request.kop_utama or "PUSAT SIBER PERTAHANAN",
                kop_sub=request.kop_satuan_bawah or "",
                judul=request.judul,
                nomor_naskah=request.nomor_naskah or "",
                pasal=pasal_dict,
                tanggal_ttd=tanggal_ttd,
                nama_pejabat=request.nama_pejabat,
                jabatan=request.jabatan,
                pangkat=request.pangkat_korps_nrp or "",
                lampiran_list=lampiran_clean
            )
        )

        return TelaahanStafOutput(
            id=surat_id,
            judul=request.judul,
            nomor_naskah=request.nomor_naskah,
            pasal=pasal_obj,
            konten_gabungan=konten_gabungan,
            file_path=pdf_path.name,
            download_url=f"/download/{surat_id}"
        )
    except Exception as e:
        logger.error(f"Error in render_telaahan_staf_pdf: {e}", exc_info=True)
        logger.error("Gagal render ulang PDF telaahan staf: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal render ulang PDF telaahan staf. Periksa log server untuk detail.")
