# Rencana LARSANA

Keputusan terbaru pengguna (1.2.1): default port MariaDB 3306, root localhost dan 127.0.0.1 tanpa password untuk instance lokal, bootstrap akun lama socket-only, preservasi password kustom dan data, serta petunjuk login phpMyAdmin menggunakan root. Default 3307 dimigrasikan satu kali.

Riwayat keputusan: rilis **1.2.0** menambahkan phpMyAdmin 5.2.3 ke installer tunggal. PHP 8.3 privat menjalankan UI database secara terpisah dari PHP proyek; akses loopback dan socket MariaDB terpilih. Penomoran 1.2.0 atas permintaan pengguna tidak memperluas klaim pengujian desktop.

Tanggal keputusan: 17 Oktober 2026. Status: distribusi utama 0.2.0 memakai satu paket lintas noble/trixie amd64; bagian milestone modular berikut adalah riwayat implementasi 0.1.1. Lihat BUILD_REPORT.md untuk bukti uji dan batas validasi desktop; target 1.0 tetap menjadi kriteria lanjutan.

## Tujuan dan batas rilis

LARSANA adalah aplikasi desktop open source untuk lingkungan pengembangan web lokal pada Debian, Ubuntu, dan Linux Mint. Target pengalaman pengguna sangat dekat dengan Laragon: jendela ringkas, menu bertingkat, kontrol layanan, pilihan versi, tray, terminal, dan akses proyek yang cepat. Implementasi ditulis sendiri berdasarkan perilaku yang diamati dan dokumentasi publik. Branding menggunakan LARSANA; aset dan kode Laragon tidak menjadi dependensi.

Target rilis 1.0 wajib mencakup Apache dan Nginx, PHP 8.1 hingga stable terbaru, MariaDB 10.11 dan stable terbaru, serta paket .deb seluruh komponen aplikasi/runtime. Tahap pengembangan boleh bertahap, tetapi rilis dengan satu server atau satu versi PHP belum memenuhi target penuh.

Lisensi kode LARSANA: GPL-3.0-or-later. Teks lengkap tersedia dalam LICENSE dan paket desktop. Runtime, Qt/PySide6, dan pustaka lain mempertahankan lisensi masing-masing; hasil distribusi mencakup notices, daftar komponen, source yang diwajibkan, patch, serta resep build.

## Antarmuka dan kesetaraan Laragon

Gunakan Python + PySide6 dengan Qt Quick/QML untuk jendela desktop modern. Core Python tidak bergantung pada komponen UI. Ini keputusan arsitektur awal; buktikan dependensi Qt dan packaging pada distro tertua sebelum membuat seluruh UI.

Layout utama mengikuti pola Laragon, bukan dashboard web besar:

```text
┌──────────────────────────────────────────────────────────┐
│ LARSANA                          Preferences    Menu     │
│ Local development environment                            │
│                                                          │
│ Apache 2.4       Running          Port 8080               │
│ PHP 8.5          Running          Change version ▾        │
│ MariaDB 10.11    Running          Port 3307               │
│                                                          │
│ Document root: ~/Larsana/www                              │
│                                                          │
│ Start All / Stop All   Web   Database   Terminal   Root    │
└──────────────────────────────────────────────────────────┘
```

Wireframe ini menyatakan hierarki, bukan klaim pixel-perfect. Milestone UI pertama harus memeriksa screenshot publik/observasi Laragon, mencatat versi referensi, lalu membuat peta posisi kontrol, ukuran, urutan menu, label, shortcut, dan perilaku klik. Ketelitian visual dinilai terhadap referensi yang benar-benar dilihat. Mintalah screenshot hanya untuk detail yang tidak tersedia dari referensi publik.

Menu: Apache/Nginx > Start/Stop/Restart, Version, Configuration, Logs; PHP > Version, Extensions, php.ini, Logs; MariaDB > Version, Start/Stop, Configuration, Logs; Projects, Quick app, Tools, Preferences, Exit. Menu tray mencerminkan aksi utama. Pada desktop tanpa dukungan tray, semua aksi tetap tersedia dari jendela.

Gunakan tipografi jelas, jarak konsisten, ikon asli/berlisensi sesuai, tema light/dark, fokus keyboard, dan skala HiDPI. Status memiliki teks serta warna. Tampilkan Starting, Running, Stopping, Stopped, Failed berdasarkan keadaan proses nyata; pekerjaan build, download, dan start tidak memblokir UI.

## Matriks runtime awal

Snapshot sumber resmi pada tanggal dokumen; patch final harus diperiksa dan dikunci ulang sebelum build.

| Komponen | Target |
| --- | --- |
| Apache httpd | Seri 2.4, patch stabil terbaru saat build |
| Nginx | Hanya channel stable; pilih patch stable terbaru yang sudah diverifikasi dan diuji |
| PHP | 8.1, 8.2, 8.3, 8.4, 8.5; tambah stable baru melalui katalog |
| MariaDB | Hanya rilis stable/GA: 10.11 dan seri terbaru yang sudah diverifikasi dan diuji; default LTS stable |

PHP 8.5 adalah cabang stable terbaru pada pengecekan. PHP 8.1 sudah EOL sejak 31 Desember 2025; tetap tersedia sebagai opsi legacy sesuai kebutuhan pengguna. Pilihan default PHP adalah stable terbaru yang lulus tes, bukan 8.1.

Pada pengecekan, MariaDB 10.11.19, 11.8.9 LTS, 12.3.3 LTS, dan 13.0.2 rolling tercantum di situs resmi. Sesuai keputusan pengguna, hanya rilis MariaDB yang sudah berstatus stable/GA boleh masuk katalog dan paket; alpha, beta, RC, dan preview dikecualikan. Default memakai LTS stable yang sudah diuji. Rolling hanya boleh tersedia jika rilisnya telah stable/GA dan lulus pengujian; label rolling sendiri tidak membuktikan status stable. Versi terbaru berarti patch yang sudah diverifikasi dan diuji, bukan download dinamis tanpa versi tetap.

Katalog menyimpan versi upstream lengkap, channel, URL sumber resmi, checksum, tanda tangan bila tersedia, resep/patch build, target distro/arsitektur, dependensi ABI, status dukungan, dan versi paket Debian. Catat provenance dan hash artefak hasil build. Katalog nantinya menggunakan metadata repository bertanda tangan.

## Core dan isolasi

Komponen: desktop UI, project manager, runtime catalog, service supervisor, configuration renderer, package integration, dan helper privileged terbatas. Shared state memiliki satu pemilik untuk mencegah dua jendela menyalakan instance ganda.

- Runtime read-only milik root: /usr/lib/larsana/runtimes/<komponen>/<seri>/.
- CLI aplikasi: /usr/bin/larsana; data desktop/ikon: /usr/share/.
- Preferensi: $XDG_CONFIG_HOME/larsana; data runtime/database: $XDG_DATA_HOME/larsana; state/log: $XDG_STATE_HOME/larsana; cache: $XDG_CACHE_HOME/larsana. Gunakan fallback XDG standar jika variabel tidak diatur.
- Socket/PID sementara: $XDG_RUNTIME_DIR/larsana, akses hanya pengguna; konfigurasi efektif tiap instance di direktori pengguna.
- Default proyek: ~/Larsana/www, dapat diganti. Instalasi paket tidak membuat proyek di home milik root.
- Supervisor hanya mengendalikan proses yang dimilikinya, memeriksa identitas proses sebelum stop, serta tidak menghentikan layanan distro/XAMPP untuk membebaskan port.
- Bind layanan ke loopback secara default. Port awal 8080/8443/3307 menghindari kebutuhan root, tetapi tetap diperiksa terhadap konflik. Domain .test memerlukan resolver/hosts yang dikelola; URL awal boleh memakai port eksplisit.
- Port 80/443, entri hosts, trust CA, dan instalasi paket memakai integrasi sistem terautentikasi. Helper tidak menerima shell bebas, executable arbitrary, atau path yang dapat menembus area yang diizinkan. Jangan menjalankan GUI sebagai root atau memberi capability bind port ke interpreter Python.

Jangan mengubah /usr/bin/php, alternatives global, konfigurasi web server distro, atau service database sistem. Terminal LARSANA menambahkan path runtime pilihannya hanya ke environment sesi tersebut. Jangan mengubah PATH global/shell rc pengguna secara diam-diam.

## Apache/Nginx dan pergantian PHP

Keduanya dapat dipasang bersamaan. Default satu web server aktif untuk port yang sama. Jika keduanya dijalankan bersamaan, wajib mempunyai port dan konfigurasi terpisah; konflik ditampilkan tanpa menghentikan server lain.

Apache menggunakan event MPM + mod_proxy_fcgi; Nginx menggunakan fastcgi_pass. Keduanya terhubung ke PHP-FPM melalui socket privat. Tidak menggunakan mod_php sehingga perpindahan versi tidak bergantung ABI modul Apache.

Setiap seri PHP menyediakan CLI dan FPM, php.ini/pool/socket sendiri, dan extension dengan ABI yang sesuai. Baseline extension: PDO MySQL, mysqli, mbstring, curl, OpenSSL, intl, zip, GD, XML/DOM/SimpleXML/XMLReader/XMLWriter, bcmath, fileinfo, sockets, dan OPcache sesuai kemampuan seri. Extension eksternal seperti Xdebug menjadi paket per seri/ABI.

Transaksi pergantian PHP: validasi runtime/extension, siapkan konfigurasi baru, jalankan FPM baru, periksa health, uji konfigurasi server, pindahkan koneksi dan reload, cek request PHP nyata, lalu hentikan FPM lama. Jika gagal, pulihkan konfigurasi/seleksi lama dan laporkan log. CLI dalam terminal baru harus sesuai pilihan; sesi terminal lama tidak dianggap otomatis berubah. Versi per proyek menjadi pengembangan lanjutan setelah switching global stabil.

## MariaDB dan perlindungan data

Setiap seri/instance mempunyai datadir, socket, port, log, dan kredensial sendiri. Memilih versi lain membuka instance seri tersebut; tidak mengarahkan binary baru ke datadir seri lama secara otomatis. Kredensial dan socket hanya dapat diakses pengguna yang bersangkutan.

Migrasi adalah alur terpisah: cek jalur upgrade resmi, backup, verifikasi backup dapat direstore, ekspor/impor atau upgrade yang didukung, cek kesehatan dan isi data. Rollback memakai pemulihan backup/instance lama; jangan melakukan downgrade in-place pada datadir yang sudah di-upgrade. Penghapusan runtime ditolak jika masih digunakan instance aktif. Remove/purge paket tidak menghapus proyek atau database di home pengguna.

## Strategi semua komponen menjadi .deb

Source upstream Apache, Nginx, PHP, dan MariaDB dikompilasi di builder terisolasi, lalu hasilnya dipaketkan sebagai .deb milik LARSANA. Python dikemas sebagai aplikasi beserta dependensi yang dideklarasikan; bukan janji mengubah seluruh Python menjadi native binary.

Nama paket rencana:

```text
larsana                         desktop + core
                               helper .test terintegrasi dalam paket larsana
larsana-apache-2.4               runtime Apache
larsana-nginx                    runtime Nginx stable
larsana-php-8.1 ... -8.5          CLI + FPM + extension baseline per seri
larsana-mariadb-10.11            runtime baseline
larsana-mariadb-11.8 / -12.3 / -13.0     LTS dan stable/GA terbaru pada lock build
larsana-full                    metapackage semua runtime baseline rilis
```

Metapackage memakai Depends untuk memasang paket lain. Ini tetap menyediakan semua komponen dalam format .deb; paket .deb tidak mengeksekusi dpkg/apt rekursif dari postinst. Jangan mengompilasi atau mengunduh runtime di mesin pengguna saat instalasi. Binary tidak ditulis ke prefix di luar ownership paket. Library sistem menggunakan Depends yang dihitung; library privat yang benar-benar perlu dibundel dicatat dan tidak menimpa library distro.

Distribusi online: repository APT bertanda tangan dengan paket per target distro dan arsitektur. Distribusi offline: bundle arsip berisi seluruh .deb beserta dependency closure target distro, metadata repository bertanda tangan, sumber/build manifest, dan panduan instalasi lokal. Jangan menyebut satu .deb kecil sebagai installer offline semua versi.

Gunakan packaging Debian standar (debian/control, rules, changelog, copyright, install, maintainer scripts bila dibutuhkan), debhelper/dpkg-buildpackage, sbuild atau builder setara, dan lintian. Skrip instalasi idempotent/noninteraktif, tidak otomatis menyalakan database dev, dan mengikuti recovery dpkg. Rilis mencakup .deb, source package/resep, checksum, notices, dan daftar komponen/SBOM. Uji reproducibility sebelum mengklaim build reproducible.

## Target distro dan verifikasi

Kandidat awal: Debian 12/13, Ubuntu 22.04/24.04 LTS, Linux Mint 21.x/22.x, amd64. Kandidat belum berarti sudah didukung. Tambahkan LTS/rilis distro terbaru setelah memeriksa sumber resmi dan ketersediaan builder. arm64 tahap berikutnya.

Bangun dan tes untuk target distro masing-masing atau buktikan kompatibilitas binary lintas distro; jangan menganggap format .deb menjamin kompatibilitas glibc, OpenSSL, libicu, Qt, atau Python. Prioritas prototipe adalah distro host dan distro tertua yang dipilih. Periksa host tanpa menginstal/menghapus layanan di luar tugas.

Container memverifikasi build dan paket; VM desktop memverifikasi GUI, tray, Polkit, service lifecycle, reboot, dan domain. Untuk setiap target rilis:

1. Install bersih, dependency resolution, upgrade, remove, reinstall, purge tanpa kehilangan data pengguna.
2. Apache dan Nginx masing-masing melayani request PHP untuk seluruh seri PHP yang dirilis; request juga menguji koneksi database.
3. CLI/FPM melaporkan versi yang dipilih; extension baseline benar-benar dapat dipakai.
4. Switching gagal memulihkan runtime sehat sebelumnya; double start dan port/socket stale ditangani.
5. MariaDB setiap seri dapat init/start/stop/restart dan mempertahankan data; instance lintas seri tidak berbagi datadir; backup/restore dibuktikan.
6. Konflik XAMPP/layanan distro, nama proyek berspasi, konfigurasi invalid, shutdown aplikasi, reboot, dan operasi offline diuji.
7. Perbandingan visual UI/menu dengan referensi Laragon, light/dark, HiDPI, akses keyboard, serta tray/fallback.

## Milestone dan kriteria selesai

| Tahap | Hasil reviewable | Kriteria selesai |
| --- | --- | --- |
| 0: spesifikasi | referensi Laragon, peta UI/menu, katalog versi terkunci, matriks target | kebutuhan lengkap dan setiap perbedaan terdokumentasi |
| 1: fondasi | scaffold GPL, core terpisah, QML compact, mock status jelas | jendela berjalan dan proof paket Qt pada distro tertua |
| 2: runtime build | resep Apache/Nginx, satu PHP, MariaDB 10.11, .deb awal | paket bersih terinstal dan satu request PHP + DB berhasil |
| 3: multi-runtime | semua PHP 8.1–stable terbaru dan seri MariaDB target | matriks switching, isolasi, failure recovery lulus |
| 4: pengalaman Laragon | menu/tray, domain .test, proyek, terminal, log, preferences | kontrol mengubah proses nyata dan alur visual terverifikasi |
| 5: distribusi | larsana-full, APT, bundle offline, source/notices | install/upgrade/remove pada matriks target lulus |
| 6: rilis 1.0 | dokumentasi pengguna/kontributor dan artefak rilis | seluruh target wajib terpenuhi; tidak ada klaim distro yang belum diuji |

Quick app Laravel/WordPress, HTTPS lokal, Composer terintegrasi, multi-PHP per proyek, Redis, Node.js, dan arm64 menjadi lanjutan. Prioritasnya tidak menunda Apache/Nginx, PHP multi-versi, MariaDB multi-versi, dan packaging yang sudah diminta.

## Sumber resmi

- Referensi interaksi: https://laragon.org/docs/context-menu dan https://laragon.org/docs/quick-start
- PHP supported/EOL: https://www.php.net/supported-versions.php dan https://www.php.net/eol.php
- Apache: https://httpd.apache.org/download.cgi
- Nginx: https://nginx.org/en/download.html
- MariaDB: https://mariadb.org/ dan https://mariadb.org/mariadb/all-releases/
- Debian maintainer scripts: https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html
- Qt for Python licenses: https://doc.qt.io/qtforpython-6/licenses.html
- GPLv3: https://www.gnu.org/licenses/gpl-3.0.html

## Hasil implementasi 0.1.1

Seluruh 11 runtime pada sources.lock.json telah dikompilasi terpisah untuk noble dan trixie: Apache 2.4.69, Nginx stable 1.30.6, PHP 8.1.34/8.2.34/8.3.35/8.4.26/8.5.11, MariaDB 10.11.19/11.8.9/12.3.3/13.0.2. Setiap target menyediakan 13 paket: desktop, metapackage, dan 11 runtime. Default PHP 8.5 dan MariaDB 12.3 LTS; PHP 8.1 berlabel legacy. Helper .test terintegrasi di paket desktop. Implementasi memilih satu web server aktif; menjalankan Apache dan Nginx bersamaan pada port berbeda belum menjadi alur UI. HTTPS lokal, Quick app, serta multi-PHP per proyek tetap lanjutan. Detail pemetaan UI ada di UI_REFERENCE.md.

## Keputusan distribusi terbaru — 0.2.0

Instruksi pengguna menggantikan rancangan modular sebagai distribusi utama: SATU file `larsana_0.2.0_amd64.deb` mengandung desktop, Apache, Nginx, semua PHP, dan empat MariaDB. File identik dipakai pada Ubuntu 24.04, Mint 22.x, Debian 13 amd64. Binary runtime noble dikemas bersama library kompatibilitas privat (RPATH), memakai libc dan desktop sistem. Artefak modular tetap internal/historis; bukan alur instalasi pengguna. Tidak ada .deb bersarang atau apt/dpkg dalam maintainer scripts. Conflicts/Replaces memungkinkan APT menghapus paket modular lama saat upgrade tanpa menghapus data di home. Lihat UNIFIED_PACKAGE.md untuk pengujian dan batas dukungan.
