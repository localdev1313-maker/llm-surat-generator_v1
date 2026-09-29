"""
Comprehensive End-to-End Verification Test for SSEB AI "Laporan Kemajuan (LAPJU) Belanja Modal"
Tests:
1. POST /api/v1/lapju/calculate (Aggregate calculations & Rupiah formatting)
2. POST /api/v1/lapju/draft (Draft creation, Roman numeral month mapping, auto numbering)
3. POST /api/v1/lapju/generate (Versi MEWAKILI - Portrait Page 1 + Landscape Page 2 merged PDF)
4. POST /api/v1/lapju/generate (Versi LANGSUNG - Direct signature layout)
5. Zero Regression Check: POST /generate-nota-dinas & POST /api/v1/kajian/generate
6. GET /download/{surat_id} verification
"""

import sys
import os
import asyncio
from pathlib import Path
import httpx
from pypdf import PdfReader

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app
from app.config import settings


async def run_all_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        print("=== STARTING COMPREHENSIVE LAPJU BELANJA MODAL E2E TESTS ===")

        # ── Test 1: Calculate Lapju Totals ──
        print("\n[TEST 1] Testing /api/v1/lapju/calculate endpoint...")
        calc_payload = {
            "kop_utama": "MARKAS BESAR ANGKATAN LAUT",
            "kop_satker": "DINAS PENGADAAN ANGKATAN LAUT",
            "bulan": "April",
            "tahun": 2025,
            "jabatan_penandatangan": "Kepala Dinas Pengadaan Angkatan Laut",
            "nama_penandatangan": "Budi Santoso, S.E., M.M.",
            "pangkat_korps_nrp": "Laksamana Pertama TNI NRP 12345/P",
            "items": [
                {
                    "no_urut": 1,
                    "nama_kegiatan": "Pengadaan Multi-Role Tactical Server Unit",
                    "pagu_anggaran": 2500000000.0,
                    "nilai_kontrak": 2450000000.0,
                    "anggaran_terserap": 735000000.0,
                    "persentase_fisik": 40,
                    "persentase_admin": 30
                },
                {
                    "no_urut": 2,
                    "nama_kegiatan": "Modernisasi Modul Sensor Radar Maritim",
                    "pagu_anggaran": 3500000000.0,
                    "nilai_kontrak": 3400000000.0,
                    "anggaran_terserap": 1020000000.0,
                    "persentase_fisik": 30,
                    "persentase_admin": 30
                }
            ]
        }
        res_calc = await client.post("/api/v1/lapju/calculate", json=calc_payload)
        assert res_calc.status_code == 200, f"Calculate failed: {res_calc.text}"
        data_calc = res_calc.json()
        assert data_calc["status"] == "success"
        totals = data_calc["totals"]

        assert totals["total_pagu"] == 6000000000.0, f"Expected 6B, got {totals['total_pagu']}"
        assert totals["total_nilai_kontrak"] == 5850000000.0
        assert totals["total_anggaran_terserap"] == 1755000000.0
        assert totals["total_sisa_anggaran"] == 4245000000.0
        assert totals["rata_rata_fisik"] == 35.0
        assert totals["rata_rata_admin"] == 30.0
        assert totals["total_pagu_formatted"] == "6.000.000.000"
        print("[PASSED] TEST 1: Kalkulasi agregat dan format rupiah 100% akurat")

        # ── Test 2: Draft Lapju ──
        print("\n[TEST 2] Testing /api/v1/lapju/draft endpoint...")
        res_draft = await client.post("/api/v1/lapju/draft", json=calc_payload)
        assert res_draft.status_code == 200, f"Draft failed: {res_draft.text}"
        data_draft = res_draft.json()
        assert "IV" in data_draft["nomor_surat"], f"Bulan April harus IV, got {data_draft['nomor_surat']}"
        assert "2025" in data_draft["nomor_surat"]
        assert "REKAPITULASI BELANJA MODAL" in data_draft["ringkasan_teks"]
        print(f"[PASSED] TEST 2: Nomor otomatis '{data_draft['nomor_surat']}' dan draf ringkasan berhasil disusun")

        # ── Test 3: Generate Versi Mewakili (mewakili,) PDF ──
        print("\n[TEST 3] Testing /api/v1/lapju/generate (Versi Mewakili)...")
        gen_mewakili_payload = {
            "kop_utama": "MARKAS BESAR ANGKATAN LAUT",
            "kop_satker": "DINAS PENGADAAN ANGKATAN LAUT",
            "bulan": "April",
            "tahun": 2025,
            "klasifikasi": "Biasa",
            "lampiran_keterangan": "Dua lembar",
            "perihal": "Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa",
            "kepada_yth": "Asisten Logistik Kasal",
            "kota_tujuan": "Jakarta",
            "dasar_rujukan": "Surat Perintah Kasal Nomor Sprin/123/I/2025 tanggal 10 Januari 2025",
            "jabatan_penandatangan": "Kepala Dinas Pengadaan Angkatan Laut",
            "jenis_ttd": "MEWAKILI",
            "nama_penandatangan": "Budi Santoso, S.E., M.M.",
            "pangkat_korps_nrp": "Laksamana Pertama TNI NRP 12345/P",
            "tembusan": [
                "Kepala Staf Angkatan Laut",
                "Wakil Kepala Staf Angkatan Laut",
                "Inspektur Jenderal Angkatan Laut"
            ],
            "items": [
                {
                    "no_urut": 1,
                    "nomor_dipa": "SP DIPA-012.01.1.678901/2025",
                    "tanggal_dipa": "28 November 2024",
                    "nama_kegiatan": "Pengadaan Multi-Role Tactical Server Unit Satker",
                    "pagu_anggaran": 2500000000.0,
                    "nilai_kontrak": 2450000000.0,
                    "nomor_kontrak": "KTR/01/II/2025",
                    "tanggal_kontrak": "15 Februari 2025",
                    "tds": "30 Juni 2025",
                    "penyedia": "PT Alkomindo Jaya Pertahanan",
                    "anggaran_terserap": 735000000.0,
                    "persentase_fisik": 40,
                    "persentase_admin": 30,
                    "keterangan_admin": ["BAP Uang Muka 30% Terbit"],
                    "keterangan_fisik": ["Pengiriman komponen tahap 1 ke gudang satker"]
                }
            ]
        }
        res_gen_m = await client.post("/api/v1/lapju/generate", json=gen_mewakili_payload)
        assert res_gen_m.status_code == 200, f"Generate Mewakili failed: {res_gen_m.text}"
        data_gen_m = res_gen_m.json()
        assert data_gen_m["status"] == "success"
        
        pdf_path_m = Path(data_gen_m["file_path"])
        assert pdf_path_m.exists(), f"File PDF {pdf_path_m} tidak ditemukan"
        assert pdf_path_m.stat().st_size > 1000, "Ukuran file PDF terlalu kecil"

        # Verifikasi Struktur Orientasi Halaman PDF (Page 1 = Portrait, Page 2 = Landscape)
        reader_m = PdfReader(str(pdf_path_m))
        assert len(reader_m.pages) >= 2, f"Expected min 2 halaman, got {len(reader_m.pages)}"
        
        p1 = reader_m.pages[0]
        w1, h1 = float(p1.mediabox.width), float(p1.mediabox.height)
        assert w1 < h1, f"Halaman 1 harus Portrait: width={w1}, height={h1}"

        p2 = reader_m.pages[1]
        w2, h2 = float(p2.mediabox.width), float(p2.mediabox.height)
        assert w2 > h2, f"Halaman 2 harus Landscape: width={w2}, height={h2}"

        # Verifikasi teks di halaman 1
        text_p1 = p1.extract_text()
        assert "mewakili," in text_p1 or "mewakili" in text_p1
        print(f"[PASSED] TEST 3: PDF Merged Portrait (p1: {w1:.0f}x{h1:.0f}pt) + Landscape (p2: {w2:.0f}x{h2:.0f}pt) dengan tajuk 'mewakili,' terverifikasi")

        # ── Test 4: Generate Versi Langsung PDF ──
        print("\n[TEST 4] Testing /api/v1/lapju/generate (Versi Langsung)...")
        gen_langsung_payload = {
            "kop_utama": "MARKAS BESAR ANGKATAN LAUT",
            "kop_satker": "DINAS PENGADAAN ANGKATAN LAUT",
            "bulan": "Mei",
            "tahun": 2025,
            "jenis_ttd": "LANGSUNG",
            "jabatan_penandatangan": "Kepala Dinas Pengadaan Angkatan Laut",
            "nama_penandatangan": "Budi Santoso, S.E., M.M.",
            "pangkat_korps_nrp": "Laksamana Pertama TNI NRP 12345/P",
            "items": [
                {
                    "no_urut": 1,
                    "nama_kegiatan": "Pengadaan Alutsista Modern",
                    "pagu_anggaran": 5000000000.0,
                    "nilai_kontrak": 4900000000.0,
                    "anggaran_terserap": 1500000000.0,
                    "persentase_fisik": 30,
                    "persentase_admin": 30
                }
            ]
        }
        res_gen_l = await client.post("/api/v1/lapju/generate", json=gen_langsung_payload)
        assert res_gen_l.status_code == 200, f"Generate Langsung failed: {res_gen_l.text}"
        data_gen_l = res_gen_l.json()
        pdf_path_l = Path(data_gen_l["file_path"])
        assert pdf_path_l.exists()
        reader_l = PdfReader(str(pdf_path_l))
        assert len(reader_l.pages) >= 2
        print(f"[PASSED] TEST 4: Versi Langsung berhasil diproduksi ({len(reader_l.pages)} halaman)")

        # ── Test 5: Verify Download URL Endpoint ──
        print("\n[TEST 5] Testing GET /download/{surat_id}...")
        surat_id = data_gen_m["surat_id"]
        res_dl = await client.get(f"/download/{surat_id}")
        assert res_dl.status_code == 200, f"Download failed: {res_dl.status_code}"
        assert res_dl.headers["content-type"] == "application/pdf"
        assert len(res_dl.content) > 1000
        print(f"[PASSED] TEST 5: Download endpoint valid ({len(res_dl.content)} bytes)")

        # ── Test 6: Zero Regression Verification ──
        print("\n[TEST 6] Verifying Zero Regression on Nota Dinas & Modul Kajian...")
        # Nota Dinas
        nd_payload = {
            "kop_utama": "MARKAS BESAR ANGKATAN LAUT",
            "kop_sub": "SATUAN OPERASI SIBER",
            "nomor_surat": "B/ND-99/IV/2025/Satsiber",
            "kepada": "Kepala Pusat Siber Pertahanan",
            "dari": "Komandan Satuan Operasi Siber",
            "perihal": "Laporan Kesiapsiagaan Tim Tanggap Insiden",
            "dasar": "Surat Perintah Kasal Nomor Sprin/100/I/2025",
            "isi_ringkas": [
                {"teks": "Sehubungan dengan dasar di atas, dilaporkan kesiapan tim operasi siber."}
            ],
            "konten_custom": "Sehubungan dengan dasar di atas, dilaporkan kesiapan tim operasi siber dalam kondisi siaga penuh.",
            "nama_pejabat": "Kolonel Laut (E) Ahmad",
            "jabatan_pejabat": "Komandan Satker"
        }
        nd_res = await client.post("/generate-nota-dinas", json=nd_payload)
        assert nd_res.status_code == 200, f"Nota Dinas failed: {nd_res.text}"
        assert "download_url" in nd_res.json()

        # Kajian Dual-Mode (Telaahan Staf)
        kajian_payload = {
            "kategori": "TELAAHAN_STAF",
            "kop_utama": "PUSAT SIBER PERTAHANAN",
            "kop_satuan_bawah": "SATUAN BAWAH",
            "judul_atau_topik": "Optimalisasi Pengamanan Data Maritim",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Budi Santoso",
            "jabatan": "Perwira Staf",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "sections_custom": {
                "persoalan": "Peningkatan ancaman siber pada sistem informasi maritim.",
                "praanggapan": "Potensi insiden berulang jika pengamanan tidak dimutakhirkan.",
                "fakta": "Terjadi peningkatan probing dan eksploitasi celah keamanan.",
                "analisis": "Pembaruan infrastruktur firewall dan SOC meningkatkan resiliensi hingga 90%.",
                "kesimpulan": "Peremajaan firewall perimeter merupakan langkah prioritas mendesak.",
                "saran": "Disarankan pimpinan menyetujui pengadaan peremajaan perangkat keamanan."
            }
        }
        kajian_res = await client.post("/api/v1/kajian/generate", json=kajian_payload)
        assert kajian_res.status_code == 200, f"Kajian failed: {kajian_res.text}"
        assert kajian_res.json()["status"] == "success"
        print("[PASSED] TEST 6: Nota Dinas & Modul Kajian tetap berjalan stabil 100% tanpa regresi")

        print("\n=======================================================")
        print(">>> ALL 6 LAPJU E2E & REGRESSION TESTS PASSED 100%! <<<")
        print("=======================================================")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
