# PROGRESS PERKEMBANGAN — Generator Naskah Dinas SSEB AI

> Backend FastAPI + Ollama lokal (`backend/`) · Klien Android Jetpack Compose (`android/`) · Bot Telegram
> Pembaruan per **25 Agustus 2026** · 4 putaran review + refactor selesai · Build debug/release hijau

---

## 1. Ringkasan Status

| Area | Status |
|---|---|
| Konektivitas LLM lokal ("sering gagal") | ✅ Akar masalah ditemukan & diperbaiki |
| Autentikasi API | ✅ HTTP Basic env-gated + login nyata di Android |
| Keamanan data perangkat | ✅ SQLCipher nyata + backup rules + biometrik nyata |
| Rotasi/stabilitas UI | ✅ ViewModel scope, guard double-submit, form tahan rotasi |
| Verifikasi | ✅ Workflow adversarial 14 agen + build debug/release + uji e2e |

Masalah awal pelapor: *"koneksi ke LLM Lokal masih sering gagal"*. Akar penyebabnya bukan jaringan, melainkan kombinasi: klien Ollama triple dengan konfigurasi menyimpang (hardcode `localhost` + timeout 10 detik di mesin kajian), endpoint async FastAPI yang dibekukan panggilan sinkron menit-menit, URL server Android yang reset ke loopback emulator setiap start, dan spinner yang menggantung selamanya saat gagal. Semuanya telah diperbaiki.

---

## 2. Kronologi Putaran Perbaikan

### Putaran 1 — Review menyeluruh + fondasi konektivitas
- Klien Ollama dikonsolidasi ke satu modul `services/ollama_client.py` (env `OLLAMA_HOST` / `OLLAMA_TIMEOUT`) — menghapus 3 implementasi menyimpang.
- Semua panggilan blocking (generasi LLM, render PDF wkhtmltopdf, indexing RAG) dipindah ke worker thread via `asyncio.to_thread` — `/api/health` & bot Telegram tidak lagi ikut beku.
- Pelacak degradasi LLM request-scoped (`services/llm_health.py`): respons API membawa `llm_degraded` + `llm_warnings`.
- Token Telegram dihapus dari source code → env (`.env.example` tersedia); token lama wajib dirotasi.
- Android: persistensi serverUrl (SharedPreferences), OkHttp readTimeout 600s, callback draft dipanggil saat gagal (spinner tidak lagi menggantung), pratinjau PDF memvalidasi kode HTTP + bersih-bersih cache.

### Putaran 2 — Review logika alur Android (10 temuan, langsung dipatch)
Dokumen berbeda dari yang disetujui pengguna (editan `konten_custom` dibuang saat render PDF), kalimat error tercetak sebagai isi surat resmi, crash-loop URL tanpa skema, STT menimpa teks, arsip mati pasca-ganti host, leak PdfRenderer, log rilis membocorkan naskah (`BuildConfig.DEBUG` gate), latent NPE telaahan staf, dst. Repository dilebur ke helper `apiCall` tunggal (CancellationException tidak lagi ditelan).

### Putaran 3 — Refactor arsitektur
- **`SuratViewModel`**: seluruh pekerjaan jaringan pindah dari lifecycleScope Activity ke viewModelScope → rotasi tidak lagi membatalkan generasi Ollama; event channel `UiEvent` untuk navigasi/Toast.
- **Autentikasi sungguhan**: backend `security.py` (Basic Auth env-gated, `/api/auth/verify`, `/api/health` tetap terbuka) + login Android memverifikasi ke server (akun demo hardcode dihapus) + interceptor Basic di seluruh request termasuk unduhan PDF.
- Guard LAPJU, hapus `TelaahanStafScreen` (~567 baris layar mati) beserta rantai callback yatim, satukan format nomor naskah TS klien==backend (`TS/01/<ROMAWI>/<TAHUN>/<KODE_SATKER>`).

### Putaran 4 — Penutupan seluruh temuan major/minor + verifikasi adversarial
Detail di bagian 3. Ditutup dengan workflow verifikasi multi-agen (3 lensa review + verifikator skeptis per temuan) yang menemukan 13 cacat pada versi pertama perbaikan sendiri — semuanya dibetulkan — lalu review ulang lensa UI menemukan 6 temuan tambahan (5 diperbaiki, 1 didokumentasikan sebagai keterbatasan).

---

## 3. Rincian Perbaikan Terkini

### Backend
| Perbaikan | File |
|---|---|
| `.env` dimuat otomatis saat startup (python-dotenv) | `config.py`, `requirements.txt` |
| Fail-fast autentikasi parsial (salah satu var terisi = tolak start) | `config.py` |
| Koersi env numerik aman (salah format → default + warning, tak matikan server) | `config.py`, `ollama_client.py` |
| `/docs` `/redoc` `/openapi.json` dimatikan saat auth aktif; `/static` publik by-design | `main.py` |
| Guardrail halusinasi melapor ke API (whitelist konteks RAG + dedup) | `llm_service.py` |
| Tanggal Indonesia via util bersama (4 titik, sebelumnya "August") | `surat.py`, `kajian.py`, `telegram_bot.py` |
| Reindex RAG atomic-swap + RLock (search tidak lagi lihat indeks kosong/parsial) | `rag_service.py` |
| Handler Telegram menerima peringatan degradasi AI di pratinjau (3 titik) | `telegram_bot.py` |

### Android
| Perbaikan | File |
|---|---|
| Guard draf lengkap: teks basi dikosongkan, tombol cetak kunci saat menyusun, tolak placeholder "⚠️", submit tertolak diberi Toast | `GenerateScreen`, `KajianScreen`, `LapjuScreen`, `SuratViewModel` |
| Kredensial: password kosong = tidak berubah (sesuai label UI) | `SuratViewModel` |
| Biometrik NYATA: FragmentActivity + BiometricPrompt + fallback PIN perangkat; tanp pintas nonaktif tanpa verifikasi; unlock di VM (proses-death tidak melewati gerbang) | `MainActivity`, `SuratViewModel` |
| Saklar "On-Device LLM Offline" palsu DIHAPUS | `SettingsScreen` |
| SQLCipher nyata: `sqlcipher-android` 4.5.6, passphrase acak 32-byte, migrasi plaintext→enkripsi transaksional + verifikasi baris, `loadLibrary` lebih awal | `AppDatabase.kt`, `build.gradle.kts` |
| Backup rules: `app_settings.xml` (kredensial+passphrase) exclude cloud-backup & device-transfer | `res/xml/*.xml` |
| Form tahan rotasi (`configChanges`), Tes Koneksi menguji URL yang diketik, field numerik LAPJU anti-korupsi ketikan, bitmap cap 2048px, redactHeader Authorization | beberapa file |

---

## 4. Verifikasi yang Dilakukan

- ✅ Kompilasi Kotlin **debug + release** `BUILD SUCCESSFUL`; APK debug utuh 83 MB (termasuk native `.so` SQLCipher 4 ABI).
- ✅ Import penuh aplikasi FastAPI OK; `py_compile` seluruh file yang berubah.
- ✅ Uji e2e uvicorn: auth aktif → health 200 / verify salah 401 / benar 200 / API tanpa header 401 / `/docs` 404; auth nonaktif → mode lama kompatibel.
- ✅ `.env` dimuat tanpa export manual; fail-fast auth parsial terbukti menolak start.
- ✅ Guardrail: sitasi sah dari RAG tidak dilaporkan; halusinasi nyata terlapor 1 warning.
- ✅ Generasi LLM asli sukses lewat jalur terautentikasi (`llm_degraded=false`).
- ✅ Workflow adversarial: 13 temuan terkonfirmasi pada versi pertama → semuanya ditutup; review UI lanjutan: 6 temuan → 5 diperbaiki, 1 didokumentasikan.

---

## 5. Konfigurasi Operasional

Salin `backend/.env.example` → `backend/.env`, minimal isi:

```ini
AUTH_USERNAME=admin            # WAJIB keduanya; salah satu saja = server menolak start
AUTH_PASSWORD=<ganti>
OLLAMA_HOST=http://<host-ollama>:11434
TELEGRAM_BOT_TOKEN=<dari @BotFather>   # kosong = bot nonaktif
```

Di aplikasi Android (Pengaturan): URL server, Username, Password (kosongkan password bila tidak berubah), Tes Koneksi, saklar Kunci Biometrik.

---

## 6. Trial & Error Live di Emulator (25 Agustus 2026)

Aplikasi dijalankan langsung di emulator (AVD `uptodown_test`) melawan backend live di `:8001` + Ollama aktif. Hasil:

| # | Skenario | Hasil |
|---|---|---|
| 1 | Launch pertama | 🐛 **Crash ditemukan & diperbaiki**: NPE urutan inisialisasi `baseHttpClient` vs `repositoryFlow` di `SuratViewModel` (lolos kompilasi; tertangkap hanya di runtime) |
| 2 | Login kolom kosong (server tanpa auth) | ✅ Masuk Home |
| 3 | Pengaturan: URL persisten, peringatan HTTP ⚠️, kartu kredensial | ✅ |
| 4 | Tes Koneksi | ✅ "Terhubung! Status: ok" |
| 5 | Draf Nota Dinas (4 panggilan LLM) | ✅ Dialog + spinner, tombol cetak terkunci selama menyusun, lalu terbuka dengan teks AI |
| 6 | Cetak dari editan | 🐛 **Duplikasi struktur ditemukan & diperbaiki**: teks gabungan editor dikirim utuh sebagai `konten_custom` → backend memecahnya jadi pasal → kop/nomor/dasar tercetak 2×. Kini dialog mengedit pasal isi saja dan mencetak via `isi_custom_list` |
| 7 | PDF final | ✅ Bersih: kop → nomor → dasar → pasal isi → penutup → tembusan; tanggal "Jakarta, 25 Agustus 2026" |
| 8 | Arsip | ✅ Dokumen tersimpan (DB SQLCipher) |
| 9 | Header login (kosmetik) | 🐛 Teks putih meluber keluar area navy → diperbaiki (tinggi header 260→340dp) |

Semua perbaikan di atas sudah masuk build dan diverifikasi ulang langsung di emulator.

---

## 7. Pengujian Penuh Fitur "Kajian" (25 Agustus 2026)

Uji end-to-end mode Telaahan Staf di emulator melawan backend live + Ollama:

**Alur input → AI terverifikasi:**
- Form (judul + 6 input pasal) → `buildGenerateRequest()` → `/api/v1/kajian/draft` → 6 panggilan Ollama berurutan (tiap pasal ditanam konteks pasal sebelumnya) + RAG grounding → guardrail → dialog editor.
- Marker input terlacak masuk output: judul "UJI PEMBANGUNAN DERMAGA LANTAMAL IV" → header naskah; fakta "2 dermaga untuk 12 KRI" → Pasal 3 & 4; saran "dermaga fase dua TA 2027" → Pasal 6.
- Nomor otomatis server bekerja: **"Nomor TS/01/VIII/2026/PSP"** (romawi bulan + kode satker dari kop).
- Cetak PDF → dokumen 6 pasal + lampiran + tanda tangan, tanpa duplikasi.

**Kegagalan yang diuji:**
- Server mati (URL diarahkan ke port 9999) → Toast error + dialog "⚠️ GAGAL MENYUSUN DRAF (Tidak dapat terhubung ke server...)" + **tombol Cetak PDF otomatis disabled** — placeholder gagal tidak mungkin tercetak. ✅
- **Dead-end ditemukan & diperbaiki**: URL salah tersimpan membuat login gagal selamanya tanpa jalan ke Pengaturan (harus clear data). Kini ada pintu darurat **"Tidak bisa terhubung? Ubah alamat server"** di layar login → dialog ubah URL → simpan → login ulang sukses. ✅ (diverifikasi live)

**Observasi kualitas AI (tidak crash, catatan produk):**
1. AI mengembangkan singkatan "KRI" → "Kapal Rudal Induk" (salah; seharusnya Kapal Perang Republik Indonesia) — halusinasi ekspansi singkatan yang tidak terdeteksi guardrail (pola saat ini hanya regulasi/nama/tanggal).
2. Input analisis/kesimpulan default (topik SIEM) tetap memengaruhi Pasal 4–5 meski judul diganti topik lain → naskah campuran bila pengguna hanya mengganti judul.
3. Judul tercetak dua kali di PDF (blok nomor + body) — kosmetik template.

---

## 8. Perbaikan Kualitas AI (25 Agustus 2026 — menyusul observasi uji Kajian)

Tiga observasi diperbaiki di akar + satu kontaminasi baru ditemukan saat verifikasi:

| Masalah | Perbaikan |
|---|---|
| Halusinasi ekspansi singkatan (KRI → "Kapal Rudal Induk") | Kamus `SINGKATAN_BAKU` (14 singkatan TNI) di `guardrail_kajian.py`: ekspansi salah dikoreksi OTOMATIS ke bentuk baku + tercatat sebagai `llm_warning`; prompt melarang menguraikan singkatan; `llm_service._validate_output` ikut menerapkan koreksi (jalur nota dinas/surat) |
| Naskah campuran topik (SIEM bocor ke pasal meski judul diganti) | Prefill 6 input pasal Android dikosongkan + placeholder panduan (label opsional tanpa `*`); prompt wajib konsisten judul/persoalan/fakta; judul kini ditanam di prompt Pasal 4/5/6 |
| Judul dobel di PDF | `render-pdf` menghapus baris header teks gabungan ("TELAAHAN STAF TENTANG…" / "KERTAS KARYA ACUAN…") sebelum render — template sudah mencetaknya |
| **Kontaminasi RAG (baru ditemukan saat verifikasi)**: AI mengutip "rekomendasi DAFTAR 50 NOTA DINAS DUMMY" | File latihan `*dummy*` + `DAFTAR_DOKUMEN.txt` disaring dari indexing RAG; prompt melarang menyebut nama dokumen referensi; reindex dilakukan (103 dokumen bersih) |
| Sisa label meta "Pasal 1", "Pasal 2 (Praanggapan):" di isi pasal | Pembersih prefix `validate_telaahan_staf` direstrukturisasi: lepas label meta + baris label pasal utuh (kasus "Fakta/Data" dengan slash kini bersih) |

**Verifikasi:** unit-test 6 skenario guardrail singkatan + strip header + prefix cleaner; E2E live di emulator (backend 8002 kode terbaru): draf kajian topik "UJI REHABILITASI DERMAGA TAMBAT KRI" dengan input pasal kosong → 6 pasal konsisten topik, KRI utuh tanpa ekspansi karangan, tanpa kutipan dummy, PDF tanpa judul dobel.

> **Catatan operasional:** backend di port 8001 (milik Anda) masih memakai kode lama (`reload=False`) — **restart backend** agar seluruh perbaikan AI-quality ini aktif. Instans verifikasi berjalan di port 8002.

---

## 9. Pengujian Menyeluruh Fitur "LAPJU" (25 Agustus 2026)

| # | Skenario | Hasil |
|---|---|---|
| 1 | API kalkulasi `/api/v1/lapju/draft` (2 kegiatan) | ✅ Pagu/sisa/rata-rata akurat (3M/2,25M/35%) |
| 2 | Rekap real-time di form | ✅ Total Pagu/Terserap/Sisa/Fisik/Admin mengikuti input |
| 3 | Field numerik: hapus seluruh isi | ✅ Tetap kosong — tidak lagi melompat ke "0" |
| 4 | Field numerik: ketik bertahap "123"+"45" | ✅ "12345" utuh tanpa korupsi |
| 5 | Pratinjau Draf (tanpa LLM, instan) | 🐛 **Temuan review lama MASIH hidup & diperbaiki**: editor memuat ringkasan KOP+rekap utuh; saat dicetak, `konten_custom` MENGGANTIKAN dua pasal resmi → halaman 1 PDF berisi blok rekap mentah. Kini backend menyediakan `pasal_list` terpisah, editor mengedit **pasal saja**, template merendernya sebagai pasal-item |
| 6 | Cetak PDF dari editan | ✅ Halaman 1: dua pasal formal utuh; halaman 2: matriks 13 kolom landscape + baris JUMLAH/TOTAL akurat |
| 7 | Arsip | ✅ Tersimpan path relatif |

Perbaikan menyentuh: `lapju_service.py` (`build_lapju_pasal_list`), `lapju.py` (draft mengirim `pasal_list`), `schemas/lapju.py`, template `lapju_surat_pengantar_template.html` (pasal-item), `SuratModels.kt` + `SuratViewModel.draftLapju` + `HomeScreen`/`GenerateScreen`/`LapjuScreen` (kontrak tipe `(String, List<String>)`).

---

## 10. Penyesuaian LAPJU Sesuai Permintaan (25 Agustus 2026)

1. **Tabel bebas N baris** — form tidak memiliki batas jumlah kegiatan (Tambah/Hapus bebas); diverifikasi 6 dan 20 kegiatan: matriks landscape otomatis paginasi multi-halaman dengan **header tabel berulang** di tiap halaman (20 item → 3 halaman).
2. **"Kepada Yth." sejajar tanggal** — dipindah ke kolom kanan blok metadata, tepat di bawah "Jakarta, <bulan> <tahun>" (sebelumnya blok terpisah di bawah kiri).
3. **Bug tersembunyi tertangkap saat verifikasi**: pasal editan (`konten_custom` mode `pre-wrap`) **terpotong di PDF** oleh kombinasi karakter tab + justify pada wkhtmltopdf — tab diganti spasi di sumber (`pasal_list` & fallback editor) + `text-align: left` pada pasal editan; diverifikasi teks utuh via ekstraksi PDF.

---

## 11. Dry Test Regresi Semua Fitur (25 Agustus 2026 — emulator, backend 8002)

| # | Fitur | Skenario | Hasil |
|---|---|---|---|
| 1 | Login | Kolom kosong (server tanpa auth) | ✅ Masuk Home |
| 2 | Nota Dinas | Draft AI → dialog pasal-only → Cetak | ✅ PDF: kop, dasar, 1 pasal AI, tembusan, ttd — tanpa duplikasi |
| 3 | Surat Umum | Isi 4 field → draft AI → Cetak | ✅ PDF kop KONI, tanggal "25 Agustus 2026", nomor otomatis |
| 4 | Kajian | (teruji penuh bagian 7-8) | ✅ |
| 5 | LAPJU | (teruji penuh bagian 9-10) | ✅ |
| 6 | Arsip | Buka entri lama | ✅ PDF dimuat via resolveDocUrl host aktif |
| 7 | Pengaturan | Tes Koneksi | ✅ "Terhubung! Status: ok"; warning HTTP tampil |
| 8 | Biometrik | Toggle ON → logout → login | ✅ Toast "Perangkat belum memiliki kunci layar/biometrik — kunci aplikasi dimatikan." (jalur auto-disable perangkat tanpa kunci layar) |
| 9 | Stabilitas | Audit logcat sepanjang sweep | ✅ 0 FATAL EXCEPTION, proses hidup |

Observasi minor baru: AI Surat Umum menyalin header Kepada/Perihal ke dalam badan surat (duplikasi ringan di PDF) — kandidat polesan prompt berikutnya.

---

## 12. Perbaikan Teks Terpotong Tepi Kanan PDF (25 Agustus 2026)

**Gejala** (laporan pengguna + pengukuran objektif PyMuPDF): huruf terpotong garis tepi kanan pada semua PDF — teks justify melewati batas cetak hingga **+6,6pt**.

**Akar (terisolasi via eksperimen terkontrol):** wkhtmltopdf di lingkungan ini me-render font **×1,125** (CSS 12pt → fisik 13,5pt) sementara lebar layout tetap — baris justify penuh melampaui area cetak. Blok `@page` ganda di template terbukti diabaikan WebKit (bukan penyebab).

**Perbaikan berlapis:**
1. Hapus blok `@page` dari 8 template — margin kini satu sumber kebenaran (CLI `pdf_service.py`).
2. Margin kanan CLI 15,2 → **18mm** (portrait & landscape matriks) — buffer anti-terpotong.
3. **Kompensasi font-size ÷1,125** pada seluruh `font-size` pt di 8 template → fisik kembali **tepat 12pt**.
4. Kunci `body width` eksplisit: **162,5mm** (portrait) / **177mm** (matriks landscape).

**Verifikasi akhir** (5 jenis dokumen, 9 halaman): semua `max_x1 ≤ batas` dengan sisa ≥ 5,5pt; font fisik terukur **12,0pt**; visual nota dinas & matriks LAPJU bersih.

> Catatan portabilitas: faktor ×1,125 bersifat environment-specific (build wkhtmltopdf/DPI mesin ini). Jika deploy ke mesin lain dan teks tampak mengecil, sesuaikan kembali kompensasi font-size template.

---

## 13. Penutupan Follow-up Terbuka (25 Agustus 2026)

Seluruh 5 item follow-up dikerjakan & diverifikasi:

| # | Item | Hasil |
|---|---|---|
| 1 | HTTPS | ✅ Panduan siap-deploy `deploy/README-HTTPS.md` (Caddy auto-TLS / nginx / uvicorn TLS + catatan trust CA perangkat) |
| 2 | Hasil draf hilang saat pindah tab | ✅ `DraftUiState` dimiliki ViewModel (`type/loading/failed/text/sections/dismissed`); dismiss hanya MENYEMBUNYIKAN dialog — saat AI selesai dialog muncul kembali otomatis dengan hasil. **Diverifikasi live**: draf kajian dipicu → BACK (dismiss) → pindah Pengaturan → 175s → kembali → dialog terbuka dengan hasil utuh |
| 3 | Identitas demo tak konsisten | ✅ Kanon diselaraskan klien↔backend↔Telegram: "Budi Santoso, S.E., M.M." / "Komandan Satuan Penindak" / "Kolonel Laut (E) NRP 12345/P"; pasis KE-64 TP 2026 |
| 4 | Passphrase DB polos di prefs | ✅ Di-wrap AES-256/GCM dengan kunci non-ekspor **Android Keystore**; migrasi otomatis dari pola lama; fallback polos bila Keystore gagal (arsip tetap terbuka). **Diverifikasi live**: arsip lama terbuka pasca-migrasi |
| 5 | Backlog kecil | ✅ Helper `SttController` bersama (3 layar, 11 situs); `downloadPdf` mati dihapus (ApiService+Repository); field kajian latent → nullable; identitas model Kotlin diselaraskan |

Verifikasi: build hijau, install emulator, uji live lintas tab + arsip pasca-Keystore, 0 crash.

---

## 14. Rekomendasi 3 & 4 (25 Agustus 2026)

**#3 — Duplikasi header Surat Umum**: AI menyalin "Kepada Yth./Penerima/Perihal" ke badan surat padahal template sudah mencetaknya. Diperbaiki dua lapis: aturan prompt baru "ATURAN ISI-SAHA" (larang menulis blok tujuan/perihal/nomor/tanggal; mulai langsung dari salam isi) + sanitasi defensif `_strip_metadata_header()` yang membuang baris metadata di awal output. **Verifikasi live**: "Kepada Yth" ×1, "Perihal:" ×1 di PDF.

**#4 — Matriks LAPJU tidak memenuhi lebar halaman**: akar masalah berlapis (kolom px tetap + auto-layout WebKit yang menempatkan tabel pada 631pt dari 748,5pt printable). Setelah beberapa pendekatan (% kolom, table-layout fixed — keduanya gagal/lebih buruk), solusi final: kolom px proporsional (total ±995px) + **kalibrasi `zoom: 1.18` pada render lampiran landscape**. **Verifikasi**: border kolom terkanan 791–792pt = tepat batas margin; 16 kolom terdistribusi proporsional; semua angka utuh.

> Perubahan backend (llm_service, pdf_service, template) — **restart backend 8001** agar aktif.

---

## 15. Status Penutupan (25 Agustus 2026 — akhir sesi)

- **Backend 8001 sudah menjalankan kode final** — terverifikasi: endpoint baru hidup (`/api/auth/verify`, `pasal_list`), duplikasi header surat umum hilang ("Kepada Yth" ×1, "Perihal:" ×1).
- **Aplikasi Android kembali mengarah ke 8001** — Tes Koneksi "Terhubung! Status: ok" (diverifikasi live di emulator).
- Instans uji port 8002 dihentikan.
- **TLS DITUNDA** oleh pengguna sampai masuk production — panduan tetap tersedia di `deploy/README-HTTPS.md` saat dibutuhkan; peringatan ⚠️ HTTP tetap tampil di Pengaturan selama itu.

**Sisa (opsional, tidak menghalangi):** rebuild `sseb-ai_v2.apk` bila ingin membawa perubahan Android terakhir (draft state lintas tab + Keystore + STT helper) — APK lama dibuat sebelum bagian 13.

> **Checklist menyeluruh** (deployment, keamanan, fungsional, kualitas, distribusi, prosedur rutin) tersedia di **`CHECKLIST.md`** — perbarui tick-nya seiring operasi.
> **Rencana lanjutan** (3 fase: validasi lapangan → production readiness → peningkatan) tersedia di **`ROADMAP.md`**.
