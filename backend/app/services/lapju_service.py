"""
Service Engine Modul Laporan Kemajuan (LAPJU) Belanja Modal Pengadaan Barang/Jasa TNI.
ARISITEKTUR: 100% DETERMINISTIK & ZERO-AI MANIPULATION.
Seluruh kalkulasi anggaran, nomor DIPA, nilai kontrak, serapan, persentase fisik/admin,
dan catatan tahapan dirender secara verbatim (data riil) tanpa modifikasi/augmentasi LLM
demi menjamin integritas audit dan akuntabilitas keuangan negara.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
from ..schemas.lapju import LapjuGenerateRequest, ItemKegiatanLapju, LapjuTotalsModel, JenisTandaTangan

def format_rupiah(amount: float) -> str:
    """
    Format nominal angka float ke representasi Rupiah resmi militer:
    Contoh: 1500000000 -> 1.500.000.000 (atau Rp 1.500.000.000,00)
    """
    if amount is None or amount == 0:
        return "0"
    # Format with thousand dots and optional decimal
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if formatted.endswith(",00"):
        return formatted[:-3]  # Return tanpa ,00 jika bilangan bulat
    return formatted

def format_rupiah_full(amount: float) -> str:
    """Format lengkap dengan prefix Rp."""
    if amount is None or amount == 0:
        return "Rp 0,00"
    formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Rp {formatted}"

def get_bulan_romawi(bulan_str: str) -> str:
    """Mengonversi nama bulan / angka bulan ke angka Romawi standar penomoran surat TNI."""
    bulan_mapping = {
        "januari": "I", "februari": "II", "maret": "III", "april": "IV",
        "mei": "V", "juni": "VI", "juli": "VII", "agustus": "VIII",
        "september": "IX", "oktober": "X", "november": "XI", "desember": "XII",
        "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI",
        "7": "VII", "8": "VIII", "9": "IX", "10": "X", "11": "XI", "12": "XII"
    }
    key = str(bulan_str).strip().lower()
    return bulan_mapping.get(key, "IV")

def calculate_lapju_data(req: LapjuGenerateRequest) -> Tuple[List[Dict[str, Any]], LapjuTotalsModel]:
    """
    Kalkulasi matematis deterministik sisa anggaran per item kegiatan dan rekapitulasi total keseluruhan.
    """
    processed_items: List[Dict[str, Any]] = []
    
    total_pagu = 0.0
    total_nilai_kontrak = 0.0
    total_anggaran_terserap = 0.0
    total_sisa_anggaran = 0.0
    sum_fisik = 0
    sum_admin = 0
    
    for idx, item in enumerate(req.items, 1):
        pagu = float(item.pagu_anggaran or 0.0)
        kontrak = float(item.nilai_kontrak or 0.0)
        terserap = float(item.anggaran_terserap or 0.0)
        
        # Sisa anggaran: Pagu dikurangi terserap. Nilai negatif (pembengkakan
        # anggaran) SENGAJA TIDAK di-clamp ke 0 - itu adalah temuan audit yang
        # harus tampak apa adanya di laporan, bukan disembunyikan.
        sisa = pagu - terserap

        fisik = int(item.persentase_fisik or 0)
        admin = int(item.persentase_admin or 0)
        
        total_pagu += pagu
        total_nilai_kontrak += kontrak
        total_anggaran_terserap += terserap
        total_sisa_anggaran += sisa
        sum_fisik += fisik
        sum_admin += admin
        
        processed_items.append({
            "no_urut": idx,
            "nomor_dipa": item.nomor_dipa,
            "tanggal_dipa": item.tanggal_dipa,
            "nama_kegiatan": item.nama_kegiatan,
            "pagu_anggaran": pagu,
            "pagu_anggaran_formatted": format_rupiah(pagu),
            "nilai_kontrak": kontrak,
            "nilai_kontrak_formatted": format_rupiah(kontrak) if kontrak > 0 else "-",
            "nomor_kontrak": item.nomor_kontrak or "-",
            "tanggal_kontrak": item.tanggal_kontrak or "-",
            "tds": item.tds or "-",
            "penyedia": item.penyedia or "-",
            "anggaran_terserap": terserap,
            "anggaran_terserap_formatted": format_rupiah(terserap) if terserap > 0 else "0",
            "sisa_anggaran": sisa,
            "sisa_anggaran_formatted": format_rupiah(sisa),
            "persentase_fisik": fisik,
            "persentase_admin": admin,
            "keterangan_admin": item.keterangan_admin or [],
            "keterangan_fisik": item.keterangan_fisik or []
        })
        
    n = len(req.items) if req.items else 1
    rata_fisik = round(sum_fisik / n, 2)
    rata_admin = round(sum_admin / n, 2)
    
    totals = LapjuTotalsModel(
        total_pagu=total_pagu,
        total_nilai_kontrak=total_nilai_kontrak,
        total_anggaran_terserap=total_anggaran_terserap,
        total_sisa_anggaran=total_sisa_anggaran,
        rata_rata_fisik=rata_fisik,
        rata_rata_admin=rata_admin,
        total_pagu_formatted=format_rupiah(total_pagu),
        total_nilai_kontrak_formatted=format_rupiah(total_nilai_kontrak),
        total_terserap_formatted=format_rupiah(total_anggaran_terserap),
        total_sisa_formatted=format_rupiah(total_sisa_anggaran)
    )
    
    return processed_items, totals

def prepare_lapju_template_data(req: LapjuGenerateRequest) -> Dict[str, Any]:
    """
    Menyiapkan context dictionary lengkap untuk rendering Jinja2 template Surat Pengantar & Lampiran Tabel.
    """
    processed_items, totals = calculate_lapju_data(req)
    
    romawi_bulan = get_bulan_romawi(req.bulan)
    nomor_surat = req.nomor_surat or f"B/   /{romawi_bulan}/{req.tahun}"
    tanggal_surat = req.tanggal_surat or f"{req.tempat},     {req.bulan} {req.tahun}"
    
    # Deteksi jenis tanda tangan
    is_mewakili = (req.jenis_ttd == JenisTandaTangan.MEWAKILI)
    
    return {
        "kop_utama": req.kop_utama,
        "kop_satker": req.kop_satker,
        "nomor_surat": nomor_surat,
        "tempat": req.tempat,
        "tanggal_surat": tanggal_surat,
        "bulan": req.bulan,
        "bulan_upper": req.bulan.upper(),
        "tahun": req.tahun,
        "klasifikasi": req.klasifikasi,
        "lampiran_keterangan": req.lampiran_keterangan,
        "perihal": req.perihal,
        "kepada_yth": req.kepada_yth,
        "kota_tujuan": req.kota_tujuan,
        "dasar_rujukan": req.dasar_rujukan,
        
        # Tanda Tangan
        "jabatan_penandatangan": req.jabatan_penandatangan,
        "is_mewakili": is_mewakili,
        "nama_penandatangan": req.nama_penandatangan,
        "pangkat_korps_nrp": req.pangkat_korps_nrp,
        
        # Tembusan & Paraf
        "tembusan": req.tembusan,
        "daftar_paraf": req.daftar_paraf or [],
        
        # Data Tabel & Rekap
        "items": processed_items,
        "totals": totals.dict(),
        "konten_custom": req.konten_custom
    }

def build_lapju_pasal_list(template_data: Dict[str, Any]) -> List[str]:
    """
    Dua pasal formal surat pengantar LAPJU (identik dengan branch baku template).
    Editor Android mengedit INI SAJA — bukan ringkasan KOP+rekap yang bila
    dikirim utuh sebagai konten_custom menggantikan pasal resmi di PDF.
    """
    return [
        (
            f"1.  Berdasarkan {template_data['dasar_rujukan']} tentang Laporan Kemajuan "
            f"Belanja Modal Pengadaan Barang/Jasa, bersama ini dikirimkan Laporan Kemajuan "
            f"Belanja Modal {template_data['kop_satker']} periode bulan {template_data['bulan']} "
            f"TA {template_data['tahun']} sebagaimana tabel terlampir."
        ),
        "2.  Demikian disampaikan mohon menjadi periksa.",
    ]


def format_lapju_summary_text(template_data: Dict[str, Any]) -> str:
    """Menyusun representasi teks ringkasan untuk draf editor."""
    ttd_label = f"{template_data['jabatan_penandatangan']}\nmewakili," if template_data.get('is_mewakili') else f"{template_data['jabatan_penandatangan']},"
    
    lines = [
        f"KOP: {template_data['kop_utama']} - {template_data['kop_satker']}",
        f"Nomor: {template_data['nomor_surat']} | Tanggal: {template_data['tanggal_surat']}",
        f"Kepada Yth: {template_data['kepada_yth']} di {template_data['kota_tujuan']}",
        f"Perihal: {template_data['perihal']}\n",
        f"1. Berdasarkan {template_data['dasar_rujukan']} tentang Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa, bersama ini dikirimkan Laporan Kemajuan Belanja Modal {template_data['kop_satker']} periode bulan {template_data['bulan']} TA {template_data['tahun']}.",
        "2. Demikian disampaikan mohon menjadi periksa.\n",
        f"--- REKAPITULASI BELANJA MODAL ---",
        f"Total Pagu Anggaran   : Rp {template_data['totals']['total_pagu_formatted']}",
        f"Total Nilai Kontrak   : Rp {template_data['totals']['total_nilai_kontrak_formatted']}",
        f"Total Realisasi Serap : Rp {template_data['totals']['total_terserap_formatted']}",
        f"Total Sisa Anggaran   : Rp {template_data['totals']['total_sisa_formatted']}",
        f"Rata-rata Fisik       : {template_data['totals']['rata_rata_fisik']}%",
        f"Rata-rata Administrasi: {template_data['totals']['rata_rata_admin']}%\n",
        f"{ttd_label}\n\n{template_data['nama_penandatangan']}\n{template_data['pangkat_korps_nrp']}"
    ]
    return "\n".join(lines)
