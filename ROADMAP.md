# ROADMAP LANJUTAN — SSEB AI (Generator Naskah Dinas)

> Disusun: 25 Agustus 2026 · Setelah penutupan follow-up bagian 13–15 PROGRESS.md
> Basis saat ini: backend 8001 = kode final (terverifikasi) · APK `sseb-ai_v3.apk` = build Android final · TLS ditunda s/d production

---

## Prinsip Prioritas

1. **Jangan go-live sebelum TLS + kredensial resmi** — Basic auth di HTTP polos belum layak untuk data riil.
2. **Uji di perangkat fisik dulu** — semua verifikasi sejauh ini di emulator; biometrik, Keystore, STT, dan jaringan intranet nyata punya perilaku berbeda di perangkat sungguhan.
3. **Umpan balik pengguna > polesan spekulatif** — kumpulkan koreksi redaksi dari pengguna sebelum menyetel ulang prompt AI.

---

## FASE 1 — Validasi Lapangan (1–2 minggu, sebelum sentuh production)

| # | Item | Detail | Estimasi | Kriteria Selesai |
|---|---|---|---|---|
| 1.1 | **Uji perangkat fisik** | Install `sseb-ai_v3.apk` di HP Android nyata (min. 2 merek); uji: koneksi ke backend via Wi-Fi intranet, biometrik dengan sidik jari/PIN terdaftar, STT bahasa Indonesia, cetak & bagikan PDF, arsip pasca-restart | 0,5–1 hari | Semua fitur C (CHECKLIST.md) lulus di ≥2 perangkat fisik |
| 1.2 | **Quick win LAPJU: prefill dinamis** | Bulan/tahun/nomor surat diisi otomatis dari tanggal berjalan (Calendar, pola `generateAutoNomorTS`) — menghapus prefill usang "April 2025" / "B/   /IV/2025"; hari pada tanggal surat diisi otomatis (menyelesaikan spasi kosong "Jakarta,     Agustus 2026") | 1–2 jam | Form LAPJU terbuka dengan periode berjalan; PDF memuat hari tanggal |
| 1.3 | **Verifikasi web frontend dengan auth aktif** | Set AUTH_* di 8001, buka UI web statis: browser harus menampilkan prompt Basic Auth (header `WWW-Authenticate` sudah dikirim); pastikan operator web tidak terkunci | 1 jam | Login web + 1 generate via web sukses dengan auth aktif |
| 1.4 | **UAT pengguna sebenarnya** | 3–5 naskah riil per jenis dibuat oleh staf tata naskah; catat semua koreksi redaksi yang mereka lakukan manual | 3–5 hari | Daftar koreksi terkumpul → menjadi input Fase 3.1 |

**Definisi selesai Fase 1:** tidak ada bug baru di perangkat fisik, UAT selesai tanpa temuan mayor, daftar polesan prompt terkompilasi.

---

## FASE 2 — Production Readiness (gerbang masuk production)

| # | Item | Detail | Estimasi | Kriteria Selesai |
|---|---|---|---|---|
| 2.1 | **Aktivasi TLS** | Ikuti `deploy/README-HTTPS.md` — rekomendasi Caddy (`tls internal` + pasang CA di perangkat pengguna, atau domain nyata + Let's Encrypt); app URL diganti `https://` (peringatan ⚠️ hilang otomatis) | 0,5–1 hari | Aplikasi & web mengakses via HTTPS; peringatan HTTP hilang; tanpa peringatan sertifikat |
| 2.2 | **Kredensial resmi** | Set `AUTH_USERNAME`/`AUTH_PASSWORD` produksi (bukan contoh), distribusikan ke pengguna via kanal resmi; konfirmasi login nyata sukses | 0,5 jam | Login Android + web sukses dengan kredensial produksi |
| 2.3 | **Release build bertanda tangan resmi** | Buat keystore organisasi (simpan aman + backup), signing config di `build.gradle.kts`, `minifyEnabled true` + proguard rules Retrofit/Gson, `versionCode 4` / `versionName 3.1.0` → `sseb-ai_v4-release.apk` | 0,5–1 hari | APK release terinstall & lulus smoke test; ukuran turun (split ABI opsional) |
| 2.4 | **Backup berkala** | Jadwalkan copy harian `backend/output/` (PDF terbit) + `app/templates/` + `.env` (tanpa commit); tentukan retensi | 1–2 jam | Backup otomatis terbukti restore 1× |
| 2.5 | **Dokumen operasional operator** | 1 halaman: restart backend, reindex RAG, rotasi kredensial, cek `llm_warnings`, apa yang dilakukan bila Ollama mati | 1 jam | Operator lain bisa menjalankan tanpa bertanya |

**Definisi selesai Fase 2 (gerbang go-live):** TLS aktif + kredensial resmi + APK release terdistribusi + backup teruji + dokumen operator ada.

---

## FASE 3 — Peningkatan Berkelanjutan (post go-live, opsional sesuai umpan balik)

| # | Item | Detail | Prioritas |
|---|---|---|---|
| 3.1 | **Setel ulang prompt dari hasil UAT** | Terjemahkan koreksi manual pengguna (Fase 1.4) menjadi aturan prompt/guardrail tambahan | Tinggi bila UAT menunjukkan pola berulang |
| 3.2 | **Guardrail ekspansi singkatan tanpa kurung** | Saat ini hanya pola "Ekspansi (KRI)" / "KRI (Ekspansi)" yang terdeteksi; tambahkan deteksi "KRI Kapal Rudal Induk" tanpa kurung + validasi format NRP | Sedang |
| 3.3 | **Hardening penyimpanan kredensial** | Naikkan kredensial server & passphrase DB ke EncryptedSharedPreferences / full-Keystore | Sedang |
| 3.4 | **Monitoring ringan** | Rotasi log uvicorn, hitung `llm_degraded` per hari, uptime `/api/health` | Sedang |
| 3.5 | **Paritas web** | Audit UI web statis mengikuti fitur baru (isi_custom_list, pasal_list, dsb.) | Rendah |
| 3.6 | **LLM on-device** | Hanya bila kebutuhan offline muncul kembali dari lapangan (saklar palsu sudah dihapus) | Rendah |

**Ditunda sengaja / tidak dikerjakan:** aktivasi on-device LLM tanpa kebutuhan nyata; modernisasi penuh web frontend; perubahan router telaahan-staf v1 & `docx_service.py` (dipakai web).

---

## Risiko yang Perlu Diwaspadai

| Risiko | Mitigasi |
|---|---|
| Kapasitas Ollama (qwen2.5:14b, panggilan berurutan 6–13× per naskah) | Antrian alami per pengguna; pertimbangkan model lebih kecil atau antrean eksplisit bila pengguna >3 bersamaan |
| Tidak ada git repo | **Inisiatifkan `git init` + commit pertama** — seluruh perubahan hari ini hanya tersimpan sebagai file; 1 jam setup melindungi semuanya |
| Kredensial plaintext di perangkat | Jangan bagikan HP yang sudah login; TLS menutup jalur penyadapan |
| Token Telegram pernah terekspos di riwayat kode | Sudah dirotasi? Bila belum, rotasi via @BotFather sekarang |

---

## Urutan Eksekusi yang Disarankan

```
MINGGU INI   : 1.1 perangkat fisik → 1.2 quick win LAPJU → 1.3 cek web+auth
MINGGU DEPAN : 1.4 UAT pengguna → kompilasi polesan prompt
GERBANG      : 2.1 TLS → 2.2 kredensial → 2.3 release build → 2.4 backup → 2.5 dokumen
GO-LIVE      : produksi dimulai
SETELAH ITU  : 3.x sesuai umpan balik
```

> Referensi: status terverifikasi → `CHECKLIST.md` · kronologi & bukti → `PROGRESS.md` bagian 1–15
