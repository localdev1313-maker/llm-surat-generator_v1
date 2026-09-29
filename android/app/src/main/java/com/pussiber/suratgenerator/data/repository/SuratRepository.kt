package com.pussiber.suratgenerator.data.repository

import com.pussiber.suratgenerator.data.local.SuratDao
import com.pussiber.suratgenerator.data.local.SuratEntity
import com.pussiber.suratgenerator.data.model.*
import com.pussiber.suratgenerator.data.remote.ApiService
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import retrofit2.Response

class SuratRepository(
    private val apiService: ApiService,
    private val suratDao: SuratDao
) {
    val archivedSurat: Flow<List<SuratEntity>> = suratDao.getArchivedSurat()
    val drafts: Flow<List<SuratEntity>> = suratDao.getDrafts()

    suspend fun draftNotaDinas(request: GenerateNotaDinasRequest): Result<DraftNotaDinasResponse> =
        apiCall("Gagal menyusun draf nota dinas") { apiService.draftNotaDinas(request) }

    suspend fun draftSuratUmum(request: GenerateSuratUmumRequest): Result<DraftSuratResponse> =
        apiCall("Gagal menyusun draf surat umum") { apiService.draftSuratUmum(request) }

    suspend fun generateNotaDinas(request: GenerateNotaDinasRequest): Result<GenerateResponse> =
        apiCall("Gagal generate nota dinas") { apiService.generateNotaDinas(request) }

    suspend fun draftTelaahanStaf(request: GenerateTelaahanStafRequest): Result<DraftTelaahanStafResponse> =
        apiCall("Gagal menyusun draf telaahan staf") { apiService.draftTelaahanStaf(request) }

    suspend fun generateTelaahanStaf(request: GenerateTelaahanStafRequest): Result<GenerateResponse> =
        apiCall("Gagal generate telaahan staf") { apiService.generateTelaahanStaf(request) }

    suspend fun renderTelaahanStafPdf(request: RenderTelaahanStafPdfRequest): Result<GenerateResponse> =
        apiCall("Gagal render PDF telaahan staf") { apiService.renderTelaahanStafPdf(request) }

    suspend fun generateSuratUmum(request: GenerateSuratUmumRequest): Result<GenerateResponse> =
        apiCall("Gagal generate surat umum") { apiService.generateSuratUmum(request) }

    // ── Kajian Dual-Mode Repository Methods ──
    suspend fun draftKajian(request: KajianGenerateRequest): Result<KajianDraftResponse> =
        apiCall("Gagal menyusun draf kajian") { apiService.draftKajian(request) }

    suspend fun generateKajian(request: KajianGenerateRequest): Result<KajianGenerateResponse> =
        apiCall("Gagal generate kajian") { apiService.generateKajian(request) }

    suspend fun renderKajianPdf(request: KajianRenderPDFRequest): Result<KajianGenerateResponse> =
        apiCall("Gagal render PDF kajian") { apiService.renderKajianPdf(request) }

    // ── Laporan Kemajuan (LAPJU) Repository Methods ──
    suspend fun draftLapju(request: LapjuGenerateRequest): Result<LapjuDraftResponse> =
        apiCall("Gagal menyusun draf lapju") { apiService.draftLapju(request) }

    suspend fun generateLapju(request: LapjuGenerateRequest): Result<LapjuGenerateResponse> =
        apiCall("Gagal generate lapju") { apiService.generateLapju(request) }

    /** Status kesehatan server — endpoint ini selalu terbuka (tanpa auth). */
    suspend fun checkHealth(): Response<HealthResponse> = apiService.checkHealth()

    /** Verifikasi kredensial login terhadap /api/auth/verify (Basic Auth). */
    suspend fun verifyCredentials(authorizationHeader: String?): Result<HealthResponse> =
        apiCall("Autentikasi gagal") { apiService.verifyAuth(authorizationHeader) }

    suspend fun saveSurat(surat: SuratEntity) {
        suratDao.insertSurat(surat)
    }

    suspend fun deleteSurat(surat: SuratEntity) {
        suratDao.deleteSurat(surat)
    }

    /**
     * Pembungkus tunggal untuk SELURUH panggilan API — sebelumnya pola try/isSuccessful/
     * body!!/catch disalin 13 kali dan sudah mendrift (pesan error downloadPdf kehilangan
     * status HTTP). Satu tempat untuk: pemeriksaan body, pesan error, dan penerjemahan
     * exception jaringan menjadi teks yang bisa dipahami pengguna.
     *
     * CancellationException TIDAK ditelan: ia adalah sinyal pembatalan structured
     * concurrency (mis. Activity dibuat ulang saat rotasi), bukan kegagalan jaringan —
     * menelannya membuat pembatalan tampil sebagai "Result.failure" palsu.
     */
    private suspend fun <T> apiCall(errorLabel: String, call: suspend () -> Response<T>): Result<T> =
        try {
            val response = call()
            val body = response.body()
            if (response.isSuccessful && body != null) {
                Result.success(body)
            } else {
                Result.failure(Exception("$errorLabel: ${response.message()} (HTTP ${response.code()})"))
            }
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Result.failure(describeNetworkError(e))
        }

    /**
     * Terjemahkan exception jaringan umum menjadi pesan yang bisa dipahami pengguna,
     * agar kegagalan koneksi tidak hanya tampil sebagai "timeout" generik.
     */
    private fun describeNetworkError(e: Exception): Exception = when (e) {
        is java.net.SocketTimeoutException -> Exception(
            "Waktu tunggu habis (timeout). Server/Ollama kemungkinan masih memproses naskah — tunggu sebentar lalu coba lagi."
        )
        is java.net.ConnectException -> Exception(
            "Tidak dapat terhubung ke server. Periksa URL server di Pengaturan dan pastikan server aktif."
        )
        is java.net.UnknownHostException -> Exception(
            "Host server tidak dikenal. Periksa URL server di Pengaturan."
        )
        else -> e
    }
}
