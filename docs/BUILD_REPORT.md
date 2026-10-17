# Hasil build LARSANA 0.1.1

Tanggal: 17 Oktober 2026. Kode LARSANA GPL-3.0-or-later. Ini build lokal yang dapat dipasang, dengan implementasi desktop dan runtime nyata. Belum dipublikasikan ke repository publik.

## Artefak dan platform

| Target ABI | Paket | Lingkungan verifikasi |
| --- | --- | --- |
| noble amd64 — Ubuntu 24.04 / Mint 22.x | dist/ | Builder berbasis paket resmi Mint/Ubuntu, host Mint 22.3, runtime dan paket dalam Bubblewrap |
| trixie amd64 — Debian 13 | dist/debian13/ | Builder terpisah dari repository Debian bertanda tangan, runtime dan paket dalam Bubblewrap |

Tiap target berisi 13 .deb: desktop, metapackage larsana-full, dan sebelas runtime hasil kompilasi source. Tidak mengklaim kompatibilitas Debian 12, Ubuntu 22.04, Mint 21.x, atau arm64.

| Runtime | Versi dalam build |
| --- | --- |
| Apache | 2.4.69 |
| Nginx stable | 1.30.6 |
| PHP CLI + FPM | 8.1.34, 8.2.34, 8.3.35, 8.4.26, 8.5.11 |
| MariaDB | 10.11.19 LTS, 11.8.9 LTS, 12.3.3 LTS, 13.0.2 stable/GA |

Default PHP 8.5, MariaDB 12.3 LTS. PHP 8.1 diberi label legacy/EOL. Versi adalah snapshot sources.lock.json, bukan unduhan terbaru otomatis. Pilihan MariaDB memakai direktori data terpisah per seri; tidak menjalankan upgrade/downgrade datadir lintas seri.

## Implementasi

Desktop Python/PySide6 Qt Quick dengan tema light/dark, menu/tray, Start/Stop All, pilihan versi, proyek, terminal, klien database, config dan log. Branding/aset SVG LARSANA dibuat sendiri. Pemetaan UI dan perbedaan dengan Laragon ada di UI_REFERENCE.md.

Apache memakai proxy_fcgi dan Nginx FastCGI ke PHP-FPM privat. Runtime read-only /usr/lib/larsana/runtimes, proses dan data milik pengguna biasa. Default HTTP localhost:8080, MariaDB localhost:3307. Terminal menambahkan PATH hanya untuk sesi tersebut. Helper Polkit hanya menambah/menghapus entri domain .test yang divalidasi.

## Bukti pengujian

- 20 unit test core/helper lulus: single-instance, isolasi environment, port, konfigurasi, pemilihan stable, preservasi data, pemulihan switching gagal, serta validasi domain.
- Request HTTP/FPM nyata untuk lima seri PHP pada Apache dan Nginx; versi CLI/FPM dan baseline extension diperiksa.
- Pergantian PHP saat web server aktif.
- Keempat MariaDB: init, stop/start, persistensi, koneksi PDO dari PHP 8.1, serta backup SQL dan restore.
- GUI dengan Qt privat dari payload paket dan Xvfb: klik Start All/Stop All, pilihan PHP aktif, pembuatan proyek, light/dark, tanpa warning QML. Warning tidak adanya session D-Bus dalam sandbox dicatat sebagai batas lingkungan headless.
- Lifecycle dpkg dalam filesystem sekali pakai: install, upgrade, remove, reinstall, purge; proyek dan database uji tetap ada. Helper .test diuji dalam root namespace dengan identitas pemanggil Polkit tersimulasi.
- Pemeriksaan struktur dan SHA256 source runtime, dependency ABI ELF, serta lintian paket final.
- Resolusi seluruh dependensi offline dari status dpkg kosong menggunakan hanya repository file bertanda tangan; tidak mengandalkan repository jaringan pada pemeriksaan ini.

Log dan ringkasan per target disertakan di validation/ pada distribusi. Semua langkah di atas harus berstatus PASS di log final sebelum artefak ditandai siap.

## Sumber, lisensi, dan packaging

Source runtime dipin beserta SHA256. PHP dicocokkan API rilis resmi, Apache/MariaDB dengan checksum resmi, Nginx dengan tanda tangan OpenPGP upstream. Paket dihasilkan melalui debhelper/dpkg-buildpackage dengan Requires-Root:no, prefix privat, dependency ABI terhitung, tanpa service global atau download/build di postinst.

Qt/PySide6 memakai wheel open source 6.8.3 privat. Arsip source Qt/PySide/Shiboken/ICU yang bersesuaian, upstream notices, lock source, resep build, dan source LARSANA disertakan dalam bundle. Library distro mempertahankan paket/lisensi distribusinya. Metapackage mengandalkan Depends; tidak menjalankan installer paket rekursif.

Pengecualian lintian yang sengaja dicatat secara spesifik: libmagic/GD bawaan upstream PHP; interpreter phar mengarah ke CLI PHP privat; plugin provider MariaDB yang mengambil simbol dari server dan tidak membutuhkan libc langsung; ICU data-only library. Pengecualian tidak mengubah perilaku linker. Warning hardening atau kebijakan distribusi yang tersisa dicatat di log, bukan klaim lolos review archive Debian.

Repository APT lokal memakai kunci build lokal dan disertai public key; private key tidak masuk bundle. Ini memverifikasi konsistensi bundle, bukan identitas rilis publik yang sudah diumumkan. SHA256SUMS mencakup artefak distribusi.

## Batas validasi

Belum ada pengujian VM desktop penuh, reboot, autentikasi dialog Polkit nyata, integrasi tray lintas GNOME/KDE/Cinnamon, atau matriks HiDPI. Render native Mint sempat diperiksa; uji interaksi terotomasi memakai Xvfb. Helper telah diuji, namun uji itu tidak menggantikan pengujian agent Polkit desktop. Build reproducible bit-for-bit belum dibuktikan.

UI mengikuti pola kerja Laragon; kesamaan pixel-perfect seluruh jendela belum terbukti. Quick app framework, HTTPS lokal, multi-PHP per proyek, runtime download/update melalui GUI, serta Apache dan Nginx bersamaan belum menjadi fitur rilis ini. Extension tambahan seperti Xdebug memerlukan paket ABI tersendiri. Kedua web server dan semua versi runtime yang tercantum sudah tersedia; pilih satu web server aktif melalui UI.

Tidak ada instalasi paket, penghentian XAMPP, perubahan hosts, atau konfigurasi layanan global pada host selama proses build dan uji. Operasi install/purge/helper dilakukan di filesystem uji terisolasi. Instalasi ke host pengguna dijalankan secara eksplisit melalui panduan README.

## Perubahan 0.1.1

Menambahkan MariaDB 11.8.9 LTS stable/GA dari pengumuman resmi https://mariadb.org/mariadb-server-12-3-11-8-11-4-and-10-11-q3-2026-maintenance-releases-and-goodbye-10-6/. Source SHA256 dikunci terhadap sha256sums.txt upstream. Paket desktop/metapackage dinaikkan ke 0.1.1 agar instalasi 0.1.0 dapat di-upgrade melalui APT. Pemilihan default MariaDB tetap LTS 12.3 untuk instalasi baru; pilihan tersimpan dan data seri lain dipertahankan.
