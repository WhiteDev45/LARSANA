# Distribusi satu paket LARSANA 1.2.1

Keputusan pengguna: satu file .deb untuk desktop dan semua runtime, dengan file yang sama pada Ubuntu 24.04/Mint22.x (noble) serta Debian13 (trixie), amd64.

Binary source-build noble dipakai pada kedua basis. Closure 72 library runtime privat berada di /usr/lib/larsana/compat/lib; RPATH runtime/library diarahkan ke prefix privat. libc/loader, Python/Perl, dan library grafis/desktop tetap memakai sistem. Tidak mengganti library sistem atau PATH global. CLI yang dibuka lewat terminal LARSANA juga memakai runtime privat. Paket tidak mengandung installer .deb bersarang dan tidak menjalankan apt/dpkg dari maintainer scripts.

Satu paket `larsana` memiliki langsung seluruh file. `Conflicts`/`Replaces` menyatakan penggantian paket modular lama; APT menghapus paket lama saat instalasi tunggal. Guard prerm menolak penghapusan/upgrade saat executable runtime masih berjalan. Preinst memeriksa basis noble/trixie; dependensi libc>=2.39 dan amd64 membatasi ABI yang didukung. Close/Stop All sebelum upgrade. Data di home tidak dimiliki/dihapus paket.

Pengujian menggunakan payload dan .deb yang sama, dengan libc/system desktop masing-masing target dalam Bubblewrap. Matriks HTTP/FPM seluruh PHP pada Apache/Nginx, keempat MariaDB (versi SQL, persistensi, PDO, backup/restore), pemilihan PHP/MariaDB GUI, dan resolusi 496 ELF dijalankan pada kedua target. Pengujian paket meliputi instalasi bersih, upgrade modular ke paket tunggal, reinstall, remove/purge, dan data pengguna uji. Hasil final tersedia di .build/unified-*.log dan dist/unified-validation/.

Library kompatibilitas mempertahankan copyright distro dan provenance sebelum modifikasi RPATH dalam compat-libraries.json. Source distro yang tepat dicerminkan di .build/compat-sources dan disalin ke distribusi source di dist/unified-sources. Source LARSANA, source upstream runtime dan Qt/PySide, serta resep patch RPATH tersedia dalam proyek/source distribusi. Library privat memerlukan pembaruan keamanan melalui rilis LARSANA.

Perbedaan ABI yang ditangani: ICU74 dan JPEG8 dari noble, serta closure dependensinya, tersedia privat pada Debian tanpa memasang paket Ubuntu sebagai paket sistem. Tidak mengklaim satu binary untuk semua versi Debian/Ubuntu/Mint: versi sebelum libc2.39, distro lain, dan arm64 belum diuji. Pengujian VM desktop, reboot, tray lintas desktop dan agent autentikasi Polkit nyata belum dilakukan. Tidak ada klaim reproducibility bit-for-bit atau kesamaan pixel-perfect Laragon.

## phpMyAdmin pada 1.2.1

Distribusi resmi phpMyAdmin 5.2.3 all-languages (GPL-2.0-only), termasuk vendor Composer dan LICENSE upstream, ditanam langsung di /usr/lib/larsana/phpmyadmin. Versi/URL/SHA256 ada di runtimes/phpmyadmin.lock.json; builder menolak checksum berbeda. Tidak perlu APT tambahan untuk phpMyAdmin.

Tombol phpMyAdmin dan tray memulai MariaDB terpilih serta PHP CLI 8.3 -S pada loopback/port bebas. PHP ini terpisah dari proyek dan memakai config/session privat XDG; cookie login memakai socket MariaDB terpilih. Sejak 1.2.1 akun default adalah root tanpa password melalui socket privat dan TCP loopback. Akun root sistem operasi tidak dipakai untuk menjalankan GUI atau server. Bootstrap satu kali mengonversi akun root bawaan lama yang masih unix_socket/invalid; password dan plugin kustom yang sudah valid dipertahankan. Router membatasi front controller dan aset publik; config, vendor, setup, SQL dan sesi tidak dapat diunduh. Stop/ganti MariaDB, Stop All dan Exit menutup proses tersebut. Bind loopback ditujukan untuk workstation pengembangan lokal.

Paket mempertahankan versi/runtime/database pilihan pengguna saat upgrade. Versi 1.2.1 adalah keputusan penomoran pengguna; batas VM desktop, reboot, tray lintas desktop dan Polkit tetap berlaku.

## MariaDB 1.2.1

Default port baru 3306; konfigurasi lama yang masih memakai 3307 beralih satu kali. Penanda database_defaults_version menyimpan keputusan ini, sehingga pilihan port pengguna setelah upgrade tidak ditimpa. Port khusus lainnya tetap dipertahankan; konflik port menampilkan error tanpa mematikan service luar atau beralih port diam-diam.

Setelah server siap, bootstrap memakai akun administrator socket lokal lalu fallback root. CREATE USER IF NOT EXISTS membuat root@127.0.0.1 dan root@localhost, GRANT memberi akses penuh lokal. ALTER USER diperlukan hanya untuk root bawaan lama yang masih unix_socket dengan password invalid/kosong; CREATE USER saja tidak memperbaikinya. Penanda per-datadir mencegah restart mengubah ulang akun/password. Kegagalan bootstrap menghentikan hanya server LARSANA yang baru dinyalakan, mempertahankan data, dan melaporkan error.

Tidak memakai root@% atau bind 0.0.0.0. skip-name-resolve tetap dipakai karena akun TCP 127.0.0.1 sudah eksplisit. Laravel dapat memakai DB_CONNECTION=mysql, DB_HOST=127.0.0.1, DB_PORT=3306, DB_USERNAME=root, DB_PASSWORD kosong. Database harus dibuat dahulu. Hapus override DB_SOCKET dan bersihkan cache konfigurasi Laravel untuk memakai TCP.
