import sys
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import httpx
from app.main import app

async def test_full_telaahan_staf_pipeline():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        print("\n--- 1. Testing Health & API Routes ---")
        res = await client.get("/api/health")
        print(f"Health status: {res.status_code}, data: {res.json()}")
        assert res.status_code == 200

        print("\n--- 2. Testing POST /draft-telaahan-staf ---")
        draft_payload = {
            "kop_utama": "PUSAT KOMANDO OPERASI",
            "kop_satuan_bawah": "SATUAN PENGAMANAN OPERASI",
            "judul": "PENGUATAN KEAMANAN SISTEM PADA PUSAT DATA OPERASIONAL",
            "nomor_naskah": "Nomor TS/01/V/2026",
            "input_persoalan": "Meningkatnya intensitas gangguan sistem operasional jenis ransomware pada server operasional satuan yang berpotensi melumpuhkan sistem komando dan kendali.",
            "input_fakta": "Dalam triwulan I tahun 2026 tercatat 145 upaya intrusi berbahaya, dan utilisasi kapasitas firewall eksisting telah mencapai 94%.",
            "input_saran": "Perlu segera dilaksanakan pengadaan Next-Generation Firewall (NGFW) dan pelatihan Incident Response bagi personel pengawak.",
            "nama_pejabat": "Budi Santoso",
            "jabatan": "Perwira Staf",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "lampiran_list": ["Tabel Analisis Ancaman", "Rencana Kebutuhan Anggaran"]
        }

        draft_res = await client.post("/draft-telaahan-staf", json=draft_payload)
        print(f"Draft Response Code: {draft_res.status_code}")
        assert draft_res.status_code == 200
        draft_data = draft_res.json()
        print(f"Draft Judul: {draft_data.get('judul')}")
        print(f"Draft Nomor: {draft_data.get('nomor_naskah')}")
        print("Pasal Persoalan:", draft_data.get("pasal", {}).get("persoalan")[:100], "...")
        print("Pasal Praanggapan:", draft_data.get("pasal", {}).get("praanggapan")[:100], "...")
        print("Pasal Fakta:", draft_data.get("pasal", {}).get("fakta")[:100], "...")
        print("Pasal Analisis:", draft_data.get("pasal", {}).get("analisis")[:100], "...")
        print("Pasal Kesimpulan:", draft_data.get("pasal", {}).get("kesimpulan")[:100], "...")
        print("Pasal Saran:", draft_data.get("pasal", {}).get("saran")[:100], "...")
        assert "persoalan" in draft_data.get("pasal", {})
        assert "praanggapan" in draft_data.get("pasal", {})
        assert "fakta" in draft_data.get("pasal", {})
        assert "analisis" in draft_data.get("pasal", {})
        assert "kesimpulan" in draft_data.get("pasal", {})
        assert "saran" in draft_data.get("pasal", {})

        print("\n--- 3. Testing POST /generate-telaahan-staf ---")
        gen_res = await client.post("/generate-telaahan-staf", json=draft_payload)
        print(f"Generate Response Code: {gen_res.status_code}")
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        print("Generate ID:", gen_data.get("id"))
        print("PDF File Path:", gen_data.get("file_path"))
        print("Download URL:", gen_data.get("download_url"))
        assert Path(gen_data.get("file_path")).exists(), "PDF file must exist on disk"

        print("\n--- 4. Testing PDF Download Endpoint ---")
        download_res = await client.get(gen_data.get("download_url"))
        print(f"Download Status: {download_res.status_code}, Content-Type: {download_res.headers.get('content-type')}")
        assert download_res.status_code == 200
        assert download_res.headers.get("content-type") == "application/pdf"
        assert len(download_res.content) > 1000

        print("\n--- 5. Testing POST /render-telaahan-staf-pdf ---")
        render_payload = {
            "kop_utama": "PUSAT KOMANDO OPERASI",
            "kop_satuan_bawah": "SATUAN PENGAMANAN OPERASI",
            "judul": "PENGUATAN KEAMANAN SISTEM PADA PUSAT DATA OPERASIONAL",
            "nomor_naskah": "Nomor TS/01/V/2026",
            "pasal": draft_data.get("pasal"),
            "tempat": "Jakarta",
            "nama_pejabat": "Budi Santoso",
            "jabatan": "Perwira Staf",
            "pangkat_korps_nrp": "Kolonel Laut (E) NRP 12345/P",
            "lampiran_list": ["Tabel Analisis Ancaman", "Rencana Kebutuhan Anggaran"]
        }
        render_res = await client.post("/render-telaahan-staf-pdf", json=render_payload)
        print(f"Render PDF Response Code: {render_res.status_code}")
        assert render_res.status_code == 200
        render_data = render_res.json()
        assert Path(render_data.get("file_path")).exists()

        print("\n✅ ALL END-TO-END TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_full_telaahan_staf_pipeline())
