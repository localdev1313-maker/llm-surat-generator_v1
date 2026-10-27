"""
Skrip Uji Skala Kecil Fitur Arsip Direktori Internal Dokumen SSEB-AI
(direktori-nota_dinas, direktori-telaah_staff, direktori-kka_sesko, direktori-lapju, direktori-surat_biasa)
"""

import sys
import io
import asyncio
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import httpx
from app.main import app
from app.config import settings
from app.services.archive_service import (
    ALL_ARCHIVE_DIRS,
    get_archive_summary,
    sync_existing_output_files
)

async def test_archive_feature():
    print("=" * 60)
    print("🚀 PENGUJIAN SKALA KECIL FITUR ARSIP DIREKTORI INTERNAL SSEB-AI")
    print("=" * 60)

    # 1. Inisialisasi dan Sinkronisasi File Output
    print("\n[Tahap 1] Sinkronisasi & Pembuatan Subdirektori Internal...")
    sync_stats = sync_existing_output_files()
    for dir_name, count in sync_stats.items():
        dir_path = settings.OUTPUT_DIR / dir_name
        assert dir_path.exists(), f"Direktori {dir_name} harus ada di disk!"
        print(f"  ✓ {dir_name}: {count} file tersinkronkan (Path: {dir_path})")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        # 2. Cek Endpoint Status Arsip
        print("\n[Tahap 2] Verifikasi Endpoint GET /api/v1/archive/status...")
        status_res = await client.get("/api/v1/archive/status")
        assert status_res.status_code == 200, f"Status response gagal: {status_res.status_code}"
        summary = status_res.json()
        for d in ALL_ARCHIVE_DIRS:
            assert d in summary, f"Direktori {d} tidak ada dalam summary!"
            info = summary[d]
            print(f"  ✓ {d}: Total {info['total_files']} file (PDF: {info['pdf_count']}, DOCX: {info['docx_count']})")

        # 3. Uji Pembuatan Dokumen Baru (Nota Dinas) & Cek Penyimpanan Otomatis
        print("\n[Tahap 3] Uji Pembuatan Nota Dinas Baru...")
        nd_payload = {
            "kop_utama": "PUSAT KOMANDO OPERASI",
            "kop_sub": "SATUAN PENGAMANAN",
            "nomor_surat": "ND/99/X/2026",
            "kepada": "Komandan Satuan",
            "dari": "Perwira Staf Operasi",
            "perihal": "Uji Pengarsipan Internal Nota Dinas",
            "dasar": "Perintah Latihan Satuan Nomor 12/2026",
            "isi_custom_list": [
                {"teks": "Penyampaian hasil pengujian sistem penyimpanan otomatis internal.", "sub_poin": []}
            ],
            "nama_pejabat": "Budi Santoso",
            "jabatan_pejabat": "Perwira Staf",
            "pangkat_pejabat": "Mayor Laut (P) NRP 12345/P",
            "jenis_penutup": "perhatian"
        }
        res_nd = await client.post("/generate-nota-dinas", json=nd_payload)
        assert res_nd.status_code == 200, f"Generate Nota Dinas gagal: {res_nd.text}"
        data_nd = res_nd.json()
        nd_id = data_nd["id"]
        pdf_nd_name = f"nota_dinas_{nd_id}.pdf"
        docx_nd_name = f"nota_dinas_{nd_id}.docx"

        # Verifikasi file ada di direktori-nota_dinas/
        archived_pdf = settings.OUTPUT_DIR / "direktori-nota_dinas" / pdf_nd_name
        archived_docx = settings.OUTPUT_DIR / "direktori-nota_dinas" / docx_nd_name
        assert archived_pdf.exists(), f"File PDF {pdf_nd_name} TIDAK ditemukan di direktori-nota_dinas!"
        assert archived_docx.exists(), f"File DOCX {docx_nd_name} TIDAK ditemukan di direktori-nota_dinas!"
        print(f"  ✓ Nota Dinas PDF tersimpan otomatis di: direktori-nota_dinas/{pdf_nd_name} ({archived_pdf.stat().st_size} bytes)")
        print(f"  ✓ Nota Dinas DOCX tersimpan otomatis di: direktori-nota_dinas/{docx_nd_name} ({archived_docx.stat().st_size} bytes)")

        # 4. Uji Download Dokumen Nota Dinas
        print("\n[Tahap 4] Uji Download Nota Dinas PDF & DOCX...")
        dl_pdf_res = await client.get(f"/download/{nd_id}")
        assert dl_pdf_res.status_code == 200, f"Download PDF gagal: {dl_pdf_res.status_code}"
        assert len(dl_pdf_res.content) > 1000
        print(f"  ✓ Download PDF berhasil ({len(dl_pdf_res.content)} bytes)")

        dl_docx_res = await client.get(f"/download-docx/{nd_id}")
        assert dl_docx_res.status_code == 200, f"Download DOCX gagal: {dl_docx_res.status_code}"
        assert len(dl_docx_res.content) > 1000
        print(f"  ✓ Download DOCX berhasil ({len(dl_docx_res.content)} bytes)")

        # 5. Uji Pembuatan Dokumen Baru (Telaahan Staf) & Cek Penyimpanan Otomatis
        print("\n[Tahap 5] Uji Pembuatan Telaahan Staf Baru...")
        ts_payload = {
            "kategori": "TELAAHAN_STAF",
            "kop_utama": "PUSAT KOMANDO OPERASI",
            "kop_satuan_bawah": "SATUAN PENGAMANAN",
            "judul_atau_topik": "UJI SISTEM ARSIP INTERNAL TELAAH STAFF",
            "nomor_naskah": "Nomor TS/99/X/2026/SAT",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Budi Santoso",
            "jabatan": "Perwira Staf",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "sections_custom": {
                "persoalan": "Kebutuhan klasifikasi dokumen naskah dinas militer secara teratur.",
                "praanggapan": "Pemisahan direktori mempercepat audit dan penelusuran naskah.",
                "fakta": "Volume berkas digital naskah meningkat setiap hari kerja.",
                "analisis": "Penyimpanan otomatis per kategori menihilkan kesalahan sortir manual.",
                "kesimpulan": "Struktur direktori internal terbukti efektif dan aman.",
                "saran": "Terapkan penyimpanan otomatis pada seluruh jenis naskah."
            }
        }
        res_ts = await client.post("/api/v1/kajian/generate", json=ts_payload)
        assert res_ts.status_code == 200, f"Generate Telaahan Staf gagal: {res_ts.text}"
        data_ts = res_ts.json()
        ts_id = data_ts["id"]
        pdf_ts_name = f"telaahan_staf_{ts_id}.pdf"
        docx_ts_name = f"telaahan_staf_{ts_id}.docx"

        # Verifikasi file ada di direktori-telaah_staff/
        archived_ts_pdf = settings.OUTPUT_DIR / "direktori-telaah_staff" / pdf_ts_name
        archived_ts_docx = settings.OUTPUT_DIR / "direktori-telaah_staff" / docx_ts_name
        assert archived_ts_pdf.exists(), f"File PDF {pdf_ts_name} TIDAK ditemukan di direktori-telaah_staff!"
        assert archived_ts_docx.exists(), f"File DOCX {docx_ts_name} TIDAK ditemukan di direktori-telaah_staff!"
        print(f"  ✓ Telaahan Staf PDF tersimpan otomatis di: direktori-telaah_staff/{pdf_ts_name} ({archived_ts_pdf.stat().st_size} bytes)")
        print(f"  ✓ Telaahan Staf DOCX tersimpan otomatis di: direktori-telaah_staff/{docx_ts_name} ({archived_ts_docx.stat().st_size} bytes)")

        # 6. Uji Download Dokumen Telaahan Staf
        print("\n[Tahap 6] Uji Download Telaahan Staf PDF & DOCX...")
        dl_ts_pdf = await client.get(f"/download/{ts_id}")
        assert dl_ts_pdf.status_code == 200
        print(f"  ✓ Download Telaahan Staf PDF berhasil ({len(dl_ts_pdf.content)} bytes)")

        dl_ts_docx = await client.get(f"/download-docx/{ts_id}")
        assert dl_ts_docx.status_code == 200
        print(f"  ✓ Download Telaahan Staf DOCX berhasil ({len(dl_ts_docx.content)} bytes)")

    print("\n" + "=" * 60)
    print("🎉 SEMUA PENGUJIAN SKALA KECIL ARSIP INTERNAL BERHASIL 100%!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_archive_feature())
