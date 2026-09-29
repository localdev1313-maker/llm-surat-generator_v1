package com.pussiber.suratgenerator

import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.pussiber.suratgenerator.ui.screens.HomeScreen
import com.pussiber.suratgenerator.ui.screens.LoginScreen
import com.pussiber.suratgenerator.ui.screens.PreviewPdfScreen
import com.pussiber.suratgenerator.ui.theme.PussiberSuratGeneratorTheme

/**
 * Activity kini TIPIS: hanya meng-host Compose, mengumpulkan state ViewModel,
 * dan mengonsumsi event satu-kali (navigasi pratinjau, Toast).
 *
 * Turunan FragmentActivity karena androidx.biometric.BiometricPrompt
 * mensyaratkannya — ini yang membuat saklar "Kunci Biometrik" benar-benar
 * berfungsi (sebelumnya hanya dekoratif).
 */
class MainActivity : FragmentActivity() {

    private val viewModel: SuratViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            PussiberSuratGeneratorTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val navController = rememberNavController()
                    val suratList by viewModel.archivedSurat.collectAsState(initial = emptyList())
                    val isLoading by viewModel.isLoading.collectAsState()
                    val connectionStatus by viewModel.connectionStatus.collectAsState()
                    val serverUrl by viewModel.serverUrl.collectAsState()
                    val biometricEnabled by viewModel.biometricEnabled.collectAsState()
                    // Status unlock di ViewModel: bertahan saat rotasi, NOL saat proses
                    // dibunuh — gerbang tidak bisa dilewati via savedInstanceState.
                    val biometricUnlocked by viewModel.biometricUnlocked.collectAsState()
                    // State dialog draf dimiliki VM — dialog & hasil draf tetap hidup
                    // saat pengguna pindah tab bottom-nav selama AI menyusun.
                    val draftState by viewModel.draftState.collectAsState()

                    // rememberSaveable: payload pratinjau bertahan melewati rotasi,
                    // karena backstack "preview" direstorasi oleh NavController.
                    var currentPdfUrl by rememberSaveable { mutableStateOf("") }
                    var currentPerihal by rememberSaveable { mutableStateOf("") }

                    // Konsumsi event satu-kali dari ViewModel (navigasi + Toast)
                    LaunchedEffect(Unit) {
                        viewModel.events.collect { event ->
                            when (event) {
                                is UiEvent.OpenPreview -> {
                                    currentPdfUrl = event.pdfUrl
                                    currentPerihal = event.perihal
                                    navController.navigate("preview")
                                }
                                is UiEvent.ShowToast ->
                                    Toast.makeText(applicationContext, event.message, Toast.LENGTH_LONG).show()
                            }
                        }
                    }

                    NavHost(navController = navController, startDestination = "login") {
                        composable("login") {
                            LoginScreen(
                                serverUrl = serverUrl,
                                onSaveServerUrl = viewModel::saveServerUrl,
                                onLogin = { username, password, onResult ->
                                    viewModel.login(username, password, onResult)
                                },
                                onLoginSuccess = {
                                    viewModel.setBiometricUnlocked(!biometricEnabled)
                                    navController.navigate("home") {
                                        popUpTo("login") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("home") {
                            if (biometricEnabled && !biometricUnlocked) {
                                // TIDAK ada tombol pintas nonaktif di sini — mematikan kunci
                                // hanya lewat Pengaturan SETELAH lolos verifikasi; kalau tidak,
                                // siapa pun yang memegang perangkat bisa membuka arsip.
                                BiometricLockScreen(
                                    onUnlocked = { viewModel.setBiometricUnlocked(true) },
                                    onDisableLock = {
                                        // Jalur pemulihan OTOMATIS untuk perangkat tanpa kunci
                                        // layar sama sekali (tidak ada yang bisa diverifikasi).
                                        viewModel.setBiometricEnabled(false)
                                        viewModel.setBiometricUnlocked(true)
                                    }
                                )
                            } else {
                                HomeScreen(
                                    suratList = suratList,
                                    onLogout = {
                                        navController.navigate("login") {
                                            popUpTo("home") { inclusive = true }
                                        }
                                    },
                                    onGenerateNotaDinas = viewModel::generateNotaDinas,
                                    onGenerateSuratUmum = viewModel::generateSuratUmum,
                                    onGenerateKajian = viewModel::generateKajian,
                                    onDraftKajian = viewModel::draftKajian,
                                    onRenderKajianPdf = viewModel::renderKajianPdf,
                                    onGenerateLapju = viewModel::generateLapju,
                                    onDraftLapju = viewModel::draftLapju,
                                    onDraftNotaDinas = viewModel::draftNotaDinas,
                                    onDraftSuratUmum = viewModel::draftSuratUmum,
                                    onSelectSurat = viewModel::openArchivedSurat,
                                    draftState = draftState,
                                    onDraftDismiss = viewModel::dismissDraft,
                                    onDraftTextChange = viewModel::updateDraftText,
                                    serverUrl = serverUrl,
                                    authUsername = viewModel.getStoredUsername(),
                                    onSaveServerUrl = viewModel::saveServerUrl,
                                    onSaveCredentials = viewModel::updateCredentials,
                                    onTestConnection = viewModel::testConnection,
                                    connectionStatus = connectionStatus,
                                    isLoading = isLoading,
                                    biometricEnabled = biometricEnabled,
                                    onToggleBiometric = viewModel::setBiometricEnabled
                                )
                            }
                        }
                        composable("preview") {
                            PreviewPdfScreen(
                                pdfUrl = currentPdfUrl,
                                perihal = currentPerihal,
                                // Unduhan manual PDF juga harus membawa kredensial
                                authHeader = viewModel.buildBasicAuthHeader(),
                                onBack = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * Gerbang kunci biometrik NYATA di depan layar Home.
 *
 * - Memakai BiometricPrompt (biometrik kuat/lemah) dengan fallback kunci layar
 *   perangkat (PIN/pola/sandi) sehingga pengguna tanpa sidik jari tetap bisa masuk.
 * - Bila perangkat sama sekali tidak punya kunci layar, kunci otomatis dilonggarkan
 *   (onDisableLock) daripada mengurung pemilik perangkat selamanya.
 */
@Composable
private fun BiometricLockScreen(
    onUnlocked: () -> Unit,
    onDisableLock: () -> Unit
) {
    val context = LocalContext.current
    val activity = context as? FragmentActivity
    var lastError by remember { mutableStateOf<String?>(null) }

    fun authenticate() {
        if (activity == null) {
            // Bukan lingkungan FragmentActivity — jangan mengurung pengguna.
            onUnlocked()
            return
        }
        val authenticators = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            BiometricManager.Authenticators.BIOMETRIC_WEAK or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL
        } else {
            BiometricManager.Authenticators.DEVICE_CREDENTIAL
        }
        val canAuth = BiometricManager.from(context).canAuthenticate(authenticators)
        if (canAuth != BiometricManager.BIOMETRIC_SUCCESS) {
            // Tanpa kunci layar/biometrik terdaftar tidak ada yang bisa diverifikasi —
            // longgarkan kunci agar pemilik perangkat tidak terkunci permanen.
            Toast.makeText(
                context,
                "Perangkat belum memiliki kunci layar/biometrik — kunci aplikasi dimatikan.",
                Toast.LENGTH_LONG
            ).show()
            onDisableLock()
            return
        }

        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("Arsip Naskah Dinas Terkunci")
            .setSubtitle("Verifikasi identitas Anda untuk membuka aplikasi")
            .apply {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    setAllowedAuthenticators(authenticators)
                } else {
                    @Suppress("DEPRECATION")
                    setDeviceCredentialAllowed(true)
                }
            }
            .build()

        BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(context),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    onUnlocked()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    if (errorCode != BiometricPrompt.ERROR_USER_CANCELED &&
                        errorCode != BiometricPrompt.ERROR_NEGATIVE_BUTTON
                    ) {
                        lastError = errString.toString()
                    }
                }
            }
        ).authenticate(promptInfo)
    }

    // Picu prompt saat gerbang pertama tampil.
    LaunchedEffect(Unit) { authenticate() }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier.fillMaxSize().padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Image(
                painter = painterResource(id = com.pussiber.suratgenerator.R.drawable.logo_utama),
                contentDescription = "Logo SSEB AI",
                modifier = Modifier.size(96.dp)
            )
            Spacer(Modifier.height(24.dp))
            Icon(
                Icons.Default.Lock,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(40.dp)
            )
            Spacer(Modifier.height(12.dp))
            Text(
                text = "Aplikasi Terkunci",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = "Verifikasi biometrik/PIN perangkat untuk membuka arsip naskah dinas.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Gray,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                modifier = Modifier.padding(vertical = 8.dp)
            )
            lastError?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
                Spacer(Modifier.height(8.dp))
            }
            Button(onClick = { authenticate() }) {
                Text("Buka Kunci")
            }
        }
    }
}
