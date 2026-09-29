# 📱 Pussiber AI Mobile — LLM Surat & Nota Dinas Generator (Android Version)

Aplikasi Android Native (Kotlin + Jetpack Compose) untuk pembuatan **Surat Resmi** dan **Nota Dinas Baku Militer** secara cepat menggunakan kecerdasan buatan lokal (**Local LLM** via Ollama) dan rendering PDF langsung dari smartphone atau tablet.

---

## 🌟 Fitur Utama (Android Mobile)

- **Input Cepat & Dikte Suara (Speech-to-Text)**: Memungkinkan penyusunan draf naskah dinas melalui pendiktean suara atau pengisian poin-poin ringkas (*progressive disclosure*).
- **Format Nota Dinas Baku Pussiber**: Layout presisi 100% (margin A4, kop instansi, nomor surat, dasar hukum bernomor abjad `a., b.`, isi bernomor angka, dan blok tanda tangan).
- **Arsitektur Hybrid AI**:
  - **Intranet Mode**: Terhubung ke backend server FastAPI + Ollama (`qwen2.5:14b`) via Wi-Fi internal.
  - **Offline Mode**: Berjalan 100% tanpa jaringan menggunakan *On-Device LLM* (`qwen2.5:1.5b/3b`).
- **Pratinjau PDF & Berbagi Instan**: Pratinjau PDF *native*, integrasi *Android Share Sheet* (ke Telegram, Signal, WhatsApp), serta *Direct Wi-Fi Printing*.
- **Keamanan Tingkat Tinggi**: Autentikasi Biometrik (sidik jari/wajah) dan penyimpanan draf lokal terenkripsi (*Room Database + SQLCipher*).

---

## 📁 Struktur Proyek

```
llm-surat-generator_android_version_v1/
├── android/                           # Proyek Android Native (Kotlin + Jetpack Compose)
│   ├── app/
│   │   ├── build.gradle.kts           # Dependencies (Compose, Room, Retrofit, SQLCipher, Biometric)
│   │   └── src/main/
│   │       ├── AndroidManifest.xml    # Permissions (Internet, Biometric, Record Audio)
│   │       ├── java/com/pussiber/suratgenerator/
│   │       │   ├── MainActivity.kt    # Entry Point & Navigation
│   │       │   ├── data/              # Models, Retrofit ApiService, Room Database, Repository
│   │       │   └── ui/                # Theme (Material 3), Compose Screens (Generate, Preview, Drafts, Settings)
│   │       └── res/                   # Resource strings, xml, themes
│   ├── build.gradle.kts               # Root Gradle configuration
│   ├── settings.gradle.kts            # Settings Gradle
│   └── gradle.properties              # JVM & AndroidX properties
├── backend/                           # On-Premise Intranet Server (FastAPI + Ollama)
│   ├── app/                           # Main FastAPI app, routes, LLM & PDF services
│   ├── run.py                         # FastAPI server launcher (Port 8001)
│   └── requirements.txt
├── PRD.md                             # Product Requirement Document (v2.0.0-alpha)
├── PRODUCT.md                         # Product specification
└── README.md
```

---

## 🧰 Prasyarat Pengembangan

1. **Pengembangan Aplikasi Android**:
   - **Android Studio** (Hedgehog / Iguana / Jellyfish atau lebih baru)
   - **JDK 17** (Java Development Kit 17 LTS)
   - Perangkat fisik Android (Android 10.0+ / API 29+) atau Android Emulator.

2. **Server Backend Intranet**:
   - **Python 3.11+**
   - **Ollama** dengan model `qwen2.5:14b` (`ollama pull qwen2.5:14b`)
   - **wkhtmltopdf** terinstal pada server.

---

## 🚀 Cara Menjalankan

### 1. Menjalankan Server Backend (Intranet API)

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
python run.py
```
Server akan berjalan di `http://0.0.0.0:8001`. Tes status kesehatan server via browser: `http://localhost:8001/api/health`.

### 2. Membuka & Membangun Aplikasi Android

1. Buka **Android Studio**.
2. Pilih **Open an Existing Project**, lalu arahkan ke folder `android/`.
3. Biarkan Gradle melakukan sinkronisasi dependensi (*Gradle Sync*).
4. Jalankan aplikasi pada **Android Emulator** atau **Smartphone Android** (dengan mengaktifkan *USB Debugging*).
5. Pada menu **Pengaturan** aplikasi Android, masukkan URL Server (contoh: `http://10.0.2.2:8001/` untuk Android Emulator atau IP lokal server `http://192.168.x.x:8001/` untuk ponsel fisik).

---

## 📄 Lisensi & Klasifikasi Data

Terbatas / Internal Pusat Siber Pertahanan (Pussiber). 100% Air-Gapped & Offline Capable.