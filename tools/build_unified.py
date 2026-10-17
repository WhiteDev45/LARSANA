#!/usr/bin/env python3
"""Build one cross-suite application/runtime package from reviewed noble binaries."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,gzip
from build_runtimes import sandbox,ROOT,BUILD
from debian_package import build_deb
VERSION='1.2.1'
STAGE=BUILD/'unified-stage'
LIB=STAGE/'usr/lib/larsana/compat/lib'
FS=BUILD/'rootfs'
CORE={'ld-linux-x86-64.so.2','libc.so.6','libm.so.6','libdl.so.2','libpthread.so.0','librt.so.1','libresolv.so.2','libutil.so.1','libanl.so.1','libnss_dns.so.2','libnss_files.so.2'}
def elf(file):
 if not file.is_file() or file.is_symlink():return False
 with file.open('rb') as stream:return stream.read(4)==b'\x7fELF'
def needed(file):
 return re.findall(r'\(NEEDED\).*?\[(.*?)\]',subprocess.check_output(['readelf','-d',str(file)],text=True))
def path_in_root(file):
 for _ in range(20):
  if not file.is_symlink():return file
  link=Path(file.readlink());file=FS/link.relative_to('/') if link.is_absolute() else file.parent/link
 raise RuntimeError('Symlink cycle: '+str(file))
def build():
 from target_info import target_info
 if target_info(ROOT)['suite']!='noble':raise RuntimeError('Unified runtime payload must be built from the noble ABI baseline')
 if STAGE.exists():shutil.rmtree(STAGE)
 STAGE.mkdir(parents=True)
 # Flatten payloads rather than nesting or installing component .debs.
 desktop=ROOT/'dist'/f'larsana_{VERSION}_amd64.deb'
 if not desktop.exists():desktop=ROOT/'dist/larsana_0.1.1_amd64.deb'
 packages=[desktop]+sorted(p for p in (ROOT/'dist').glob('larsana-*.deb') if not p.name.startswith('larsana-full_'))
 assert len(packages)==12
 for file in packages:subprocess.run(['dpkg-deb','-x',str(file),str(STAGE)],check=True)
 app=STAGE/'usr/lib/larsana/larsana'
 shutil.rmtree(app);shutil.copytree(ROOT/'src/larsana',app,ignore=shutil.ignore_patterns('__pycache__'))
 # Verified upstream distribution includes Composer dependencies and GPL notices.
 lock=json.loads((ROOT/'runtimes/phpmyadmin.lock.json').read_text())
 archive=BUILD/'phpmyadmin'/lock['archive']
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=lock['sha256']:
  raise RuntimeError('phpMyAdmin source checksum mismatch')
 import tarfile
 with tarfile.open(archive) as tar:
  tar.extractall(BUILD/'phpmyadmin',filter='data')
 shutil.copytree(BUILD/'phpmyadmin'/lock['directory'],STAGE/'usr/lib/larsana/phpmyadmin')
 shutil.copy2(ROOT/'runtimes/phpmyadmin.lock.json',STAGE/'usr/share/doc/larsana/phpmyadmin.lock.json')
 shutil.copy2(STAGE/'usr/lib/larsana/phpmyadmin/LICENSE',STAGE/'usr/share/doc/larsana/phpmyadmin-LICENSE')
 notice=(ROOT/'packaging/phpmyadmin-router.copyright').read_text()
 copyright=STAGE/'usr/share/doc/larsana/copyright'
 copyright.write_text(copyright.read_text()+'\n'+notice)
 shutil.copy2(ROOT/'packaging/phpmyadmin-router.copyright',STAGE/'usr/share/doc/larsana/phpmyadmin-router.copyright')
 runtime=STAGE/'usr/lib/larsana/runtimes'
 files=[p for p in runtime.rglob('*') if elf(p)]
 private={p.name for p in files}
 LIB.mkdir(parents=True)
 queue=[n for p in files for n in needed(p)];origins={}
 while queue:
  name=queue.pop()
  if name in CORE or name in private or name in origins:continue
  candidates=[FS/'usr/lib/x86_64-linux-gnu'/name,FS/'usr/lib'/name]
  file=next((p for p in candidates if p.exists()),None)
  if file is None:raise RuntimeError('Unresolved native dependency: '+name)
  file=path_in_root(file)
  shutil.copy2(file,LIB/name)
  origins[name]={'path':str(file.relative_to(FS)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
  queue.extend(needed(file))
 # Preserve private upstream paths, then add compat paths to every runtime ELF.
 for file in files+list(LIB.iterdir()):
  rel=str(file.relative_to(ROOT))
  args=['patchelf','--print-rpath','/work/'+rel]
  old=subprocess.check_output(['bwrap','--ro-bind',str(FS),'/', '--bind',str(ROOT),'/work','--dev','/dev','--proc','/proc']+args,text=True).strip()
  dirs=[x for x in old.split(':') if x]+(['$ORIGIN'] if file.parent==LIB else [])+['/usr/lib/larsana/compat/lib']
  sandbox(['patchelf','--force-rpath','--set-rpath',':'.join(dict.fromkeys(dirs)),'/work/'+rel])
 # Record exact distro payload provenance and retain each library copyright notice.
 ownership={}
 for listing in (FS/'var/lib/dpkg/info').glob('*.list'):
  package=listing.name[:-5].split(':')[0]
  for line in listing.read_text().splitlines():ownership[line.lstrip('/')]=package
 notices=STAGE/'usr/share/doc/larsana/compat-copyright';notices.mkdir(parents=True)
 for entry in origins.values():
  package=ownership.get(entry['path']);entry['package']=package
  if not package:raise RuntimeError('No package owner: '+entry['path'])
  source=FS/'usr/share/doc'/package/'copyright'
  if not source.exists():raise RuntimeError('No library copyright: '+package)
  shutil.copy2(source,notices/(package+'.copyright'))
 doc=STAGE/'usr/share/doc/larsana'
 (doc/'compat-libraries.json').write_text(json.dumps(origins,indent=2)+'\n')
 source_manifest=BUILD/'compat-sources/manifest.json'
 if not source_manifest.exists():raise RuntimeError('Run fetch_compat_sources.py before final packaging')
 shutil.copy2(source_manifest,doc/'compat-source-manifest.json')
 (STAGE/'usr/share/man/man1/larsana.1.gz').write_bytes(gzip.compress((ROOT/'packaging/larsana.1').read_bytes(),mtime=0))
 (doc/'sources.lock.json').write_bytes((ROOT/'runtimes/sources.lock.json').read_bytes())
 for file in ['README.md','docs/PLAN.md','docs/BUILD_REPORT.md','docs/UNIFIED_PACKAGE.md']:
  shutil.copy2(ROOT/file,doc/Path(file).name)
 # No component package dependency: all components are owned by this one package.
 deps='python3 (>= 3.10), perl, libc6 (>= 2.39), libstdc++6 (>= 13.1), libgcc-s1, libgl1, libegl1, libopengl0, libglib2.0-0t64 | libglib2.0-0, libdbus-1-3, libfontconfig1, libfreetype6, libx11-6, libx11-xcb1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0, libxcb-xfixes0, libxcb-xinerama0, libxcb-randr0, libxcb-render0, libxcb-shm0, libxcb-sync1, libxkbcommon0, libxkbcommon-x11-0, libsm6, libice6, zlib1g, libxext6, fonts-dejavu-core'
 old=['larsana-full']+[subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip() for p in packages[1:]]
 control=STAGE/'DEBIAN';control.mkdir()
 (control/'control').write_text(f'''Package: larsana
Version: {VERSION}
Architecture: amd64
Maintainer: LARSANA Contributors <maintainers@larsana.invalid>
Section: devel
Priority: optional
Depends: {deps}
Recommends: x-terminal-emulator, polkitd, pkexec
Conflicts: {', '.join(old)}
Replaces: {', '.join(old)}
Description: Complete LARSANA desktop and local web development runtimes
 Includes Apache, stable Nginx, five PHP versions, four MariaDB versions
 and phpMyAdmin for local database management.
 One amd64 package for Ubuntu 24.04, Linux Mint 22.x and Debian 13.
''')
 guard='''#!/bin/sh
set -eu
case "$1" in remove|upgrade|deconfigure)
 for entry in /proc/[0-9]*/exe; do
  running=$(readlink "$entry" 2>/dev/null || true)
  case "$running" in /usr/lib/larsana/runtimes/*)
   echo 'Stop and close LARSANA before removing or upgrading.' >&2; exit 1;;
  esac
 done;;
esac
exit 0
'''
 (control/'prerm').write_text(guard);(control/'prerm').chmod(0o755)
 (control/'preinst').write_text('''#!/bin/sh
set -eu
. /etc/os-release
case "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}" in noble|trixie) ;; *)
 echo 'LARSANA supports Ubuntu 24.04, Mint 22.x or Debian 13 (amd64).' >&2; exit 1;;
esac
exit 0
''');(control/'preinst').chmod(0o755)
 # Rename component lintian overrides to match the single owner package.
 folder=STAGE/'usr/share/lintian/overrides'
 all_lines=[]
 for file in folder.iterdir():
  all_lines.extend(re.sub(r'^larsana[^:]*:', 'larsana:',line) for line in file.read_text().splitlines())
  file.unlink()
 all_lines += ['# ICU compatibility data library contains no code dependencies.', 'larsana: shared-library-lacks-prerequisites [usr/lib/larsana/compat/lib/libicudata.so.74]']
 # These individually pinned distro libraries are intentionally relocated for
 # cross-suite ABI compatibility. Exact corresponding distro source is mirrored.
 embedded={'libbz2.so.1.0':'bzip2','libcurl.so.4':'curl','libexpat.so.1':'expat','libfreetype.so.6':'freetype','libgmp.so.10':'gmp','libidn2.so.0':'libidn2-0','libjpeg.so.8':'libjpeg','libpng16.so.16':'libpng','libssh.so.4':'libssh','libxml2.so.2':'libxml2','libzstd.so.1':'libzstd','libtinfo.so.6':'ncurses'}
 all_lines+=['# Cross-suite private compatibility libraries; see compat-libraries.json and compat-source-manifest.json.']
 for file,library in embedded.items():
  all_lines.append(f'larsana: embedded-library {library} [usr/lib/larsana/compat/lib/{file}]')
 (folder/'larsana').write_text('\n'.join(all_lines)+'\n')
 from package_permissions import normalize
 normalize(STAGE/'usr')
 output=BUILD/'unified-artifacts'/f'larsana_{VERSION}_amd64.deb'
 output.parent.mkdir(parents=True,exist_ok=True)
 build_deb(STAGE,output)
 (BUILD/'unified-libraries.json').write_text(json.dumps(origins,indent=2)+'\n')
 print('BUILT',output,'private libraries',len(origins),flush=True)
if __name__=='__main__':build()
