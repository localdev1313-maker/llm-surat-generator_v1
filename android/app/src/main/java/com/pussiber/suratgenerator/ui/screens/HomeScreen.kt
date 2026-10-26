package com.pussiber.suratgenerator.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.pussiber.suratgenerator.R
import com.pussiber.suratgenerator.DraftUiState
import com.pussiber.suratgenerator.data.local.SuratEntity
import com.pussiber.suratgenerator.data.model.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    suratList: List<SuratEntity>,
    onGenerateNotaDinas: (GenerateNotaDinasRequest) -> Unit,
    onGenerateSuratUmum: (GenerateSuratUmumRequest) -> Unit,
    onDraftNotaDinas: (GenerateNotaDinasRequest) -> Unit,
    onDraftSuratUmum: (GenerateSuratUmumRequest) -> Unit,
    onGenerateKajian: (KajianGenerateRequest) -> Unit,
    onDraftKajian: (KajianGenerateRequest) -> Unit,
    onRenderKajianPdf: (KajianRenderPDFRequest) -> Unit,
    onGenerateLapju: (LapjuGenerateRequest) -> Unit,
    onDraftLapju: (LapjuGenerateRequest) -> Unit,
    onSelectSurat: (SuratEntity) -> Unit,
    draftState: DraftUiState?,
    onDraftDismiss: () -> Unit,
    onDraftTextChange: (String) -> Unit,
    serverUrl: String,
    authUsername: String,
    onSaveServerUrl: (String) -> Unit,
    onSaveCredentials: (String, String) -> Unit,
    onTestConnection: (String) -> Unit,
    connectionStatus: String?,
    isLoading: Boolean,
    biometricEnabled: Boolean,
    onToggleBiometric: (Boolean) -> Unit,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableIntStateOf(0) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Image(
                            painter = painterResource(id = R.drawable.logo_utama),
                            contentDescription = "Logo SSEB AI",
                            contentScale = ContentScale.Fit,
                            modifier = Modifier
                                .size(36.dp)
                                .clip(RoundedCornerShape(8.dp))
                        )
                        Column {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(
                                    text = "SSEB AI",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface
                                )
                                Surface(
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    shape = RoundedCornerShape(4.dp)
                                ) {
                                    Text(
                                        text = "TNI",
                                        style = MaterialTheme.typography.labelSmall,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                                        modifier = Modifier.padding(horizontal = 5.dp, vertical = 1.dp)
                                    )
                                }
                            }
                            Text(
                                text = "Standar KEP/868/IX/2022 & Sesko 2020",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(
                            Icons.AutoMirrored.Filled.Logout,
                            contentDescription = "Keluar / Logout",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                contentColor = MaterialTheme.colorScheme.primary,
                tonalElevation = 4.dp
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.AutoAwesome, contentDescription = null) },
                    label = { Text("Buat Naskah", fontWeight = if (selectedTab == 0) FontWeight.Bold else FontWeight.Normal) }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.Folder, contentDescription = null) },
                    label = { Text("Arsip & Draf", fontWeight = if (selectedTab == 1) FontWeight.Bold else FontWeight.Normal) }
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.Settings, contentDescription = null) },
                    label = { Text("Pengaturan", fontWeight = if (selectedTab == 2) FontWeight.Bold else FontWeight.Normal) }
                )
            }
        }
    ) { paddingValues ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            color = MaterialTheme.colorScheme.background
        ) {
            when (selectedTab) {
                0 -> GenerateScreen(
                    onGenerateNotaDinas = onGenerateNotaDinas,
                    onGenerateSuratUmum = onGenerateSuratUmum,
                    onDraftNotaDinas = onDraftNotaDinas,
                    onDraftSuratUmum = onDraftSuratUmum,
                    onGenerateKajian = onGenerateKajian,
                    onDraftKajian = onDraftKajian,
                    onRenderKajianPdf = onRenderKajianPdf,
                    onGenerateLapju = onGenerateLapju,
                    onDraftLapju = onDraftLapju,
                    draftState = draftState,
                    onDraftDismiss = onDraftDismiss,
                    onDraftTextChange = onDraftTextChange,
                    isLoading = isLoading
                )
                1 -> DraftsScreen(
                    suratList = suratList,
                    onSelectSurat = onSelectSurat
                )
                2 -> SettingsScreen(
                    serverUrl = serverUrl,
                    authUsername = authUsername,
                    onSaveServerUrl = onSaveServerUrl,
                    onSaveCredentials = onSaveCredentials,
                    onTestConnection = onTestConnection,
                    connectionStatus = connectionStatus,
                    biometricEnabled = biometricEnabled,
                    onToggleBiometric = onToggleBiometric
                )
            }
        }
    }
}

