package com.pussiber.suratgenerator.ui.screens

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.net.Uri
import android.os.ParcelFileDescriptor
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PreviewPdfScreen(
    pdfUrl: String,
    perihal: String,
    authHeader: String? = null,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    var pdfBitmaps by remember { mutableStateOf<List<Bitmap>>(emptyList()) }
    var localPdfFile by remember { mutableStateOf<File?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(pdfUrl) {
        isLoading = true
        errorMessage = null
        try {
            val file = withContext(Dispatchers.IO) {
                downloadPdfToFile(context, pdfUrl, authHeader)
            }
            localPdfFile = file
            val bitmaps = withContext(Dispatchers.IO) {
                renderPdfToBitmaps(file)
            }
            pdfBitmaps = bitmaps
            isLoading = false
        } catch (e: Exception) {
            isLoading = false
            errorMessage = "Gagal memuat PDF: ${e.message}"
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(perihal.ifBlank { "Pratinjau Naskah Dinas" }, maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Kembali")
                    }
                },
                actions = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.Edit, contentDescription = "Edit Naskah")
                    }
                    IconButton(onClick = {
                        localPdfFile?.let { file ->
                            sharePdfFile(context, file, perihal)
                        } ?: Toast.makeText(context, "PDF sedang diunduh...", Toast.LENGTH_SHORT).show()
                    }) {
                        Icon(Icons.Default.Share, contentDescription = "Bagikan")
                    }
                    IconButton(onClick = {
                        localPdfFile?.let { file ->
                            openPdfWithExternalApp(context, file)
                        } ?: run {
                            try {
                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(pdfUrl)))
                            } catch (e: Exception) {
                                // Perangkat tanpa handler http (browser) — jangan crash
                                Toast.makeText(context, "Tidak ada aplikasi untuk membuka tautan ini", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }) {
                        Icon(Icons.Default.OpenInNew, contentDescription = "Buka di App PDF Eksternal")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background),
            contentAlignment = Alignment.Center
        ) {
            if (isLoading) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(12.dp))
                    Text("Mengunduh & merender dokumen PDF...", style = MaterialTheme.typography.bodyMedium)
                }
            } else if (errorMessage != null) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(errorMessage ?: "", color = MaterialTheme.colorScheme.error)
                    Spacer(Modifier.height(12.dp))
                    Button(onClick = {
                        try {
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(pdfUrl)))
                        } catch (e: Exception) {
                            Toast.makeText(context, "Tidak ada aplikasi browser pada perangkat ini", Toast.LENGTH_SHORT).show()
                        }
                    }) {
                        Text("Buka via Browser")
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(pdfBitmaps) { bitmap ->
                        Card(
                            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
                            shape = RoundedCornerShape(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Image(
                                bitmap = bitmap.asImageBitmap(),
                                contentDescription = "Halaman PDF",
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                }
            }
        }
    }
}

private fun downloadPdfToFile(context: Context, urlString: String, authHeader: String?): File {
    // Bersihkan sisa file pratinjau sebelumnya agar cacheDir tidak menumpuk tanpa batas
    context.cacheDir.listFiles { f -> f.name.startsWith("preview_document_") }?.forEach { it.delete() }

    val connection = URL(urlString).openConnection() as HttpURLConnection
    try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 15000
        connection.readTimeout = 30000
        // Endpoint /download dilindungi Basic Auth — lampirkan kredensial tersimpan.
        if (!authHeader.isNullOrBlank()) {
            connection.setRequestProperty("Authorization", authHeader)
        }
        connection.connect()

        // Validasi respons sebelum menyimpan — tanpa ini, halaman error 404/500 ikut
        // tersimpan sebagai .pdf dan membuat PdfRenderer melempar "invalid document".
        val code = connection.responseCode
        if (code != HttpURLConnection.HTTP_OK) {
            throw IOException("Server merespons HTTP $code — PDF belum tersedia atau ID tidak ditemukan.")
        }
        val contentType = connection.contentType
        if (contentType != null && contentType.substringBefore(';').trim().equals("text/html", ignoreCase = true)) {
            throw IOException("Server mengembalikan halaman HTML, bukan berkas PDF.")
        }

        val file = File(context.cacheDir, "preview_document_${System.currentTimeMillis()}.pdf")
        try {
            connection.inputStream.use { input ->
                FileOutputStream(file).use { output ->
                    input.copyTo(output)
                }
            }
            return file
        } catch (e: Exception) {
            // Buang unduhan parsial — sisa file akan dirender sebagai PDF rusak
            // atau menumpuk di cacheDir tanpa batas.
            file.delete()
            throw e
        }
    } finally {
        connection.disconnect()
    }
}

private fun renderPdfToBitmaps(pdfFile: File): List<Bitmap> {
    val bitmaps = mutableListOf<Bitmap>()
    // try/finally berlapis: jika openPage/render/createBitmap melempar (mis. PDF
    // terpotong dari unduhan gagal), renderer dan file descriptor TETAP ditutup —
    // tanpa ini setiap percobaan ulang bocorkan satu native file descriptor.
    val fileDescriptor = ParcelFileDescriptor.open(pdfFile, ParcelFileDescriptor.MODE_READ_ONLY)
    try {
        val renderer = PdfRenderer(fileDescriptor)
        try {
            for (i in 0 until renderer.pageCount) {
                val page = renderer.openPage(i)
                try {
                    // Skala dibatasi: 2x untuk halaman normal, tapi sisi terpanjang
                    // tidak melewati MAX_RENDER_DIMENSION — dokumen berukuran besar/
                    // banyak halaman sebelumnya bisa menghabiskan ~8MB per halaman
                    // ARGB_8888 dan memicu OutOfMemoryError di perangkat RAM kecil.
                    val longestSide = maxOf(page.width, page.height)
                    val scale = minOf(2f, MAX_RENDER_DIMENSION.toFloat() / longestSide)
                    val bitmapWidth = (page.width * scale).toInt().coerceAtLeast(1)
                    val bitmapHeight = (page.height * scale).toInt().coerceAtLeast(1)
                    val bitmap = Bitmap.createBitmap(bitmapWidth, bitmapHeight, Bitmap.Config.ARGB_8888)
                    page.render(bitmap, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    bitmaps.add(bitmap)
                } finally {
                    page.close()
                }
            }
        } finally {
            renderer.close()
        }
    } finally {
        fileDescriptor.close()
    }
    return bitmaps
}

/** Batas dimensi render bitmap pratinjau (px) — kontrol konsumsi memori per halaman. */
private const val MAX_RENDER_DIMENSION = 2048

private fun sharePdfFile(context: Context, file: File, perihal: String) {
    try {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        val shareIntent = Intent().apply {
            action = Intent.ACTION_SEND
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, perihal)
            type = "application/pdf"
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(shareIntent, "Bagikan Naskah Dinas PDF"))
    } catch (e: Exception) {
        Toast.makeText(context, "Gagal membagikan: ${e.message}", Toast.LENGTH_LONG).show()
    }
}

private fun openPdfWithExternalApp(context: Context, file: File) {
    try {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file
        )
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/pdf")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "Buka Dokumen PDF"))
    } catch (e: Exception) {
        Toast.makeText(context, "Gagal membuka PDF: ${e.message}", Toast.LENGTH_LONG).show()
    }
}
