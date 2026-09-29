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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.pussiber.suratgenerator.data.model.*
import java.util.Calendar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun KajianScreen(
    modifier: Modifier = Modifier,
    onGenerateKajian: (KajianGenerateRequest) -> Unit,
    onDraftKajian: (KajianGenerateRequest) -> Unit,
    onRenderKajianPdf: (KajianRenderPDFRequest) -> Unit,
    draftState: com.pussiber.suratgenerator.DraftUiState? = null,
    onDraftDismiss: () -> Unit = {},
    onDraftTextChange: (String) -> Unit = {},
    isLoading: Boolean = false
) {
    val context = LocalContext.current

    // Category & Model State
    var selectedCategory by remember { mutableStateOf(KajianCategory.TELAAHAN_STAF) }
    var selectedKkaModel by remember { mutableStateOf(KKAModelType.STUDI_KASUS) }

    // Common Form State
    var kopUtama by remember { mutableStateOf("PUSAT SIBER PERTAHANAN") }
    var kopSub by remember { mutableStateOf("SATUAN PENINDAK SIBER") }
    var judulAtauTopik by remember { mutableStateOf("PENGUATAN KEAMANAN SIBER OPERASIONAL SATUAN") }
    // Kosong = backend menomori otomatis (Nomor TS/01/<ROMAWI>/<TAHUN>/<KODE_SATKER>).
    // Sebelumnya prefill usang "Nomor TS/01/IV/2025" selalu terkirim dan menekan
    // penomoran otomatis server dengan format yang sudah kedaluwarsa.
    var nomorNaskah by remember { mutableStateOf("") }
    var tempat by remember { mutableStateOf("Jakarta") }
    var namaPejabatAtauPasis by remember { mutableStateOf("Budi Santoso, S.E., M.M.") }
    var jabatan by remember { mutableStateOf("Komandan Satuan Penindak") }
    var pangkatKorpsNrp by remember { mutableStateOf("Kolonel Laut (E) NRP 12345/P") }

    // KKA Specific State
    var nomorPasis by remember { mutableStateOf("No. Pasis 59-012") }
    var kelompokPasis by remember { mutableStateOf("Kelompok III / Sindikat Bravo") }
    var jenisDanTahunPendidikan by remember { mutableStateOf("PASIS DIKREG SESKOAL ANGKATAN KE-64 TA 2026") }

    // Telaahan Staf Specific State (6 Pasal)
    // KOSONG by default — prefill contoh bertopik tertentu (mis. SIEM) pernah
    // mencemari pasal AI ketika pengguna hanya mengganti judul -> naskah campuran.
    // Field kosong ditangani backend dengan kalimat baku yang konsisten judul.
    var inputPersoalan by remember { mutableStateOf("") }
    var inputPraanggapan by remember { mutableStateOf("") }
    var inputFakta by remember { mutableStateOf("") }
    var inputAnalisis by remember { mutableStateOf("") }
    var inputKesimpulan by remember { mutableStateOf("") }
    var inputSaran by remember { mutableStateOf("") }
    val lampiranList = remember { mutableStateListOf("Tabel Perbandingan Analisis Solusi Teknis") }

    // KKA Model A (Studi Kasus) Specific State
    var inputKronologisPra by remember { mutableStateOf("Deteksi awal anomali pergerakan kapal asing tanpa AIS aktif di ZEEI.") }
    var inputKronologisKejadian by remember { mutableStateOf("Pengerahan KRI patroli dan manuver intercept penghentian kapal target.") }
    var inputKronologisPasca by remember { mutableStateOf("Pengawalan menuju pangkalan utama dan serah terima penyidikan hukum laut.") }
    var inputSaranStudiKasus by remember { mutableStateOf("Penguatan integrasi sensor radar pantai terpadu dan interoperabilitas satgas laut.") }

    // KKA Model B (Analisis MoE) Specific State
    var inputOpsi1 by remember { mutableStateOf("Kapal Patroli Cepat (KPC-60)") }
    var inputOpsi2 by remember { mutableStateOf("Pesawat Patroli Maritim (CN-235 MPA)") }
    var inputFaktaMoE by remember { mutableStateOf("Kebutuhan surveilans maritim intensif di wilayah ALKI I dan II.") }
    var inputSaranMoE by remember { mutableStateOf("Disarankan memprioritaskan opsi alutsista dengan perolehan skor MoE tertinggi.") }

    // KKA Model C (Pemecahan Masalah SOM) Specific State
    var inputPokokMasalah by remember { mutableStateOf("Belum optimalnya integrasi pusat komando siber maritim antarsatker operasi.") }
    var inputPersoalan1 by remember { mutableStateOf("Keterbatasan kuantitas dan kompetensi SDM personel siber.") }
    var inputPersoalan2 by remember { mutableStateOf("Infrastruktur server dan sensor pemantau belum merata.") }
    var inputPersoalan3 by remember { mutableStateOf("SOP koordinasi tanggap insiden lintas pangkalan masih manual.") }
    var inputSaranSOM by remember { mutableStateOf("Pemberlakuan doktrin pertahanan siber terpadu dan pembentukan satgas siber pangkalan.") }

    // Dialog Preview & Live Edit — STATE DIMILIKI VIEWMODEL (bertahan lintas tab & rotasi).
    // Sebelumnya state Compose lokal: pindah tab saat AI menyusun membuang hasil senyap.
    val ds = draftState?.takeIf { it.type == com.pussiber.suratgenerator.DraftType.KAJIAN }
    val isDraftLoading = ds?.isLoading == true
    val previewDraftText = ds?.text.orEmpty()
    val currentSections: Map<String, Any> = ds?.sections ?: emptyMap()
    val showPreviewDialog = ds != null && !ds.dismissed

    // Speech to Text (STT) Target Callback
    // Speech-to-Text bersama (helper ui/common/SttController.kt)
    val stt = com.pussiber.suratgenerator.ui.common.rememberSttController(
        onUnsupported = { Toast.makeText(context, "Speech-to-Text tidak didukung pada perangkat ini", Toast.LENGTH_SHORT).show() }
    )

    fun generateAutoNomorTS() {
        val cal = Calendar.getInstance()
        val year = cal.get(Calendar.YEAR)
        val romanMonths = arrayOf("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
        val monthRoman = romanMonths[cal.get(Calendar.MONTH)]
        // Format DISEMAKINI dengan backend _get_auto_nomor_ts():
        // "Nomor TS/01/<bulan-romawi>/<tahun>/<inisial-satker dari kop>"
        // Sebelumnya klien menghilangkan kode satker → format berbeda dari server.
        val satkerCode = kopUtama.split(" ")
            .filter { it.isNotBlank() }
            .map { it.first().uppercaseChar() }
            .joinToString("")
            .ifEmpty { "SAT" }
        nomorNaskah = "Nomor TS/01/$monthRoman/$year/$satkerCode"
    }

    fun buildGenerateRequest(): KajianGenerateRequest {
        val isKka = (selectedCategory == KajianCategory.KKA_SESKOAL)
        return KajianGenerateRequest(
            kategori = selectedCategory,
            kkaModel = if (isKka) selectedKkaModel else null,
            kopUtama = kopUtama,
            kopSatuanBawah = kopSub,
            judulAtauTopik = judulAtauTopik,
            nomorNaskah = if (isKka) null else nomorNaskah.ifBlank { null },
            tempat = tempat,
            namaPejabatAtauPasis = namaPejabatAtauPasis,
            pangkatKorpsNrp = pangkatKorpsNrp,
            jabatan = if (isKka) null else jabatan,
            nomorPasis = if (isKka) nomorPasis else null,
            kelompokPasis = if (isKka) kelompokPasis else null,
            jenisDanTahunPendidikan = if (isKka) jenisDanTahunPendidikan else null,
            lampiranList = if (isKka) null else lampiranList.toList(),

            // Inputs
            inputPersoalan = if (!isKka) inputPersoalan else null,
            inputPraanggapan = if (!isKka) inputPraanggapan.ifBlank { null } else null,
            inputFakta = if (!isKka) inputFakta else if (selectedKkaModel == KKAModelType.ANALISIS_MOE) inputFaktaMoE else null,
            inputAnalisis = if (!isKka) inputAnalisis.ifBlank { null } else null,
            inputKesimpulan = if (!isKka) inputKesimpulan.ifBlank { null } else null,
            inputSaran = when {
                !isKka -> inputSaran
                selectedKkaModel == KKAModelType.STUDI_KASUS -> inputSaranStudiKasus
                selectedKkaModel == KKAModelType.ANALISIS_MOE -> inputSaranMoE
                else -> inputSaranSOM
            },

            inputKronologisPra = if (isKka && selectedKkaModel == KKAModelType.STUDI_KASUS) inputKronologisPra.ifBlank { null } else null,
            inputKronologisKejadian = if (isKka && selectedKkaModel == KKAModelType.STUDI_KASUS) inputKronologisKejadian else null,
            inputKronologisPasca = if (isKka && selectedKkaModel == KKAModelType.STUDI_KASUS) inputKronologisPasca.ifBlank { null } else null,

            inputAlutsistaOpsi1 = if (isKka && selectedKkaModel == KKAModelType.ANALISIS_MOE) inputOpsi1 else null,
            inputAlutsistaOpsi2 = if (isKka && selectedKkaModel == KKAModelType.ANALISIS_MOE) inputOpsi2 else null,

            inputPokokMasalah = if (isKka && selectedKkaModel == KKAModelType.PEMECAHAN_MASALAH) inputPokokMasalah else null,
            inputPermasalahanList = if (isKka && selectedKkaModel == KKAModelType.PEMECAHAN_MASALAH) listOf(inputPersoalan1, inputPersoalan2, inputPersoalan3) else null
        )
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // ── Card Pemilihan Mode Kajian ──
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            shape = RoundedCornerShape(14.dp)
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "Format Standar Kajian Militer",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FilterChip(
                        selected = selectedCategory == KajianCategory.TELAAHAN_STAF,
                        onClick = { selectedCategory = KajianCategory.TELAAHAN_STAF },
                        label = {
                            Text(
                                "📑 Telaahan Staf",
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodySmall
                            )
                        },
                        modifier = Modifier.weight(1f)
                    )
                    FilterChip(
                        selected = selectedCategory == KajianCategory.KKA_SESKOAL,
                        onClick = { selectedCategory = KajianCategory.KKA_SESKOAL },
                        label = {
                            Text(
                                "🎓 KKA Seskoal",
                                modifier = Modifier.fillMaxWidth(),
                                textAlign = TextAlign.Center,
                                style = MaterialTheme.typography.bodySmall
                            )
                        },
                        modifier = Modifier.weight(1f)
                    )
                }

                if (selectedCategory == KajianCategory.KKA_SESKOAL) {
                    HorizontalDivider(color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.2f))
                    Text(
                        text = "Pilih Model KKA Pasis:",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        FilterChip(
                            selected = selectedKkaModel == KKAModelType.STUDI_KASUS,
                            onClick = { selectedKkaModel = KKAModelType.STUDI_KASUS },
                            label = { Text("A. Kasus", style = MaterialTheme.typography.bodySmall) },
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = selectedKkaModel == KKAModelType.ANALISIS_MOE,
                            onClick = { selectedKkaModel = KKAModelType.ANALISIS_MOE },
                            label = { Text("B. MoE", style = MaterialTheme.typography.bodySmall) },
                            modifier = Modifier.weight(1f)
                        )
                        FilterChip(
                            selected = selectedKkaModel == KKAModelType.PEMECAHAN_MASALAH,
                            onClick = { selectedKkaModel = KKAModelType.PEMECAHAN_MASALAH },
                            label = { Text("C. SOM", style = MaterialTheme.typography.bodySmall) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }
        }

        // ── Card Kop & Identitas Naskah ──
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "1. Identitas Dokumen",
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
                    value = kopSub,
                    onValueChange = { kopSub = it },
                    label = { Text("Kop Sub / Satuan Bawah") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = judulAtauTopik,
                    onValueChange = { judulAtauTopik = it },
                    label = { Text(if (selectedCategory == KajianCategory.KKA_SESKOAL) "Topik / Judul KKA *" else "Judul Telaahan Staf *") },
                    trailingIcon = {
                        IconButton(onClick = { stt.launch { spoken -> judulAtauTopik = if (judulAtauTopik.isBlank()) spoken else "$judulAtauTopik $spoken" } }) {
                            Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                        }
                    },
                    modifier = Modifier.fillMaxWidth()
                )

                if (selectedCategory == KajianCategory.TELAAHAN_STAF) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            value = nomorNaskah,
                            onValueChange = { nomorNaskah = it },
                            label = { Text("Nomor Naskah TS") },
                            placeholder = { Text("Kosongkan untuk nomor otomatis server") },
                            modifier = Modifier.weight(1f)
                        )
                        FilledTonalButton(
                            onClick = { generateAutoNomorTS() },
                            shape = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                        ) {
                            Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("Auto", style = MaterialTheme.typography.labelMedium)
                        }
                    }

                    OutlinedTextField(
                        value = tempat,
                        onValueChange = { tempat = it },
                        label = { Text("Tempat Pembuatan") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }

                if (selectedCategory == KajianCategory.KKA_SESKOAL) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = nomorPasis,
                            onValueChange = { nomorPasis = it },
                            label = { Text("No. Pasis") },
                            modifier = Modifier.weight(1f)
                        )
                        OutlinedTextField(
                            value = kelompokPasis,
                            onValueChange = { kelompokPasis = it },
                            label = { Text("Kelompok") },
                            modifier = Modifier.weight(1f)
                        )
                    }
                    OutlinedTextField(
                        value = jenisDanTahunPendidikan,
                        onValueChange = { jenisDanTahunPendidikan = it },
                        label = { Text("Pendidikan & Angkatan") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // ── Card Identitas Pejabat / Pasis ──
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "2. Identitas Penandatangan / Pasis",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )

                OutlinedTextField(
                    value = namaPejabatAtauPasis,
                    onValueChange = { namaPejabatAtauPasis = it },
                    label = { Text("Nama Lengkap & Gelar") },
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = pangkatKorpsNrp,
                    onValueChange = { pangkatKorpsNrp = it },
                    label = { Text("Pangkat / Korps / NRP") },
                    modifier = Modifier.fillMaxWidth()
                )

                if (selectedCategory == KajianCategory.TELAAHAN_STAF) {
                    OutlinedTextField(
                        value = jabatan,
                        onValueChange = { jabatan = it },
                        label = { Text("Jabatan Pejabat") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // ── Form Struktur Telaahan Staf (6 Pasal KEP/868) ──
        if (selectedCategory == KajianCategory.TELAAHAN_STAF) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "3. Struktur 6 Pasal Baku (KEP/868 Contoh 26)",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )

                    OutlinedTextField(
                        value = inputPersoalan,
                        onValueChange = { inputPersoalan = it },
                        label = { Text("1. Persoalan *") },
                        placeholder = { Text("Inti persoalan yang dipecahkan") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputPersoalan = if (inputPersoalan.isBlank()) spoken else "$inputPersoalan $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = inputPraanggapan,
                        onValueChange = { inputPraanggapan = it },
                        label = { Text("2. Praanggapan") },
                        placeholder = { Text("Kosongkan agar AI menyusun dari persoalan & fakta") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputPraanggapan = if (inputPraanggapan.isBlank()) spoken else "$inputPraanggapan $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = inputFakta,
                        onValueChange = { inputFakta = it },
                        label = { Text("3. Fakta/Data yang Memengaruhi *") },
                        placeholder = { Text("Data/fakta konkret pendukung") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputFakta = if (inputFakta.isBlank()) spoken else "$inputFakta $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = inputAnalisis,
                        onValueChange = { inputAnalisis = it },
                        label = { Text("4. Analisis Solusi") },
                        placeholder = { Text("Kosongkan agar AI menganalisis dari fakta & praanggapan") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputAnalisis = if (inputAnalisis.isBlank()) spoken else "$inputAnalisis $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 3,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = inputKesimpulan,
                        onValueChange = { inputKesimpulan = it },
                        label = { Text("5. Kesimpulan") },
                        placeholder = { Text("Kosongkan agar AI menetapkan cara bertindak terbaik") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputKesimpulan = if (inputKesimpulan.isBlank()) spoken else "$inputKesimpulan $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = inputSaran,
                        onValueChange = { inputSaran = it },
                        label = { Text("6. Saran Pimpinan *") },
                        placeholder = { Text("Usulan tindakan konkret untuk pimpinan") },
                        trailingIcon = {
                            IconButton(onClick = { stt.launch { spoken -> inputSaran = if (inputSaran.isBlank()) spoken else "$inputSaran $spoken" } }) {
                                Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                            }
                        },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }

        // ── Form Model KKA Seskoal ──
        if (selectedCategory == KajianCategory.KKA_SESKOAL) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f))
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "3. Substansi Pokok KKA (${selectedKkaModel.name.replace('_', ' ')})",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )

                    when (selectedKkaModel) {
                        KKAModelType.STUDI_KASUS -> {
                            OutlinedTextField(
                                value = inputKronologisPra,
                                onValueChange = { inputKronologisPra = it },
                                label = { Text("a. Pra-Kejadian (Latar)") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputKronologisKejadian,
                                onValueChange = { inputKronologisKejadian = it },
                                label = { Text("b. Saat Kejadian (Kronologis)") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputKronologisPasca,
                                onValueChange = { inputKronologisPasca = it },
                                label = { Text("c. Pasca-Kejadian (Dampak)") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputSaranStudiKasus,
                                onValueChange = { inputSaranStudiKasus = it },
                                label = { Text("Saran / Rekomendasi Pasis") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                        KKAModelType.ANALISIS_MOE -> {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(
                                    value = inputOpsi1,
                                    onValueChange = { inputOpsi1 = it },
                                    label = { Text("Alutsista Opsi 1") },
                                    modifier = Modifier.weight(1f)
                                )
                                OutlinedTextField(
                                    value = inputOpsi2,
                                    onValueChange = { inputOpsi2 = it },
                                    label = { Text("Alutsista Opsi 2") },
                                    modifier = Modifier.weight(1f)
                                )
                            }
                            OutlinedTextField(
                                value = inputFaktaMoE,
                                onValueChange = { inputFaktaMoE = it },
                                label = { Text("Fakta & Kebutuhan Operasi") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputSaranMoE,
                                onValueChange = { inputSaranMoE = it },
                                label = { Text("Saran Keputusan MoE") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                        KKAModelType.PEMECAHAN_MASALAH -> {
                            OutlinedTextField(
                                value = inputPokokMasalah,
                                onValueChange = { inputPokokMasalah = it },
                                label = { Text("Pokok Masalah Utama (Gap)") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputPersoalan1,
                                onValueChange = { inputPersoalan1 = it },
                                label = { Text("Persoalan 1 (Subyek - SDM)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputPersoalan2,
                                onValueChange = { inputPersoalan2 = it },
                                label = { Text("Persoalan 2 (Obyek - Sarpras)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputPersoalan3,
                                onValueChange = { inputPersoalan3 = it },
                                label = { Text("Persoalan 3 (Metoda - Doktrin)") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = inputSaranSOM,
                                onValueChange = { inputSaranSOM = it },
                                label = { Text("Saran Kebijakan Strategis") },
                                minLines = 2,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }
            }
        }

        // ── Action Buttons Dock ──
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 4.dp, bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            OutlinedButton(
                onClick = {
                    // State dialog dikelola ViewModel — hasil tetap hidup meski
                    // pengguna pindah tab selama AI menyusun (dulu hilang senyap).
                    onDraftKajian(buildGenerateRequest())
                },
                // Guard double-tap: satu generasi multi-bagian berjalan menit-menit —
                // tap kedua memicu pekerjaan Ollama paralel yang sia-sia.
                enabled = !isLoading && !isDraftLoading && judulAtauTopik.isNotBlank(),
                modifier = Modifier.weight(1f).height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isDraftLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                } else {
                    Icon(Icons.Default.Visibility, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Pratinjau Draf", fontWeight = FontWeight.SemiBold)
                }
            }

            Button(
                onClick = {
                    val req = buildGenerateRequest()
                    onGenerateKajian(req)
                },
                enabled = !isLoading && judulAtauTopik.isNotBlank(),
                modifier = Modifier.weight(1.2f).height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("Memproses...")
                } else {
                    Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Generate PDF", fontWeight = FontWeight.Bold)
                }
            }
        }
    }

    // ── Dialog Preview & Live Edit ──
    if (showPreviewDialog) {
        Dialog(
            onDismissRequest = onDraftDismiss,
            properties = DialogProperties(usePlatformDefaultWidth = false)
        ) {
            Surface(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surface
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Pratinjau & Edit Redaksi",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )
                        IconButton(onClick = onDraftDismiss) {
                            Icon(Icons.Default.Close, contentDescription = "Tutup")
                        }
                    }

                    HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))

                    if (isDraftLoading) {
                        // Draf disusun — indikator, bukan teks basi/kosong
                        Box(
                            modifier = Modifier.fillMaxWidth().weight(1f),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator()
                                Spacer(modifier = Modifier.height(12.dp))
                                Text("AI sedang menyusun draf naskah...")
                            }
                        }
                    } else {
                        OutlinedTextField(
                            value = previewDraftText,
                            onValueChange = onDraftTextChange,
                            modifier = Modifier
                                .fillMaxWidth()
                                .weight(1f),
                            placeholder = { Text("Teks redaksi kajian...") }
                        )
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedButton(
                            onClick = onDraftDismiss,
                            modifier = Modifier.weight(1f).height(48.dp),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Text("Batal")
                        }

                        Button(
                            onClick = {
                                val isKka = (selectedCategory == KajianCategory.KKA_SESKOAL)
                                val renderReq = KajianRenderPDFRequest(
                                    kategori = selectedCategory,
                                    kkaModel = if (isKka) selectedKkaModel else null,
                                    kopUtama = kopUtama,
                                    kopSatuanBawah = kopSub,
                                    judulAtauTopik = judulAtauTopik,
                                    nomorNaskah = if (isKka) null else nomorNaskah.ifBlank { null },
                                    tempat = tempat,
                                    namaPejabatAtauPasis = namaPejabatAtauPasis,
                                    pangkatKorpsNrp = pangkatKorpsNrp,
                                    jabatan = if (isKka) null else jabatan,
                                    nomorPasis = if (isKka) nomorPasis else null,
                                    kelompokPasis = if (isKka) kelompokPasis else null,
                                    jenisDanTahunPendidikan = if (isKka) jenisDanTahunPendidikan else null,
                                    sections = currentSections,
                                    lampiranList = if (isKka) null else lampiranList.toList(),
                                    kontenCustom = previewDraftText
                                )
                                onDraftDismiss() // tutup state dialog, lalu render
                                onRenderKajianPdf(renderReq)
                            },
                            // Cetak hanya bila ada isi: sections kosong + teks penanda
                            // kegagalan berarti draf GAGAL — mencetak akan menghasilkan
                            // dokumen resmi tanpa badan isi (sections={} dirender kosong).
                            enabled = !isDraftLoading && (
                                currentSections.isNotEmpty() ||
                                    (previewDraftText.isNotBlank() && !previewDraftText.startsWith("⚠️"))
                                ),
                            modifier = Modifier.weight(1.5f).height(48.dp),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Icon(Icons.Default.PictureAsPdf, contentDescription = "Render PDF", modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("Cetak PDF", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}
