import asyncio
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..schemas.lapju import (
    LapjuGenerateRequest,
    LapjuDraftResponse,
    LapjuGenerateResponse,
    LapjuTotalsModel,
    JenisTandaTangan
)
from ..services.lapju_service import (
    calculate_lapju_data,
    prepare_lapju_template_data,
    format_lapju_summary_text,
    build_lapju_pasal_list
)
from ..services.pdf_service import create_pdf_lapju

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/lapju",
    tags=["Laporan Kemajuan (LAPJU)"]
)

@router.post("/calculate", response_model=Dict[str, Any])
async def calculate_lapju(req: LapjuGenerateRequest):
    """
    Endpoint kalkulasi deterministik instan untuk tabel belanja modal (Non-AI):
    Menghitung sisa anggaran per item kegiatan dan rekapitulasi total keseluruhan secara matematis presisi.
    """
    try:
        items, totals = calculate_lapju_data(req)
        return {
            "status": "success",
            "items": items,
            "totals": totals.dict()
        }
    except Exception as e:
        logger.error(f"Gagal kalkulasi lapju: {e}", exc_info=True)
        logger.error("Gagal kalkulasi data lapju: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal kalkulasi data lapju. Periksa log server untuk detail.")

@router.post("/draft", response_model=LapjuDraftResponse)
async def draft_lapju(req: LapjuGenerateRequest):
    """
    Generate draf naskah induk surat pengantar dan rekapitulasi tabel matriks Lapju data riil tanpa AI & tanpa render PDF.
    """
    try:
        template_data = prepare_lapju_template_data(req)
        items, totals = calculate_lapju_data(req)
        summary_text = format_lapju_summary_text(template_data)

        return LapjuDraftResponse(
            status="success",
            nomor_surat=template_data["nomor_surat"],
            tanggal_surat=template_data["tanggal_surat"],
            ringkasan_teks=summary_text,
            pasal_list=build_lapju_pasal_list(template_data),
            totals=totals,
            items_processed=items
        )
    except Exception as e:
        logger.error(f"Gagal menyusun draf lapju: {e}", exc_info=True)
        logger.error("Gagal menyusun draf lapju: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal menyusun draf lapju. Periksa log server untuk detail.")

@router.post("/generate", response_model=LapjuGenerateResponse)
async def generate_lapju(req: LapjuGenerateRequest):
    """
    Generate dokumen Laporan Kemajuan (LAPJU) Belanja Modal terpadu (Portrait + Landscape PDF) 100% data riil tanpa AI.
    """
    try:
        lapju_id = str(uuid.uuid4())
        template_data = prepare_lapju_template_data(req)
        items, totals = calculate_lapju_data(req)
        
        filename = f"lapju_belanja_modal_{lapju_id}.pdf"
        output_path = settings.OUTPUT_DIR / filename

        # Render PDF (blocking wkhtmltopdf) — worker thread agar event loop beku tidak terjadi.
        await asyncio.to_thread(
            create_pdf_lapju,
            template_data=template_data,
            output_path=output_path
        )
        
        return LapjuGenerateResponse(
            status="success",
            message="Dokumen Laporan Kemajuan (LAPJU) Belanja Modal berhasil dibuat",
            id=lapju_id,
            surat_id=lapju_id,
            nomor_surat=template_data["nomor_surat"],
            file_path=output_path.name,
            download_url=f"/download/{lapju_id}",
            preview_pdf_url=f"/preview-pdf/{lapju_id}",
            totals=totals
        )
    except Exception as e:
        logger.error(f"Gagal generate dokumen lapju PDF: {e}", exc_info=True)
        logger.error("Gagal generate dokumen lapju PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gagal generate dokumen lapju PDF. Periksa log server untuk detail.")
