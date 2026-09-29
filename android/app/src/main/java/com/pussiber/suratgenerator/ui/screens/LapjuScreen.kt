package com.pussiber.suratgenerator.ui.screens

import android.app.Activity
import android.content.Intent
import android.speech.RecognizerIntent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.pussiber.suratgenerator.data.model.*
import com.pussiber.suratgenerator.ui.theme.StatusError
import com.pussiber.suratgenerator.ui.theme.StatusSuccess
import com.pussiber.suratgenerator.ui.theme.StatusWarning

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LapjuScreen(
    modifier: Modifier = Modifier,
    onGenerateLapju: (LapjuGenerateRequest) -> Unit,
    onDraftLapju: (LapjuGenerateRequest) -> Unit,
    draftState: com.pussiber.suratgenerator.DraftUiState? = null,
    onDraftDismiss: () -> Unit = {},
    onDraftTextChange: (String) -> Unit = {},
    isLoading: Boolean = false
) {
    val context = LocalContext.current

    // Kop & Metadata
    var kopUtama by remember { mutableStateOf("MARKAS BESAR ANGKATAN LAUT") }
    var kopSatker by remember { mutableStateOf("DINAS PENGADAAN ANGKATAN LAUT") }
    var nomorSurat by remember { mutableStateOf("B/   /IV/2025") }
    var tempat by remember { mutableStateOf("Jakarta") }
    var bulan by remember { mutableStateOf("April") }
    var tahun by remember { mutableStateOf("2025") }
    var klasifikasi by remember { mutableStateOf("Biasa") }
    var lampiranKet by remember { mutableStateOf("Dua lembar") }
    var perihal by remember { mutableStateOf("Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa") }
    var kepadaYth by remember { mutableStateOf("Asisten Logistik Kasal") }
    var kotaTujuan by remember { mutableStateOf("Jakarta") }
    var dasarRujukan by remember { mutableStateOf("Surat Perintah Kasal Nomor Sprin/123/I/2025 tanggal 10 Januari 2025") }

    // Penandatangan & Jenis TTD
    var jenisTtd by remember { mutableStateOf(JenisTandaTangan.MEWAKILI) }
    var jabatanPenandatangan by remember { mutableStateOf("Kepala Dinas Pengadaan Angkatan Laut") }
    var namaPenandatangan by remember { mutableStateOf("Budi Santoso, S.E., M.M.") }
    var pangkatKorpsNrp by remember { mutableStateOf("Laksamana Pertama TNI NRP 12345/P") }

    // Speech to Text (STT) Target Callback
    // Speech-to-Text bersama (helper ui/common/SttController.kt)
    val stt = com.pussiber.suratgenerator.ui.common.rememberSttController(
        onUnsupported = { Toast.makeText(context, "Speech-to-Text tidak didukung pada perangkat ini", Toast.LENGTH_SHORT).show() }
    )

    // Daftar Kegiatan Belanja Modal
    // ── Field numerik: teks mentah per (index, field) ──
    // Sebelumnya value TextField dihitung dari Double sehingga mengetik terasa
    // "rusak": menghapus seluruh isi langsung kembali ke "0", nol depan hilang,
    // dan ketikan parsial ("1.", "0") ditolak. Teks disimpan apa adanya di sini;
    // model hanya menerima angka yang valid.
    val numericDrafts = remember { mutableStateMapOf<String, String>() }

    fun numericText(key: String, value: Double): String =
        numericDrafts[key] ?: if (value == 0.0) "" else value.toLong().toString()

    fun onNumericChange(key: String, raw: String, commit: (Double) -> Unit) {
        val digits = raw.filter { it.isDigit() }.take(15)
        numericDrafts[key] = digits
        commit(digits.toDoubleOrNull() ?: 0.0)
    }

    /** Struktur daftar berubah (tambah/hapus) → indeks bergeser, buang cache teks. */
    fun resetNumericDrafts() = numericDrafts.clear()

    var itemsList by remember {
        mutableStateOf(
            listOf(
                ItemKegiatanLapju(
                    noUrut = 1,
                    nomorDipa = "SP DIPA-012.01.1.678901/2025",
                    tanggalDipa = "28 November 2024",
                    namaKegiatan = "Pengadaan Multi-Role Tactical Server Unit Satker",
                    paguAnggaran = 2500000000.0,
                    nilaiKontrak = 2450000000.0,
                    nomorKontrak = "KTR/01/II/2025",
                    tanggalKontrak = "15 Februari 2025",
                    tds = "30 Juni 2025",
                    penyedia = "PT Alkomindo Jaya Pertahanan",
                    anggaranTerserap = 735000000.0,
                    persentaseFisik = 40,
                    persentaseAdmin = 30,
                    keteranganAdmin = listOf("BAP Uang Muka 30% Terbit"),
                    keteranganFisik = listOf("Pengiriman komponen tahap 1 ke gudang satker")
                ),
                ItemKegiatanLapju(
                    noUrut = 2,
                    nomorDipa = "SP DIPA-012.01.1.678901/2025",
                    tanggalDipa = "28 November 2024",
                    namaKegiatan = "Modernisasi Modul Sensor Pemantau Maritim",
                    paguAnggaran = 3800000000.0,
                    nilaiKontrak = 3750000000.0,
                    nomorKontrak = "KTR/02/II/2025",
                    tanggalKontrak = "20 Februari 2025",
                    tds = "31 Agustus 2025",
                    penyedia = "PT Maritim Elektro Nusantara",
                    anggaranTerserap = 1125000000.0,
                    persentaseFisik = 35,
                    persentaseAdmin = 30,
                    keteranganAdmin = listOf("BAP Tahap 1 Selesai"),
                    keteranganFisik = listOf("Pabrikasi modul sensor 35%")
                )
            )
        )
    }

    // Tembusan
    var tembusanText by remember {
        mutableStateOf(
            "Kepala Staf Angkatan Laut\n" +
            "Wakil Kepala Staf Angkatan Laut\n" +
            "Inspektur Jenderal Angkatan Laut\n" +
            "Asisten Perencanaan dan Anggaran Kasal"
        )
    }

    // Dialog Pratinjau
    // Dialog Preview — STATE DIMILIKI VIEWMODEL (bertahan lintas tab & rotasi).
    val ds = draftState?.takeIf { it.type == com.pussiber.suratgenerator.DraftType.LAPJU }
    val isDraftLoading = ds?.isLoading == true
    val previewDraftText = ds?.text.orEmpty()
    val showPreviewDialog = ds != null && !ds.dismissed

    fun buildRequest(customContent: String? = null): LapjuGenerateRequest {
        val tembusanList = tembusanText.lines().map { it.trim() }.filter { it.isNotEmpty() }
        return LapjuGenerateRequest(
            kopUtama = kopUtama,
            kopSatker = kopSatker,
            nomorSurat = nomorSurat.ifBlank { null },
            tempat = tempat,
            bulan = bulan,
            tahun = tahun.toIntOrNull() ?: 2025,
            klasifikasi = klasifikasi,
            lampiranKeterangan = lampiranKet,
            perihal = perihal,
            kepadaYth = kepadaYth,
            kotaTujuan = kotaTujuan,
            dasarRujukan = dasarRujukan,
            jabatanPenandatangan = jabatanPenandatangan,
            jenisTtd = jenisTtd,
            namaPenandatangan = namaPenandatangan,
            pangkatKorpsNrp = pangkatKorpsNrp,
            tembusan = tembusanList,
            items = itemsList,
            kontenCustom = customContent
        )
    }

    // Kalkulasi Rekapitulasi Real-time
    val totalPagu = itemsList.sumOf { it.paguAnggaran }
    val totalKontrak = itemsList.sumOf { it.nilaiKontrak }
    val totalSerap = itemsList.sumOf { it.anggaranTerserap }
    // Overbudget (sisa negatif) SENGAJA TIDAK di-clamp ke 0 - harus terlihat
    // di rekap real-time agar konsisten dengan PDF resmi (backend juga tidak
    // lagi menyembunyikan pembengkakan anggaran, lihat lapju_service.py).
    val totalSisa = itemsList.sumOf { it.paguAnggaran - it.anggaranTerserap }
    val count = if (itemsList.isNotEmpty()) itemsList.size else 1
    val avgFisik = itemsList.sumOf { it.persentaseFisik } / count
    val avgAdmin = itemsList.sumOf { it.persentaseAdmin } / count

    fun formatRupiahShort(num: Double): String {
        return when {
            num >= 1_000_000_000 -> String.format("%.2f M", num / 1_000_000_000)
            num >= 1_000_000 -> String.format("%.1f Jt", num / 1_000_000)
            else -> String.format("%,.0f", num)
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // ── Header Card ──
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            shape = RoundedCornerShape(14.dp)
        ) {
            Row(
                modifier = Modifier.padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Assessment,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(32.dp)
                )
                Column {
                    Text(
                        text = "Laporan Kemajuan (LAPJU)",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Text(
                        text = "Mode Data Riil Verbatim (Non-AI) • Surat Pengantar A4 + Matriks 13 Kolom",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.85f)
                    )
                }
            }
        }

        // ── Tactical Live Metrics KPI Card ──
        Surface(
            color = MaterialTheme.colorScheme.surface,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = "REKAPITULASI ANGGARAN & PROGRES REAL-TIME",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(10.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Pagu
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            Text("Total Pagu", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Rp ${formatRupiahShort(totalPagu)}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                        }
                    }
                    // Terserap
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            Text("Terserap", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Rp ${formatRupiahShort(totalSerap)}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = StatusSuccess)
                        }
                    }
                    // Sisa
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            Text("Sisa", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Rp ${formatRupiahShort(totalSisa)}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold, color = StatusWarning)
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Fisik
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Row(modifier = Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Progres Fisik", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("${avgFisik}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                        }
                    }
                    // Admin
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.weight(1f)
                    ) {
                        Row(modifier = Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Progres Admin", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("${avgAdmin}%", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // ── 1. Kop & Metadata Satker ──
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "1. Kop & Metadata Surat Pengantar",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                OutlinedTextField(
                    value = kopUtama,
                    onValueChange = { kopUtama = it },
                    label = { Text("Kop Utama Satuan") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = kopSatker,
                    onValueChange = { kopSatker = it },
                    label = { Text("Kop Satker Pelaksana") },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = bulan,
                        onValueChange = { bulan = it },
                        label = { Text("Bulan Periode") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = tahun,
                        onValueChange = { tahun = it },
                        label = { Text("Tahun Anggaran") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.weight(1f)
                    )
                }
                OutlinedTextField(
                    value = nomorSurat,
                    onValueChange = { nomorSurat = it },
                    label = { Text("Nomor Surat Pengantar") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = dasarRujukan,
                    onValueChange = { dasarRujukan = it },
                    label = { Text("Dasar Rujukan Surat") },
                    trailingIcon = {
                        IconButton(onClick = { stt.launch { spoken -> dasarRujukan = if (dasarRujukan.isBlank()) spoken else "$dasarRujukan $spoken" } }) {
                            Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = kepadaYth,
                        onValueChange = { kepadaYth = it },
                        label = { Text("Kepada Yth.") },
                        modifier = Modifier.weight(1f)
                    )
                    OutlinedTextField(
                        value = kotaTujuan,
                        onValueChange = { kotaTujuan = it },
                        label = { Text("Kota Tujuan") },
                        modifier = Modifier.weight(1f)
                    )
                }
            }
        }

        // ── 2. Format Tanda Tangan & Penandatangan ──
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "2. Format Tanda Tangan & Penandatangan",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                Text(
                    text = "Pilih Versi Tajuk Tanda Tangan:",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                // Equal-Width Responsive Chips (NEVER Wraps Awkwardly)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = (jenisTtd == JenisTandaTangan.MEWAKILI),
                        onClick = { jenisTtd = JenisTandaTangan.MEWAKILI },
                        label = {
                            Text(
                                text = "Mewakili (mewakili,)",
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodySmall
                            )
                        },
                        modifier = Modifier.weight(1f)
                    )
                    FilterChip(
                        selected = (jenisTtd == JenisTandaTangan.LANGSUNG),
                        onClick = { jenisTtd = JenisTandaTangan.LANGSUNG },
                        label = {
                            Text(
                                text = "Langsung (Definitif)",
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodySmall
                            )
                        },
                        modifier = Modifier.weight(1f)
                    )
                }

                OutlinedTextField(
                    value = jabatanPenandatangan,
                    onValueChange = { jabatanPenandatangan = it },
                    label = { Text("Tajuk Jabatan Penandatangan") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = namaPenandatangan,
                    onValueChange = { namaPenandatangan = it },
                    label = { Text("Nama Lengkap & Gelar") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = pangkatKorpsNrp,
                    onValueChange = { pangkatKorpsNrp = it },
                    label = { Text("Pangkat, Korps, dan NRP") },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        // ── 3. Matriks Kegiatan Belanja Modal (Tabel 13 Kolom) ──
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "3. Matriks Belanja Modal (${itemsList.size} Kegiatan)",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    FilledTonalButton(
                        onClick = {
                            resetNumericDrafts()
                            val nextNo = itemsList.size + 1
                            itemsList = itemsList + ItemKegiatanLapju(
                                noUrut = nextNo,
                                nomorDipa = "SP DIPA-012.01.1.678901/2025",
                                tanggalDipa = "28 November 2024",
                                namaKegiatan = "Pengadaan Sarpras / Alutsista Paket #$nextNo",
                                paguAnggaran = 1000000000.0,
                                nilaiKontrak = 950000000.0,
                                nomorKontrak = "KTR/0$nextNo/II/2025",
                                tanggalKontrak = "15 Februari 2025",
                                tds = "30 Juni 2025",
                                penyedia = "PT Industri Pertahanan",
                                anggaranTerserap = 285000000.0,
                                persentaseFisik = 30,
                                persentaseAdmin = 30
                            )
                        },
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Tambah", style = MaterialTheme.typography.labelMedium)
                    }
                }

                itemsList.forEachIndexed { index, item ->
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "Kegiatan #${item.noUrut}",
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    style = MaterialTheme.typography.labelLarge
                                )
                                if (itemsList.size > 1) {
                                    IconButton(
                                        onClick = {
                                            resetNumericDrafts()
                                            itemsList = itemsList.filterIndexed { i, _ -> i != index }
                                        },
                                        modifier = Modifier.size(24.dp)
                                    ) {
                                        Icon(Icons.Default.Delete, contentDescription = "Hapus", tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(18.dp))
                                    }
                                }
                            }

                            OutlinedTextField(
                                value = item.namaKegiatan,
                                onValueChange = { newVal ->
                                    itemsList = itemsList.toMutableList().also { it[index] = item.copy(namaKegiatan = newVal) }
                                },
                                label = { Text("Uraian Kegiatan / Akun") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = numericText("$index:pagu", item.paguAnggaran),
                                    onValueChange = { raw ->
                                        onNumericChange("$index:pagu", raw) { v ->
                                            itemsList = itemsList.toMutableList().also { it[index] = item.copy(paguAnggaran = v) }
                                        }
                                    },
                                    label = { Text("Pagu (Rp)") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f)
                                )
                                OutlinedTextField(
                                    value = numericText("$index:serap", item.anggaranTerserap),
                                    onValueChange = { raw ->
                                        onNumericChange("$index:serap", raw) { v ->
                                            itemsList = itemsList.toMutableList().also { it[index] = item.copy(anggaranTerserap = v) }
                                        }
                                    },
                                    label = { Text("Terserap (Rp)") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f)
                                )
                            }

                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = numericText("$index:fisik", item.persentaseFisik.toDouble()),
                                    onValueChange = { raw ->
                                        onNumericChange("$index:fisik", raw) { v ->
                                            itemsList = itemsList.toMutableList().also { it[index] = item.copy(persentaseFisik = v.toInt()) }
                                        }
                                    },
                                    label = { Text("% Fisik") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f)
                                )
                                OutlinedTextField(
                                    value = numericText("$index:admin", item.persentaseAdmin.toDouble()),
                                    onValueChange = { raw ->
                                        onNumericChange("$index:admin", raw) { v ->
                                            itemsList = itemsList.toMutableList().also { it[index] = item.copy(persentaseAdmin = v.toInt()) }
                                        }
                                    },
                                    label = { Text("% Admin") },
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }
                    }
                }
            }
        }

        // ── Action Buttons Dock ──
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 4.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            OutlinedButton(
                onClick = {
                    // State dialog dikelola ViewModel — pasal formal tetap hidup
                    // meski pengguna pindah tab selama penyusunan.
                    onDraftLapju(buildRequest())
                },
                // Guard: cegah tap ganda selama draf disusun ATAU generasi berjalan —
                // tanpa isLoading, submit dilayani lalu dibuang senyap oleh ViewModel.
                enabled = !isDraftLoading && !isLoading,
                modifier = Modifier.weight(1f).height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isDraftLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Default.Visibility, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Pratinjau Draf", fontWeight = FontWeight.SemiBold)
                }
            }

            Button(
                onClick = {
                    val req = buildRequest()
                    onGenerateLapju(req)
                },
                // Guard double-submit: selama generasi berjalan tombol dikunci
                // (sebelumnya bebas ditekan berulang → request menumpuk di server)
                enabled = !isLoading,
                modifier = Modifier.weight(1.2f).height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Generate PDF", fontWeight = FontWeight.Bold)
                }
            }
        }
    }

    // Live Editor / Preview Dialog
    if (showPreviewDialog) {
        AlertDialog(
            onDismissRequest = onDraftDismiss,
            title = { Text("Pratinjau & Edit Naskah Lapju", fontWeight = FontWeight.Bold) },
            text = {
                if (isDraftLoading) {
                    // Draf sedang disusun — tampilkan indikator, bukan teks basi/kosong
                    Box(
                        modifier = Modifier.fillMaxWidth().height(380.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator()
                            Spacer(Modifier.height(12.dp))
                            Text("Menyiapkan draf naskah resmi...")
                        }
                    }
                } else {
                    OutlinedTextField(
                        value = previewDraftText,
                        onValueChange = onDraftTextChange,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(380.dp),
                        label = { Text("Redaksi Naskah Lapju (Dapat Diedit)") }
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onDraftDismiss() // tutup state dialog, lalu cetak
                        val req = buildRequest(previewDraftText)
                        onGenerateLapju(req)
                    },
                    // Jangan cetak selama draf/generasi berjalan, kosong, atau berisi
                    // penanda kegagalan ("⚠️ GAGAL MENYUSUN DRAF...") — tanpa ini blok
                    // pesan kesalahan tercetak sebagai badan surat pengantar resmi.
                    enabled = !isDraftLoading && !isLoading &&
                        previewDraftText.isNotBlank() && !previewDraftText.startsWith("⚠️")
                ) {
                    Text("Cetak PDF dari Editan")
                }
            },
            dismissButton = {
                TextButton(onClick = onDraftDismiss) {
                    Text("Tutup")
                }
            }
        )
    }
}
