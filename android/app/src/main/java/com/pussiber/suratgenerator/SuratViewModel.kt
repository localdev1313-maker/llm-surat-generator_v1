package com.pussiber.suratgenerator

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.pussiber.suratgenerator.data.local.AppDatabase
import com.pussiber.suratgenerator.data.local.SuratEntity
import com.pussiber.suratgenerator.data.model.*
import com.pussiber.suratgenerator.data.remote.ApiService
import com.pussiber.suratgenerator.data.repository.SuratRepository
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Event satu-kali dari ViewModel ke UI.
 * Dipakai alih-alih memanggil Toast/navigasi langsung di dalam ViewModel,
 * sehingga Activity hanya mengonsumsi event dan tetap bebas konfigurasi ulang.
 */
sealed interface UiEvent {
    data class OpenPreview(val pdfUrl: String, val perihal: String) : UiEvent
    data class ShowToast(val message: String) : UiEvent
}

/** Jenis draf yang dialog pratinjau-editnya dikelola ViewModel. */
enum class DraftType { NOTA_DINAS, SURAT_UMUM, KAJIAN, LAPJU }

/**
 * State dialog pratinjau & edit draf — DIMILIKI VIEWMODEL, bukan layar.
 *
 * Sebelumnya state dialog hidup di Compose lokal tiap layar: pindah tab
 * bottom-nav saat draf AI disusun membuang hasilnya senyap (state yatim).
 * Kini state bertahan melewati pergantian tab & rotasi; kembali ke tab
 * asal menampilkan dialog beserta hasilnya.
 */
data class DraftUiState(
    val type: DraftType,
    val isLoading: Boolean,
    val failed: Boolean,
    val text: String,
    val sections: Map<String, Any> = emptyMap(), // khusus KAJIAN
    // true = pengguna menutup dialog sementara; state TETAP disimpan agar hasil
    // AI tidak hilang — dialog muncul kembali otomatis saat generasi selesai.
    val dismissed: Boolean = false
)

/**
 * Pemilik SELURUH pekerjaan jaringan aplikasi.
 *
 * Semua generasi/render/draft berjalan di [viewModelScope] — bukan lifecycleScope
 * Activity — sehingga rotasi layar atau proses dibunuh sistem TIDAK lagi
 * membatalkan permintaan Ollama yang berjalan menit-menit lamanya. State
 * (serverUrl, isLoading, connectionStatus) juga bertahan melewati rotasi.
 */
class SuratViewModel(application: Application) : AndroidViewModel(application) {

    companion object {
        const val DEFAULT_SERVER_URL = "http://10.0.2.2:8001/" // Default Android Emulator host
        const val PREFS_NAME = "app_settings"
        const val KEY_SERVER_URL = "server_url"
        const val KEY_AUTH_USER = "auth_username"
        const val KEY_AUTH_PASS = "auth_password"
        const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
    }

    private val prefs = application.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // WAJIB dideklarasikan SEBELUM repositoryFlow: initializer repositoryFlow
    // memanggil createRepository -> createApiService yang memakai klien ini.
    // Deklarasi setelahnya membuat lazy delegate masih null saat konstruktor
    // berjalan -> NullPointerException saat peluncuran (tertangkap trial di emulator).
    // Satu OkHttpClient bersama (connection pool dipakai ulang antar Retrofit).
    // Read timeout jauh lebih besar dari total waktu generasi karena satu request
    // dapat memicu banyak panggilan Ollama berurutan (mis. 6 pasal Telaahan Staf).
    private val baseHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(600, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()
    }

    // ── State yang bertahan melewati rotasi ──
    private val _serverUrl = MutableStateFlow(
        normalizeServerUrl(prefs.getString(KEY_SERVER_URL, null)) ?: DEFAULT_SERVER_URL
    )
    val serverUrl: StateFlow<String> = _serverUrl.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _connectionStatus = MutableStateFlow<String?>(null)
    val connectionStatus: StateFlow<String?> = _connectionStatus.asStateFlow()

    private val _events = Channel<UiEvent>(Channel.BUFFERED)
    val events: Flow<UiEvent> = _events.receiveAsFlow()

    // ── State dialog draf (dimiliki VM — bertahan melewati tab & rotasi) ──
    private val _draftState = MutableStateFlow<DraftUiState?>(null)
    val draftState: StateFlow<DraftUiState?> = _draftState.asStateFlow()

    /** Tutup dialog draf — hanya SEMBUNYIKAN; state & hasil tetap di VM. */
    fun dismissDraft() {
        _draftState.update { it?.copy(dismissed = true) }
    }

    /** Perbarui teks draf dari editor (ketikan pengguna). */
    fun updateDraftText(text: String) {
        _draftState.update { it?.copy(text = text) }
    }

    // Repository dapat diganti saat URL server diubah; arsip mengalir ulang otomatis.
    private val repositoryFlow = MutableStateFlow(createRepository(_serverUrl.value))
    private val repository: SuratRepository get() = repositoryFlow.value

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    val archivedSurat: Flow<List<SuratEntity>> =
        repositoryFlow.flatMapLatest { it.archivedSurat }

    // ════════════════════════ GENERATE / RENDER ════════════════════════

    fun generateNotaDinas(request: GenerateNotaDinasRequest) = launchGeneration {
        repository.generateNotaDinas(request).onSuccess { response ->
            notifyIfLlmDegraded(response.llmDegraded)
            saveToArchive(
                id = response.id, jenisSurat = "nota_dinas", perihal = request.perihal,
                kepada = request.kepada, dari = request.dari,
                downloadUrl = response.downloadUrl, jsonContent = response.kontenSurat.orEmpty()
            )
            emitOpenPreview(response.downloadUrl, request.perihal)
        }.onFailure { emitToast("Error: ${it.message}") }
    }

    fun generateSuratUmum(request: GenerateSuratUmumRequest) = launchGeneration {
        repository.generateSuratUmum(request).onSuccess { response ->
            notifyIfLlmDegraded(response.llmDegraded)
            saveToArchive(
                id = response.id, jenisSurat = "surat_umum", perihal = request.perihal,
                kepada = request.namaPenerima, dari = request.namaPengirim,
                downloadUrl = response.downloadUrl, jsonContent = response.kontenSurat.orEmpty()
            )
            emitOpenPreview(response.downloadUrl, request.perihal)
        }.onFailure { emitToast("Error: ${it.message}") }
    }

    fun generateKajian(request: KajianGenerateRequest) = launchGeneration {
        repository.generateKajian(request).onSuccess { response ->
            notifyIfLlmDegraded(response.llmDegraded)
            val isKka = (request.kategori == KajianCategory.KKA_SESKOAL)
            saveToArchive(
                id = response.suratId,
                jenisSurat = if (isKka) "kka_seskoal" else "telaahan_staf",
                perihal = request.judulAtauTopik,
                kepada = if (isKka) "Komandan Sesko" else "Pimpinan",
                dari = request.namaPejabatAtauPasis,
                downloadUrl = response.downloadUrl,
                jsonContent = response.kontenKajian
            )
            emitOpenPreview(response.downloadUrl, request.judulAtauTopik)
        }.onFailure { emitToast("Error Kajian: ${it.message}") }
    }

    fun renderKajianPdf(request: KajianRenderPDFRequest) = launchGeneration {
        repository.renderKajianPdf(request).onSuccess { response ->
            // Respons render membawa llm_degraded juga — jangan lewatkan peringatan.
            notifyIfLlmDegraded(response.llmDegraded)
            val isKka = (request.kategori == KajianCategory.KKA_SESKOAL)
            saveToArchive(
                id = response.suratId,
                jenisSurat = if (isKka) "kka_seskoal" else "telaahan_staf",
                perihal = request.judulAtauTopik,
                kepada = if (isKka) "Komandan Sesko" else "Pimpinan",
                dari = request.namaPejabatAtauPasis,
                downloadUrl = response.downloadUrl,
                jsonContent = response.kontenKajian
            )
            emitOpenPreview(response.downloadUrl, request.judulAtauTopik)
        }.onFailure { emitToast("Error Render Kajian: ${it.message}") }
    }

    fun generateLapju(request: LapjuGenerateRequest) = launchGeneration {
        repository.generateLapju(request).onSuccess { response ->
            saveToArchive(
                id = response.suratId, jenisSurat = "lapju", perihal = request.perihal,
                kepada = request.kepadaYth, dari = request.namaPenandatangan,
                downloadUrl = response.downloadUrl,
                jsonContent = "Laporan Kemajuan Belanja Modal Periode ${request.bulan} ${request.tahun}\nNomor: ${response.nomorSurat}"
            )
            emitOpenPreview(response.downloadUrl, request.perihal)
        }.onFailure { emitToast("Error Generate Lapju: ${it.message}") }
    }

    // ════════════════════════ DRAFT (pratinjau & edit) ════════════════════════
    // Hasil draf ditulis ke _draftState (bukan callback layar) sehingga tidak
    // hilang saat pengguna pindah tab bottom-nav selama AI menyusun.

    private fun mulaiDraft(type: DraftType) {
        if (_draftState.value?.isLoading == true) {
            _events.trySend(UiEvent.ShowToast("Masih ada draf yang sedang disusun — tunggu hingga selesai."))
            return
        }
        _draftState.value = DraftUiState(type = type, isLoading = true, failed = false, text = "", dismissed = false)
    }

    fun draftNotaDinas(request: GenerateNotaDinasRequest) {
        mulaiDraft(DraftType.NOTA_DINAS)
        viewModelScope.launch {
            repository.draftNotaDinas(request).onSuccess { response ->
                notifyIfLlmDegraded(response.llmDegraded)
                // Editor memuat PASAL ISI SAJA — teks gabungan utuh dikirim balik
                // sebagai konten_custom membuat backend memecahnya jadi pasal
                // (struktur surat terduplikasi di PDF — tertangkap trial).
                val pasal = response.isiList.joinToString("\n\n") { p ->
                    if (!p.subPoin.isNullOrEmpty()) {
                        p.teks + "\n" + p.subPoin.mapIndexed { j, s -> "${'a' + j}. $s" }.joinToString("\n")
                    } else p.teks
                }
                _draftState.update { it?.copy(isLoading = false, text = pasal, dismissed = false) }
            }.onFailure { e ->
                emitToast("Gagal menyusun draf: ${e.message}")
                _draftState.update { st -> st?.copy(isLoading = false, failed = true, text = fallbackFailedDraft(e.message), dismissed = false) }
            }
        }
    }

    fun draftSuratUmum(request: GenerateSuratUmumRequest) {
        mulaiDraft(DraftType.SURAT_UMUM)
        viewModelScope.launch {
            repository.draftSuratUmum(request).onSuccess { response ->
                notifyIfLlmDegraded(response.llmDegraded)
                _draftState.update { it?.copy(isLoading = false, text = response.kontenDraft, dismissed = false) }
            }.onFailure { e ->
                emitToast("Gagal menyusun draf: ${e.message}")
                _draftState.update { st -> st?.copy(isLoading = false, failed = true, text = fallbackFailedDraft(e.message), dismissed = false) }
            }
        }
    }

    fun draftKajian(request: KajianGenerateRequest) {
        mulaiDraft(DraftType.KAJIAN)
        viewModelScope.launch {
            repository.draftKajian(request).onSuccess { response ->
                notifyIfLlmDegraded(response.llmDegraded)
                _draftState.update {
                    it?.copy(isLoading = false, text = response.kontenKajian, sections = response.sections, dismissed = false)
                }
            }.onFailure { e ->
                emitToast("Gagal menyusun draf kajian: ${e.message}")
                _draftState.update { st -> st?.copy(isLoading = false, failed = true, text = fallbackFailedDraft(e.message), dismissed = false) }
            }
        }
    }

    fun draftLapju(request: LapjuGenerateRequest) {
        mulaiDraft(DraftType.LAPJU)
        viewModelScope.launch {
            repository.draftLapju(request).onSuccess { response ->
                // Pasal formal saja (bukan ringkasan KOP+rekap — merusak pasal
                // resmi saat dicetak; tertangkap trial di emulator).
                val pasal = if (response.pasalList.isNotEmpty()) {
                    response.pasalList.joinToString("\n\n")
                } else {
                    "1.  Berdasarkan ${request.dasarRujukan} tentang Laporan Kemajuan Belanja Modal Pengadaan Barang/Jasa, bersama ini dikirimkan Laporan Kemajuan Belanja Modal ${request.kopSatker} periode bulan ${request.bulan} TA ${request.tahun} sebagaimana tabel terlampir.\n\n2.  Demikian disampaikan mohon menjadi periksa."
                }
                _draftState.update { it?.copy(isLoading = false, text = pasal, dismissed = false) }
            }.onFailure { e ->
                emitToast("Gagal menyusun draf lapju: ${e.message}")
                _draftState.update { st -> st?.copy(isLoading = false, failed = true, text = fallbackFailedDraft(e.message), dismissed = false) }
            }
        }
    }

    // ════════════════════════ ARSIP & NAVIGASI ════════════════════════

    /** Bangun ulang URL dokumen terhadap host AKTIF — path relatif tersimpan di Room
     *  agar arsip tidak mati setelah alamat server diganti di Pengaturan. */
    fun resolveDocUrl(storedUrl: String?): String = when {
        storedUrl.isNullOrEmpty() -> ""
        storedUrl.startsWith("http://") || storedUrl.startsWith("https://") -> storedUrl
        else -> _serverUrl.value.trimEnd('/') + storedUrl
    }

    fun openArchivedSurat(surat: SuratEntity) {
        if (surat.downloadUrl.isNullOrEmpty()) return
        _events.trySend(
            UiEvent.OpenPreview(resolveDocUrl(surat.downloadUrl), surat.perihal)
        )
    }

    // ════════════════════════ LOGIN / KREDENSIAL ════════════════════════

    /**
     * Verifikasi kredensial nyata ke server (/api/auth/verify, Basic Auth).
     * Bila valid, kredensial disimpan dan otomatis dilampirkan ke setiap request
     * oleh auth interceptor. Server tanpa auth menerima kolom kosong apa pun.
     */
    fun login(username: String, password: String, onResult: (Result<Unit>) -> Unit) {
        viewModelScope.launch {
            val result = repository.verifyCredentials(basicHeaderOf(username, password))
            result.fold(
                onSuccess = {
                    prefs.edit()
                        .putString(KEY_AUTH_USER, username.trim())
                        .putString(KEY_AUTH_PASS, password)
                        .apply()
                    onResult(Result.success(Unit))
                },
                onFailure = { e ->
                    val msg = e.message.orEmpty()
                    onResult(
                        Result.failure(
                            // Repository memformat pesan gagal sebagai "... (HTTP <code>)"
                            if (msg.contains("(HTTP 401)")) Exception("Username atau password salah.")
                            else e
                        )
                    )
                }
            )
        }
    }

    /**
     * Simpan kredensial. Password null/kosong = TIDAK berubah (sesuai janji label
     * UI "Password tidak berubah bila kosong") — sebelumnya nilai kosong menimpa
     * sandi tersimpan sehingga seluruh request berikutnya gagal 401.
     */
    fun updateCredentials(username: String, password: String?) {
        val editor = prefs.edit().putString(KEY_AUTH_USER, username.trim())
        if (!password.isNullOrBlank()) {
            editor.putString(KEY_AUTH_PASS, password)
        }
        editor.apply()
        _events.trySend(UiEvent.ShowToast("Kredensial disimpan"))
    }

    fun getStoredUsername(): String = prefs.getString(KEY_AUTH_USER, "").orEmpty()

    // ── Kunci Biometrik ──

    private val _biometricEnabled = MutableStateFlow(
        prefs.getBoolean(KEY_BIOMETRIC_ENABLED, false)
    )
    val biometricEnabled: StateFlow<Boolean> = _biometricEnabled.asStateFlow()

    /** Toggle nyata: bila aktif, layar Home terkunci di balik BiometricPrompt. */
    fun setBiometricEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_BIOMETRIC_ENABLED, enabled).apply()
        _biometricEnabled.value = enabled
    }

    // Status buka-kunci DI-VM (bukan rememberSaveable): bertahan melewati rotasi,
    // tetapi HILANG saat proses dibunuh sistem — gerbang biometrik tidak bisa
    // dilewati lewat restorasi savedInstanceState.
    private val _biometricUnlocked = MutableStateFlow(false)
    val biometricUnlocked: StateFlow<Boolean> = _biometricUnlocked.asStateFlow()

    fun setBiometricUnlocked(unlocked: Boolean) {
        _biometricUnlocked.value = unlocked
    }

    /** Header Authorization untuk unduhan manual PDF (HttpURLConnection). */
    fun buildBasicAuthHeader(): String? =
        basicHeaderOf(
            prefs.getString(KEY_AUTH_USER, "").orEmpty(),
            prefs.getString(KEY_AUTH_PASS, "").orEmpty()
        )

    private fun basicHeaderOf(user: String, pass: String): String? {
        if (user.isBlank()) return null
        val creds = "${user.trim()}:$pass"
        return "Basic " + java.util.Base64.getEncoder().encodeToString(creds.toByteArray())
    }

    // ════════════════════════ PENGATURAN SERVER ════════════════════════

    /**
     * Validasi SEBELUM persist: URL tanpa skema membuat Retrofit.baseUrl()
     * melempar IllegalArgumentException → crash saat ini DAN crash-loop setiap
     * launch berikutnya. Input tidak valid ditolak dengan Toast.
     */
    fun saveServerUrl(rawUrl: String) {
        val normalized = normalizeServerUrl(rawUrl)
        if (normalized == null) {
            _events.trySend(
                UiEvent.ShowToast(
                    "URL tidak valid. Gunakan format http://<alamat-server>:<port> " +
                        "(contoh: http://192.168.1.100:8001)"
                )
            )
            return
        }
        prefs.edit().putString(KEY_SERVER_URL, normalized).apply()
        _serverUrl.value = normalized
        repositoryFlow.value = createRepository(normalized)
        _events.trySend(UiEvent.ShowToast("URL Server Diperbarui"))
    }

    /**
     * Uji koneksi ke URL KANDIDAT (isi kolom yang sedang diedit) — bukan hanya
     * URL tersimpan — agar "Tes Koneksi" tidak memberi sinyal palsu.
     * Bila url null/kosong, pakai URL tersimpan.
     */
    fun testConnection(rawUrl: String? = null) {
        viewModelScope.launch {
            val target = rawUrl?.takeIf { it.isNotBlank() }?.let { normalizeServerUrl(it) }
            if (rawUrl != null && rawUrl.isNotBlank() && target == null) {
                _connectionStatus.value = "URL tidak valid. Format: http://<alamat>:<port>"
                return@launch
            }
            val url = target ?: _serverUrl.value
            _connectionStatus.value = "Menguji koneksi ke $url..."
            try {
                // Service sementara khusus untuk URL kandidat (tidak mengubah yang tersimpan)
                val res = createApiService(url).checkHealth()
                _connectionStatus.value = if (res.isSuccessful) {
                    "Terhubung! Status: ${res.body()?.status}"
                } else {
                    "Gagal terhubung: Code ${res.code()}"
                }
            } catch (e: Exception) {
                _connectionStatus.value = "Koneksi gagal: ${e.message}"
            }
        }
    }

    // ════════════════════════ INTERNAL ════════════════════════

    /**
     * Kerangka bersama seluruh aksi generasi/render:
     * - Guard double-submit: abaikan tap kedua selama satu generasi berjalan.
     * - Berjalan di viewModelScope → aman terhadap rotasi Activity.
     */
    private fun launchGeneration(block: suspend () -> Unit) {
        if (_isLoading.value) {
            // Jangan buang submit secara senyap — beri tahu pengguna kenapa tidak jalan.
            _events.trySend(
                UiEvent.ShowToast("Masih ada proses yang berjalan — tunggu hingga selesai.")
            )
            return
        }
        viewModelScope.launch {
            _isLoading.value = true
            try {
                block()
            } finally {
                _isLoading.value = false
            }
        }
    }

    private suspend fun saveToArchive(
        id: String?,
        jenisSurat: String,
        perihal: String,
        kepada: String?,
        dari: String?,
        downloadUrl: String?,
        jsonContent: String
    ) {
        if (id == null) return
        repository.saveSurat(
            SuratEntity(
                id = id,
                jenisSurat = jenisSurat,
                perihal = perihal,
                kepada = kepada ?: "",
                dari = dari ?: "",
                downloadUrl = downloadUrl, // path relatif: tahan perubahan host server
                jsonContent = jsonContent
            )
        )
    }

    private fun fallbackFailedDraft(message: String?): String =
        "⚠️ GAGAL MENYUSUN DRAF ($message). Jangan cetak dokumen ini — " +
            "periksa koneksi server/Ollama lalu susun ulang draf."

    private suspend fun notifyIfLlmDegraded(degraded: Boolean?) {
        if (degraded == true) {
            _events.send(
                UiEvent.ShowToast(
                    "⚠️ Ollama lokal tidak merespons — hasil memakai templat standar, " +
                        "mohon periksa ulang naskah."
                )
            )
        }
    }

    private suspend fun emitOpenPreview(downloadUrl: String?, perihal: String) {
        if (!downloadUrl.isNullOrEmpty()) {
            _events.send(UiEvent.OpenPreview(resolveDocUrl(downloadUrl), perihal))
        }
    }

    private suspend fun emitToast(message: String) {
        _events.send(UiEvent.ShowToast(message))
    }

    /**
     * Normalisasi + validasi URL server. Mengembalikan null bila tidak valid
     * (tanpa skema http/https atau tanpa host) sehingga pemanggil bisa menolak
     * input alih-alih crash di Retrofit.Builder.baseUrl().
     */
    private fun normalizeServerUrl(raw: String?): String? {
        val trimmed = raw?.trim().orEmpty()
        if (trimmed.isEmpty()) return null
        val withScheme =
            if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) "http://$trimmed"
            else trimmed
        val validUrl = if (withScheme.endsWith("/")) withScheme else "$withScheme/"
        // toHttpUrlOrNull mengembalikan null (bukan melempar) untuk URL tidak valid.
        return if (validUrl.toHttpUrlOrNull() != null) validUrl else null
    }

    private fun createApiService(baseUrl: String): ApiService {
        val logging = HttpLoggingInterceptor().apply {
            // BODY mencatat seluruh isi surat (identitas pejabat, NRP, redaksi
            // naskah dinas) ke logcat — hanya untuk debug; rilis WAJIB NONE.
            level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
            else HttpLoggingInterceptor.Level.NONE
            // Kredensial Basic Auth TIDAK boleh muncul di logcat walau build debug
            redactHeader("Authorization")
        }

        val client = baseHttpClient.newBuilder()
            .addInterceptor(logging)
            .addInterceptor(authInterceptor())
            .build()

        val validUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

        return Retrofit.Builder()
            .baseUrl(validUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    private fun createRepository(baseUrl: String): SuratRepository =
        SuratRepository(
            createApiService(baseUrl),
            AppDatabase.getDatabase(getApplication()).suratDao()
        )

    /**
     * Lampirkan kredensial Basic Auth ke setiap request dari preferensi tersimpan.
     * Request yang SUDAH membawa Authorization (mis. verifikasi login dengan
     * kredensial yang baru diketik) diteruskan tanpa ditimpa.
     */
    private fun authInterceptor() = Interceptor { chain ->
        val request = chain.request()
        if (request.header("Authorization") != null) {
            chain.proceed(request)
        } else {
            buildBasicAuthHeader()?.let { header ->
                chain.proceed(request.newBuilder().header("Authorization", header).build())
            } ?: chain.proceed(request)
        }
    }
}
