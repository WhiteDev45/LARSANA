# LARSANA

**A robust, clean environment for modern web development on Linux.**

[English](README.md) · [Bahasa Indonesia](README.id.md)

LARSANA is an open-source desktop environment for local PHP development on Ubuntu, Linux Mint, and Debian. Inspired by Laragon's workflow, it brings Apache, stable Nginx, multiple PHP versions, MariaDB, and phpMyAdmin into one `.deb` installer.

LARSANA is independently implemented with its own branding and assets. It is not an official Laragon release and is not affiliated with Laragon or Laravel.

## Name and philosophy

The project's name expresses its identity: **Lar** reflects inspiration from the Laragon/Laravel web development ecosystem; **Sana** represents a means of supporting developers, with an emphasis on a clean, organized environment. It also evokes bringing that development experience to another platform: Linux.

These are the project's chosen brand meanings. LARSANA aims to make everyday development convenient while keeping application runtimes separate from system services and preserving user projects and databases.

> LARSANA: a robust, clean environment for modern web development on Linux.

## Included in version 1.2.0

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

The same **amd64 / x86-64** installer targets Ubuntu 24.04 LTS, Linux Mint 22.x, and Debian 13. Shared payloads were tested in isolated noble and trixie environments, including HTTP/FPM, database operations, GUI interaction, package installation, upgrade, and removal.

Other distribution releases and ARM64 are unverified. Full desktop VM/reboot tests, tray behavior across desktops, and real Polkit-agent authentication remain outside the completed validation. The version number does not imply those tests have been completed.

## Install or upgrade

Download **`larsana_1.2.0_amd64.deb`** from this repository's **Releases** page. GitHub's automatically generated source ZIP/TAR files are for source code; choose the `.deb` to install the application.

Close LARSANA before upgrading, then run from the download directory:

```bash
sudo apt install ./larsana_1.2.0_amd64.deb
larsana
```

You can also launch **LARSANA** from the application menu. Run the application as your regular user. All LARSANA runtimes are included; APT may need internet access for missing operating-system libraries.

## Projects and databases

| Item | Default location or address |
| --- | --- |
| Application and bundled runtimes | `/usr/lib/larsana/` |
| Projects | `~/Larsana/www/` |
| Web server | `http://localhost:8080` |
| MariaDB TCP port | `3307` |
| Settings | `~/.config/larsana/` |
| Database files | `~/.local/share/larsana/mariadb/<series>/` |
| Logs | `~/.local/state/larsana/` |

User paths follow XDG settings when set. Port 3307 helps avoid conflicts with system or XAMPP databases on 3306. Database versions use separate data directories; changing versions does not migrate or downgrade an existing database.

Click **phpMyAdmin** to start the selected MariaDB instance and open its management interface in your browser. For a newly initialized database, log in with your Linux username (`whoami`) and an empty password using local socket authentication. Use your existing credentials if you changed the database account.

For Laravel, use the selected MariaDB Unix socket with the default socket-authenticated account. For a TCP connection to `127.0.0.1:3307`, create a password-authenticated database account and grant it access to your project's database. phpMyAdmin uses the selected instance's private socket and a loopback web address with an available port. Stopping/changing MariaDB, Stop All, or exiting LARSANA stops the phpMyAdmin server.

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

Read the [packaging documentation](docs/UNIFIED_PACKAGE.md), [development plan](docs/PLAN.md), [contribution guide](CONTRIBUTING.md), and [GitHub publishing guide](docs/GITHUB_PUBLISH.md). The GitHub workflow runs Python core checks; it does not build or certify the complete installer.

## License and source availability

The Python/Qt application uses [GPL-3.0-or-later](LICENSE). The phpMyAdmin PHP router is an explicit GPL-2.0-only exception; see [its notice](packaging/phpmyadmin-router.copyright). phpMyAdmin, runtimes, Qt, and other bundled dependencies retain their upstream licenses and notices.

Binary distributions must be accompanied by the corresponding source and build/patch instructions required by those licenses. The prepared release sources are in `dist/unified-sources/` locally; maintainers publish them alongside the installer. They are not additional installation dependencies.
