#!/usr/bin/env python3
"""Resolve actual .deb dependencies with APT and complete the isolated test base.
Compilation roots are not upgraded: conflicting existing library files are rejected.
"""
import os
from pathlib import Path
import shutil
import subprocess
from builder_database import register_package
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.build';fs=BUILD/'rootfs'
cache=BUILD/'test-dependency-cache';cache.mkdir(exist_ok=True)
opts=['-o',f'Dir::State::status={fs}/var/lib/dpkg/status','-o',f'Dir::Cache::archives={cache}','-o','Debug::NoLocking=true']
apt=BUILD/'apt'
if (apt/'sources.list').exists():
    opts+=['-o',f'Dir::Etc::sourcelist={apt}/sources.list','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={apt}/lists','-o',f'Dir::Cache::pkgcache={apt}/pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={apt}/srcpkgcache.bin']
packages=[]
for deb in sorted((ROOT/'dist').glob('*.deb')):
    if subprocess.run(['dpkg-deb','--info',str(deb)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:packages.append(str(deb))
subprocess.run(['apt-get']+opts+['--download-only','--yes','--no-install-recommends','install','libc-bin','diffutils','util-linux']+packages,check=True)
status_file=fs/'var/lib/dpkg/status'
entries={}
for paragraph in status_file.read_text().strip().split('\n\n'):
    for line in paragraph.splitlines():
        if line.startswith('Package: '):entries[line[9:]]=paragraph+'\n';break
replaceable={'usr/bin/diff','usr/bin/getopt','usr/bin/mcookie','usr/sbin/ldconfig','usr/sbin/ldconfig.real'}
for deb in sorted(cache.glob('*.deb')):
    name=subprocess.check_output(['dpkg-deb','-f',str(deb),'Package'],text=True).strip()
    if name.startswith('larsana'):continue
    overlay=BUILD/'test-overlay'/name
    if overlay.exists():shutil.rmtree(overlay)
    overlay.mkdir(parents=True)
    subprocess.run(['dpkg-deb','-x',str(deb),str(overlay)],check=True)
    for source in overlay.rglob('*'):
        rel=source.relative_to(overlay)
        parts=rel.parts
        if parts[0] in ('bin','sbin','lib','lib64'):rel=Path('usr')/rel
        dest=fs/rel
        if source.is_symlink():
            if dest.is_symlink() and os.readlink(dest)==os.readlink(source):continue
            if dest.exists() or dest.is_symlink():raise RuntimeError('Refusing to replace builder path: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(os.readlink(source));continue
        if source.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
        if dest.exists() and dest.read_bytes()!=source.read_bytes():
            if str(rel) not in replaceable and not str(rel).startswith('usr/lib/locale/'):
                raise RuntimeError('Refusing to change an existing builder library/file: '+str(dest))
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    pkg,entry=register_package(deb,fs);entries[pkg]=entry
    shutil.copy2(deb,BUILD/'cache'/deb.name)
    print('PROVISIONED',name,flush=True)
new=status_file.with_name('status.new');new.write_text('\n'.join(entries.values()));new.replace(status_file)
print('Isolated package test base complete; host packages untouched.')
