# Third-party software in the desktop package

The private `python/` directory includes PySide6 Essentials and Shiboken6 6.8.3 wheel libraries, with development tools/unused image plugins omitted, permissions normalized, and ICU debug symbols stripped by tools/build_desktop.py distributed by the Qt for Python project. Their package metadata specifies LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only. The license texts accompany this package. LARSANA does not restrict replacement of these shared libraries or reverse engineering for debugging modifications.

Qt modules and their bundled third-party libraries retain their individual upstream terms. Upstream source, license and attribution information for the exact Qt 6.8.3 / Qt for Python 6.8.3 release:

- https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
- https://download.qt.io/archive/qt/6.8/6.8.3/single/
- https://code.qt.io/cgit/pyside/pyside-setup.git/tree/?h=v6.8.3
- https://code.qt.io/cgit/qt/qtbase.git/tree/LICENSES?h=v6.8.3
- https://doc.qt.io/qt-6.8/licenses-used-in-qt.html

Matching Qt 6.8.3 modules, PySide/Shiboken 6.8.3 and ICU 73.2 source archives are collected in the release bundle under upstream-sources/desktop. Version, upstream URL and SHA256 are recorded in desktop-sources.lock.json. Extracted upstream license, copyright and attribution documents accompany the desktop package under third-party-notices/. The repackaging modifications are described in tools/build_desktop.py.

Apache, Nginx, PHP and MariaDB runtime .deb packages include their upstream license/notice files and source provenance. Their corresponding upstream archives are collected in the local release bundle. System library dependencies are supplied by the target distribution.
