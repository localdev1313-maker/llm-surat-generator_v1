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

async def run_tests():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        print("[1/4] Testing Health Check...")
        res = await client.get("/api/health")
        assert res.status_code == 200
        print("  -> Status:", res.json())

        print("[2/4] Testing POST /draft-telaahan-staf...")
        payload = {
            "kop_utama": "PUSAT KOMANDO OPERASI",
            "kop_satuan_bawah": "SATUAN PENGAMANAN OPERASI",
            "judul": "PENGUATAN KEAMANAN SISTEM PADA PUSAT DATA OPERASIONAL",
            "nomor_naskah": "Nomor TS/01/V/2026",
            "input_persoalan": "Peningkatan intensitas ancaman gangguan sistem jenis ransomware pada server operasional satuan.",
            "input_fakta": "Dalam triwulan I tahun 2026 tercatat 145 upaya intrusi berbahaya dan utilisasi firewall mencapai 94%.",
            "input_saran": "Pengadaan Next-Generation Firewall dan pelatihan Incident Response terpadu.",
            "nama_pejabat": "Budi Santoso",
            "jabatan": "Perwira Staf",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "lampiran_list": ["Tabel Analisis Ancaman", "Rencana Kebutuhan Anggaran"]
        }
        draft_res = await client.post("/draft-telaahan-staf", json=payload)
        assert draft_res.status_code == 200
        draft_data = draft_res.json()
        print("  -> Draft Judul:", draft_data.get("judul"))
        print("  -> Draft Nomor:", draft_data.get("nomor_naskah"))
        pasal = draft_data.get("pasal", {})
        for k in ["persoalan", "praanggapan", "fakta", "analisis", "kesimpulan", "saran"]:
            assert k in pasal and len(pasal[k]) > 10, f"Missing or empty section {k}"
            print(f"  -> Pasal {k.capitalize()}: {pasal[k][:70]}...")

        print("[3/4] Testing POST /generate-telaahan-staf...")
        gen_res = await client.post("/generate-telaahan-staf", json=payload)
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        print("  -> Generated ID:", gen_data.get("id"))
        print("  -> Download URL:", gen_data.get("download_url"))
        pdf_path = Path(gen_data.get("file_path"))
        assert pdf_path.exists(), "PDF file must exist"
        print(f"  -> PDF File on disk: {pdf_path.name} ({pdf_path.stat().st_size} bytes)")

        print("[4/4] Testing PDF Download...")
        dl_res = await client.get(gen_data.get("download_url"))
        assert dl_res.status_code == 200
        assert dl_res.headers.get("content-type") == "application/pdf"
        assert len(dl_res.content) > 5000
        print(f"  -> Downloaded PDF bytes: {len(dl_res.content)}")

        print("\n*** ALL BACKEND TELAAHAN STAF TESTS PASSED SUCCESSFULLY! ***")

if __name__ == "__main__":
    asyncio.run(run_tests())
