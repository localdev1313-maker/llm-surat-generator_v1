# ✅ CHECKLIST MENYELURUH — SSEB AI (Generator Naskah Dinas)

> Pembaruan: 25 Agustus 2026 · Backend FastAPI+Ollama (`backend/`) · Android Compose (`android/`) · Bot Telegram
> Legenda: **[x]** selesai & terverifikasi · **[ ]** terbuka (butuh tindakan/keputusan) · **[~]** ditunda sengaja

---

## A. Backend — Konfigurasi & Deployment

- [x] `.env` dimuat otomatis saat startup (`python-dotenv` di `config.py`) — tanpa perlu export manual
- [x] `AUTH_USERNAME` + `AUTH_PASSWORD` diset **keduanya** — salah satu saja = server menolak start (fail-fast)
- [x] Autentikasi Basic aktif di seluruh endpoint; `/api/health` selalu terbuka
- [x] `/docs` `/redoc` `/openapi.json` dimatikan saat auth aktif
- [x] `/static` publik by-design (halaman login web)
- [x] `OLLAMA_HOST` / `OLLAMA_TIMEOUT` / `OLLAMA_MODEL` via env — selaras semua layanan
- [x] Token Telegram via env; kosong = bot nonaktif + warning startup
- [x] `.env.example` lengkap & akurat sebagai panduan operator
- [x] Koersi env numerik aman (salah format → default + warning, server tetap hidup)
- [x] **Backend di-restart** menjalankan kode final (terverifikasi: endpoint baru + PDF bersih)
- [ ] **TLS/HTTPS aktif** — [~] DITUNDA sampai masuk production; panduan siap: `deploy/README-HTTPS.md`
- [ ] Backup berkala folder `backend/output/` (PDF terbit) — belum ada mekanisme; putuskan retensi
- [ ] Rotasi kredensial berkala (AUTH_*, token Telegram) — prosedur manual organisasi

## B. Keamanan

- [x] Perbandingan kredensial anti timing-attack (`hmac.compare_digest`)
- [x] Guardrail anti-halusinasi melapor ke API (`llm_degraded`/`llm_warnings`) dengan whitelist konteks RAG + dedup
- [x] Kamus singkatan baku TNI — ekspansi karangan AI dikoreksi otomatis + tercatat
- [x] SQLCipher aktif (AES-256) + passphrase acak 32 byte
- [x] Passphrase DB dibungkus kunci **Android Keystore** (AES-256/GCM, non-ekspor) + migrasi otomatis dari pola lama
- [x] `app_settings.xml` (kredensial + passphrase) di-exclude dari cloud-backup & device-transfer
- [x] Kunci biometrik nyata (BiometricPrompt + fallback PIN perangkat); tanpa jalur pintas tanpa verifikasi
- [x] Logging rilis `NONE` + `redactHeader("Authorization")` di debug
- [x] `CancellationException` tidak ditelan sebagai kegagalan palsu
- [x] RAG: file latihan `*dummy*` & daftar indeks disaring dari indexing
- [ ] Kredensial di SharedPreferences masih plaintext — [~] diterima utk intranet; upgrade ke EncryptedSharedPreferences bila diperlukan
- [ ] TLS (lihat A) — menutup vektor penyadapan jalur

## C. Android — Fungsional (diverifikasi live di emulator)

- [x] Login nyata via `/api/auth/verify`; kolom kosong utk server tanpa auth
- [x] Pintu darurat ubah URL server dari layar login (anti dead-end)
- [x] URL server persisten (SharedPreferences) + validasi anti crash-loop
- [x] **Nota Dinas**: draft AI pasal-only → cetak → PDF tanpa duplikasi
- [x] **Surat Umum**: draft AI → cetak → PDF; tanggal Indonesia; nomor otomatis
- [x] **Kajian TS**: 6 pasal AI ter-grounding input; nomor otomatis `TS/01/<ROMAWI>/<TAHUN>/<SATKER>`; PDF utuh
- [x] **Kajian KKA** (3 model) — endpoint + template teruji (pemecahan masalah diverifikasi penuh)
- [x] **LAPJU**: 100% data riil deterministik (Zero-AI); kalkulasi matematis akurat; pasal formal utuh saat cetak dari editan; PDF 2 halaman (portrait+landscape)
- [x] Tabel LAPJU bebas N baris; paginasi multi-halaman dengan header berulang (teruji 20 kegiatan)
- [x] Field numerik anti-korupsi ketikan (hapus = kosong; ketik bertahap utuh)
- [x] Matriks LAPJU memenuhi lebar halaman (zoom terkalibrasi; border tepat di margin)
- [x] "Kepada Yth." sejajar blok tanggal (kolom kanan)
- [x] Arsip: simpan path relatif; buka lintas pergantian host; DB SQLCipher
- [x] Pratinjau PDF: validasi kode HTTP + header auth + anti-OOM (cap 2048px)
- [x] Pengaturan: Tes Koneksi menguji URL yang diketik; kartu kredensial (password kosong = tidak berubah)
- [x] Peringatan ⚠️ HTTP tanpa enkripsi tampil saat URL non-HTTPS
- [x] Biometrik: toggle persisten; gerbang di depan Home; auto-longgarkan di perangkat tanpa kunci layar
- [x] Hasil draf AI **tidak hilang saat pindah tab** — dialog muncul otomatis saat generasi selesai (state di ViewModel)
- [x] Guard draf: teks basi dikosongkan; tombol cetak kunci saat menyusun; placeholder "⚠️" tak bisa tercetak
- [x] Guard double-submit global (ViewModel) + per tombol; submit tertolak diberi Toast
- [x] Rotasi tidak membatalkan generasi (viewModelScope) & tidak menghapus isi form (`configChanges`)
- [x] Degradasi LLM terlihat: Toast "templat standar" + field `llm_degraded` (REST & Telegram)

## D. Kualitas Dokumen (PDF)

- [x] Teks tidak terpotong tepi kanan (margin 18mm + kompensasi font ÷1,125 + body width terkunci) — terukur ≤ batas di 9/9 halaman uji
- [x] Font fisik tepat 12pt (faktor boost mesin ×1,125 terkompensasi)
- [x] Tanggal Indonesia konsisten ("25 Agustus 2026") via util bersama
- [x] Tanpa duplikasi struktur (kop/nomor/dasar tercetak sekali)
- [x] Matriks LAPJU kolom proporsional (persen, total 100%)

## E. Kualitas Kode

- [x] Klien Ollama terpusat (satu sumber konfigurasi)
- [x] Panggilan blocking di worker thread (`asyncio.to_thread`) — event loop tidak beku
- [x] `SuratViewModel` memilik seluruh jaringan (rotasi-safe)
- [x] Repository satu helper `apiCall` (13 duplikat dilebur)
- [x] Layar mati `TelaahanStafScreen` (~567 baris) dihapus beserta plumbing yatim
- [x] Helper STT bersama (`SttController`) — 11 situs, 3 layar
- [x] 13 wrapper repository → `apiCall`; field latent nullable; permukaan mati klien dibersihkan
- [x] Kompilasi Kotlin debug + release `BUILD SUCCESSFUL`

## F. Pengujian yang Sudah Dijalankan

- [x] Review kode 3 putaran (30+ temuan → seluruh major/minor ditutup)
- [x] Workflow verifikasi adversarial 14 agen (13 temuan pada fix v1 → semuanya diperbaiki)
- [x] Trial & error live: nota dinas, kajian, LAPJU (crash + 2 bug logika tertangkap & diperbaiki)
- [x] Dry test regresi 9/9 fitur — 0 crash
- [x] Uji kegagalan: server mati (toast + placeholder terlindungi), URL salah (pintu darurat), auth salah (401 → pesan jelas)
- [x] Unit: guardrail singkatan 6 skenario, prefix cleaner, strip header, koersi env, fail-fast auth
- [x] E2E backend: auth aktif/nonaktif, .env loading, degradasi, tanggal, duplikasi header

## G. Distribusi APK

- [x] `sseb-ai_v3.apk` (root proyek) — debug-signed, memuat seluruh perubahan
- [x] `sseb-ai_v2.apk` — arsip versi sebelumnya (jangan dipakai)
- [ ] **Release build + keystore resmi** — wajib bila distribusi luas/Play Store (minify, split ABI → ukuran turun drastis)
- [ ] versionName/versionCode bump per rilis (saat ini 3.0.0 / 3)

## H. Known Issues / Catatan (tidak menghalangi operasi)

- [ ] LAPJU: prefill "April 2025" & nomor "B/   /IV/2025" masih contoh statis — pengguna harus mengganti manual
- [ ] LAPJU: ringkasan draf "Jakarta,␣␣␣␣Agustus 2026" — spasi kosong utk hari (kosmetik)
- [ ] Identitas prefill tetap contoh demo — pengguna wajib mengganti dengan data riil
- [ ] AI Surat Umum: kualitas redaksi bergantung kualitas input poin (normal)
- [ ] `docx_service.py` & router telaahan-staf v1 tidak dipakai Android (dipakai web) — biarkan

## I. Prosedur Operasional Rutin

- [ ] **Restart backend** setiap selesai edit kode Python (`reload=False` by design)
- [ ] **Reindex RAG** setelah menambah dokumen referensi (`/rag/reindex` atau tombol bot) — jangan beri nama file "dummy"
- [ ] Ganti URL server di aplikasi saat host berubah (Pengaturan → Simpan URL → Tes Koneksi)
- [ ] Set `AUTH_*` di setiap deployment baru; simpan kredensial di kanal resmi organisasi
- [ ] Periksa `llm_warnings` pada respons bila naskah terasa janggal (juga muncul sebagai peringatan di aplikasi)

---

**Referensi:** kronologi lengkap & bukti verifikasi → `PROGRESS.md` (bagian 1–15) · konfigurasi → `backend/.env.example` · TLS → `deploy/README-HTTPS.md`
