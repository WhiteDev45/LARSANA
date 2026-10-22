# LARSANA 1.2.3

Satu source dan satu installer amd64 berisi seluruh runtime dari 1.2.2.

Installer tidak lagi mengunci codename noble/trixie: menerima Ubuntu 24.04–26.04, Linux Mint dengan basis Ubuntu dalam rentang tersebut, dan Debian 13+. APT memvalidasi dependensi ABI (termasuk libc6 >= 2.39). Debian 12/Mint 21 tidak memenuhi baseline. Versi distro mendatang yang diterima guard belum otomatis tervalidasi.

Cache QML memakai `$XDG_CACHE_HOME/larsana/qml/1.2.3` (fallback `~/.cache`). Saat upgrade aplikasi memakai cache versi baru; cache lama tetap tersimpan tetapi tidak digunakan. Jika cache tidak bisa ditulis, QML dikompilasi tanpa disk cache. Tidak ada penghapusan home oleh maintainer script.

## Validasi

Satu file `.deb` yang identik diuji dalam rootfs terisolasi berbasis paket resmi bertanda tangan. Pengujian ini bukan pengujian VM desktop penuh.

| Basis sistem | Runtime dan GUI Xvfb | Install/upgrade/reinstall/purge |
| --- | --- | --- |
| Ubuntu 24.04 noble | Lulus | Lulus |
| Ubuntu 26.04 resolute, Python 3.14 | Lulus | Lulus |
| Debian 13 trixie | Lulus | Lulus |

- 30 tes unit lulus, termasuk cache lama rusak, namespace cache baru, dan fallback cache tidak dapat ditulis; juga dijalankan pada Python 3.14 Ubuntu 26.04.
- Lima PHP melalui Apache dan Nginx, switching langsung, 496 ELF runtime, serta ICU/JPEG/cURL TLS lulus pada ketiga basis.
- Empat MariaDB: persistensi/PDO/backup/restore; phpMyAdmin login root, JavaScript, SQL dan roundtrip ekspor/impor lulus.
- GUI Xvfb: Start/Stop, pemilihan PHP/MariaDB, phpMyAdmin, tema, serta cache QML baru dengan cache 1.2.2 rusak tetap tersimpan lulus.
- Installer: fixture Ubuntu 24.04/24.10/25.04/25.10/26.04, basis Mint noble/resolute, LMDE basis trixie; basis lama dan distro lain ditolak.
- Upgrade 1.2.2 → 1.2.3 menjaga fixture proyek, database, pengaturan dan konfigurasi MIME kustom. Untuk skenario Ubuntu 26.04, identitas noble dipakai hanya saat memasang installer lama (yang menolak resolute); identitas asli 26.04 dipulihkan sebelum upgrade kandidat dan seluruh tes aplikasi.
- Dependensi Qt `libgssapi-krb5-2` sekarang eksplisit agar instalasi bersih tidak bergantung pada library yang kebetulan sudah terpasang.

Log, hasil lintian (dengan pengecualian phpMyAdmin yang ditinjau), checksum, dan corresponding source disertakan sebagai aset rilis.

Belum mencakup VM desktop/reboot penuh, tray lintas desktop, Polkit agent nyata, ARM64, atau instalasi langsung pada desktop Mint. Ubuntu interim 24.10/25.04/25.10 diterima oleh guard tetapi bukan klaim validasi runtime tersendiri.
