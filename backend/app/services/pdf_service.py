# pyrefly: ignore [missing-import]
import pdfkit
from jinja2 import Template
from pathlib import Path
from ..config import settings

# Konfigurasi Standar Tata Tulis Militer TNI (KEP/868/2022)
# CATATAN margin-right: dengan `disable-smart-shrinking`, teks justify merender
# hingga menyentuh batas cetak (bahkan +1..7pt pada tabel/teks lebar) sehingga
# huruf terpotong garis tepi. Margin kanan 18mm memberi buffer ±8pt — huruf
# tidak lagi tersentuh tepi, ukuran font tetap 12pt persis.
MILITARY_PDF_OPTIONS = {
    'page-size': 'A4',
    'margin-top': '20.3mm',      # 0.8 inci (Top Margin)
    'margin-right': '18mm',      # 15.2mm + buffer anti-terpotong
    'margin-bottom': '12.7mm',   # 0.5 inci (Bottom Margin)
    'margin-left': '25.4mm',     # 1.0 inci (Left Margin)
    'encoding': 'UTF-8',
    'no-outline': None,
    'enable-local-file-access': None,
    'disable-smart-shrinking': None
}

def generate_pdf_from_template(template_path: Path, template_data: dict, output_path: Path) -> Path:
    """
    Render template HTML dengan data dan konversi ke PDF sesuai standar KEP/868/2022.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)
    html_content = template.render(**template_data)

    config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)
    pdfkit.from_string(
        html_content,
        str(output_path),
        configuration=config,
        options=MILITARY_PDF_OPTIONS
    )
    return output_path

def create_pdf_surat(template_data: dict, output_path: Path) -> Path:
    """
    Generate PDF untuk surat resmi / dinas.
    """
    template_file = settings.TEMPLATE_DIR / "surat_template.html"
    return generate_pdf_from_template(template_file, template_data, output_path)

def create_pdf_nota_dinas(template_data: dict, output_path: Path) -> Path:
    """
    Generate PDF untuk nota dinas baku TNI.
    """
    template_file = settings.TEMPLATE_DIR / "nota_dinas_template.html"
    return generate_pdf_from_template(template_file, template_data, output_path)

def create_pdf_telaahan_staf(template_data: dict, output_path: Path) -> Path:
    """
    Generate PDF untuk telaahan staf / kajian baku TNI (KEP/868 Contoh 26).
    """
    template_file = settings.TEMPLATE_DIR / "telaahan_staf_template.html"
    return generate_pdf_from_template(template_file, template_data, output_path)

def create_pdf_kajian(kategori: str, kka_model: str, template_data: dict, output_path: Path) -> Path:
    """
    Generate PDF untuk Modul Kajian Dual-Mode:
    - TELAAHAN_STAF: KEP/868/IX/2022 Contoh 26
    - KKA_SESKO: STUDI_KASUS, ANALISIS_MOE, PEMECAHAN_MASALAH
    """
    data = dict(template_data)
    # Ensure interoperability between pasal and sections keys
    if "sections" in data and "pasal" not in data:
        data["pasal"] = data["sections"]
    elif "pasal" in data and "sections" not in data:
        data["sections"] = data["pasal"]

    # Ensure interoperability for signature and header metadata
    nama = data.get("nama_pejabat") or data.get("nama_pejabat_atau_pasis") or "Budi Santoso"
    jabatan = data.get("jabatan_pejabat") or data.get("jabatan") or "Perwira Staf"
    pangkat = data.get("pangkat_pejabat") or data.get("pangkat_korps_nrp") or ""

    data["nama_pejabat"] = nama
    data["nama_pejabat_atau_pasis"] = nama
    data["jabatan_pejabat"] = jabatan
    data["jabatan"] = jabatan
    data["pangkat_pejabat"] = pangkat
    data["pangkat_korps_nrp"] = pangkat

    kat_upper = str(kategori).upper()
    if kat_upper == "TELAAHAN_STAF" or "TELAAHAN" in kat_upper:
        template_file = settings.TEMPLATE_DIR / "telaahan_staf_template.html"
    else:
        # KKA Sesko 2020
        model_upper = str(kka_model).upper()
        if "STUDI_KASUS" in model_upper or "KASUS" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_studi_kasus_template.html"
        elif "ANALISIS" in model_upper or "MOE" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_analisis_moe_template.html"
        elif "MASALAH" in model_upper or "SOM" in model_upper:
            template_file = settings.TEMPLATE_DIR / "kka_pemecahan_masalah_template.html"
        else:
            template_file = settings.TEMPLATE_DIR / "kka_studi_kasus_template.html"
            
    return generate_pdf_from_template(template_file, data, output_path)

LANDSCAPE_PDF_OPTIONS = {
    'page-size': 'A4',
    'orientation': 'Landscape',
    'margin-top': '15mm',
    'margin-right': '18mm',      # buffer anti-terpotong (matriks 13 kolom)
    'margin-bottom': '15mm',
    'margin-left': '15mm',
    'encoding': 'UTF-8',
    'no-outline': None,
    'enable-local-file-access': None,
    'disable-smart-shrinking': None,
    # Kalibrasi empiris: mesin render menempatkan tabel matriks pada 631pt dari
    # 748.5pt printable — zoom 1.18 memenuhi lebar area cetak tanpa melampaui
    # margin (terverifikasi: border kolom terkanan ~789pt dari 791pt batas).
    'zoom': '1.18',
}

def create_pdf_lapju(template_data: dict, output_path: Path) -> Path:
    """
    Generate PDF resmi terpadu Laporan Kemajuan (LAPJU) Belanja Modal:
    - Halaman 1+: Surat Pengantar (Portrait A4 Standar KEP/868/2022)
    - Halaman 2+: Lampiran Matriks Tabel 13 Kolom Realisasi (Landscape A4)
    Kedua berkas digabungkan secara otomatis menggunakan pypdf.
    """
    import uuid
    import pypdf
    import os

    config = pdfkit.configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH)

    # Nama temp file ditentukan sebelum try/finally sehingga cleanup di
    # finally selalu berjalan walau render/merge gagal di tengah jalan
    # (mencegah file .pdf sementara menumpuk permanen di OUTPUT_DIR).
    temp_portrait = settings.OUTPUT_DIR / f"temp_lapju_portrait_{uuid.uuid4().hex}.pdf"
    temp_landscape = settings.OUTPUT_DIR / f"temp_lapju_landscape_{uuid.uuid4().hex}.pdf"

    try:
        # 1. Render Surat Pengantar (Portrait)
        pengantar_tpl = settings.TEMPLATE_DIR / "lapju_surat_pengantar_template.html"
        with open(pengantar_tpl, "r", encoding="utf-8") as f:
            html_pengantar = Template(f.read()).render(**template_data)

        pdfkit.from_string(
            html_pengantar,
            str(temp_portrait),
            configuration=config,
            options=MILITARY_PDF_OPTIONS
        )

        # 2. Render Lampiran Matriks Tabel (Landscape)
        lampiran_tpl = settings.TEMPLATE_DIR / "lapju_lampiran_tabel_template.html"
        with open(lampiran_tpl, "r", encoding="utf-8") as f:
            html_lampiran = Template(f.read()).render(**template_data)

        pdfkit.from_string(
            html_lampiran,
            str(temp_landscape),
            configuration=config,
            options=LANDSCAPE_PDF_OPTIONS
        )

        # 3. Merge Surat Pengantar (Portrait) + Lampiran Tabel (Landscape)
        writer = pypdf.PdfWriter()

        with open(temp_portrait, "rb") as f_p:
            r_p = pypdf.PdfReader(f_p)
            for page in r_p.pages:
                writer.add_page(page)

        with open(temp_landscape, "rb") as f_l:
            r_l = pypdf.PdfReader(f_l)
            for page in r_l.pages:
                writer.add_page(page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
    finally:
        # Clean up temporary PDFs - selalu dijalankan, termasuk saat exception.
        try:
            if os.path.exists(temp_portrait):
                os.remove(temp_portrait)
            if os.path.exists(temp_landscape):
                os.remove(temp_landscape)
        except Exception:
            pass

    return output_path