#!/usr/bin/env python3
"""Build the desktop .deb with private Qt/PySide libraries, no root needed."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.2.1'
STAGE=ROOT/'.build/stage/desktop'


def write(path, text, mode=None):
    file=STAGE/path
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(text)
    if mode: file.chmod(mode)


def build():
    if STAGE.exists(): shutil.rmtree(STAGE)
    private=STAGE/'usr/lib/larsana'
    private.mkdir(parents=True)
    shutil.copytree(ROOT/'src/larsana',private/'larsana',ignore=shutil.ignore_patterns('__pycache__'))
    from package_permissions import normalize
    # Wheel binaries are ABI3 and support Python 3.10+. Keep upstream license files.
    site=ROOT/'.venv/lib/python3.12/site-packages'
    for name in ['PySide6','shiboken6']:
        shutil.copytree(site/name,private/'python'/name,ignore=shutil.ignore_patterns('__pycache__','include','typesystems','glue','examples','*.pyi'))
    qt=private/'python/PySide6/Qt'
    for folder in ['bin','libexec','plugins/designer']:
        shutil.rmtree(qt/folder,ignore_errors=True)
    for plugin in ['libqjpeg.so','libqtiff.so']:
        (qt/'plugins/imageformats'/plugin).unlink(missing_ok=True)
    (private/'python/PySide6/QtExampleIcons.abi3.so').unlink(missing_ok=True)
    for folder in ['scripts','support/deprecated']:
        shutil.rmtree(private/'python/PySide6'/folder,ignore_errors=True)
    for tool in ['lupdate','lrelease','rcc','designer','linguist','qmlformat','qmllint','qmlimportscanner']:
        (private/'python/PySide6'/tool).unlink(missing_ok=True)
    for library in (qt/'lib').glob('libicu*.so.*'):
        subprocess.run(['strip','--strip-unneeded',str(library)],check=True)
    normalize(private)
    for path in site.glob('*.dist-info'):
        if path.name.lower().startswith(('pyside6','shiboken6')):
            shutil.copytree(path,private/'python'/path.name)
    write(Path('usr/bin/larsana'),'''#!/bin/sh
exec /usr/bin/python3 -B /usr/lib/larsana/launch.py "$@"
''',0o755)
    write(Path('usr/lib/larsana/launch.py'),'''from pathlib import Path
import sys
root = Path(__file__).resolve().parent
sys.path[:0] = [str(root), str(root / 'python')]
from larsana.__main__ import main
raise SystemExit(main())
''')
    write(Path('usr/lib/larsana/larsana-hosts'),'''#!/usr/bin/python3 -IB
import sys
sys.path.insert(0, '/usr/lib/larsana')
from larsana.hosts import main
main()
''',0o755)
    for source,dest in [('packaging/larsana.desktop','usr/share/applications/larsana.desktop'),('src/larsana/qml/larsana.svg','usr/share/icons/hicolor/scalable/apps/larsana.svg'),('packaging/org.larsana.hosts.policy','usr/share/polkit-1/actions/org.larsana.hosts.policy')]:
        target=STAGE/dest;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(ROOT/source,target)
    doc=STAGE/'usr/share/doc/larsana'
    doc.mkdir(parents=True)
    for source in ['LICENSE','README.md','README.id.md']:
        if (ROOT/source).exists(): shutil.copy(ROOT/source,doc/Path(source).name)
    shutil.copy(ROOT/'packaging/THIRD_PARTY.md',doc/'THIRD_PARTY.md')
    shutil.copytree(ROOT/'packaging/licenses',doc/'licenses',dirs_exist_ok=True)
    if (ROOT/'packaging/desktop-notices').exists():
        shutil.copytree(ROOT/'packaging/desktop-notices',doc/'third-party-notices',dirs_exist_ok=True)
    if (ROOT/'packaging/desktop-sources.lock.json').exists():
        shutil.copy(ROOT/'packaging/desktop-sources.lock.json',doc/'desktop-sources.lock.json')
    (doc/'larsana.1.gz').write_bytes(gzip.compress((ROOT/'packaging/larsana.1').read_bytes(),mtime=0))
    man=STAGE/'usr/share/man/man1';man.mkdir(parents=True,exist_ok=True)
    shutil.move(str(doc/'larsana.1.gz'),man/'larsana.1.gz')
    (doc/'copyright').write_text('LARSANA code: Copyright 2026 LARSANA contributors.\nLicense: GPL-3.0-or-later; see LICENSE.\nQt/PySide6/Shiboken6: The Qt Company and contributors.\nSee THIRD_PARTY.md, upstream package METADATA and licenses/.\nThe GPL version 3 text is available at /usr/share/common-licenses/GPL-3.\n')
    (doc/'changelog.gz').write_bytes(gzip.compress(b'larsana (0.1.1) noble; urgency=low\n\n  * Initial local desktop build.\n\n -- LARSANA Contributors <maintainers@larsana.invalid>  Sat, 17 Oct 2026 12:00:00 +0700\n',mtime=0))
    deps='python3 (>= 3.10), libc6 (>= 2.35), libstdc++6, libgcc-s1, libgl1, libegl1, libopengl0, libglib2.0-0, libdbus-1-3, libfontconfig1, libfreetype6, libx11-6, libx11-xcb1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-xfixes0, libxcb-xinerama0, libxcb-randr0, libxcb-render0, libxcb-shm0, libxcb-sync1, libxkbcommon0, libxkbcommon-x11-0, libsm6, libice6, zlib1g, libxext6'
    write(Path('DEBIAN/control'),f'''Package: larsana
Version: {VERSION}
Architecture: amd64
Maintainer: LARSANA Contributors <maintainers@larsana.invalid>
Section: devel
Priority: optional
Depends: {deps}
Recommends: x-terminal-emulator, polkitd, pkexec
Suggests: larsana-full
Description: Local web development desktop for Linux
 Compact Qt desktop for isolated Apache, Nginx, PHP and MariaDB runtimes.
 Includes Qt for Python under its upstream open source licenses.
''')
    write(Path('usr/share/lintian/overrides/larsana'), '# ICU data-only ELF intentionally has no library prerequisites.\nlarsana: shared-library-lacks-prerequisites [usr/lib/larsana/python/PySide6/Qt/lib/libicudata.so.73]\n')
    normalize(STAGE/'usr')
    (STAGE/'usr/bin/larsana').chmod(0o755)
    (private/'larsana-hosts').chmod(0o755)
    out=ROOT/'dist'/f'larsana_{VERSION}_amd64.deb'
    from debian_package import build_deb
    build_deb(STAGE,out)
    print(out)


def metapackage():
    lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
    deps=['larsana (= '+VERSION+')']
    for item in lock['sources']:
        file=ROOT/'dist'/f"larsana-{item['id']}_{item['version']}-1larsana1_amd64.deb"
        if not file.exists(): raise RuntimeError(f'Missing runtime package: {file.name}')
        deps.append(f"larsana-{item['id']} (= {item['version']}-1larsana1)")
    stage=ROOT/'.build/stage/full/DEBIAN';stage.mkdir(parents=True,exist_ok=True)
    (stage/'control').write_text(f'''Package: larsana-full
Version: {VERSION}
Architecture: all
Maintainer: LARSANA Contributors <maintainers@larsana.invalid>
Section: metapackages
Priority: optional
Depends: {', '.join(deps)}
Description: Complete LARSANA runtime collection
 Installs the desktop and every source-built runtime in this release.
''')
    doc=stage.parent/'usr/share/doc/larsana-full'
    doc.mkdir(parents=True,exist_ok=True)
    (doc/'copyright').write_text('Copyright: 2026 LARSANA contributors.\nLicense: GPL-3.0-or-later; full text at /usr/share/common-licenses/GPL-3.\n')
    from debian_package import build_deb
    build_deb(stage.parent,ROOT/'dist'/f'larsana-full_{VERSION}_all.deb')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--full',action='store_true');args=parser.parse_args()
    build()
    if args.full: metapackage()
