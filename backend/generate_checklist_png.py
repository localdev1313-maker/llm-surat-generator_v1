# -*- coding: utf-8 -*-
"""
Generate visual checklist PNG (CHECKLIST.png di root proyek) dari data
CHECKLIST.md. Render via wkhtmltoimage (satu paket dengan wkhtmltopdf).

Jalankan:  python generate_checklist_png.py
Output :   ../CHECKLIST.png (relatif terhadap folder backend)
"""
import os
import subprocess
from datetime import date

WKHTMLTOIMAGE = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltoimage.exe"
OUT_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "CHECKLIST.png")

# status: "done" | "open" | "note" | "rutin"
SECTIONS = [
    ("A", "Backend — Konfigurasi & Deployment", [
        ("done", ".env dimuat otomatis saat startup (python-dotenv)"),
        ("done", "AUTH_USERNAME + AUTH_PASSWORD diset keduanya — fail-fast parsial"),
        ("done", "Basic auth di seluruh endpoint; /api/health selalu terbuka"),
        ("done", "/docs & /openapi.json dimatikan saat auth aktif"),
        ("done", "OLLAMA_HOST / OLLAMA_TIMEOUT / OLLAMA_MODEL via env"),
        ("done", "Token Telegram via env; kosong = bot nonaktif"),
        ("done", ".env.example lengkap sebagai panduan operator"),
        ("done", "Koersi env numerik aman (salah format → default + warning)"),
        ("done", "Backend 8001 menjalankan kode final (terverifikasi)"),
        ("done", "Margin & zoom PDF terkalibrasi (anti-terpotong)"),
        ("open", "TLS/HTTPS aktif — ditunda s/d production; panduan siap"),
        ("open", "Backup berkala folder output/ (PDF terbit)"),
        ("open", "Rotasi kredensial berkala (AUTH_*, Telegram)"),
    ]),
    ("B", "Keamanan", [
        ("done", "Basic auth anti timing-attack (compare_digest)"),
        ("done", "Guardrail halusinasi → llm_degraded/warnings (whitelist RAG + dedup)"),
        ("done", "Kamus singkatan TNI/AL — koreksi otomatis ekspansi karangan"),
        ("done", "SQLCipher aktif (AES-256) + passphrase acak 32 byte"),
        ("done", "Passphrase dibungkus kunci Android Keystore (GCM, non-ekspor)"),
        ("done", "app_settings.xml di-exclude dari backup perangkat"),
        ("done", "Biometrik nyata + fallback PIN; tanpa jalur pintas"),
        ("done", "Logging rilis NONE + redact Authorization"),
        ("done", "RAG: file latihan dummy disaring dari indexing"),
        ("done", "Fail-open auth parsial dihilangkan"),
        ("done", "CancellationException tidak ditelan sebagai kegagalan"),
        ("note", "Kredensial prefs plaintext — diterima utk intranet; upgrade bila perlu"),
        ("open", "TLS — menutup vektor penyadapan jalur"),
    ]),
    ("C", "Android — Fungsional (verifikasi live emulator)", [
        ("done", "Login nyata via /api/auth/verify; kolom kosong utk server tanpa auth"),
        ("done", "Pintu darurat ubah URL server dari layar login (anti dead-end)"),
        ("done", "URL server persisten + validasi anti crash-loop"),
        ("done", "Nota Dinas: draft AI pasal-only → PDF tanpa duplikasi"),
        ("done", "Surat Umum: draft AI → PDF; tanggal Indonesia; nomor otomatis"),
        ("done", "Kajian TS: 6 pasal ter-grounding input; nomor otomatis baku"),
        ("done", "Kajian KKA 3 model teruji"),
        ("done", "LAPJU: kalkulasi akurat; pasal formal utuh dari editan"),
        ("done", "Tabel LAPJU bebas N baris + paginasi header (teruji 20 kegiatan)"),
        ("done", "Field numerik anti-korupsi ketikan"),
        ("done", "Matriks memenuhi lebar halaman (zoom terkalibrasi 1.18)"),
        ("done", "Kepada Yth. sejajar blok tanggal (kolom kanan)"),
        ("done", "Arsip path relatif lintas host + DB SQLCipher"),
        ("done", "Pratinjau PDF: validasi HTTP + header auth + anti-OOM"),
        ("done", "Tes Koneksi menguji URL yang sedang diketik"),
        ("done", "Peringatan HTTP non-HTTPS tampil di Pengaturan"),
        ("done", "Biometrik nyata + auto-longgarkan perangkat tanpa kunci layar"),
        ("done", "Draf AI lintas tab — dialog muncul otomatis saat generasi selesai"),
        ("done", "Guard draf: teks basi / kunci cetak / placeholder terlindungi"),
        ("done", "Double-submit guard global + Toast"),
        ("done", "Rotasi aman (viewModelScope + configChanges)"),
        ("done", "Degradasi LLM terlihat (Toast + llm_degraded, REST & Telegram)"),
    ]),
    ("D", "Kualitas Dokumen (PDF)", [
        ("done", "Teks tidak terpotong tepi kanan (terukur 9/9 halaman uji)"),
        ("done", "Font fisik tepat 12pt (kompensasi boost mesin ×1,125)"),
        ("done", "Tanggal Indonesia konsisten via util bersama"),
        ("done", "Matriks LAPJU kolom proporsional (total 100%)"),
    ]),
    ("E", "Kualitas Kode", [
        ("done", "Klien Ollama terpusat — satu sumber konfigurasi"),
        ("done", "Panggilan blocking di worker thread (event loop tidak beku)"),
        ("done", "SuratViewModel memilik seluruh jaringan (rotasi-safe)"),
        ("done", "Repository satu helper apiCall (13 duplikat dilebur)"),
        ("done", "Layar mati TelaahanStafScreen (±567 baris) dihapus"),
        ("done", "SttController bersama (11 situs, 3 layar)"),
        ("done", "Kompilasi Kotlin debug + release BUILD SUCCESSFUL"),
    ]),
    ("F", "Pengujian yang Sudah Dijalankan", [
        ("done", "Review kode 3 putaran — 30+ temuan, seluruh major/minor ditutup"),
        ("done", "Verifikasi adversarial 14 agen — 13 temuan pada fix v1 diperbaiki"),
        ("done", "Trial & error live — crash + 2 bug logika tertangkap & diperbaiki"),
        ("done", "Dry test regresi 9/9 fitur — 0 crash"),
        ("done", "Uji kegagalan: server mati / URL salah / auth salah"),
        ("done", "Unit: guardrail singkatan, prefix, strip header, koersi env"),
        ("done", "E2E backend: auth, .env, degradasi, tanggal, duplikasi header"),
    ]),
    ("G", "Distribusi APK", [
        ("done", "sseb-ai_v3.apk siap (debug-signed, seluruh perubahan)"),
        ("done", "sseb-ai_v2.apk sebagai arsip versi sebelumnya"),
        ("open", "Release build + keystore resmi (bila distribusi luas)"),
        ("open", "versionName/versionCode bump per rilis (kini 3.0.0 / 3)"),
    ]),
    ("H", "Known Issues (tidak menghalangi operasi)", [
        ("note", "LAPJU: prefill April 2025 & nomor B/  /IV/2025 masih contoh statis"),
        ("note", "LAPJU: ringkasan draf — spasi kosong utk hari pada tanggal"),
        ("note", "Identitas prefill = contoh demo; wajib diganti dengan data riil"),
        ("note", "Kualitas redaksi AI mengikuti kualitas input poin pengguna"),
        ("note", "docx_service & router telaahan-staf v1 dipakai web — biarkan"),
    ]),
    ("I", "Prosedur Operasional Rutin", [
        ("rutin", "Restart backend setiap selesai edit kode Python (reload=False)"),
        ("rutin", "Reindex RAG setelah tambah dokumen referensi (jangan nama dummy)"),
        ("rutin", "Update URL server aplikasi saat host berubah → Tes Koneksi"),
        ("rutin", "Set AUTH_* di setiap deployment baru; simpan di kanal resmi"),
        ("rutin", "Pantau llm_warnings bila naskah terasa janggal"),
    ]),
]

W = 1080
done = sum(1 for _, _, items in SECTIONS for st, _ in items if st == "done")
open_ = sum(1 for _, _, items in SECTIONS for st, _ in items if st == "open")
note = sum(1 for _, _, items in SECTIONS for st, _ in items if st == "note")
rutin = sum(1 for _, _, items in SECTIONS for st, _ in items if st == "rutin")
total_actionable = done + open_
pct = round(done * 100 / total_actionable)

MARK = {
    "done":  ('✔', '#15803d', '#dcfce7'),
    "open":  ('○', '#b45309', '#fef3c7'),
    "note":  ('•', '#475569', '#e2e8f0'),
    "rutin": ('↻', '#1d4ed8', '#dbeafe'),
}

rows = []
for huruf, judul, items in SECTIONS:
    d = sum(1 for st, _ in items if st == "done")
    t = len(items)
    pct_s = round(d * 100 / t)
    bar_color = "#15803d" if pct_s == 100 else "#b45309"
    item_html = ""
    for st, teks in items:
        gl, col, bg = MARK[st]
        label = {"note": "CATATAN", "rutin": "RUTIN"}.get(st, "")
        badge = f'<span class="lbl" style="background:{bg};color:{col};">{label}</span>' if label else ""
        item_html += (
            f'<div class="item"><span class="mark" style="color:{col};background:{bg};">{gl}</span>'
            f'<span class="txt">{teks}</span>{badge}</div>'
        )
    rows.append(f'''
    <div class="card">
      <div class="sec-head">
        <span class="badge">{huruf}</span>
        <span class="sec-title">{judul}</span>
        <span class="sec-count">{d}/{t}</span>
      </div>
      <div class="bar"><div class="fill" style="width:{pct_s}%;background:{bar_color};"></div></div>
      {item_html}
    </div>''')

chips = "".join(
    f'<div class="chip"><div class="chip-num">{d}/{t}</div><div class="chip-lbl">{j.split("—")[0].strip()}</div></div>'
    for (huruf, j, items) in SECTIONS
    for d, t in [(sum(1 for st, _ in items if st == "done"), len(items))]
)

html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ width: {W}px; margin:0; padding:0; background:#eef2f7; font-family: Arial, 'Segoe UI Symbol', 'DejaVu Sans', sans-serif; }}
.header {{ background:#14264a; color:#fff; padding:26px 36px 20px; border-bottom:6px solid #c9a227; }}
.h-title {{ font-size:26px; font-weight:bold; letter-spacing:0.5px; }}
.h-sub {{ font-size:13px; color:#b9c4d8; margin-top:4px; }}
.h-stats {{ margin-top:14px; }}
.h-stat {{ display:inline-block; margin-right:26px; vertical-align:top; }}
.h-num {{ font-size:30px; font-weight:bold; }}
.h-lbl {{ font-size:11px; color:#b9c4d8; text-transform:uppercase; letter-spacing:1px; }}
.chips {{ padding:16px 36px 4px; }}
.chip {{ display:inline-block; width:158px; margin:0 10px 10px 0; background:#fff; border:1px solid #d7dee8;
        border-radius:8px; padding:8px 10px; text-align:center; vertical-align:top; }}
.chip-num {{ font-size:16px; font-weight:bold; color:#14264a; }}
.chip-lbl {{ font-size:10px; color:#64748b; margin-top:2px; }}
.wrap {{ padding:8px 36px 30px; }}
.card {{ background:#fff; border:1px solid #d7dee8; border-radius:10px; padding:14px 18px 10px; margin-bottom:14px; }}
.sec-head {{ border-bottom:2px solid #e6ebf2; padding-bottom:8px; margin-bottom:6px; }}
.badge {{ display:inline-block; width:30px; height:30px; line-height:30px; text-align:center; border-radius:7px;
         background:#14264a; color:#fff; font-weight:bold; font-size:16px; vertical-align:middle; }}
.sec-title {{ font-size:16px; font-weight:bold; color:#14264a; margin-left:10px; vertical-align:middle; }}
.sec-count {{ float:right; font-size:15px; font-weight:bold; color:#475569; margin-top:6px; }}
.bar {{ height:6px; background:#e6ebf2; border-radius:3px; margin:6px 0 4px; }}
.fill {{ height:6px; border-radius:3px; }}
.item {{ padding:5px 0 5px 4px; border-bottom:1px solid #f1f5f9; font-size:12.5px; color:#1e293b; }}
.item:last-child {{ border-bottom:none; }}
.mark {{ display:inline-block; width:22px; height:22px; line-height:22px; text-align:center; border-radius:11px;
        font-size:13px; font-weight:bold; margin-right:9px; vertical-align:middle; }}
.txt {{ vertical-align:middle; }}
.lbl {{ display:inline-block; float:right; font-size:9px; font-weight:bold; padding:2px 8px;
       border-radius:9px; letter-spacing:0.5px; vertical-align:middle; }}
.footer {{ text-align:center; font-size:11px; color:#64748b; padding:4px 0 26px; }}
</style></head><body>
<div class="header">
  <div class="h-title">CHECKLIST MENYELURUH — SSEB AI</div>
  <div class="h-sub">Generator Naskah Dinas Otomatis · Backend FastAPI+Ollama · Android Compose · Bot Telegram · {date.today().strftime("%d %B %Y")}</div>
  <div class="h-stats">
    <div class="h-stat"><div class="h-num" style="color:#4ade80;">{done}</div><div class="h-lbl">Selesai &amp; Terverifikasi</div></div>
    <div class="h-stat"><div class="h-num" style="color:#fbbf24;">{open_}</div><div class="h-lbl">Terbuka</div></div>
    <div class="h-stat"><div class="h-num">{note}</div><div class="h-lbl">Catatan</div></div>
    <div class="h-stat"><div class="h-num">{rutin}</div><div class="h-lbl">Rutin</div></div>
    <div class="h-stat"><div class="h-num" style="color:#c9a227;">{pct}%</div><div class="h-lbl">Kesiapan</div></div>
  </div>
</div>
<div class="chips">{chips}</div>
<div class="wrap">{''.join(rows)}</div>
<div class="footer">Dirender otomatis dari CHECKLIST.md · rincian bukti verifikasi: PROGRESS.md bagian 1–15 · TLS ditunda s/d production (deploy/README-HTTPS.md)</div>
</body></html>'''

tmp_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_checklist_tmp.html")
with open(tmp_html, "w", encoding="utf-8") as f:
    f.write(html)

subprocess.run([WKHTMLTOIMAGE, "--width", str(W), "--quality", "92",
                "--enable-local-file-access", tmp_html, os.path.abspath(OUT_PNG)], check=True)
os.remove(tmp_html)
print("OK:", os.path.abspath(OUT_PNG))
