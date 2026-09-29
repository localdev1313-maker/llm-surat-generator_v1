package com.pussiber.suratgenerator.data.remote

import com.pussiber.suratgenerator.data.model.*
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface ApiService {
    @GET("api/health")
    suspend fun checkHealth(): Response<HealthResponse>

    /** Verifikasi kredensial login (Basic Auth) — 200 bila valid / auth nonaktif. */
    @GET("api/auth/verify")
    suspend fun verifyAuth(@Header("Authorization") authorization: String?): Response<HealthResponse>

    @POST("draft-nota-dinas")
    suspend fun draftNotaDinas(@Body request: GenerateNotaDinasRequest): Response<DraftNotaDinasResponse>

    @POST("draft-surat")
    suspend fun draftSuratUmum(@Body request: GenerateSuratUmumRequest): Response<DraftSuratResponse>

    @POST("generate-nota-dinas")
    suspend fun generateNotaDinas(@Body request: GenerateNotaDinasRequest): Response<GenerateResponse>

    @POST("draft-telaahan-staf")
    suspend fun draftTelaahanStaf(@Body request: GenerateTelaahanStafRequest): Response<DraftTelaahanStafResponse>

    @POST("generate-telaahan-staf")
    suspend fun generateTelaahanStaf(@Body request: GenerateTelaahanStafRequest): Response<GenerateResponse>

    @POST("render-telaahan-staf-pdf")
    suspend fun renderTelaahanStafPdf(@Body request: RenderTelaahanStafPdfRequest): Response<GenerateResponse>

    @POST("generate-surat")
    suspend fun generateSuratUmum(@Body request: GenerateSuratUmumRequest): Response<GenerateResponse>

    // ── Kajian Dual-Mode Endpoints ──
    @POST("api/v1/kajian/draft")
    suspend fun draftKajian(@Body request: KajianGenerateRequest): Response<KajianDraftResponse>

    @POST("api/v1/kajian/generate")
    suspend fun generateKajian(@Body request: KajianGenerateRequest): Response<KajianGenerateResponse>

    @POST("api/v1/kajian/render-pdf")
    suspend fun renderKajianPdf(@Body request: KajianRenderPDFRequest): Response<KajianGenerateResponse>

    // ── Laporan Kemajuan (LAPJU) Belanja Modal Endpoints ──
    @POST("api/v1/lapju/draft")
    suspend fun draftLapju(@Body request: LapjuGenerateRequest): Response<LapjuDraftResponse>

    @POST("api/v1/lapju/generate")
    suspend fun generateLapju(@Body request: LapjuGenerateRequest): Response<LapjuGenerateResponse>
}

