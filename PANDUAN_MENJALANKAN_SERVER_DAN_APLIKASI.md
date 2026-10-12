# 📖 Panduan Menjalankan SSEB-AI — Server, Website, Bot Telegram & APK Android

## Arsitektur Sistem

```
┌──────────────┐     HTTP API      ┌──────────────────┐     Ollama      ┌──────────┐
│  Website     │◄─────────────────►│  Backend Server  │◄──────────────►│  LLM     │
│  (Frontend)  │   Port 8001       │  (FastAPI/Python) │   Port 11434   │  Lokal   │
└──────────────┘                   └────────┬─────────┘                └──────────┘
                                            │
┌──────────────┐     HTTP API              │
│  APK Android │◄──────────────────────────┤
│  (Kotlin)    │   WiFi/Intranet           │
└──────────────┘                            │
                                            │
┌──────────────┐     Telegram API          │
│  Bot         │◄──────────────────────────┘
│  Telegram    │   (embedded/standalone)
└──────────────┘
```

---

## Prasyarat

| Komponen | Versi Minimum | Keterangan |
|----------|---------------|------------|
| Python | 3.11+ | Runtime backend |
| Ollama | Terbaru | LLM inference engine |
| Model LLM | qwen2.5:14b | `ollama pull qwen2.5:14b` |
| wkhtmltopdf | 0.12.6+ | Konversi HTML → PDF |
| Android Studio | Hedgehog+ | Build APK (opsional) |
| JDK | 17 LTS | Kompilasi Android |

---

## 1️⃣ Menjalankan Backend Server (API + Website)

### a. Persiapan Awal (sekali saja)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### b. Konfigurasi

Salin dan sesuaikan file environment:
```powershell
copy .env.example .env
# Edit .env sesuai kebutuhan (Notepad, VS Code, dll.)
```

**Konfigurasi wajib:**
- `OLLAMA_HOST` — alamat server Ollama (default: http://localhost:11434)
- `WKHTMLTOPDF_PATH` — path ke wkhtmltopdf.exe

**Konfigurasi opsional:**
- `AUTH_USERNAME` & `AUTH_PASSWORD` — aktifkan Basic Auth
- `TELEGRAM_BOT_TOKEN` — aktifkan Bot Telegram

### c. Jalankan Ollama

```powershell
# Terminal terpisah
ollama serve
# Pastikan model sudah di-pull:
ollama pull qwen2.5:14b
```

### d. Jalankan Server

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python run.py
```

Server berjalan di **http://0.0.0.0:8001**

**Verifikasi:**
- Health check: http://localhost:8001/api/health
- Website frontend: http://localhost:8001/
- API Docs (tanpa auth): http://localhost:8001/docs

---

## 2️⃣ Mengakses Website Frontend

Website otomatis tersaji saat server backend berjalan:

- **Lokal:** http://localhost:8001/
- **Jaringan:** http://<IP_SERVER>:8001/

Tidak perlu server frontend terpisah — file `index.html` disajikan langsung oleh FastAPI dari folder `backend/static/`.

---

## 3️⃣ Menjalankan Bot Telegram

### Opsi A: Embedded (otomatis saat server jalan)

1. Dapatkan token dari [@BotFather](https://t.me/BotFather) di Telegram
2. Isi `TELEGRAM_BOT_TOKEN=<token>` di file `backend/.env`
3. Jalankan server (`python run.py`) — bot otomatis aktif

### Opsi B: Standalone (tanpa server)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python run_bot.py
```

> ⚠️ Mode standalone memerlukan server backend tetap berjalan di terminal lain karena bot memanggil API backend untuk generate surat.

### Perintah Bot Telegram

| Perintah | Fungsi |
|----------|--------|
| `/start` | Menu utama — pilih jenis naskah |
| `/batal` | Batalkan percakapan saat ini |

---

## 4️⃣ Aplikasi Android (APK)

### Opsi A: Instal APK yang sudah tersedia

File APK siap pakai tersedia di root proyek:
- `AI_Surat_Generator_Latest.apk` — versi terbaru
- `sseb-ai_v5.apk` — versi stabil terakhir

**Instal ke perangkat Android:**
```powershell
adb install AI_Surat_Generator_Latest.apk
```

Atau transfer file APK ke smartphone dan buka langsung.

### Opsi B: Build dari Source Code

1. Buka **Android Studio**
2. Pilih **Open** → arahkan ke folder `android/`
3. Tunggu Gradle Sync selesai
4. Jalankan di emulator atau perangkat fisik

### Konfigurasi Koneksi Android → Server

Di dalam aplikasi Android, buka **Pengaturan** dan isi:
- **URL Server:** `http://<IP_SERVER>:8001/`
  - Emulator: `http://10.0.2.2:8001/`
  - Fisik (WiFi): `http://192.168.x.x:8001/`
- **Username & Password** (jika auth aktif)

---

## 5️⃣ Menjalankan Seluruh Sistem Sekaligus

Buka 2 terminal PowerShell:

**Terminal 1 — Ollama:**
```powershell
ollama serve
```

**Terminal 2 — Backend + Website + Bot Telegram:**
```powershell
cd d:\DEV_OPS\llm-surat-generator_android_version_v1\backend
.\.venv\Scripts\Activate.ps1
python run.py
```

Setelah server aktif:
- ✅ Website: http://localhost:8001/
- ✅ Bot Telegram: otomatis aktif (jika token diisi)
- ✅ APK Android: hubungkan ke IP server

---

## 🔧 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `Ollama tidak merespons` | Pastikan `ollama serve` berjalan dan model sudah di-pull |
| `wkhtmltopdf not found` | Install dari https://wkhtmltopdf.org dan set path di `.env` |
| `Bot Telegram error` | Pastikan token valid dari @BotFather |
| `Android connection refused` | Cek IP server, pastikan firewall mengizinkan port 8001 |
| `ModuleNotFoundError` | Jalankan `pip install -r requirements.txt` |
| `.venv\Scripts\Activate.ps1 not found` | Gunakan `Activate.ps1` atau buat ulang venv |
