import asyncio
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from ..models import (
    SuratRequest,
    SuratResponse,
    NotaDinasRequest,
    DraftSuratResponse,
    DraftNotaDinasResponse
)
from ..utils import format_tanggal_indonesia
from ..services.llm_service import generate_surat_content, generate_isi_nota_dinas
from ..services.llm_health import start_llm_request_scope, collect_llm_warnings
from ..services.pdf_service import create_pdf_surat, create_pdf_nota_dinas
from ..services.docx_service import create_docx_surat, create_docx_nota_dinas
from ..services.guardrail_kajian import escape_custom_html

router = APIRouter()

@router.post("/draft-surat", response_model=DraftSuratResponse)
async def draft_surat(request: SuratRequest):
    """
    Generate draf teks surat umum dengan AI tanpa membuat PDF (untuk pratinjau & edit).
    """
    try:
        # Generasi LLM berjalan sinkron dan berlangsung lama — jalankan di worker
        # thread agar event loop tidak membeku (endpoint /api/health tetap responsif).
        start_llm_request_scope()
        konten = await asyncio.to_thread(generate_surat_content, request)
        warnings = collect_llm_warnings()
        return DraftSuratResponse(
            perihal=request.perihal,
            konten_draft=konten,
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat draf surat: {str(e)}")

@router.post("/draft-nota-dinas", response_model=DraftNotaDinasResponse)
async def draft_nota_dinas(request: NotaDinasRequest):
    """
    Generate draf teks nota dinas dengan AI tanpa membuat PDF (untuk pratinjau & edit).
    """
    try:
        dasar_raw = request.dasar or ""
        dasar_list = [line.strip() for line in dasar_raw.split('\n') if line.strip()]
        if not dasar_list:
            dasar_list = ["Peraturan terkait."]

        start_llm_request_scope()
        isi_list = await asyncio.to_thread(generate_isi_nota_dinas, request)
        warnings = collect_llm_warnings()
        if not isi_list:
            isi_list = [{"teks": "Permohonan terkait.", "sub_poin": []}]

        # Format teks gabungan
        bagian_isi_list = []
        for i, itm in enumerate(isi_list):
            num = 2 + i
            if isinstance(itm, dict):
                teks = itm.get("teks", "")
                subs = itm.get("sub_poin", [])
                if subs:
                    sub_str = "\n" + "\n".join([f"   {chr(97 + j)}. {s}" for j, s in enumerate(subs)])
                    bagian_isi_list.append(f"{num}. {teks}{sub_str}")
                else:
                    bagian_isi_list.append(f"{num}. {teks}")
            else:
                bagian_isi_list.append(f"{num}. {itm}")

        bagian_isi = "\n\n".join(bagian_isi_list)
        nomor_penutup = 2 + len(isi_list)
        kalimat_penutup = "Demikian mohon menjadi periksa." if request.jenis_penutup == "periksa" else "Demikian disampaikan mohon menjadi perhatian."
        
        tembusan_list = [str(t).strip() for t in (request.tembusan or []) if str(t).strip()]
        tembusan_text = ""
        if tembusan_list:
            tembusan_text = "\n\nTembusan:\n" + "\n".join([f"{idx + 1}. {t}" for idx, t in enumerate(tembusan_list)])

        konten_gabungan = (
            f"NOTA DINAS\nNomor {request.nomor_surat}\n\n"
            f"Kepada Yth: {request.kepada}\nDari: {request.dari}\nPerihal: {request.perihal}\n\n"
            f"1. Dasar:\n" + "\n".join([f"{chr(97+i)}. {d}" for i,d in enumerate(dasar_list)]) +
            f"\n\n{bagian_isi}\n\n{nomor_penutup}. {kalimat_penutup}{tembusan_text}"
        )

        return DraftNotaDinasResponse(
            perihal=request.perihal,
            nomor_surat=request.nomor_surat,
            dasar_list=dasar_list,
            isi_list=isi_list,
            konten_gabungan=konten_gabungan,
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat draf nota dinas: {str(e)}")

@router.post("/generate-surat", response_model=SuratResponse)
async def generate_surat(request: SuratRequest):
    """
    Generate surat biasa dan simpan sebagai PDF. Mendukung teks hasil edit (konten_custom).
    """
    try:
        surat_id = str(uuid.uuid4())

        # Jika ada konten_custom (hasil edit user di preview), gunakan langsung
        warnings = []
        if request.konten_custom and request.konten_custom.strip():
            # konten_custom melewati LLM & guardrail lain — escape sebelum masuk
            # Jinja2 autoescape=False (cegah LFI/SSRF via wkhtmltopdf).
            konten = escape_custom_html(request.konten_custom.strip())
        else:
            start_llm_request_scope()
            konten = await asyncio.to_thread(generate_surat_content, request)
            warnings = collect_llm_warnings()

        tanggal = format_tanggal_indonesia()
        nomor_surat = f"{surat_id[:8]}/SK/{datetime.now().strftime('%m/%Y')}"

        template_data = {
            'nama_pengirim': (request.nama_pengirim or "").strip(),
            'alamat_pengirim': (request.alamat_pengirim or "").strip(),
            'nama_penerima': (request.nama_penerima or "").strip(),
            'alamat_penerima': (request.alamat_penerima or "").strip(),
            'perihal': (request.perihal or "").strip(),
            'tanggal': tanggal,
            'nomor_surat': nomor_surat,
            'isi_surat': konten.replace('\n', '<br>')
        }

        pdf_filename = f"surat_{surat_id}.pdf"
        pdf_path = settings.OUTPUT_DIR / pdf_filename
        docx_filename = f"surat_{surat_id}.docx"
        docx_path = settings.OUTPUT_DIR / docx_filename

        await asyncio.gather(
            asyncio.to_thread(create_pdf_surat, template_data, pdf_path),
            asyncio.to_thread(create_docx_surat, template_data, docx_path)
        )

        return SuratResponse(
            id=surat_id,
            konten_surat=konten,
            file_path=str(pdf_path),
            download_url=f"/download/{surat_id}",
            download_docx_url=f"/download/{surat_id}.docx",
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat surat: {str(e)}")

@router.post("/generate-nota-dinas", response_model=SuratResponse)
async def generate_nota_dinas(request: NotaDinasRequest):
    """
    Generate nota dinas dan simpan sebagai PDF. Mendukung teks hasil edit (isi_custom_list / konten_custom).
    """
    try:
        surat_id = str(uuid.uuid4())

        # Parse dasar menjadi list
        dasar_raw = request.dasar or ""
        dasar_list = [line.strip() for line in dasar_raw.split('\n') if line.strip()]
        if not dasar_list:
            dasar_list = ["Peraturan terkait."]

        # Cek apakah ada isi_custom_list (hasil edit user per-paragraf di editor)
        warnings = []
        if request.isi_custom_list and len(request.isi_custom_list) > 0:
            isi_list = []
            for item in request.isi_custom_list:
                if isinstance(item, dict):
                    isi_list.append(item)
                elif hasattr(item, "teks"):
                    isi_list.append({"teks": item.teks, "sub_poin": item.sub_poin or []})
                else:
                    isi_list.append({"teks": str(item), "sub_poin": []})
            # isi_custom_list melewati LLM & guardrail lain — escape sebelum masuk
            # Jinja2 autoescape=False (cegah LFI/SSRF via wkhtmltopdf).
            isi_list = escape_custom_html(isi_list)
        elif request.konten_custom and request.konten_custom.strip():
            # Jika user mengedit seluruh blok teks bebas
            import re
            custom_blocks = [l.strip() for l in request.konten_custom.strip().split('\n\n') if l.strip()]
            isi_list = []
            for block in custom_blocks:
                lines = [b.strip() for b in block.split('\n') if b.strip()]
                if not lines:
                    continue
                # Bersihkan penomoran awal paragraf utama (misal: "2. " atau "2) ") agar tidak dobel nomor
                main_teks = re.sub(r'^\d+[\.\)]\s*', '', lines[0]).strip()
                subs = []
                for sub_line in lines[1:]:
                    clean_sub = re.sub(r'^[a-z][\.\)]\s*|^[-*•]\s*', '', sub_line).strip()
                    if clean_sub:
                        subs.append(clean_sub)
                isi_list.append({"teks": escape_custom_html(main_teks), "sub_poin": [escape_custom_html(s) for s in subs]})
        else:
            # Generate via LLM dengan RAG (blocking → worker thread)
            start_llm_request_scope()
            isi_list = await asyncio.to_thread(generate_isi_nota_dinas, request)
            warnings = collect_llm_warnings()

        if not isi_list:
            isi_list = [{"teks": "Permohonan terkait.", "sub_poin": []}]

        now = datetime.now()
        bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        tanggal_ttd = f"Jakarta, {now.day} {bulan_id[now.month - 1]} {now.year}"

        # Ekstrak nama unit / pengirim & penandatangan
        dari_clean = (request.dari or "").strip()
        if not dari_clean:
            dari_clean = "Divisi Operasi"

        nama_pejabat = (request.nama_pejabat or "Budi Santoso").strip()
        jabatan_pejabat = (request.jabatan_pejabat or "Kadiv").strip()
        pangkat_pejabat = (request.pangkat_pejabat or "").strip()
        tembusan_list = [str(t).strip() for t in (request.tembusan or []) if str(t).strip()]

        # Tentukan kalimat penutup sesuai hierarki KEP-868 (atasan vs sejajar/bawahan)
        if request.jenis_penutup == "periksa":
            kalimat_penutup = "Demikian mohon menjadi periksa."
        else:
            kalimat_penutup = "Demikian disampaikan mohon menjadi perhatian."

        template_data = {
            'kop_utama': (request.kop_utama or "PUSAT KOMANDO OPERASI").strip(),
            'kop_sub': (request.kop_sub or "SATUAN BAWAH").strip(),
            'nomor_surat': (request.nomor_surat or "").strip(),
            'kepada': (request.kepada or "").strip(),
            'dari': dari_clean,
            'perihal': (request.perihal or "").strip(),
            'dasar_list': dasar_list,
            'isi_list': isi_list,
            'tanggal_ttd': tanggal_ttd,
            'nama_pejabat': nama_pejabat,
            'jabatan_pejabat': jabatan_pejabat,
            'pangkat_pejabat': pangkat_pejabat,
            'tembusan_list': tembusan_list,
            'kalimat_penutup': kalimat_penutup,
        }

        pdf_filename = f"nota_dinas_{surat_id}.pdf"
        pdf_path = settings.OUTPUT_DIR / pdf_filename
        docx_filename = f"nota_dinas_{surat_id}.docx"
        docx_path = settings.OUTPUT_DIR / docx_filename

        await asyncio.gather(
            asyncio.to_thread(create_pdf_nota_dinas, template_data, pdf_path),
            asyncio.to_thread(create_docx_nota_dinas, template_data, docx_path)
        )

        # Format teks naskah untuk respons
        bagian_isi_list = []
        for i, itm in enumerate(isi_list):
            num = 2 + i
            if isinstance(itm, dict):
                teks = itm.get("teks", "")
                subs = itm.get("sub_poin", [])
                if subs:
                    sub_str = "\n" + "\n".join([f"   {chr(97 + j)}. {s}" for j, s in enumerate(subs)])
                    bagian_isi_list.append(f"{num}. {teks}{sub_str}")
                else:
                    bagian_isi_list.append(f"{num}. {teks}")
            else:
                bagian_isi_list.append(f"{num}. {itm}")

        bagian_isi = "\n\n".join(bagian_isi_list)
        nomor_penutup = 2 + len(isi_list)

        tembusan_text = ""
        if tembusan_list:
            tembusan_text = "\n\nTembusan:\n" + "\n".join([f"{idx + 1}. {t}" for idx, t in enumerate(tembusan_list)])

        konten_gabungan = f"NOTA DINAS\nNomor {request.nomor_surat}\n\n" \
                          f"Kepada Yth: {request.kepada}\nDari: {request.dari}\nPerihal: {request.perihal}\n\n" \
                          f"1. Dasar:\n" + "\n".join([f"{chr(97+i)}. {d}" for i,d in enumerate(dasar_list)]) + \
                          f"\n\n{bagian_isi}\n\n{nomor_penutup}. {kalimat_penutup}{tembusan_text}"

        return SuratResponse(
            id=surat_id,
            konten_surat=konten_gabungan,
            file_path=str(pdf_path),
            download_url=f"/download/{surat_id}",
            download_docx_url=f"/download/{surat_id}.docx",
            llm_degraded=bool(warnings),
            llm_warnings=warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat nota dinas: {str(e)}")

@router.get("/download/{surat_id}")
async def download_surat(surat_id: str, inline: bool = False, format: str = "pdf"):
    """
    Download atau preview file PDF atau DOCX surat berdasarkan ID atau nama file.
    Mendukung format: UUID, nama file dengan ekstensi .pdf/.docx, atau query param ?format=docx.
    """
    clean_id = Path(surat_id).name.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="ID surat tidak valid")

    # Deteksi apakah format yang diminta adalah DOCX
    is_docx = clean_id.lower().endswith(".docx") or (format and format.lower() == "docx")

    if clean_id.lower().endswith(".pdf"):
        raw_name = clean_id[:-4]
    elif clean_id.lower().endswith(".docx"):
        raw_name = clean_id[:-5]
    else:
        raw_name = clean_id

    ext = ".docx" if is_docx else ".pdf"
    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if is_docx
        else "application/pdf"
    )

    candidates = [
        clean_id,
        f"{raw_name}{ext}",
        f"surat_{raw_name}{ext}",
        f"nota_dinas_{raw_name}{ext}",
        f"telaahan_staf_{raw_name}{ext}",
        f"kka_studi_kasus_{raw_name}{ext}",
        f"kka_analisis_moe_{raw_name}{ext}",
        f"kka_pemecahan_masalah_{raw_name}{ext}",
        f"kka_{raw_name}{ext}",
        f"lapju_belanja_modal_{raw_name}{ext}",
        f"lapju_{raw_name}{ext}",
    ]

    matched_path = None
    for filename in candidates:
        candidate_path = settings.OUTPUT_DIR / filename
        if candidate_path.exists() and candidate_path.is_file():
            matched_path = candidate_path
            break

    if not matched_path or not matched_path.exists():
        format_label = "DOCX" if is_docx else "PDF"
        raise HTTPException(status_code=404, detail=f"File {format_label} '{clean_id}' tidak ditemukan di server")

    disposition = "inline" if (inline and not is_docx) else "attachment"
    return FileResponse(
        path=str(matched_path),
        filename=matched_path.name,
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{matched_path.name}"'
        }
    )

@router.get("/download-docx/{surat_id}")
async def download_docx(surat_id: str):
    """
    Download file DOCX surat berdasarkan ID.
    """
    return await download_surat(surat_id=surat_id, inline=False, format="docx")

@router.get("/preview-pdf/{surat_id}")
async def preview_pdf(surat_id: str):
    """
    Buka/preview file PDF langsung di browser tab baru (inline).
    """
    return await download_surat(surat_id=surat_id, inline=True)

# ── RAG Management Endpoints ──

@router.get("/rag/status")
async def get_rag_status():
    """
    Mengambil status sistem RAG (apakah aktif, jumlah dokumen terindeks, dan waktu update).
    """
    from ..services.rag_service import rag_engine
    return rag_engine.get_status()

@router.post("/rag/reindex")
async def reindex_rag():
    """
    Melakukan sinkronisasi dan indexing ulang seluruh dokumen referensi.
    """
    from ..services.rag_service import rag_engine
    # Indexing CPU-bound — jalankan di worker thread agar tidak membekukan event loop.
    total = await asyncio.to_thread(rag_engine.index_all_documents, force=True)
    return {
        "status": "success",
        "message": f"Berhasil mengindeks {total} dokumen referensi ke knowledge base.",
        "total_documents": total,
        "indexed_at": rag_engine.last_indexed_at
    }

@router.get("/rag/search")
async def search_rag(q: str, limit: int = 5):
    """
    Pencarian semantik pada koleksi dokumen referensi naskah dinas.
    """
    from ..services.rag_service import rag_engine
    results = rag_engine.search(query=q, top_k=limit)
    return {
        "query": q,
        "total_results": len(results),
        "results": results
    }