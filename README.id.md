# LARSANA

**Sarana tangguh dan bersih untuk web development modern di Linux.**

[English](README.md) · [Bahasa Indonesia](README.id.md)

[![Unduh .deb](https://img.shields.io/badge/Download-.deb-2563eb?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/WhiteDev45/LARSANA/releases/download/v1.2.0/larsana_1.2.0_amd64.deb)

[Unduh .deb — LARSANA 1.2.0](https://github.com/WhiteDev45/LARSANA/releases/download/v1.2.0/larsana_1.2.0_amd64.deb)

LARSANA 1.2.0 · amd64 · Ubuntu 24.04 / Linux Mint 22.x / Debian 13

LARSANA adalah aplikasi desktop open source untuk pengembangan PHP lokal pada Ubuntu, Linux Mint, dan Debian. Terinspirasi alur kerja Laragon, LARSANA menyediakan Apache, Nginx stable, pilihan versi PHP, MariaDB, serta phpMyAdmin dalam satu installer `.deb`.

LARSANA dikembangkan secara independen dengan branding dan aset sendiri. Proyek ini bukan rilis resmi Laragon dan tidak berafiliasi dengan Laragon maupun Laravel.

## Nama dan filosofi

Nama LARSANA mencerminkan identitas proyek: **Lar** membawa inspirasi ekosistem pengembangan web Laragon/Laravel; **Sana** dimaknai sebagai sarana pendukung developer yang mengutamakan lingkungan kerja bersih dan tertata. Nama ini juga menggambarkan perpindahan pengalaman pengembangan tersebut ke platform lain: Linux.

Makna tersebut merupakan filosofi merek yang dipilih proyek. LARSANA bertujuan memudahkan pekerjaan harian developer, menjaga runtime aplikasi terpisah dari layanan sistem, serta mempertahankan proyek dan database pengguna.

> LARSANA: Sarana tangguh dan bersih untuk web development modern di Linux.

## Isi versi 1.2.0

| Komponen | Versi yang disertakan |
| --- | --- |
| Apache | 2.4.69 |
| Nginx | 1.30.6, channel stable |
| PHP | 8.1.34, 8.2.34, 8.3.35, 8.4.26, 8.5.11 |
| MariaDB | 10.11.19, 11.8.9 LTS, 12.3.3 LTS, 13.0.2 stable/GA rolling |
| phpMyAdmin | 5.2.3 |

PHP 8.1 tersedia sebagai pilihan legacy/EOL. Default aplikasi adalah PHP 8.5 dan MariaDB 12.3 LTS. phpMyAdmin memakai proses PHP 8.3 bawaan secara terpisah, sehingga tidak mengubah pilihan PHP proyek.

Desktop menyediakan Start All / Stop All, pemilihan runtime, pembuatan proyek, akses konfigurasi dan log, pemeriksaan extension PHP, terminal, menu tray jika didukung desktop, serta konfigurasi domain `.test` melalui autentikasi Polkit.

## Sistem yang didukung

Satu installer **amd64 / x86-64** yang sama menargetkan Ubuntu 24.04 LTS, Linux Mint 22.x, dan Debian 13. Payload yang sama telah diuji pada lingkungan terisolasi noble dan trixie, termasuk HTTP/FPM, operasi database, interaksi GUI, instalasi, upgrade, dan penghapusan paket.

Versi distro lain dan ARM64 belum diverifikasi. Pengujian VM desktop/reboot penuh, tray lintas desktop, serta autentikasi melalui agent Polkit nyata masih belum tercakup. Nomor versi tidak berarti pengujian tersebut sudah selesai.

## Instalasi atau upgrade

Unduh **`larsana_1.2.0_amd64.deb`** dari halaman **Releases** repository ini. ZIP/TAR source code yang dibuat otomatis oleh GitHub merupakan kode sumber; pilih `.deb` untuk memasang aplikasi.

Tutup LARSANA sebelum upgrade, lalu jalankan dari folder unduhan:

```bash
sudo apt install ./larsana_1.2.0_amd64.deb
larsana
```

Aplikasi juga dapat dibuka lewat ikon **LARSANA** di menu aplikasi. Jalankan sebagai pengguna biasa. Seluruh runtime LARSANA sudah disertakan; APT dapat memerlukan internet untuk library sistem operasi yang belum terpasang.

## Proyek dan database

| Kebutuhan | Lokasi atau alamat default |
| --- | --- |
| Aplikasi dan runtime bawaan | `/usr/lib/larsana/` |
| Proyek | `~/Larsana/www/` |
| Web server | `http://localhost:8080` |
| Port TCP MariaDB | `3307` |
| Pengaturan | `~/.config/larsana/` |
| Data database | `~/.local/share/larsana/mariadb/<seri>/` |
| Log | `~/.local/state/larsana/` |

Lokasi data pengguna mengikuti pengaturan XDG jika diatur. Port 3307 membantu menghindari bentrok dengan database sistem atau XAMPP pada 3306. Setiap seri MariaDB memakai direktori data terpisah; mengganti versi tidak memigrasikan atau menurunkan versi database lama.

Klik **phpMyAdmin** untuk menyalakan MariaDB terpilih dan membuka pengelolaan database di browser. Untuk database yang baru diinisialisasi, login memakai nama pengguna Linux (`whoami`) dan password kosong melalui autentikasi socket lokal. Gunakan kredensial yang sudah ada jika akun database pernah diubah.

Untuk Laravel, gunakan socket Unix MariaDB terpilih jika memakai akun bawaan dengan autentikasi socket. Untuk koneksi TCP ke `127.0.0.1:3307`, buat akun database dengan password dan berikan akses ke database proyek. phpMyAdmin memakai socket privat instance terpilih dan alamat web loopback dengan port yang tersedia. Stop/ganti MariaDB, Stop All, atau keluar dari LARSANA akan menghentikan server phpMyAdmin.

## Menghapus aplikasi

Hentikan semua layanan dan tutup LARSANA, lalu jalankan:

```bash
sudo apt remove larsana
```

Remove maupun purge mempertahankan proyek, database, dan pengaturan di direktori home pengguna.

## Pengembangan dan packaging

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials==6.8.3 pytest
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m larsana
```

Menjalankan GUI dari source saja tidak memasang runtime atau phpMyAdmin. Gunakan installer lengkap untuk lingkungan yang siap digunakan.

Versi/checksum sumber runtime dikunci dalam `runtimes/sources.lock.json`; phpMyAdmin dikunci dalam `runtimes/phpmyadmin.lock.json`. Tool build rootless berada di `tools/`. Packaging memerlukan runtime hasil kompilasi, payload desktop, builder noble, dan sumber dependensi yang sudah disiapkan; `build_unified.py` bukan perintah build mandiri dari checkout kosong.

Baca [dokumentasi packaging](docs/UNIFIED_PACKAGE.md), [rencana pengembangan](docs/PLAN.md), [panduan kontribusi](CONTRIBUTING.md), dan [panduan publikasi GitHub](docs/GITHUB_PUBLISH.md). Workflow GitHub menjalankan pemeriksaan core Python; workflow tersebut tidak membangun atau mensertifikasi installer lengkap.

## Lisensi dan ketersediaan source

Aplikasi Python/Qt menggunakan [GPL-3.0-or-later](LICENSE). Router PHP phpMyAdmin mempunyai pengecualian GPL-2.0-only; lihat [notice terkait](packaging/phpmyadmin-router.copyright). phpMyAdmin, runtime, Qt, dan dependensi bawaan lainnya mempertahankan lisensi dan notice upstream masing-masing.

Distribusi binary harus disertai source yang bersesuaian serta instruksi build/patch yang diwajibkan lisensinya. Source rilis yang disiapkan tersedia secara lokal di `dist/unified-sources/`; maintainer memublikasikannya bersama installer. Source tersebut bukan dependensi tambahan untuk instalasi.
