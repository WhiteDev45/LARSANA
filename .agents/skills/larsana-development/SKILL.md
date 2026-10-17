---
name: larsana-development
description: Rencanakan dan implementasikan desktop LARSANA bergaya Laragon untuk Debian, Ubuntu, dan Linux Mint, termasuk UI Qt, runtime Apache/Nginx, multi-PHP, MariaDB, dan packaging .deb. Gunakan untuk pekerjaan pada proyek LARSANA.
---

# LARSANA development

## Konteks proyek

Temukan root repository LARSANA dari workspace aktif; baca `docs/PLAN.md` sebelum mengubah arsitektur, UI, runtime, atau packaging. Jika skill dimuat lewat symlink, resolve lokasi fisik untuk menemukan root proyek. Rencana adalah keputusan awal yang dapat diperbarui menurut instruksi pengguna; jangan mengklaim milestone selesai hanya karena dokumennya tersedia.

Target wajib pengguna: UI modern sangat dekat dengan Laragon; Apache dan Nginx; pilihan PHP mulai 8.1 hingga stable terbaru; MariaDB 10.11 dan terbaru; aplikasi serta runtime terdistribusi sebagai .deb. Gunakan bahasa Indonesia untuk penjelasan kepada pengguna. Jangan mengurangi target penuh menjadi hanya satu web server atau satu versi runtime.

## UI dan reverse engineering perilaku

- Gunakan referensi publik/observasi Laragon, catat versi dan asal referensi. Petakan posisi kontrol, menu, shortcut, status, dan aksi sebelum membuat UI. Pertahankan jendela ringkas, Start All/Stop All, Web, Database, Terminal, Root, serta menu/tray bertingkat.
- Gunakan implementasi sendiri, branding LARSANA, dan aset asli atau berlisensi sesuai. Jangan mengasumsikan hak distribusi kode/aset Laragon.
- Python + PySide6/Qt Quick adalah pilihan awal. Buktikan packaging Qt pada target tertua sebelum memperluas UI. Pisahkan core dari QML; jalankan pekerjaan lama secara asynchronous dengan progress/cancel yang sesuai.
- Status layanan berasal dari observasi proses/health check. Mock harus ditandai sebagai mock. Jangan mengklaim kesamaan pixel-perfect tanpa perbandingan referensi. Sediakan fallback ketika tray desktop tidak tersedia.

## Runtime dan versi

- Cek versi melalui sumber resmi yang ditautkan di rencana saat memperbarui katalog. Pin versi lengkap, checksum, source, channel, recipe/patch, distro, arsitektur, dan dependency ABI. Bedakan stable, LTS, rolling, RC, preview, dan EOL.
- PHP 8.1 tetap tersedia sebagai legacy; stable terbaru yang sudah diuji menjadi default. CLI, FPM, php.ini, socket, dan extension harus sesuai seri/ABI yang dipilih.
- Nginx hanya menggunakan channel stable sesuai keputusan pengguna. Pilih patch stable terbaru yang diverifikasi dan diuji; jangan menyediakan mainline sebagai pilihan katalog atau paket.
- Apache memakai PHP-FPM melalui proxy_fcgi dan Nginx melalui FastCGI. Satu server per port default; keduanya boleh berjalan jika port terpisah. Jangan mengambil alih port dari layanan lain.
- Switching PHP adalah transaksi: siapkan instance baru, validasi, health check, uji konfigurasi server, reload, request nyata, lalu commit; kegagalan memulihkan konfigurasi dan seleksi lama.
- MariaDB mempunyai datadir/socket/kredensial terpisah per seri/instance. Version picker tidak menjalankan migrasi/downgrade in-place. Migrasi memerlukan jalur resmi, backup terverifikasi, dan pemulihan yang diuji.
- MariaDB hanya menyediakan rilis stable/GA, termasuk seri 10.11, 11.8 LTS, dan versi terbaru yang telah diverifikasi dan diuji. Default memakai LTS stable. Jangan menyediakan alpha, beta, RC, atau preview; rilis rolling hanya memenuhi syarat jika sudah stable/GA dan lulus pengujian.

## phpMyAdmin

- Rilis 1.2.0 menyertakan phpMyAdmin stabil 5.2.3 langsung dalam paket tunggal, dipin URL/SHA256/lisensi dalam runtimes/phpmyadmin.lock.json. Jangan memakai snapshot development.
- Tombol phpMyAdmin/tray memakai PHP 8.3 privat terpisah dari pilihan PHP proyek, bind loopback, cookie login dan socket MariaDB terpilih. Stop/ganti MariaDB dan Stop All/Exit harus menutup layanan phpMyAdmin. Config/cache/session mengikuti XDG pengguna.
- Verifikasi aset JavaScript (termasuk js/messages.php dan js/vendor), login nyata, SQL dan roundtrip impor/ekspor pada setiap MariaDB; router tidak boleh mengekspos config/vendor PHP/setup/SQL/session.

## Batas operasi sistem

- Jalankan GUI dan layanan pengembangan sebagai pengguna biasa. Runtime paket read-only milik root; state/config/data mengikuti XDG; proyek default ~/Larsana/www.
- Jangan mengganti PHP global, alternatives, konfigurasi layanan distro/XAMPP, atau shell rc untuk memilih runtime LARSANA. Terminal hanya mewarisi PATH sesi yang dipilih.
- Kelola hanya proses milik LARSANA. Bind loopback, deteksi konflik port, verifikasi identitas proses sebelum stop, dan hindari shell interpolation atas input pengguna.
- Integrasi privileged harus berupa operasi terbatas dengan autentikasi sistem, validasi input/path, dan helper yang tidak menjalankan command bebas. Jangan memberi kemampuan privileged ke interpreter Python.
- Instalasi/penghapusan paket mempertahankan database dan proyek pengguna. Jangan menguji purge atau migrasi terhadap data pengguna nyata; gunakan instance sekali pakai.

## Build dan .deb

- Distribusi utama mengikuti permintaan pengguna terbaru: SATU paket larsana .deb berisi desktop dan seluruh runtime. Paket modular hanya artefak build internal/historis. Uji file .deb yang sama di noble dan trixie; library kompatibilitas privat tidak boleh mengganti library sistem.
- Semua runtime yang diminta harus tersedia sebagai .deb, tetapi library distro boleh menjadi Depends. Jangan mengganti runtime terisolasi dengan service global distro tanpa instruksi pengguna.
- Jangan menyarang .deb, installer apt/dpkg, build, atau download di maintainer scripts. Payload tunggal dimiliki langsung oleh paket larsana; Conflicts/Replaces mengelola penggantian paket modular lama melalui APT. Library dasar desktop tetap boleh menjadi Depends OS.
- Builder saat ini memakai Bubblewrap dan paket APT yang diekstrak tanpa root. Selesaikan bootstrap dan normalisasi alias usr-merge sebelum kompilasi; jangan mengekstrak dependensi tambahan ke builder yang sedang dipakai karena alias /lib atau /bin dapat berubah menjadi direktori dan merusak linking.
- Paketkan hanya prefix runtime privat dari hasil install upstream. Jangan ikut memasang file systemd/PAM global yang dihasilkan upstream. PHP memakai INSTALL_ROOT untuk staging make install; Apache/Nginx memakai DESTDIR. Normalisasi permission dan pertahankan lisensi pada payload Qt privat.
- Gunakan debhelper/dpkg-buildpackage dan builder per target. Hitung dependency library, simpan source/patch/build manifest, notices dan kewajiban lisensi setiap komponen. Kode LARSANA direncanakan GPL-3.0-or-later; runtime tidak otomatis berganti lisensi.
- Maintainer scripts idempotent dan noninteraktif; uji install/upgrade/remove/reinstall, recovery instalasi gagal, dan preservasi data. Klaim dukungan distro hanya setelah tes pada target tersebut.

## Verifikasi dan pelaporan

Jalankan pemeriksaan yang sesuai perubahan. Untuk runtime, gunakan request PHP nyata pada Apache dan Nginx, cek CLI/FPM/extension dan koneksi MariaDB; untuk switching, uji rollback; untuk DB, uji persistensi dan backup/restore; untuk packaging, gunakan lintian dan lingkungan bersih. GUI/tray/Polkit perlu VM desktop, bukan hanya container.

Laporkan file/artefak yang dibuat, hasil uji yang benar-benar dijalankan, target yang belum diuji, serta batas implementasi. Bedakan rencana, mock UI, resep build, paket hasil build, dan rilis tervalidasi. Jangan menerbitkan paket atau mengubah layanan host hanya untuk memenuhi tugas perencanaan.
