# Referensi UI LARSANA 0.1.1

Diperiksa 17 Oktober 2026 melalui dokumentasi publik Laragon:

- https://laragon.org/docs/quick-start — alur Start All, proyek, domain .test, dan gambar baris tombol.
- https://laragon.org/docs/context-menu — menu tray, pengelolaan layanan, log, dan terminal.

Dokumentasi tidak menetapkan nomor versi binary untuk semua screenshot. Tidak ada inspeksi binary Windows atau source Laragon. Referensi gambar yang sempat diunduh berukuran 887×57, sehingga hanya memvalidasi baris tombol; perbandingan pixel seluruh jendela belum dilakukan.

| Pola yang diamati | Implementasi LARSANA |
| --- | --- |
| Jendela kontrol ringkas | Qt Quick 760×534, header, tiga baris layanan, area proyek |
| Lima tombol utama | Start All/Stop All, Web, Database, Terminal, Root dalam urutan sama |
| Menu layanan bertingkat | Apache/Nginx, PHP, MariaDB dengan aksi, versi, config, log |
| Start All | Menjalankan web server, PHP-FPM, MariaDB milik pengguna |
| Terminal dengan runtime terpilih | Emulator terminal Linux dengan PATH sesi privat |
| Domain proyek | .localhost dan helper .test berautentikasi |
| System tray | Tampil jendela, Start/Stop All, submenu layanan, terminal, root, keluar |

Logo SVG dan tema ivory/orange LARSANA dibuat sendiri. Tersedia light/dark dan status teks proses nyata. Menu versi lengkap ada di jendela; tray menyediakan aksi layanan utama. Shortcut bawaan menu/fokus Qt tersedia; kesetaraan shortcut Laragon belum dipetakan menyeluruh. Database membuka klien MariaDB di terminal. Quick app, HTTPS, terminal embedded, serta kesamaan pixel-perfect belum diimplementasikan/divalidasi.

Hasil render dan interaksi nyata: `dist/larsana-running.png` serta `dist/larsana-dark.png`; versi Debian berada dalam `dist/debian13/`.
