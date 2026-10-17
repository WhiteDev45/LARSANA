# LARSANA 1.2.1 — Local MariaDB access fix

## English

This patch fixes local MariaDB access for Laravel and other PHP applications. The default connection is now **127.0.0.1:3306**, username **root**, with an **empty password** for the default local accounts. phpMyAdmin uses the same root login, and the desktop login message has been updated.

- Enables both TCP `root@127.0.0.1` and socket `root@localhost` with local administrator privileges.
- Migrates the untouched root account from the previous socket-only configuration once per database instance. `CREATE USER IF NOT EXISTS` alone cannot update an existing socket-authenticated account, so the old default account is explicitly converted.
- Migrates the previous default port 3307 to 3306 once. Other custom ports are preserved, as are port choices made after this migration.
- Preserves database files, projects, user-set root passwords, and subsequent account changes. Passwords are not reset on every startup.
- Detects occupied ports without stopping system/XAMPP services or silently choosing another port.
- Retains the single amd64 `.deb` for Ubuntu 24.04, Linux Mint 22.x, and Debian 13. Runtime versions are unchanged.

Close LARSANA before installing the update:

```bash
sudo apt install ./larsana_1.2.1_amd64.deb
```

Create your database in phpMyAdmin, then configure Laravel:

```dotenv
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=your_database
DB_USERNAME=root
DB_PASSWORD=
```

Remove any old `DB_SOCKET` override and run `php artisan config:clear`, followed by `php artisan migrate`. Port 3306 must be available; if another database already uses it, stop that service yourself or select a different port in LARSANA Preferences. The passwordless root defaults are for the local loopback instance. Existing custom credentials remain in effect.

Validation covers real Laravel 12.70.0 artisan migrations on PHP 8.2–8.5 against MariaDB 10.11, 11.8, 12.3, and 13.0, root login/SQL/import/export in phpMyAdmin, upgrade of databases initialized by 1.2.0, password/data preservation, conflict handling, and desktop root-login guidance in isolated noble/trixie environments. Package installation/upgrade/reinstall/purge and full runtime smoke checks also passed before publication. This is not a claim of full desktop VM/reboot/Polkit/tray certification.

## Bahasa Indonesia

Patch ini memperbaiki akses MariaDB lokal untuk Laravel dan aplikasi PHP lainnya. Koneksi default menjadi **127.0.0.1:3306**, username **root**, dan **password kosong** untuk akun lokal bawaan. Login phpMyAdmin serta petunjuk pada desktop juga memakai root.

- Mengaktifkan akses TCP dan socket untuk root pada instance MariaDB LARSANA.
- Memperbaiki akun root bawaan lama yang masih memakai autentikasi socket, satu kali per instance database.
- Mengubah default lama 3307 ke 3306 satu kali, sambil mempertahankan port khusus lainnya dan pilihan port pengguna setelah migrasi.
- Mempertahankan data, proyek, password root yang sudah diubah, dan perubahan akun setelah bootstrap. Password tidak direset setiap aplikasi dinyalakan.
- Menampilkan error jika port terpakai; tidak mematikan layanan database sistem/XAMPP atau berpindah port diam-diam.
- Tetap satu `.deb` amd64 untuk Ubuntu 24.04, Linux Mint 22.x, dan Debian 13. Versi runtime tetap sama.

Tutup LARSANA sebelum upgrade. Gunakan perintah instalasi di atas, lalu login phpMyAdmin sebagai **root** dengan password kosong jika akun masih memakai default. Untuk Laravel, gunakan konfigurasi TCP di atas, ganti nama database, hapus `DB_SOCKET` lama, dan jalankan `php artisan config:clear` sebelum migrasi. Port 3306 harus tersedia. Jika kredensial pernah diubah, gunakan kredensial tersebut.

Installer adalah satu file `.deb`; arsip corresponding source yang disediakan bersama rilis ditujukan untuk pengembang dan tidak diperlukan untuk instalasi. APT dapat mengunduh library OS yang belum terpasang.
