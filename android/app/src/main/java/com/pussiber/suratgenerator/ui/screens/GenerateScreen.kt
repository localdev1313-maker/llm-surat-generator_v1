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
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.runtime.snapshots.SnapshotStateList
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

class PoinItemState(
    initialText: String = "",
    val subPoinList: SnapshotStateList<String> = mutableStateListOf()
) {
    var text by mutableStateOf(initialText)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GenerateScreen(
    onGenerateNotaDinas: (GenerateNotaDinasRequest) -> Unit,
    onGenerateSuratUmum: (GenerateSuratUmumRequest) -> Unit,
    onDraftNotaDinas: (GenerateNotaDinasRequest) -> Unit = {},
    onDraftSuratUmum: (GenerateSuratUmumRequest) -> Unit = {},
    onGenerateKajian: (KajianGenerateRequest) -> Unit = {},
    onDraftKajian: (KajianGenerateRequest) -> Unit = {},
    onRenderKajianPdf: (KajianRenderPDFRequest) -> Unit = {},
    onGenerateLapju: (LapjuGenerateRequest) -> Unit = {},
    onDraftLapju: (LapjuGenerateRequest) -> Unit = {},
    draftState: com.pussiber.suratgenerator.DraftUiState? = null,
    onDraftDismiss: () -> Unit = {},
    onDraftTextChange: (String) -> Unit = {},
    isLoading: Boolean = false
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(0) } // 0: Nota Dinas, 1: Kajian, 2: Lapju, 3: Surat Umum

    // Form State Nota Dinas
    var kopUtama by remember { mutableStateOf("PUSAT KOMANDO OPERASI") }
    var kopSub by remember { mutableStateOf("SATUAN PELAKSANA OPERASI") }
    var nomorSurat by remember { mutableStateOf("") }
    var kepada by remember { mutableStateOf("Kepala Pusat Komando Operasi") }
    var dari by remember { mutableStateOf("Kadiv Operasional") }
    var perihal by remember { mutableStateOf("Laporan Kesiapsiagaan Tim Tanggap Insiden Operasional") }
    var dasar by remember {
        mutableStateOf(
            "Keputusan Panglima TNI Nomor KEP/868/IX/2022 tentang Petunjuk Tata Tulis Militer\n" +
            "Surat Perintah Kasal Nomor Sprin/100/I/2025 tanggal 10 Januari 2025"
        )
    }
    var namaPejabat by remember { mutableStateOf("Budi Santoso, S.E., M.M.") }
    var jabatanPejabat by remember { mutableStateOf("Komandan Satuan Penindak") }
    var pangkatPejabat by remember { mutableStateOf("Kolonel Laut (E) NRP 12345/P") }
    var jenisPenutup by remember { mutableStateOf("perhatian") } // "periksa" (atasan) atau "perhatian" (sejajar/bawahan)

    val isiPoinList = remember {
        mutableStateListOf<PoinItemState>().apply {
            add(PoinItemState("Sehubungan dasar tersebut di atas, dilaporkan bahwa kesiapsiagaan operasional pemantauan sistem wilayah pertahanan berada dalam status siaga penuh selama 24/7."))
        }
    }

    val tembusanList = remember {
        mutableStateListOf("Kepala Staf Angkatan Laut", "Wakil Kepala Staf Angkatan Laut")
    }

    // Form State Surat Umum
    var jenisSurat by remember { mutableStateOf("resmi") }
    var namaPengirim by remember { mutableStateOf("") }
    var alamatPengirim by remember { mutableStateOf("") }
    var namaPenerima by remember { mutableStateOf("") }
    var alamatPenerima by remember { mutableStateOf("") }
    var perihalSurat by remember { mutableStateOf("") }
    var isiRingkasSurat by remember { mutableStateOf("") }

    // Dialog Preview & Edit — STATE DIMILIKI VIEWMODEL (bertahan lintas tab & rotasi).
    // Sebelumnya state Compose lokal: pindah tab saat AI menyusun membuang hasil senyap.
    val ds = draftState
    val isDraftLoading = ds?.isLoading == true
    val isNotaDinasDraft = ds?.type == com.pussiber.suratgenerator.DraftType.NOTA_DINAS
    val previewDraftText = ds?.text.orEmpty()
    val showEditPreviewDialog = ds != null && !ds.dismissed &&
        (ds.type == com.pussiber.suratgenerator.DraftType.NOTA_DINAS ||
         ds.type == com.pussiber.suratgenerator.DraftType.SURAT_UMUM)

    // Speech to Text (STT) Target Callback
    // Speech-to-Text bersama (helper ui/common/SttController.kt)
    val stt = com.pussiber.suratgenerator.ui.common.rememberSttController(
        onUnsupported = { Toast.makeText(context, "Speech-to-Text tidak didukung pada perangkat ini", Toast.LENGTH_SHORT).show() }
    )

    // Helper Auto Format Nomor ND
    fun generateAutoNomorND() {
        val cal = Calendar.getInstance()
        val year = cal.get(Calendar.YEAR)
        val monthRoman = when (cal.get(Calendar.MONTH) + 1) {
            1 -> "I"; 2 -> "II"; 3 -> "III"; 4 -> "IV"; 5 -> "V"; 6 -> "VI"
            7 -> "VII"; 8 -> "VIII"; 9 -> "IX"; 10 -> "X"; 11 -> "XI"; 12 -> "XII"
            else -> "I"
        }
        nomorSurat = "B/ND-01/$monthRoman/$year/Unit"
    }

    // Function to build current Nota Dinas Request
    fun buildNotaDinasRequest(
        customText: String? = null,
        isiCustom: List<PoinNotaDinasModel>? = null
    ): GenerateNotaDinasRequest {
        val formattedPoints = isiPoinList
            .filter { it.text.isNotBlank() || it.subPoinList.any { s -> s.isNotBlank() } }
            .map { item ->
                PoinNotaDinasModel(
                    teks = item.text.ifBlank { "Rincian sebagai berikut:" },
                    subPoin = item.subPoinList.filter { it.isNotBlank() }.ifEmpty { null }
                )
            }
        val cleanTembusan = tembusanList.filter { it.isNotBlank() }.ifEmpty { null }

        return GenerateNotaDinasRequest(
            kopUtama = kopUtama,
            kopSub = kopSub,
            nomorSurat = nomorSurat.ifBlank { "B/ND-01/IV/2025/Unit" },
            kepada = kepada,
            dari = dari,
            perihal = perihal,
            dasar = dasar,
            namaPejabat = namaPejabat,
            jabatanPejabat = jabatanPejabat,
            pangkatPejabat = pangkatPejabat.ifBlank { null },
            tembusan = cleanTembusan,
            jenisPenutup = jenisPenutup,
            isiRingkas = formattedPoints,
            // Cetak dari editan memakai isi_custom_list (pasal isi SAJA).
            // konten_custom utuh membuat backend memecah teks gabungan jadi pasal
            // sehingga kop/nomor/dasar/penutup terduplikasi di PDF (tertangkap
            // trial di emulator).
            isiCustomList = isiCustom,
            kontenCustom = if (isiCustom != null) null else customText
        )
    }

    // Function to build current Surat Umum Request
    fun buildSuratUmumRequest(customText: String? = null): GenerateSuratUmumRequest {
        return GenerateSuratUmumRequest(
            jenisSurat = jenisSurat,
            namaPengirim = namaPengirim,
            alamatPengirim = alamatPengirim,
            namaPenerima = namaPenerima,
            alamatPenerima = alamatPenerima,
            perihal = perihalSurat,
            isiRingkas = isiRingkasSurat,
            kontenCustom = customText
        )
    }

    // ── DIALOG PRATINJAU & EDIT DOKUMEN ──
    if (showEditPreviewDialog) {
        Dialog(
            // Tutup kapan saja — state draf tetap di VM, hasil tidak hilang
            onDismissRequest = onDraftDismiss,
            properties = DialogProperties(usePlatformDefaultWidth = false)
        ) {
            Card(
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                modifier = Modifier
                    .fillMaxWidth(0.95f)
                    .fillMaxHeight(0.85f)
                    .padding(8.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(18.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.padding(bottom = 10.dp)
                    ) {
                        Icon(
                            Icons.Default.Edit,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                        Column {
                            Text(
                                text = "Pratinjau & Edit Redaksi Dokumen",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Anda dapat mengoreksi teks di bawah sebelum dicetak ke PDF",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    HorizontalDivider(modifier = Modifier.padding(bottom = 12.dp))

                    if (isDraftLoading) {
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxWidth(),
                            contentAlignment = Alignment.Center
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator()
                                Spacer(Modifier.height(12.dp))
                                Text("AI sedang menyusun draf naskah...", style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    } else {
                        OutlinedTextField(
                            value = previewDraftText,
                            onValueChange = onDraftTextChange,
                            label = { Text("Teks Naskah Dinas (Dapat Diedit)") },
                            modifier = Modifier
                                .weight(1f)
                                .fillMaxWidth(),
                            textStyle = MaterialTheme.typography.bodyMedium
                        )
                    }

                    Spacer(Modifier.height(16.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        OutlinedButton(
                            onClick = onDraftDismiss,
                            // Membatalkan dialog selama draf disusun aman — hasil tetap
                            // tersimpan di ViewModel dan bisa dibuka ulang.
                            modifier = Modifier.weight(1f).height(48.dp),
                            shape = RoundedCornerShape(10.dp)
                        ) {
                            Text("Batal")
                        }

                        Button(
                            onClick = {
                                onDraftDismiss() // tutup state dialog — dokumen dicetak
                                if (isNotaDinasDraft) {
                                    // Pecah editan per paragraf -> isi_custom_list
                                    // (bukan konten_custom utuh — lihat catatan di atas)
                                    val isiCustom = previewDraftText
                                        .split("\n\n")
                                        .map { it.trim() }
                                        .filter { it.isNotEmpty() }
                                        .map { PoinNotaDinasModel(teks = it) }
                                    onGenerateNotaDinas(
                                        buildNotaDinasRequest(isiCustom = isiCustom.ifEmpty { null })
                                    )
                                } else {
                                    onGenerateSuratUmum(buildSuratUmumRequest(customText = previewDraftText))
                                }
                            },
                            modifier = Modifier.weight(1.5f).height(48.dp),
                            shape = RoundedCornerShape(10.dp),
                            // Kunci saat draf MASIH disusun (isDraftLoading, bukan isLoading
                            // global — inilah yang tadinya membiarkan teks basi tercetak) dan
                            // tolak placeholder kegagalan agar tidak menjadi isi surat resmi.
                            enabled = !isDraftLoading && !isLoading &&
                                previewDraftText.isNotBlank() && !previewDraftText.startsWith("⚠️")
                        ) {
                            Icon(Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Simpan & Cetak PDF", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }

    // ── MAIN LAYOUT ──
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // ── Pinned Top Header & Segmented Tab Navigation ──
        Surface(
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 2.dp,
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 10.dp)
            ) {
                Text(
                    text = "Pilih Jenis Naskah Dinas",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                // High-Contrast Line Tab Switcher
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.primary,
                    indicator = { tabPositions ->
                        TabRowDefaults.SecondaryIndicator(
                            Modifier.tabIndicatorOffset(tabPositions[selectedTab]),
                            height = 3.dp,
                            color = MaterialTheme.colorScheme.primary
                        )
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Tab(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        text = {
                            Text(
                                text = "Nota Dinas",
                                fontWeight = if (selectedTab == 0) FontWeight.Bold else FontWeight.Medium,
                                color = if (selectedTab == 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    )
                    Tab(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        text = {
                            Text(
                                text = "Kajian",
                                fontWeight = if (selectedTab == 1) FontWeight.Bold else FontWeight.Medium,
                                color = if (selectedTab == 1) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    )
                    Tab(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        text = {
                            Text(
                                text = "Lapju",
                                fontWeight = if (selectedTab == 2) FontWeight.Bold else FontWeight.Medium,
                                color = if (selectedTab == 2) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    )
                    Tab(
                        selected = selectedTab == 3,
                        onClick = { selectedTab = 3 },
                        text = {
                            Text(
                                text = "Umum",
                                fontWeight = if (selectedTab == 3) FontWeight.Bold else FontWeight.Medium,
                                color = if (selectedTab == 3) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    )
                }
            }
        }

        // ── Tab Viewport Area ──
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
        ) {
            if (selectedTab == 0) {
                // ════ NOTA DINAS FORM ════
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    // 1. Kop & Penomoran
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text(
                                text = "1. Kop & Penomoran Naskah",
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
                                label = { Text("Kop Sub Satuan / Divisi") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                OutlinedTextField(
                                    value = nomorSurat,
                                    onValueChange = { nomorSurat = it },
                                    label = { Text("Nomor Nota Dinas") },
                                    placeholder = { Text("B/ND-01/VIII/2026/Unit") },
                                    modifier = Modifier.weight(1f)
                                )
                                Spacer(Modifier.width(8.dp))
                                FilledTonalButton(
                                    onClick = { generateAutoNomorND() },
                                    shape = RoundedCornerShape(8.dp),
                                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp)
                                ) {
                                    Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(4.dp))
                                    Text("Auto", style = MaterialTheme.typography.labelMedium)
                                }
                            }
                        }
                    }

                    // 2. Pejabat & Perihal
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text(
                                text = "2. Pejabat & Perihal",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )

                            OutlinedTextField(
                                value = kepada,
                                onValueChange = { kepada = it },
                                label = { Text("Kepada (Yth.)") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            OutlinedTextField(
                                value = dari,
                                onValueChange = { dari = it },
                                label = { Text("Dari") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            OutlinedTextField(
                                value = perihal,
                                onValueChange = { perihal = it },
                                label = { Text("Perihal Nota Dinas") },
                                trailingIcon = {
                                    IconButton(onClick = { stt.launch { spoken -> perihal = if (perihal.isBlank()) spoken else "$perihal $spoken" } }) {
                                        Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                                    }
                                },
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }

                    // 3. Dasar Hukum
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text(
                                text = "3. Dasar Hukum / Rujukan",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )

                            OutlinedTextField(
                                value = dasar,
                                onValueChange = { dasar = it },
                                label = { Text("Dasar Rujukan Surat (1 baris per poin)") },
                                trailingIcon = {
                                    IconButton(onClick = { stt.launch { spoken -> dasar = if (dasar.isBlank()) spoken else "$dasar $spoken" } }) {
                                        Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                                    }
                                },
                                minLines = 3,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }

                    // 4. Poin-Poin Isi
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "4. Poin-Poin Isi Naskah",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                Text(
                                    text = "${isiPoinList.size} Paragraf",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            isiPoinList.forEachIndexed { index, poinItem ->
                                val poinNumber = index + 2
                                Card(
                                    shape = RoundedCornerShape(10.dp),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)),
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Text(
                                                text = "Poin $poinNumber",
                                                style = MaterialTheme.typography.labelLarge,
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.primary
                                            )
                                            if (isiPoinList.size > 1) {
                                                IconButton(
                                                    onClick = { isiPoinList.removeAt(index) },
                                                    modifier = Modifier.size(24.dp)
                                                ) {
                                                    Icon(Icons.Default.Delete, contentDescription = "Hapus Poin", tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(18.dp))
                                                }
                                            }
                                        }

                                        OutlinedTextField(
                                            value = poinItem.text,
                                            onValueChange = { poinItem.text = it },
                                            label = { Text("Teks Paragraf Poin $poinNumber") },
                                            trailingIcon = {
                                                IconButton(onClick = { stt.launch { spoken -> poinItem.text = if (poinItem.text.isBlank()) spoken else "${poinItem.text} $spoken" } }) {
                                                    Icon(Icons.Default.Mic, contentDescription = "Diktekan", tint = MaterialTheme.colorScheme.primary)
                                                }
                                            },
                                            modifier = Modifier.fillMaxWidth()
                                        )

                                        if (poinItem.subPoinList.isNotEmpty()) {
                                            poinItem.subPoinList.forEachIndexed { subIndex, subPoinText ->
                                                val subLetter = ('a' + subIndex)
                                                Row(
                                                    modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
                                                    verticalAlignment = Alignment.CenterVertically
                                                ) {
                                                    OutlinedTextField(
                                                        value = subPoinText,
                                                        onValueChange = { poinItem.subPoinList[subIndex] = it },
                                                        label = { Text("Sub-poin $subLetter)") },
                                                        modifier = Modifier.weight(1f)
                                                    )
                                                    IconButton(
                                                        onClick = { poinItem.subPoinList.removeAt(subIndex) },
                                                        modifier = Modifier.size(28.dp).padding(start = 4.dp)
                                                    ) {
                                                        Icon(Icons.Default.Delete, contentDescription = "Hapus Sub-poin", tint = MaterialTheme.colorScheme.error)
                                                    }
                                                }
                                            }
                                        }

                                        TextButton(
                                            onClick = { poinItem.subPoinList.add("") },
                                            modifier = Modifier.align(Alignment.Start)
                                        ) {
                                            Icon(Icons.Default.FormatListNumbered, contentDescription = null, modifier = Modifier.size(16.dp))
                                            Spacer(Modifier.width(4.dp))
                                            Text("Tambah Sub-poin (a, b, c)", style = MaterialTheme.typography.labelMedium)
                                        }
                                    }
                                }
                            }

                            if (isiPoinList.size < 5) {
                                OutlinedButton(
                                    onClick = { isiPoinList.add(PoinItemState("")) },
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(10.dp)
                                ) {
                                    Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                                    Spacer(Modifier.width(6.dp))
                                    Text("Tambah Paragraf Poin (${isiPoinList.size + 2})")
                                }
                            }
                        }
                    }

                    // 5. Pengesahan
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text(
                                text = "5. Pengesahan & Distribusi",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )

                            OutlinedTextField(
                                value = namaPejabat,
                                onValueChange = { namaPejabat = it },
                                label = { Text("Nama Pejabat Penandatangan") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            OutlinedTextField(
                                value = jabatanPejabat,
                                onValueChange = { jabatanPejabat = it },
                                label = { Text("Jabatan") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            OutlinedTextField(
                                value = pangkatPejabat,
                                onValueChange = { pangkatPejabat = it },
                                label = { Text("Pangkat / Korps / NRP") },
                                modifier = Modifier.fillMaxWidth()
                            )

                            // Hierarki Penutup (Equal-Width Responsive FilterChips)
                            Column(modifier = Modifier.fillMaxWidth()) {
                                Text(
                                    text = "Hierarki Kalimat Penutup:",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Spacer(Modifier.height(6.dp))
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    FilterChip(
                                        selected = (jenisPenutup == "perhatian"),
                                        onClick = { jenisPenutup = "perhatian" },
                                        label = {
                                            Text(
                                                "Sejajar (Perhatian)",
                                                modifier = Modifier.fillMaxWidth(),
                                                textAlign = TextAlign.Center,
                                                style = MaterialTheme.typography.bodySmall
                                            )
                                        },
                                        modifier = Modifier.weight(1f)
                                    )
                                    FilterChip(
                                        selected = (jenisPenutup == "periksa"),
                                        onClick = { jenisPenutup = "periksa" },
                                        label = {
                                            Text(
                                                "Atasan (Periksa)",
                                                modifier = Modifier.fillMaxWidth(),
                                                textAlign = TextAlign.Center,
                                                style = MaterialTheme.typography.bodySmall
                                            )
                                        },
                                        modifier = Modifier.weight(1f)
                                    )
                                }
                            }
                        }
                    }

                    // Action Buttons Dock
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 4.dp, bottom = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        OutlinedButton(
                            onClick = {
                                onGenerateNotaDinas(buildNotaDinasRequest())
                            },
                            enabled = !isLoading && perihal.isNotBlank(),
                            modifier = Modifier.weight(1f).height(50.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            if (isLoading) {
                                CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(6.dp))
                                Text("Memproses...")
                            } else {
                                Icon(Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Cetak PDF", fontWeight = FontWeight.SemiBold)
                            }
                        }

                        Button(
                            onClick = {
                                onDraftNotaDinas(buildNotaDinasRequest())
                            },
                            enabled = !isLoading && !isDraftLoading && perihal.isNotBlank(),
                            modifier = Modifier.weight(1.3f).height(50.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            if (isDraftLoading) {
                                CircularProgressIndicator(color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(6.dp))
                                Text("Menyusun AI...")
                            } else {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Susun AI & Pratinjau", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            } else if (selectedTab == 1) {
                // ════ KAJIAN DUAL-MODE ════
                KajianScreen(
                    onGenerateKajian = onGenerateKajian,
                    onDraftKajian = onDraftKajian,
                    onRenderKajianPdf = onRenderKajianPdf,
                    draftState = draftState,
                    onDraftDismiss = onDraftDismiss,
                    onDraftTextChange = onDraftTextChange,
                    isLoading = isLoading
                )
            } else if (selectedTab == 2) {
                // ════ LAPORAN KEMAJUAN (LAPJU) ════
                LapjuScreen(
                    onGenerateLapju = onGenerateLapju,
                    onDraftLapju = onDraftLapju,
                    draftState = draftState,
                    onDraftDismiss = onDraftDismiss,
                    onDraftTextChange = onDraftTextChange,
                    isLoading = isLoading
                )
            } else {
                // ════ SURAT UMUM ════
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        shape = RoundedCornerShape(14.dp),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.4f)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(
                                value = namaPengirim,
                                onValueChange = { namaPengirim = it },
                                label = { Text("Nama/Instansi Pengirim") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = alamatPengirim,
                                onValueChange = { alamatPengirim = it },
                                label = { Text("Alamat Pengirim") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = namaPenerima,
                                onValueChange = { namaPenerima = it },
                                label = { Text("Nama/Instansi Penerima") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = alamatPenerima,
                                onValueChange = { alamatPenerima = it },
                                label = { Text("Alamat Penerima") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = perihalSurat,
                                onValueChange = { perihalSurat = it },
                                label = { Text("Perihal Surat") },
                                modifier = Modifier.fillMaxWidth()
                            )
                            OutlinedTextField(
                                value = isiRingkasSurat,
                                onValueChange = { isiRingkasSurat = it },
                                label = { Text("Poin-Poin Ringkas Isi Surat") },
                                minLines = 4,
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }

                    // Action Buttons for Surat Umum
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 4.dp, bottom = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        OutlinedButton(
                            onClick = {
                                onGenerateSuratUmum(buildSuratUmumRequest())
                            },
                            enabled = !isLoading && perihalSurat.isNotBlank(),
                            modifier = Modifier.weight(1f).height(50.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            if (isLoading) {
                                CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(6.dp))
                                Text("Memproses...")
                            } else {
                                Icon(Icons.Default.PictureAsPdf, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Cetak PDF", fontWeight = FontWeight.SemiBold)
                            }
                        }

                        Button(
                            onClick = {
                                onDraftSuratUmum(buildSuratUmumRequest())
                            },
                            enabled = !isLoading && !isDraftLoading && perihalSurat.isNotBlank(),
                            modifier = Modifier.weight(1.3f).height(50.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            if (isDraftLoading) {
                                CircularProgressIndicator(color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                                Spacer(Modifier.width(6.dp))
                                Text("Menyusun AI...")
                            } else {
                                Icon(Icons.Default.AutoAwesome, contentDescription = null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(6.dp))
                                Text("Susun AI & Pratinjau", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}
