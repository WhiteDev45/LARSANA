# Publikasi LARSANA ke GitHub

Panduan ini menyiapkan repository kode dan rilis binary. Perintah publikasi dijalankan oleh pemilik akun GitHub; belum ada repository remote atau rilis yang dibuat oleh penyiapan dokumentasi ini.

## Deskripsi repository

English:

> A clean local PHP development environment for Ubuntu, Debian, and Linux Mint, with Apache, Nginx, multi-version PHP, MariaDB, and phpMyAdmin in one .deb installer.

Bahasa Indonesia:

> Sarana pengembangan PHP lokal untuk Ubuntu, Debian, dan Linux Mint, dengan Apache, Nginx, pilihan versi PHP, MariaDB, serta phpMyAdmin dalam satu installer .deb.

Tagline: **Sarana tangguh dan bersih untuk web development modern di Linux.**

Topics yang sesuai: `linux`, `php`, `laravel`, `local-development`, `debian`, `ubuntu`, `linux-mint`, `apache`, `nginx`, `mariadb`, `phpmyadmin`, `pyside6`.

## 1. Buat repository kosong

Login ke GitHub, pilih **New repository**, gunakan nama `LARSANA`, visibility **Public**, dan isi deskripsi di atas. Jangan menambahkan README, .gitignore, atau license dari template GitHub karena proyek sudah memilikinya.

## 2. Unggah source

Jalankan dari folder proyek. Contoh berikut untuk folder yang belum diinisialisasi sebagai repository Git:

```bash
cd /opt/lampp/htdocs/LARSANA
git init -b main
git add .
git status --short
```

Pastikan `.build/`, `.venv/`, `dist/`, `releases/`, file `.deb`, serta `.env` tidak masuk staging. `.gitignore` proyek sudah mengabaikannya. Lihat perubahan sebelum commit:

```bash
git diff --cached --stat
git commit -m "Initial release: LARSANA 1.2.1"
```

Jika Git belum mengenal identitas penulis, atur **hanya untuk repository ini**, lalu ulangi commit:

```bash
git config user.name "Nama Kamu"
git config user.email "Email GitHub atau email noreply GitHub kamu"
```

Ganti `USERNAME` dengan akun/organisasi GitHub kamu:

```bash
git remote add origin https://github.com/USERNAME/LARSANA.git
git push -u origin main
```

Untuk autentikasi HTTPS gunakan GitHub CLI (`gh auth login`) atau personal access token lewat prompt Git, bukan password akun. Jangan memasukkan token ke URL remote atau file proyek. Jika remote `origin` sudah ada, periksa `git remote -v` sebelum mengubahnya; jangan membuat remote duplikat.

README.md menampilkan bahasa Inggris; README.id.md menampilkan bahasa Indonesia. Keduanya mempunyai tautan untuk berpindah bahasa.

## 3. Buat GitHub Release v1.2.1

Buka repository → **Releases** → **Draft a new release**. Buat tag `v1.2.1` pada branch `main`, judul **LARSANA 1.2.1**, dan gunakan catatan rilis di bagian berikut. Lampirkan:

```text
releases/larsana_1.2.1_amd64.deb
```

Installer sekitar 202 MiB. GitHub memblokir file Git biasa di atas 100 MiB; aset Releases harus berukuran di bawah 2 GiB per file. Karena itu installer didistribusikan sebagai aset release, bukan di-commit ke repository. Folder `releases/` lokal tetap berisi satu installer.

Verifikasi sebelum mengunggah:

```bash
sha256sum releases/larsana_1.2.1_amd64.deb
```

## 4. Sertakan corresponding source

GitHub otomatis membuat arsip source repository pada tag tersebut. Arsip ini tidak mencakup runtime/dependensi vendor di folder yang diabaikan Git. Untuk binary yang dibagikan, publikasikan juga source upstream yang bersesuaian, notices, dan resep/patch build yang sudah disiapkan di `dist/sources-1.2.1/`.

Bila perlu, siapkan arsip source dalam beberapa bagian berukuran di bawah batas aset GitHub:

```bash
tar -C dist -cf - sources-1.2.1 | split -b 1800M - dist/larsana-corresponding-source-1.2.1.tar.part-
```

Unggah **semua** file `dist/larsana-corresponding-source-1.2.1.tar.part-*` sebagai aset source di release yang sama. Untuk membuka source, penerima menggabungkan bagian-bagiannya:

```bash
cat larsana-corresponding-source-1.2.1.tar.part-* | tar -xf -
```

Pengguna biasa hanya memerlukan **satu `.deb`** untuk memasang aplikasi. Bagian source ditujukan untuk pemenuhan distribusi source dan kebutuhan pengembang. README/source snapshot di arsip rilis lokal berasal dari saat build; dokumentasi terbaru juga tersedia pada tag GitHub yang dipublikasikan.

## Catatan rilis siap salin

### English

LARSANA 1.2.1 fixes local MariaDB access: root over TCP/socket, default port 3306, and updated phpMyAdmin login guidance. One amd64 .deb includes the desktop, Apache, stable Nginx, PHP 8.1–8.5, MariaDB 10.11/11.8/12.3/13.0, and phpMyAdmin.

Targets Ubuntu 24.04, Linux Mint 22.x, and Debian 13. phpMyAdmin follows the selected database and uses a separate bundled PHP 8.3 process. Local database instances use root with an empty password over a private socket or TCP at 127.0.0.1:3306. Existing custom passwords are preserved.

Installation, upgrades, database persistence, phpMyAdmin login/SQL/import/export, and GUI interactions were tested in isolated noble/trixie environments. Full desktop VM/reboot/tray/real Polkit-agent validation remains incomplete. PHP 8.1 is provided as a legacy/EOL option.

Close LARSANA before installing or upgrading. Download the .deb asset, then run `sudo apt install ./larsana_1.2.1_amd64.deb`. Project and database data are retained on removal. APT may download missing OS libraries. Corresponding source assets are for developers and are not required for installation.

### Bahasa Indonesia

LARSANA 1.2.1 memperbaiki akses MariaDB lokal: root lewat TCP/socket, default port 3306, dan petunjuk login phpMyAdmin terbaru. Satu .deb amd64 berisi desktop, Apache, Nginx stable, PHP 8.1–8.5, MariaDB 10.11/11.8/12.3/13.0, dan phpMyAdmin.

Menargetkan Ubuntu 24.04, Linux Mint 22.x, dan Debian 13. phpMyAdmin mengikuti database terpilih dan memakai proses PHP 8.3 bawaan secara terpisah. Instance database lokal memakai root dengan password kosong melalui socket privat maupun TCP 127.0.0.1:3306. Password kustom yang sudah ada dipertahankan.

Instalasi, upgrade, persistensi database, login/SQL/impor/ekspor phpMyAdmin, serta interaksi GUI telah diuji pada lingkungan terisolasi noble/trixie. Pengujian VM desktop/reboot/tray/agent Polkit nyata masih belum lengkap. PHP 8.1 disediakan sebagai pilihan legacy/EOL.

Tutup LARSANA sebelum instalasi atau upgrade. Unduh aset .deb, lalu jalankan `sudo apt install ./larsana_1.2.1_amd64.deb`. Penghapusan paket mempertahankan data proyek dan database. APT dapat mengunduh library OS yang belum tersedia. Aset corresponding source ditujukan untuk pengembang dan tidak diperlukan untuk instalasi.

## Referensi resmi

- [Menambahkan source lokal ke GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [Batas ukuran file GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
