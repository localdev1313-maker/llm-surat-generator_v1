# Panduan HTTPS (TLS) untuk Backend SSEB AI

Basic auth saat ini berjalan di atas HTTP polos intranet — kredensial dan isi
naskah dapat disadap di jaringan bersama. Aplikasi Android sudah menampilkan
peringatan ⚠️ di layar Pengaturan. Solusi tuntas: **reverse-proxy TLS** di depan
backend. Pilih salah satu opsi di bawah (Caddy paling sederhana — sertifikat
otomatis).

Setelah TLS aktif:
1. Aplikasi Android → Pengaturan → URL server diganti `https://<host>/`.
2. Peringatan ⚠️ HTTP otomatis hilang (URL diawali `https://`).

---

## Opsi A — Caddy (direkomendasikan; sertifikat self-signed internal otomatis)

`Caddyfile`:

```
https://:8443 {
    tls internal
    reverse_proxy 127.0.0.1:8001
}
```

Jalankan: `caddy run` (folder `deploy/`). Aplikasi memakai
`https://<ip-server>:8443/`.

> `tls internal` memakai CA lokal Caddy — perangkat Android perlu memasang root
> CA Caddy sekali (unduh `http://<host>:2019/m/ca` lalu instal via
> Setelan > Keamanan > Enkripsi & kredensial > Instal sertifikat > CA), atau
> gunakan domain nyata + Let's Encrypt bila server punya nama DNS publik:
> ganti baris tls menjadi `tls email@anda@instansi.go.id`.

## Opsi B — Nginx + sertifikat existing

```nginx
server {
    listen 8443 ssl;
    server_name sseb.intranet.go.id;

    ssl_certificate     /etc/ssl/certs/sseb.crt;
    ssl_certificate_key /etc/ssl/private/sseb.key;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 25m;
    }
}
```

## Opsi C — uvicorn langsung dengan sertifikat

Bila tidak ingin proxy, uvicorn bisa melayani TLS sendiri (edit `run.py`):

```python
uvicorn.run(
    "app.main:app", host="0.0.0.0", port=8443,
    ssl_certfile="cert.pem", ssl_keyfile="key.pem",
)
```

Sertifikat self-signed untuk intranet:

```
openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
  -keyout key.pem -out cert.pem \
  -subj "/CN=sseb.intranet.go.id" \
  -addext "subjectAltName=IP:192.168.1.100"
```

> Sertifikat self-signed TIDAK dipercaya Android secara default. Untuk
> mempercayainya di perangkat: tambahkan `network_security_config.xml` yang
> memuat sertifikat CA tersebut (minta panduan bila diperlukan), atau gunakan
> CA yang dipercaya perangkat.

## Catatan keamanan tambahan

- Set `AUTH_USERNAME` + `AUTH_PASSWORD` di `.env` (wajib — tanpa itu API
  terbuka, dan server menolak start bila hanya salah satunya diset).
- SharedPreferences kredensial & passphrase DB sudah di-exclude dari backup
  perangkat; TLS menutup vektor penyadapan jalur.
