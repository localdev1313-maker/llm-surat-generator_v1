package com.pussiber.suratgenerator.data.model

import com.google.gson.annotations.SerializedName

data class PoinNotaDinasModel(
    @SerializedName("teks") val teks: String,
    @SerializedName("sub_poin") val subPoin: List<String>? = null
)

data class GenerateNotaDinasRequest(
    @SerializedName("kop_utama") val kopUtama: String = "PUSAT KOMANDO OPERASI",
    @SerializedName("kop_sub") val kopSub: String = "SATUAN BAWAH",
    @SerializedName("nomor_surat") val nomorSurat: String,
    @SerializedName("kepada") val kepada: String,
    @SerializedName("dari") val dari: String,
    @SerializedName("perihal") val perihal: String,
    @SerializedName("dasar") val dasar: String,
    @SerializedName("isi_ringkas") val isiRingkas: List<PoinNotaDinasModel>,
    // Pasal isi hasil edit pengguna (per-paragraf) — diprioritaskan backend
    // di atas isi_ringkas/konten_custom.
    @SerializedName("isi_custom_list") val isiCustomList: List<PoinNotaDinasModel>? = null,
    @SerializedName("konten_custom") val kontenCustom: String? = null,
    @SerializedName("nama_pejabat") val namaPejabat: String = "Budi Santoso, S.E., M.M.",
    @SerializedName("jabatan_pejabat") val jabatanPejabat: String = "Komandan Satuan Penindak",
    @SerializedName("pangkat_pejabat") val pangkatPejabat: String? = "Kolonel Laut (E) NRP 12345/P",
    @SerializedName("tembusan") val tembusan: List<String>? = null,
    @SerializedName("jenis_penutup") val jenisPenutup: String = "perhatian"
)

data class GenerateSuratUmumRequest(
    @SerializedName("jenis_surat") val jenisSurat: String = "resmi",
    @SerializedName("nama_pengirim") val namaPengirim: String,
    @SerializedName("alamat_pengirim") val alamatPengirim: String,
    @SerializedName("nama_penerima") val namaPenerima: String,
    @SerializedName("alamat_penerima") val alamatPenerima: String,
    @SerializedName("perihal") val perihal: String,
    @SerializedName("isi_ringkas") val isiRingkas: String,
    @SerializedName("konten_custom") val kontenCustom: String? = null
)

data class GenerateResponse(
    @SerializedName("id") val id: String,
    // Nullable dengan sengaja: endpoint telaahan-staf mengembalikan
    // "konten_gabungan" (bukan "konten_surat"). Gson melewati constructor
    // Kotlin — field non-null akan diam-diam bernilai null dan memicu NPE.
    @SerializedName("konten_surat") val kontenSurat: String? = null,
    @SerializedName("file_path") val filePath: String? = null,
    @SerializedName("download_url") val downloadUrl: String,
    // true = Ollama gagal/timeout, output memakai templat standar (bukan hasil AI)
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class DraftSuratResponse(
    @SerializedName("perihal") val perihal: String,
    @SerializedName("konten_draft") val kontenDraft: String,
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class DraftNotaDinasResponse(
    @SerializedName("perihal") val perihal: String,
    @SerializedName("nomor_surat") val nomorSurat: String,
    @SerializedName("dasar_list") val dasarList: List<String>,
    @SerializedName("isi_list") val isiList: List<PoinNotaDinasModel>,
    @SerializedName("konten_gabungan") val kontenGabungan: String,
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class HealthResponse(
    @SerializedName("status") val status: String,
    @SerializedName("version") val version: String
)

data class TelaahanStafPasalModel(
    @SerializedName("persoalan") val persoalan: String = "",
    @SerializedName("praanggapan") val praanggapan: String = "",
    @SerializedName("fakta") val fakta: String = "",
    @SerializedName("analisis") val analisis: String = "",
    @SerializedName("kesimpulan") val kesimpulan: String = "",
    @SerializedName("saran") val saran: String = ""
)

data class GenerateTelaahanStafRequest(
    @SerializedName("kop_utama") val kopUtama: String = "PUSAT KOMANDO OPERASI",
    @SerializedName("kop_satuan_bawah") val kopSatuanBawah: String = "SATUAN BAWAH",
    @SerializedName("judul") val judul: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String? = null,
    @SerializedName("input_persoalan") val inputPersoalan: String,
    @SerializedName("input_praanggapan") val inputPraanggapan: String? = null,
    @SerializedName("input_fakta") val inputFakta: String,
    @SerializedName("input_analisis") val inputAnalisis: String? = null,
    @SerializedName("input_kesimpulan") val inputKesimpulan: String? = null,
    @SerializedName("input_saran") val inputSaran: String,
    @SerializedName("tempat") val tempat: String = "Jakarta",
    @SerializedName("tanggal") val tanggal: String? = null,
    @SerializedName("nama_pejabat") val namaPejabat: String = "Budi Santoso, S.E., M.M.",
    @SerializedName("pangkat_korps_nrp") val pangkatKorpsNrp: String? = "Kolonel Laut (E) NRP 12345/P",
    @SerializedName("jabatan") val jabatan: String = "Komandan Satuan Penindak",
    @SerializedName("lampiran_list") val lampiranList: List<String>? = null,
    @SerializedName("konten_custom") val kontenCustom: String? = null,
    @SerializedName("pasal_custom") val pasalCustom: Map<String, String>? = null
)

data class DraftTelaahanStafResponse(
    @SerializedName("judul") val judul: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String?,
    @SerializedName("pasal") val pasal: TelaahanStafPasalModel,
    @SerializedName("konten_gabungan") val kontenGabungan: String,
    @SerializedName("lampiran_list") val lampiranList: List<String> = emptyList(),
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class RenderTelaahanStafPdfRequest(
    @SerializedName("kop_utama") val kopUtama: String = "PUSAT KOMANDO OPERASI",
    @SerializedName("kop_satuan_bawah") val kopSatuanBawah: String = "SATUAN BAWAH",
    @SerializedName("judul") val judul: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String? = null,
    @SerializedName("pasal") val pasal: TelaahanStafPasalModel,
    @SerializedName("tempat") val tempat: String = "Jakarta",
    @SerializedName("tanggal") val tanggal: String? = null,
    @SerializedName("nama_pejabat") val namaPejabat: String = "Budi Santoso, S.E., M.M.",
    @SerializedName("pangkat_korps_nrp") val pangkatKorpsNrp: String? = "Kolonel Laut (E) NRP 12345/P",
    @SerializedName("jabatan") val jabatan: String = "Komandan Satuan Penindak",
    @SerializedName("lampiran_list") val lampiranList: List<String>? = null,
    @SerializedName("konten_custom") val kontenCustom: String? = null
)

// ═══════════════════════════════════════════════════════════════════════════
// KAJIAN DUAL-MODE (TELAAHAN STAF & KKA SESKO)
// ═══════════════════════════════════════════════════════════════════════════

enum class KajianCategory {
    @SerializedName("TELAAHAN_STAF") TELAAHAN_STAF,
    @SerializedName("KKA_SESKOAL") KKA_SESKOAL
}

enum class KKAModelType {
    @SerializedName("STUDI_KASUS") STUDI_KASUS,
    @SerializedName("ANALISIS_MOE") ANALISIS_MOE,
    @SerializedName("PEMECAHAN_MASALAH") PEMECAHAN_MASALAH
}

data class KajianGenerateRequest(
    @SerializedName("kategori") val kategori: KajianCategory = KajianCategory.TELAAHAN_STAF,
    @SerializedName("kka_model") val kkaModel: KKAModelType? = null,
    @SerializedName("kop_utama") val kopUtama: String = "PUSAT KOMANDO OPERASI",
    @SerializedName("kop_satuan_bawah") val kopSatuanBawah: String = "SATUAN BAWAH",
    @SerializedName("judul_atau_topik") val judulAtauTopik: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String? = null,
    @SerializedName("tempat") val tempat: String = "Jakarta",
    @SerializedName("tanggal") val tanggal: String? = null,
    @SerializedName("nama_pejabat_atau_pasis") val namaPejabatAtauPasis: String = "Budi Santoso",
    @SerializedName("pangkat_korps_nrp") val pangkatKorpsNrp: String? = "Kolonel Laut (E) NRP 12345/P",
    @SerializedName("jabatan") val jabatan: String? = "Perwira Staf",
    @SerializedName("nomor_pasis") val nomorPasis: String? = null,
    @SerializedName("kelompok_pasis") val kelompokPasis: String? = null,
    @SerializedName("jenis_dan_tahun_pendidikan") val jenisDanTahunPendidikan: String? = null,
    @SerializedName("lampiran_list") val lampiranList: List<String>? = null,
    @SerializedName("konten_custom") val kontenCustom: String? = null,
    @SerializedName("sections_custom") val sectionsCustom: Map<String, Any>? = null,

    // Input fields per model
    @SerializedName("input_persoalan") val inputPersoalan: String? = null,
    @SerializedName("input_praanggapan") val inputPraanggapan: String? = null,
    @SerializedName("input_fakta") val inputFakta: String? = null,
    @SerializedName("input_analisis") val inputAnalisis: String? = null,
    @SerializedName("input_kesimpulan") val inputKesimpulan: String? = null,
    @SerializedName("input_saran") val inputSaran: String? = null,

    @SerializedName("input_kronologis_pra") val inputKronologisPra: String? = null,
    @SerializedName("input_kronologis_kejadian") val inputKronologisKejadian: String? = null,
    @SerializedName("input_kronologis_pasca") val inputKronologisPasca: String? = null,

    @SerializedName("input_alutsista_opsi_1") val inputAlutsistaOpsi1: String? = null,
    @SerializedName("input_alutsista_opsi_2") val inputAlutsistaOpsi2: String? = null,

    @SerializedName("input_pokok_masalah") val inputPokokMasalah: String? = null,
    @SerializedName("input_permasalahan_list") val inputPermasalahanList: List<String>? = null
)

data class KajianDraftResponse(
    @SerializedName("kategori") val kategori: KajianCategory,
    @SerializedName("kka_model") val kkaModel: KKAModelType?,
    @SerializedName("judul_atau_topik") val judulAtauTopik: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String?,
    @SerializedName("sections") val sections: Map<String, Any>,
    @SerializedName("konten_kajian") val kontenKajian: String,
    // Nullable: backend tidak pernah mengirim ketiganya — Gson bisa menyuntik
    // null lewat reflection ke field non-null Kotlin (NPE latent saat diakses).
    @SerializedName("daftar_pustaka") val daftarPustaka: List<String>? = null,
    @SerializedName("footnotes") val footnotes: List<String>? = null,
    @SerializedName("rag_references") val ragReferences: List<String>? = null,
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class KajianGenerateResponse(
    @SerializedName("status") val status: String = "success",
    @SerializedName("message") val message: String,
    @SerializedName("kategori") val kategori: KajianCategory,
    @SerializedName("kka_model") val kkaModel: KKAModelType?,
    @SerializedName("surat_id") val suratId: String,
    @SerializedName("download_url") val downloadUrl: String,
    @SerializedName("preview_pdf_url") val previewPdfUrl: String,
    @SerializedName("konten_kajian") val kontenKajian: String,
    @SerializedName("sections") val sections: Map<String, Any>,
    @SerializedName("rag_references") val ragReferences: List<String> = emptyList(),
    @SerializedName("llm_degraded") val llmDegraded: Boolean? = null
)

data class KajianRenderPDFRequest(
    @SerializedName("kategori") val kategori: KajianCategory = KajianCategory.TELAAHAN_STAF,
    @SerializedName("kka_model") val kkaModel: KKAModelType? = null,
    @SerializedName("kop_utama") val kopUtama: String = "PUSAT KOMANDO OPERASI",
    @SerializedName("kop_satuan_bawah") val kopSatuanBawah: String = "SATUAN BAWAH",
    @SerializedName("judul_atau_topik") val judulAtauTopik: String,
    @SerializedName("nomor_naskah") val nomorNaskah: String? = null,
    @SerializedName("tempat") val tempat: String = "Jakarta",
    @SerializedName("tanggal") val tanggal: String? = null,
    @SerializedName("nama_pejabat_atau_pasis") val namaPejabatAtauPasis: String = "Budi Santoso",
    @SerializedName("pangkat_korps_nrp") val pangkatKorpsNrp: String? = "Kolonel Laut (E) NRP 12345/P",
    @SerializedName("jabatan") val jabatan: String? = "Perwira Staf",
    @SerializedName("nomor_pasis") val nomorPasis: String? = null,
    @SerializedName("kelompok_pasis") val kelompokPasis: String? = null,
    @SerializedName("jenis_dan_tahun_pendidikan") val jenisDanTahunPendidikan: String? = null,
    @SerializedName("sections") val sections: Map<String, Any> = emptyMap(),
    @SerializedName("lampiran_list") val lampiranList: List<String>? = null,
    @SerializedName("konten_custom") val kontenCustom: String? = null
)

// ═══════════════════════════════════════════════════════════════════════════
// LAPORAN KEMAJUAN (LAPJU) BELANJA MODAL
// ═══════════════════════════════════════════════════════════════════════════

enum class JenisTandaTangan {
    @SerializedName("LANGSUNG") LANGSUNG,
    @SerializedName("MEWAKILI") MEWAKILI
}

data class ItemKegiatanLapju(
    @SerializedName("no_urut") val noUrut: Int = 1,
    @SerializedName("nomor_dipa") val nomorDipa: String = "SP DIPA-012.01.1.678901/2025",
    @SerializedName("tanggal_dipa") val tanggalDipa: String = "28 November 2024",
    @SerializedName("nama_kegiatan") val namaKegiatan: String,
    @SerializedName("pagu_anggaran") val paguAnggaran: Double,
    @SerializedName("nilai_kontrak") val nilaiKontrak: Double = 0.0,
    @SerializedName("nomor_kontrak") val nomorKontrak: String = "-",
    @SerializedName("tanggal_kontrak") val tanggalKontrak: String = "-",
    @SerializedName("tds") val tds: String = "-",
    @SerializedName("penyedia") val penyedia: String = "-",
    @SerializedName("anggaran_terserap") val anggaranTerserap: Double = 0.0,
    @SerializedName("sisa_anggaran") val sisaAnggaran: Double = 0.0,
    @SerializedName("persentase_fisik") val persentaseFisik: Int = 0,
    @SerializedName("persentase_admin") val persentaseAdmin: Int = 0,
    @SerializedName("keterangan_admin") val keteranganAdmin: List<String> = emptyList(),
    @SerializedName("keterangan_fisik") val keteranganFisik: List<String> = emptyList()
)

data class LapjuTotalsModel(
    @SerializedName("total_pagu") val totalPagu: Double = 0.0,
    @SerializedName("total_nilai_kontrak") val totalNilaiKontrak: Double = 0.0,
    @SerializedName("total_anggaran_terserap") val totalAnggaranTerserap: Double = 0.0,
    @SerializedName("total_sisa_anggaran") val totalSisaAnggaran: Double = 0.0,
    @SerializedName("rata_rata_fisik") val rataRataFisik: Double = 0.0,
    @SerializedName("rata_rata_admin") val rataRataAdmin: Double = 0.0,
    @SerializedName("total_pagu_formatted") val totalPaguFormatted: String = "Rp 0,00",
    @SerializedName("total_nilai_kontrak_formatted") val totalNilaiKontrakFormatted: String = "Rp 0,00",
    @SerializedName("total_terserap_formatted") val totalTerserapFormatted: String = "Rp 0,00",
    @SerializedName("total_sisa_formatted") val totalSisaFormatted: String = "Rp 0,00"
)

data class LapjuGenerateRequest(
    @SerializedName("kop_utama") val kopUtama: String = "MARKAS BESAR ANGKATAN LAUT",
    @SerializedName("kop_satker") val kopSatker: String = "DINAS PENGADAAN ANGKATAN LAUT",
    @SerializedName("nomor_surat") val nomorSurat: String? = null,
    @SerializedName("tempat") val tempat: String = "Jakarta",
    @SerializedName("tanggal_surat") val tanggalSurat: String? = null,
    @SerializedName("bulan") val bulan: String = "April",
    @SerializedName("tahun") val tahun: Int = 2025,
    @SerializedName("klasifikasi") val klasifikasi: String = "Biasa",
    @SerializedName("lampiran_keterangan") val lampiranKeterangan: String = "Dua lembar",
    @SerializedName("perihal") val perihal: String = "Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa",
    @SerializedName("kepada_yth") val kepadaYth: String = "Asisten Logistik Kasal",
    @SerializedName("kota_tujuan") val kotaTujuan: String = "Jakarta",
    @SerializedName("dasar_rujukan") val dasarRujukan: String = "Surat Perintah Kasal Nomor Sprin/123/I/2025 tanggal 10 Januari 2025",
    @SerializedName("jabatan_penandatangan") val jabatanPenandatangan: String = "Kepala Dinas Pengadaan Angkatan Laut",
    @SerializedName("jenis_ttd") val jenisTtd: JenisTandaTangan = JenisTandaTangan.MEWAKILI,
    @SerializedName("nama_penandatangan") val namaPenandatangan: String = "Budi Santoso, S.E., M.M.",
    @SerializedName("pangkat_korps_nrp") val pangkatKorpsNrp: String = "Laksamana Pertama TNI NRP 12345/P",
    @SerializedName("tembusan") val tembusan: List<String> = listOf(
        "Kepala Staf Angkatan Laut",
        "Wakil Kepala Staf Angkatan Laut",
        "Inspektur Jenderal Angkatan Laut",
        "Asisten Perencanaan dan Anggaran Kasal"
    ),
    @SerializedName("items") val items: List<ItemKegiatanLapju>,
    @SerializedName("konten_custom") val kontenCustom: String? = null
)

data class LapjuDraftResponse(
    @SerializedName("status") val status: String = "success",
    @SerializedName("nomor_surat") val nomorSurat: String,
    @SerializedName("tanggal_surat") val tanggalSurat: String,
    @SerializedName("ringkasan_teks") val ringkasanTeks: String,
    // Dua pasal formal surat pengantar — yang diedit & dicetak HANYA ini.
    @SerializedName("pasal_list") val pasalList: List<String> = emptyList(),
    @SerializedName("totals") val totals: LapjuTotalsModel,
    @SerializedName("items_processed") val itemsProcessed: List<Map<String, Any>> = emptyList()
)

data class LapjuGenerateResponse(
    @SerializedName("status") val status: String = "success",
    @SerializedName("message") val message: String,
    @SerializedName("id") val id: String,
    @SerializedName("surat_id") val suratId: String,
    @SerializedName("nomor_surat") val nomorSurat: String,
    @SerializedName("file_path") val filePath: String,
    @SerializedName("download_url") val downloadUrl: String,
    @SerializedName("preview_pdf_url") val previewPdfUrl: String,
    @SerializedName("totals") val totals: LapjuTotalsModel
)


