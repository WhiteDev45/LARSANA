# Contributing to LARSANA

Read `docs/PLAN.md` and `.agents/skills/larsana-development/SKILL.md` for product requirements and runtime isolation rules. Code contributions use GPL-3.0-or-later; preserve upstream notices when modifying packaging.

Keep desktop/QML and the Python core separate. Validate changes with the unit suite and, for runtime changes, real HTTP/FPM/database tests in the rootless builder. Explain the target distro/architecture and the checks actually run in change descriptions.

Do not commit `.build`, `.venv`, private data, credentials, or generated packages. Pin upstream source versions and checksums. Verify stable/GA status before updating Nginx or MariaDB. Database version selection must preserve separate data directories; migration is a distinct operation with verified backups.

Public releases need review of license notices, source availability, the tested distro matrix, package lifecycle, checksums/signatures, and release notes. A passing test on Mint 22/noble does not establish Debian or older Ubuntu compatibility.
