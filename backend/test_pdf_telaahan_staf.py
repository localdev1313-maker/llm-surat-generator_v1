import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.services.pdf_service import create_pdf_telaahan_staf
from app.config import settings

def test_pdf():
    now = datetime.now()
    bulan_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    tanggal_ttd = f"Jakarta, {now.day} {bulan_id[now.month - 1]} {now.year}"

    template_data = {
        "kop_utama": "PUSAT KOMANDO OPERASI",
        "kop_satuan_bawah": "SATUAN PENGAMANAN OPERASI",
        "judul": "PENGUATAN KEAMANAN SISTEM PADA PUSAT DATA OPERASIONAL",
        "nomor_naskah": "Nomor TS/01/V/2026",
        "pasal": {
            "persoalan": "Kebutuhan perumusan langkah strategis dan terpadu dalam mengatasi peningkatan intensitas gangguan sistem operasional jenis ransomware pada server operasional satuan guna menjamin kelancaran pelaksanaan tugas pokok satuan secara optimal.",
            "praanggapan": "Dukungan alokasi sumber daya yang memadai, penguatan regulasi operasional, serta sinergi antarunsur terkait diyakini mampu mengakselerasi penyelesaian persoalan dan meminimalisasi potensi hambatan di masa mendatang.",
            "fakta": "Berdasarkan data dan evaluasi di lapangan, kondisi saat ini menunjukkan bahwa dalam triwulan I tahun 2026 tercatat 145 upaya intrusi berbahaya, dan utilisasi kapasitas firewall eksisting telah mencapai 94%. Kondisi ini secara langsung memengaruhi efektivitas pelaksanaan tugas kedinasan.",
            "analisis": "Melalui penelaahan mendalam terhadap fakta yang ada, keterbatasan yang dihadapi dapat diatasi melalui penerapan langkah terstruktur dan terukur. Alternatif tindakan ini memberikan keuntungan signifikan berupa efisiensi waktu, optimalisasi sumber daya yang ada, serta memitigasi risiko disrupsi operasional, meskipun memerlukan koordinasi intensif pada tahap awal implementasi.",
            "kesimpulan": "Berdasarkan hasil analisis terhadap persoalan dan fakta yang ada, disimpulkan bahwa penerapan langkah pengadaan perangkat Next-Generation Firewall dan pelatihan personel pengawak merupakan cara bertindak terbaik yang paling efektif, efisien, dan realistis untuk menyelesaikan permasalahan secara menyeluruh.",
            "saran": "Sebagai langkah tindak lanjut dalam mengatasi persoalan yang dihadapi, disarankan kepada pimpinan untuk menyetujui pengadaan Next-Generation Firewall (NGFW) dan menyelenggarakan pelatihan Incident Response terpadu."
        },
        "tanggal_ttd": tanggal_ttd,
        "nama_pejabat": "Budi Santoso",
        "jabatan_pejabat": "Perwira Staf",
        "pangkat_pejabat": "Kolonel Laut (E) NRP 12345/P",
        "lampiran_list": ["Tabel Analisis Ancaman", "Rencana Kebutuhan Anggaran"]
    }

    out_path = settings.OUTPUT_DIR / "test_telaahan_staf_direct.pdf"
    create_pdf_telaahan_staf(template_data, out_path)
    print(f"✅ Telaahan Staf PDF generated successfully at: {out_path} (Size: {out_path.stat().st_size} bytes)")
    assert out_path.exists()
    assert out_path.stat().st_size > 5000

if __name__ == "__main__":
    test_pdf()
