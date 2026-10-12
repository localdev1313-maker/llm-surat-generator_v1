# Product

<!-- impeccable:product-schema 1 -->

## Platform

android

## Users

Staf administrasi dan pimpinan di lingkungan **Satuan Kerja Operasional** dan satuan pelaksananya yang bermobilitas tinggi. Pengguna membuat surat resmi dan nota dinas baku kedinasan/militer langsung dari perangkat genggam (smartphone atau tablet Android) saat bertugas di kantor maupun di lapangan/area operasional.

## Product Purpose

Menghasilkan surat resmi dan nota dinas dalam hitungan detik langsung dari perangkat Android menggunakan AI (hybrid on-device & on-premise). Pengguna cukup mengisi poin-poin utama atau mendiktekan suara; aplikasi meng-generate paragraf formal lengkap dan langsung mengonversi ke PDF siap cetak atau siap dibagikan melalui secure sharing sheet.

## Positioning

Pemrosesan berjalan secara mandiri di perangkat Android (fully offline) menggunakan on-device LLM atau terhubung ke server lokal intranet dinas. Data sensitif diamankan menggunakan enkripsi database lokal dan autentikasi biometrik, menjamin kerahasiaan informasi kedinasan tanpa kebocoran ke cloud publik.

## Operating Context

- Pengguna mengakses melalui aplikasi native Android pada smartphone atau tablet taktis.
- Mendukung dua mode operasi AI: **Offline Mode** (menggunakan model 1.5B/3B lokal pada ponsel) dan **Intranet Mode** (menghubungkan ke backend FastAPI + Ollama `qwen2.5:14b` via Wi-Fi dinas).
- Hasil PDF dapat langsung dicetak nirkabel melalui Android Print Framework atau dibagikan ke aplikasi pesan aman (Telegram/Signal).
- Data draf dan riwayat dokumen disimpan di database lokal Room dengan enkripsi SQLCipher.

## Capabilities and Constraints

### Capabilities
- Generate Surat & Nota Dinas via input poin atau Speech-to-Text (dikte suara).
- Dual Engine LLM: On-device LLM (via llama.cpp/MediaPipe) dan Server-side LLM (via API).
- Render PDF lokal secara native sesuai standar tata naskah dinas militer.
- Keamanan lokal: Autentikasi Biometrik (sidik jari/wajah) dan SQLCipher Encrypted DB.
- Integrasi Android Share Sheet dan Direct Wi-Fi/Bluetooth Printing.

### Constraints
- Membutuhkan sistem operasi Android 10.0+ (API Level 29+).
- Untuk performa On-Device LLM yang optimal, disarankan perangkat dengan RAM minimum 6GB (alokasi runtime model maksimal 2.0GB).
- Model LLM on-device diunduh terpisah demi menjaga ukuran awal file APK tetap ramping.

### Undecided
- Mekanisme penandatanganan QR Code: Apakah sertifikat digital diverifikasi melalui otoritas eksternal atau verifikasi tanda tangan hash lokal di dalam aplikasi.

## Brand Commitments

- Nama instansi default: "PUSAT KOMANDO OPERASI" dengan sub "SATUAN PELAKSANA OPERASI"
- Logo Resmi: Menggunakan lambang resmi "Autonomous AI Surat Generator" (`android/app/src/main/res/drawable/logo_utama.jpg`) yang menampilkan stempel lingkar emas formal, pena bulu emas & tempat tinta, dokumen naskah dinas, serta sirkuit AI.
- Format dokumen wajib mengikuti standar baku tata naskah dinas kedinasan/militer (kop, margin presisi, penomoran dasar abjad, penomoran isi angka, dan penutup formal).
- Identitas visual bernuansa taktis/militer modern (olive green, dark indigo & gold accent) yang disesuaikan dengan lambang resmi dan panduan Material You (Material 3).

## Evidence on Hand

- Lambang Resmi: `logo_utama.jpg` tersimpan di `android/app/src/main/res/drawable/logo_utama.jpg` dan `backend/static/logo_utama.jpg`.
- 50 contoh nota dinas dummy (DOCX) di `fine-tune-dokumen/` sebagai acuan format.
- Struktur template HTML yang siap dikonversi ke engine rendering Android WebView Print.


## Product Principles

1. **Portabilitas & Keamanan Utama** - Akses dokumen dinas kapan saja, di mana saja, dengan perlindungan data tingkat militer pada perangkat.
2. **Kemandirian Operasional (Offline-First)** - Aplikasi harus tetap berfungsi menghasilkan naskah dinas walau berada di area blank spot atau air-gapped.
3. **Kemudahan Input Mobile** - Mengoptimalkan masukan suara (dikte) dan form ringkas untuk menghemat waktu mengetik di keyboard virtual.
4. **Format Saklek** - Hasil render PDF di perangkat mobile harus presisi 100% mengikuti tata letak baku naskah dinas resmi.
