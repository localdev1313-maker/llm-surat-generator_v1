package com.pussiber.suratgenerator

import com.pussiber.suratgenerator.data.model.*
import com.pussiber.suratgenerator.data.remote.ApiService
import kotlinx.coroutines.runBlocking
import okhttp3.Credentials
import okhttp3.OkHttpClient
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

class AndroidApiIntegrationTest {

    private lateinit var apiService: ApiService

    @Before
    fun setup() {
        val okHttpClient = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(180, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val authHeader = Credentials.basic("admin", "ganti-password-ini")
                val request = chain.request().newBuilder()
                    .header("Authorization", authHeader)
                    .build()
                chain.proceed(request)
            }
            .build()

        val retrofit = Retrofit.Builder()
            .baseUrl("http://127.0.0.1:8001/")
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        apiService = retrofit.create(ApiService::class.java)
    }

    @Test
    fun test1_HealthCheck() = runBlocking {
        val response = apiService.checkHealth()
        assertTrue("Health check HTTP should be 200", response.isSuccessful)
        val body = response.body()
        assertNotNull("Body should not be null", body)
        assertEquals("Status should be ok", "ok", body?.status)
        println("✅ [1/5] Health Check OK: version=${body?.version}")
    }

    @Test
    fun test2_DraftSuratUmum() = runBlocking {
        val request = GenerateSuratUmumRequest(
            jenisSurat = "SURAT EDARAN",
            namaPengirim = "Kolonel Inf. Bambang",
            alamatPengirim = "Pusat Siber Pertahanan, Jakarta",
            namaPenerima = "Mayor Andi",
            alamatPenerima = "Surabaya",
            perihal = "Himbauan Kewaspadaan Phishing",
            isiRingkas = "Ditemukan peningkatan email mencurigakan yang mengatasnamakan pejabat. Seluruh staf diinstruksikan untuk tidak mengklik tautan apapun."
        )

        val response = apiService.draftSuratUmum(request)
        assertTrue("Draft surat HTTP should be 200: ${response.errorBody()?.string()}", response.isSuccessful)
        val body = response.body()
        assertNotNull("Draft body should not be null", body)
        assertFalse("llmDegraded should be false after guardrail regex fix", body?.llmDegraded ?: true)
        assertTrue("kontenDraft should not be empty", !body?.kontenDraft.isNullOrBlank())
        println("✅ [2/5] Draft Surat Umum OK (Length: ${body?.kontenDraft?.length}, Degraded: ${body?.llmDegraded})")
    }

    @Test
    fun test3_DraftNotaDinas() = runBlocking {
        val request = GenerateNotaDinasRequest(
            kopUtama = "PUSAT SIBER PERTAHANAN",
            kopSub = "SATUAN PENGAMANAN SIBER",
            nomorSurat = "B/ND-12/V/2026",
            kepada = "Kepala Pusat Siber Pertahanan",
            dari = "Komandan Satuan Pengamanan Siber",
            perihal = "Permohonan Peningkatan Kapasitas Server SIEM",
            dasar = "Surat Keputusan Kapussiber Nomor Kep/05/I/2026.",
            isiRingkas = listOf(
                PoinNotaDinasModel(
                    teks = "Log traffic firewall mengalami lonjakan 300% sehingga kapasitas server SIEM saat ini mencapai 92%.",
                    subPoin = listOf("Storage tersisa 8% pada volume utama", "CPU load rata-rata mencapai 88%")
                ),
                PoinNotaDinasModel(
                    teks = "Disarankan untuk melakukan penambahan kapasitas RAM 64GB dan storage NVMe 4TB guna menjamin kelancaran analisis ancaman siber."
                )
            ),
            namaPejabat = "Kolonel Laut (E) Hendra Wijaya",
            jabatanPejabat = "Komandan Satuan",
            pangkatPejabat = "Kolonel Laut (E) NRP 14562/P"
        )

        val response = apiService.draftNotaDinas(request)
        assertTrue("Draft nota dinas HTTP should be 200: ${response.errorBody()?.string()}", response.isSuccessful)
        val body = response.body()
        assertNotNull("Draft nota dinas body should not be null", body)
        assertFalse("llmDegraded should be false", body?.llmDegraded ?: true)
        assertTrue("isiList should have items", !body?.isiList.isNullOrEmpty())
        println("✅ [3/5] Draft Nota Dinas OK (Items: ${body?.isiList?.size}, Degraded: ${body?.llmDegraded})")
    }

    @Test
    fun test4_DraftLapju() = runBlocking {
        val request = LapjuGenerateRequest(
            kopUtama = "MARKAS BESAR ANGKATAN LAUT",
            kopSatker = "DINAS PENGADAAN ANGKATAN LAUT",
            nomorSurat = "B/123/IV/2026/Disadal",
            tempat = "Jakarta",
            bulan = "Mei",
            tahun = 2026,
            perihal = "Laporan Kemajuan Belanja Modal Pengadaan Perangkat Siber",
            kepadaYth = "Asisten Logistik Kasal",
            kotaTujuan = "Jakarta",
            dasarRujukan = "DIPA Petikan Tahun Anggaran 2026",
            jabatanPenandatangan = "Kepala Dinas Pengadaan",
            namaPenandatangan = "Laksamana Pertama TNI Sutrisno",
            items = listOf(
                ItemKegiatanLapju(
                    noUrut = 1,
                    namaKegiatan = "Pengadaan Server SIEM",
                    paguAnggaran = 1000000000.0,
                    nilaiKontrak = 950000000.0,
                    nomorKontrak = "KTR/01/V/2026",
                    tanggalKontrak = "10 Mei 2026",
                    tds = "2026-05-10",
                    penyedia = "PT Teknologi Siber Nusantara",
                    anggaranTerserap = 475000000.0,
                    sisaAnggaran = 475000000.0,
                    persentaseFisik = 50,
                    persentaseAdmin = 50,
                    keteranganAdmin = listOf("Tahap Termin 1 Berkas Lengkap"),
                    keteranganFisik = listOf("Perangkat Rack Server Tiba di Lokasi")
                )
            )
        )

        val response = apiService.draftLapju(request)
        assertTrue("Draft Lapju HTTP should be 200: ${response.errorBody()?.string()}", response.isSuccessful)
        val body = response.body()
        assertNotNull("Draft lapju body should not be null", body)
        assertEquals("Status should be success", "success", body?.status)
        assertTrue("ringkasanTeks should not be empty", !body?.ringkasanTeks.isNullOrBlank())
        println("✅ [4/5] Draft LAPJU OK (Status: ${body?.status}, Pagu Total: ${body?.totals?.totalPaguFormatted})")
    }

    @Test
    fun test5_DraftTelaahanStaf() = runBlocking {
        val request = GenerateTelaahanStafRequest(
            kopUtama = "PUSAT SIBER PERTAHANAN",
            kopSatuanBawah = "SATUAN PENGAMANAN SIBER",
            judul = "PENGUATAN KEAMANAN SIBER DATA CENTER",
            nomorNaskah = "TS/05/V/2026",
            inputPersoalan = "Kapasitas firewall utama mendekati batas maksimal akibat lonjakan serangan DDoS.",
            inputFakta = "Terdeteksi 45 kali serangan volume tinggi dalam 30 hari terakhir.",
            inputSaran = "Penyediaan perangkat anti-DDoS terdedikasi dan upgrade bandwidth gateway.",
            namaPejabat = "Kolonel Laut (E) Hendra Wijaya",
            jabatan = "Komandan Satuan",
            pangkatKorpsNrp = "Kolonel Laut (E) NRP 14562/P"
        )

        val response = apiService.draftTelaahanStaf(request)
        assertTrue("Draft Telaahan Staf HTTP should be 200: ${response.errorBody()?.string()}", response.isSuccessful)
        val body = response.body()
        assertNotNull("Draft TS body should not be null", body)
        assertFalse("llmDegraded should be false", body?.llmDegraded ?: true)
        assertTrue("Persoalan should not be empty", body?.pasal?.persoalan?.isNotBlank() ?: false)
        assertTrue("Analisis should not be empty", body?.pasal?.analisis?.isNotBlank() ?: false)
        println("✅ [5/5] Draft Telaahan Staf OK (Pasal Persoalan: ${body?.pasal?.persoalan?.take(50)}...)")
    }
}
