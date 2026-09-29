package com.pussiber.suratgenerator.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.NetworkCheck
import androidx.compose.material.icons.filled.Save
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    serverUrl: String,
    authUsername: String,
    onSaveServerUrl: (String) -> Unit,
    onSaveCredentials: (String, String) -> Unit,
    onTestConnection: (String) -> Unit,
    connectionStatus: String?,
    biometricEnabled: Boolean,
    onToggleBiometric: (Boolean) -> Unit
) {
    var urlInput by remember { mutableStateOf(serverUrl) }
    var userInput by remember { mutableStateOf(authUsername) }
    var passwordInput by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp)
            .verticalScroll(rememberScrollState())
    ) {
        Text(
            text = "Pengaturan Aplikasi",
            style = MaterialTheme.typography.titleLarge,
            color = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        // Server Configuration Card
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Konfigurasi Server Intranet",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                OutlinedTextField(
                    value = urlInput,
                    onValueChange = { urlInput = it },
                    label = { Text("URL Server Backend") },
                    placeholder = { Text("http://192.168.1.100:8001") },
                    modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp)
                )

                // Risiko koneksi terenkripsi-hilang dibuat TERLIHAT — Basic Auth lewat
                // HTTP polos dapat disadap di jaringan bersama (intranet/Wi-Fi).
                if (!urlInput.trim().startsWith("https://", ignoreCase = true)) {
                    Text(
                        text = "⚠️ Koneksi HTTP tanpa enkripsi: kredensial & isi naskah " +
                            "dapat disadap di jaringan. Untuk keamanan penuh, gunakan " +
                            "server ber-HTTPS (mis. reverse-proxy TLS).",
                        style = MaterialTheme.typography.bodySmall,
                        color = com.pussiber.suratgenerator.ui.theme.StatusWarning,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )
                } else {
                    Spacer(Modifier.height(8.dp))
                }

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { onSaveServerUrl(urlInput) },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Save, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Simpan URL")
                    }
                    OutlinedButton(
                        // Uji URL yang DIKOLOM (kandidat), bukan hanya URL tersimpan —
                        // sebelumnya "Terhubung!" bisa berarti server lama yang masih tersimpan.
                        onClick = { onTestConnection(urlInput) },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.NetworkCheck, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Tes Koneksi")
                    }
                }

                if (connectionStatus != null) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = connectionStatus,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }

        // Catatan: saklar "On-Device LLM (Offline)" DIHAPUS karena tidak pernah
        // terhubung ke mesin inferensi mana pun — menampilkannya menipu pengguna.

        // Security Settings Card
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth().padding(bottom = 16.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Kredensial Server (Basic Auth)",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                Text(
                    text = "Dilampirkan otomatis ke setiap request. Kosongkan bila server tidak mengaktifkan autentikasi.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 12.dp)
                )

                OutlinedTextField(
                    value = userInput,
                    onValueChange = { userInput = it },
                    label = { Text("Username") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().padding(bottom = 10.dp)
                )

                OutlinedTextField(
                    value = passwordInput,
                    onValueChange = { passwordInput = it },
                    label = { Text(if (passwordInput.isBlank()) "Password (tidak berubah bila kosong)" else "Password") },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)
                )

                Button(
                    onClick = { onSaveCredentials(userInput, passwordInput) },
                    enabled = userInput.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Save, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Simpan Kredensial")
                }
            }
        }

        // Security Settings Card — Kunci Biometrik (NYATA: BiometricPrompt di depan Home)
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            shape = RoundedCornerShape(16.dp),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Keamanan & Akses Biometrik",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Kunci Biometrik Saat Dibuka", fontWeight = FontWeight.SemiBold)
                        Text(
                            "Meminta verifikasi sidik jari/wajah/PIN perangkat sebelum masuk arsip naskah",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(
                        checked = biometricEnabled,
                        onCheckedChange = onToggleBiometric
                    )
                }
            }
        }
    }
}
