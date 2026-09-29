"""
Comprehensive End-to-End Verification Test for SSEB AI "Modul Kajian Dual-Mode"
Tests:
1. POST /api/v1/kajian/draft (TELAAHAN_STAF)
2. POST /api/v1/kajian/generate (TELAAHAN_STAF - KEP/868 Contoh 26)
3. POST /api/v1/kajian/generate (KKA_SESKOAL - Model A Studi Kasus OMSP)
4. POST /api/v1/kajian/generate (KKA_SESKOAL - Model B Analisis MoE)
5. POST /api/v1/kajian/generate (KKA_SESKOAL - Model C Pemecahan Masalah SOM)
6. POST /api/v1/kajian/render-pdf (Edit Re-render)
7. POST /generate-nota-dinas (Regression check)
8. Download PDF verification
"""

import sys
import os
import asyncio
from pathlib import Path
import httpx

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import app

async def run_all_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        print("=== STARTING COMPREHENSIVE DUAL-MODE KAJIAN E2E TESTS ===")

        # Test 1: Draft Telaahan Staf
        payload_1 = {
            "kategori": "TELAAHAN_STAF",
            "kop_utama": "PUSAT SIBER PERTAHANAN",
            "kop_satuan_bawah": "SATUAN OPERASI SIBER",
            "judul_atau_topik": "PENGUATAN SISTEM PERTAHANAN SIBER OPERASIONAL",
            "nomor_naskah": "Nomor TS/01/VIII/2026",
            "input_persoalan": "Peningkatan frekuensi serangan siber lanjutan (APT) pada jaringan komando dan kendali.",
            "input_fakta": "Terjadi 250 upaya anomali trafik per hari dan kapasitas firewall perimeter mendekati 90%.",
            "input_saran": "Implementasi sistem Next-Generation SIEM dan peningkatan kapasitas SOC 24/7.",
            "nama_pejabat_atau_pasis": "Budi Santoso",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "jabatan": "Perwira Staf"
        }
        res_1 = await client.post("/api/v1/kajian/draft", json=payload_1)
        assert res_1.status_code == 200, f"Draft TS failed: {res_1.text}"
        data_1 = res_1.json()
        assert data_1["kategori"] == "TELAAHAN_STAF"
        assert "sections" in data_1
        assert "persoalan" in data_1["sections"]
        assert "analisis" in data_1["sections"]
        assert "kesimpulan" in data_1["sections"]
        assert len(data_1["konten_kajian"]) > 100
        print("[PASS] Test 01: Draft Telaahan Staf successful.")

        # Test 2: Generate Telaahan Staf PDF
        payload_2 = {
            "kategori": "TELAAHAN_STAF",
            "kop_utama": "PUSAT SIBER PERTAHANAN",
            "kop_satuan_bawah": "SATUAN OPERASI SIBER",
            "judul_atau_topik": "PENGUATAN SISTEM PERTAHANAN SIBER OPERASIONAL",
            "nomor_naskah": "Nomor TS/01/VIII/2026",
            "input_persoalan": "Peningkatan frekuensi serangan siber lanjutan (APT) pada jaringan komando dan kendali.",
            "input_fakta": "Terjadi 250 upaya anomali trafik per hari dan kapasitas firewall perimeter mendekati 90%.",
            "input_saran": "Implementasi sistem Next-Generation SIEM dan peningkatan kapasitas SOC 24/7.",
            "nama_pejabat_atau_pasis": "Budi Santoso",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "jabatan": "Perwira Staf",
            "lampiran_list": ["Tabel Matriks Analisis Solusi Cyber Defense"]
        }
        res_2 = await client.post("/api/v1/kajian/generate", json=payload_2)
        assert res_2.status_code == 200, f"Generate TS failed: {res_2.text}"
        data_2 = res_2.json()
        assert data_2["status"] == "success"
        assert data_2["kategori"] == "TELAAHAN_STAF"
        assert "download_url" in data_2

        dl_res_2 = await client.get(data_2["download_url"])
        assert dl_res_2.status_code == 200
        assert dl_res_2.headers.get("content-type") == "application/pdf"
        assert len(dl_res_2.content) > 1000
        print(f"[PASS] Test 02: Generate Telaahan Staf PDF successful ({len(dl_res_2.content)} bytes).")

        # Test 3: Generate KKA Model A Studi Kasus
        payload_3 = {
            "kategori": "KKA_SESKOAL",
            "kka_model": "STUDI_KASUS",
            "kop_utama": "SEKOLAH STAF DAN KOMANDO TNI AL",
            "kop_satuan_bawah": "DEPARTEMEN ILMU PENGETAHUAN DAN TEKNOLOGI",
            "judul_atau_topik": "STUDI KASUS OPERASI SAR BENCANA TSUNAMI SELAT SUNDA OLEH TNI AL",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Arya Pratama",
            "pangkat_korps_nrp": "Mayor Laut (P) NRP 18900/P",
            "nomor_pasis": "No. Pasis 59-045",
            "kelompok_pasis": "Kelompok 2",
            "jenis_dan_tahun_pendidikan": "PASIS DIKREG SESKOAL ANGKATAN KE-59 TP 2021",
            "input_kronologis_pra": "Aktivitas vulkanik Gunung Anak Krakatau meningkat dan peringatan dini gelombang tinggi dikeluarkan.",
            "input_kronologis_kejadian": "Tsunami menghantam pesisir Banten dan Lampung Selatan; Lanal Banten segera mengerahkan KAL dan tim SAR Marinir.",
            "input_kronologis_pasca": "Evakuasi korban selamat, penyaluran logistik kesehatan, dan pemulihan jalur laut selesai.",
            "input_saran": "Perlunya pembentukan Satgas Cepat Tanggap Bencana Maritim terpadu berbasis komando gabungan."
        }
        res_3 = await client.post("/api/v1/kajian/generate", json=payload_3)
        assert res_3.status_code == 200, f"Generate KKA Model A failed: {res_3.text}"
        data_3 = res_3.json()
        assert data_3["status"] == "success"
        assert data_3["kategori"] == "KKA_SESKOAL"
        assert data_3["kka_model"] == "STUDI_KASUS"
        assert "download_url" in data_3

        dl_res_3 = await client.get(data_3["download_url"])
        assert dl_res_3.status_code == 200
        assert dl_res_3.headers.get("content-type") == "application/pdf"
        assert len(dl_res_3.content) > 1000
        print(f"[PASS] Test 03: Generate KKA Model A Studi Kasus PDF successful ({len(dl_res_3.content)} bytes).")

        # Test 4: Generate KKA Model B Analisis MoE
        payload_4 = {
            "kategori": "KKA_SESKOAL",
            "kka_model": "ANALISIS_MOE",
            "kop_utama": "SEKOLAH STAF DAN KOMANDO TNI AL",
            "kop_satuan_bawah": "DEPARTEMEN ILMU PENGETAHUAN DAN TEKNOLOGI",
            "judul_atau_topik": "ANALISIS PENGAMBILAN KEPUTUSAN PENGADAAN ALUTSISTA PATROLI MARITIM WILAYAH ALKI",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Dwi Hendrawan",
            "pangkat_korps_nrp": "Mayor Laut (T) NRP 19230/P",
            "nomor_pasis": "No. Pasis 59-078",
            "kelompok_pasis": "Kelompok 3",
            "jenis_dan_tahun_pendidikan": "PASIS DIKREG SESKOAL ANGKATAN KE-59 TP 2021",
            "input_alutsista_opsi_1": "Kapal Patroli Cepat (KPC 40M)",
            "input_alutsista_opsi_2": "Pesawat Patroli Maritim (MPA CN-235)",
            "input_fakta": "Kebutuhan peningkatan cakupan pengawasan di Selat Sunda dan Selat Lombok menghadapi peningkatan lalu lintas pelayaran internasional.",
            "input_saran": "Memprioritaskan pengadaan Pesawat Patroli Maritim (MPA) didukung integrasi data link ke KRI kombatan."
        }
        res_4 = await client.post("/api/v1/kajian/generate", json=payload_4)
        assert res_4.status_code == 200, f"Generate KKA Model B failed: {res_4.text}"
        data_4 = res_4.json()
        assert data_4["status"] == "success"
        assert data_4["kategori"] == "KKA_SESKOAL"
        assert data_4["kka_model"] == "ANALISIS_MOE"
        assert "download_url" in data_4

        dl_res_4 = await client.get(data_4["download_url"])
        assert dl_res_4.status_code == 200
        assert dl_res_4.headers.get("content-type") == "application/pdf"
        assert len(dl_res_4.content) > 1000
        print(f"[PASS] Test 04: Generate KKA Model B Analisis MoE PDF successful ({len(dl_res_4.content)} bytes).")

        # Test 5: Generate KKA Model C Pemecahan Masalah SOM
        payload_5 = {
            "kategori": "KKA_SESKOAL",
            "kka_model": "PEMECAHAN_MASALAH",
            "kop_utama": "SEKOLAH STAF DAN KOMANDO TNI AL",
            "kop_satuan_bawah": "DEPARTEMEN ILMU PENGETAHUAN DAN TEKNOLOGI",
            "judul_atau_topik": "OPTIMALISASI KEMAMPUAN PERANG ELEKTRONIKA KRI DALAM MENDUKUNG OPERASI LAUT",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Eko Prasetyo",
            "pangkat_korps_nrp": "Mayor Laut (E) NRP 19560/P",
            "nomor_pasis": "No. Pasis 59-112",
            "kelompok_pasis": "Kelompok 4",
            "jenis_dan_tahun_pendidikan": "PASIS DIKREG SESKOAL ANGKATAN KE-59 TP 2021",
            "input_pokok_masalah": "Kesenjangan kapabilitas deteksi dan jamming elektronika KRI terhadap ancaman radar rudal generasi baru.",
            "input_permasalahan_list": [
                "Kualitas SDM teknis peperangan elektronika masih memerlukan sertifikasi lanjutan.",
                "Dukungan peralatan sensor ESM dan ECM pada armada KRI belum terstandardisasi merata.",
                "Doktrin dan interoperabilitas data perang elektronika antar matra belum terintegrasi penuh."
            ],
            "input_saran": "Percepatan modernisasi modul ESM terintegrasi dan pembentukan pusat latihan simulasi peperangan elektronika TNI AL."
        }
        res_5 = await client.post("/api/v1/kajian/generate", json=payload_5)
        assert res_5.status_code == 200, f"Generate KKA Model C failed: {res_5.text}"
        data_5 = res_5.json()
        assert data_5["status"] == "success"
        assert data_5["kategori"] == "KKA_SESKOAL"
        assert data_5["kka_model"] == "PEMECAHAN_MASALAH"
        assert "download_url" in data_5

        dl_res_5 = await client.get(data_5["download_url"])
        assert dl_res_5.status_code == 200
        assert dl_res_5.headers.get("content-type") == "application/pdf"
        assert len(dl_res_5.content) > 1000
        print(f"[PASS] Test 05: Generate KKA Model C Pemecahan Masalah PDF successful ({len(dl_res_5.content)} bytes).")

        # Test 6: Render PDF Custom Edit
        payload_6 = {
            "kategori": "TELAAHAN_STAF",
            "kop_utama": "PUSAT SIBER PERTAHANAN",
            "kop_satuan_bawah": "SATUAN OPERASI SIBER",
            "judul_atau_topik": "TELAAHAN STAF HASIL EDIT MANUAL",
            "nomor_naskah": "Nomor TS/99/VIII/2026",
            "tempat": "Jakarta",
            "nama_pejabat_atau_pasis": "Budi Santoso",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "jabatan": "Perwira Staf",
            "konten_custom": "Teks naskah telaahan staf yang telah diedit secara manual oleh pengguna.",
            "sections": {
                "persoalan": "Persoalan khusus hasil penyesuaian staf.",
                "praanggapan": "Praanggapan strategis yang disesuaikan.",
                "fakta": "Fakta intelijen terbaru.",
                "analisis": "Analisis mendalam alternatif tindakan.",
                "kesimpulan": "Kesimpulan tunggal cara bertindak terbaik.",
                "saran": "Saran implementasi segera."
            }
        }
        res_6 = await client.post("/api/v1/kajian/render-pdf", json=payload_6)
        assert res_6.status_code == 200, f"Render PDF failed: {res_6.text}"
        data_6 = res_6.json()
        assert data_6["status"] == "success"
        assert "download_url" in data_6
        print("[PASS] Test 06: Render PDF Custom Edit successful.")

        # Test 7: Regression Check Nota Dinas
        payload_7 = {
            "kop_utama": "PUSAT SIBER PERTAHANAN",
            "kop_sub": "SATUAN BAWAH",
            "nomor_surat": "B/ND-01/VIII/2026/Unit",
            "kepada": "Kepala Bagian Logistik",
            "dari": "Divisi Operasi Siber",
            "perihal": "Permohonan Dukungan Laptop Operasional",
            "dasar": "Peraturan Panglima TNI Nomor 1 Tahun 2022\nSurat Perintah Kepala Siber",
            "isi_ringkas_1": "Permohonan pengadaan 5 unit laptop operasional berspesifikasi tinggi.",
            "nama_pejabat": "Budi Santoso",
            "jabatan_pejabat": "Kadiv",
            "pangkat_pejabat": "Kolonel Laut (E) NRP 12345/P"
        }
        res_7 = await client.post("/generate-nota-dinas", json=payload_7)
        assert res_7.status_code == 200, f"Generate Nota Dinas failed: {res_7.text}"
        data_7 = res_7.json()
        assert "download_url" in data_7
        dl_res_7 = await client.get(data_7["download_url"])
        assert dl_res_7.status_code == 200
        assert len(dl_res_7.content) > 1000
        print(f"[PASS] Test 07: Nota Dinas regression check passed ({len(dl_res_7.content)} bytes).")

        print("=== ALL 7 E2E TESTS PASSED WITH 100% SUCCESS RATE ===")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
