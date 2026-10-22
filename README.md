# LARSANA

**A robust, clean environment for modern web development on Linux.**

[English](README.md) · [Bahasa Indonesia](README.id.md)

[![Download .deb](https://img.shields.io/badge/Download-.deb-2563eb?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/WhiteDev45/LARSANA/releases/download/v1.2.3/larsana_1.2.3_amd64.deb)

[Download .deb — LARSANA 1.2.3](https://github.com/WhiteDev45/LARSANA/releases/download/v1.2.3/larsana_1.2.3_amd64.deb)

LARSANA 1.2.3 · amd64 · Ubuntu 24.04–26.04 / compatible Linux Mint / Debian 13+

LARSANA is an open-source desktop environment for local PHP development on Ubuntu, Linux Mint, and Debian. Inspired by Laragon's workflow, it brings Apache, stable Nginx, multiple PHP versions, MariaDB, and phpMyAdmin into one `.deb` installer.

LARSANA is independently implemented with its own branding and assets. It is not an official Laragon release and is not affiliated with Laragon or Laravel.

## Name and philosophy

The project's name expresses its identity: **Lar** reflects inspiration from the Laragon/Laravel web development ecosystem; **Sana** represents a means of supporting developers, with an emphasis on a clean, organized environment. It also evokes bringing that development experience to another platform: Linux.

These are the project's chosen brand meanings. LARSANA aims to make everyday development convenient while keeping application runtimes separate from system services and preserving user projects and databases.

> LARSANA: a robust, clean environment for modern web development on Linux.

## Fixed in 1.2.3

- Accept Ubuntu 24.04 through 26.04 and detect Linux Mint's Ubuntu base instead of requiring only noble/trixie codenames.
- Validate system ABI through APT dependencies; older bases below libc6 2.39 remain unsupported.
- Automatically use a fresh version-specific QML cache after upgrades, preserving projects, databases and settings.
- Retain all Nginx MIME and reload fixes from 1.2.2 in the single installer.

## Included in version 1.2.3

| Component | Included versions |
| --- | --- |
| Apache | 2.4.69 |
| Nginx | 1.30.6, stable channel |
| PHP | 8.1.34, 8.2.34, 8.3.35, 8.4.26, 8.5.11 |
| MariaDB | 10.11.19, 11.8.9 LTS, 12.3.3 LTS, 13.0.2 stable/GA rolling |
| phpMyAdmin | 5.2.3 |

PHP 8.1 is a legacy/EOL option. Defaults are PHP 8.5 and MariaDB 12.3 LTS. phpMyAdmin runs on its own bundled PHP 8.3 process without changing the PHP version selected for your projects.

The desktop provides Start All / Stop All, runtime selection, project creation, configuration and log access, PHP extension inspection, terminal access, a tray menu where supported, and optional `.test` domain configuration through Polkit authentication.

## Supported systems

The same **amd64 / x86-64** installer targets Ubuntu 24.04–26.04, Linux Mint based on those Ubuntu releases, and Debian 13+. See [1.2.3 validation notes](RELEASE-1.2.3.md) for tested targets and limitations. Installer acceptance alone does not establish desktop validation.

ARM64, full desktop VM/reboot testing, cross-desktop tray behavior and real Polkit agent authentication remain unverified.

## Install or upgrade

Download **`larsana_1.2.3_amd64.deb`** from this repository's **Releases** page. GitHub's automatically generated source ZIP/TAR files are for source code; choose the `.deb` to install the application.

Close LARSANA before upgrading, then run from the download directory:

```bash
sudo apt install ./larsana_1.2.3_amd64.deb
larsana
```

You can also launch **LARSANA** from the application menu. Run the application as your regular user. All LARSANA runtimes are included; APT may need internet access for missing operating-system libraries.

## Projects and databases

| Item | Default location or address |
| --- | --- |
| Application and bundled runtimes | `/usr/lib/larsana/` |
| Projects | `~/Larsana/www/` |
| Web server | `http://localhost:8080` |
| MariaDB TCP port | `3306` |
| Settings | `~/.config/larsana/` |
| Database files | `~/.local/share/larsana/mariadb/<series>/` |
| Logs | `~/.local/state/larsana/` |

User paths follow XDG settings when set. MariaDB binds to loopback on port 3306 by default; an occupied port produces an error without stopping other services. The previous default 3307 is migrated once; other custom ports are preserved. Database versions use separate data directories; changing versions does not migrate or downgrade an existing database.

Click **phpMyAdmin** to start the selected MariaDB instance and open its management interface in your browser. Log in as **root** with an empty password for default local instances. Root works through both the private Unix socket and TCP at `127.0.0.1:3306`. Existing user-set passwords are preserved.

For Laravel's MySQL connection, use the following values after creating the database in phpMyAdmin:

```dotenv
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=your_database
DB_USERNAME=root
DB_PASSWORD=
```

Remove any old `DB_SOCKET` override to use TCP, then run `php artisan config:clear`. The framework must be configured to use MySQL/MariaDB rather than SQLite. The empty-password root default is intended for local development and remains bound to loopback. Existing credentials are not reset on restart. phpMyAdmin continues to use the selected instance's private socket; Stop All or changing/stopping MariaDB closes its server.

## Uninstall

Stop all services and close LARSANA, then run:

```bash
sudo apt remove larsana
```

Removal and purge preserve projects, databases, and settings in your home directory.

## Development and packaging

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials==6.8.3 pytest
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m larsana
```

Running the source GUI alone does not install runtimes or phpMyAdmin. Use the complete installer for the ready-to-use environment.

Runtime source versions/checksums are pinned in `runtimes/sources.lock.json`; phpMyAdmin is pinned in `runtimes/phpmyadmin.lock.json`. Rootless build tools live in `tools/`. Packaging requires prepared source-built runtimes, the desktop payload, a noble builder, and corresponding dependency sources; `build_unified.py` is not a standalone fresh-checkout build command.

Read the [contribution guide](CONTRIBUTING.md) for development expectations. The GitHub workflow runs Python core checks; it does not build or certify the complete installer.

## License and source availability

The Python/Qt application uses [GPL-3.0-or-later](LICENSE). The phpMyAdmin PHP router is an explicit GPL-2.0-only exception; see [its notice](packaging/phpmyadmin-router.copyright). phpMyAdmin, runtimes, Qt, and other bundled dependencies retain their upstream licenses and notices.

Binary distributions must be accompanied by the corresponding source and build/patch instructions required by those licenses. Project source and build recipes are available in this repository; pinned upstream source URLs and checksums are recorded in `runtimes/` and package metadata. Complete source bundles and validation reports are retained locally. The release installer asset is the `.deb` file.

## Compatibility and upgrade cache in 1.2.3

The single amd64 installer accepts Ubuntu 24.04 through 26.04, Linux Mint with an Ubuntu base in that range, and Debian 13+. APT validates the actual library dependencies, including libc6 >= 2.39. Older Debian/Mint bases remain unsupported. QML caches use a new version-specific directory automatically after upgrading; user projects, databases and settings are preserved. See [1.2.3 validation notes](RELEASE-1.2.3.md) for tested targets and limits.
