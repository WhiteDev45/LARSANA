#!/usr/bin/env python3
"""Prepare a disposable Ubuntu root from signed APT packages, without host installs."""
from pathlib import Path
import argparse, os, shutil, subprocess
from builder_database import register_package
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--suite',default='resolute');args=p.parse_args()
base=ROOT/'.build/ubuntu-tests'/args.suite
fs=base/'rootfs';cache=base/'cache';apt=base/'apt'
for folder in [fs,cache/'partial',apt/'lists/partial']:folder.mkdir(parents=True,exist_ok=True)
status=base/'empty-status';status.touch()
sources=apt/'sources.list'
sources.write_text(f'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://archive.ubuntu.com/ubuntu {args.suite} main universe\n')
opts=['-o',f'Dir::Etc::sourcelist={sources}','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={apt}/lists','-o',f'Dir::State::status={status}','-o',f'Dir::Cache::archives={cache}','-o',f'Dir::Cache::pkgcache={apt}/pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={apt}/srcpkgcache.bin','-o','Debug::NoLocking=true']
subprocess.run(['apt-get',*opts,'update'],check=True)
package=ROOT/'.build/unified-artifacts/larsana_1.2.3_amd64.deb'
subprocess.run(['apt-get',*opts,'--download-only','--yes','--no-install-recommends','install',str(package),'apt','dpkg','bash','dash','libc-bin','sed','grep','util-linux','openssl','hostname','diffutils','mawk','libgssapi-krb5-2','coreutils','findutils','xvfb','xauth','libxcb1','libgl1-mesa-dri'],check=True)
for alias in ['bin','sbin','lib','lib64']:
 (fs/'usr'/alias).mkdir(parents=True,exist_ok=True)
 if not (fs/alias).exists():(fs/alias).symlink_to('usr/'+alias)
entries=[]
for deb in sorted(cache.glob('*.deb')):
 if subprocess.check_output(['dpkg-deb','-f',str(deb),'Package'],text=True).strip()=='larsana':continue
 subprocess.run(['dpkg-deb','-x',str(deb),str(fs)],check=True)
 entries.append(register_package(deb,fs)[1])
for alias in ['bin','sbin','lib','lib64']:
 path=fs/alias
 if path.is_dir() and not path.is_symlink():
  shutil.copytree(path,fs/'usr'/alias,dirs_exist_ok=True,symlinks=True);shutil.rmtree(path);path.symlink_to('usr/'+alias)
(fs/'var/lib/dpkg/status').write_text('\n'.join(entries))
for name in ['tmp','proc','dev','work','artifacts','root','var/lib/dpkg/updates','var/lib/dpkg/triggers']:(fs/name).mkdir(parents=True,exist_ok=True)
(fs/'etc/passwd').write_text(f'root:x:0:0:root:/root:/bin/bash\nbuilder:x:{os.getuid()}:{os.getgid()}:Builder:/tmp/home:/bin/bash\n')
(fs/'etc/group').write_text(f'root:x:0:\nbuilder:x:{os.getgid()}:\n')
(fs/'etc/machine-id').write_text('00000000000000000000000000000001\n')
(fs/'etc/hosts').write_text('127.0.0.1 localhost\n::1 localhost\n')
(fs/'etc/nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files dns\n')
if not (fs/'usr/bin/awk').exists():(fs/'usr/bin/awk').symlink_to('mawk')
if not (fs/'usr/bin/sh').exists():(fs/'usr/bin/sh').symlink_to('dash')
print('PASS prepared signed Ubuntu test root',args.suite,flush=True)
