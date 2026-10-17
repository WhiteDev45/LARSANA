#!/usr/bin/env python3
"""Extract downloaded build dependencies into a rootless Bubblewrap filesystem."""
from pathlib import Path
import os
import subprocess
ROOT = Path(__file__).resolve().parents[1]
fs = ROOT / '.build/rootfs'
fs.mkdir(parents=True, exist_ok=True)
for alias in ('bin', 'sbin', 'lib', 'lib64'):
    target = fs / 'usr' / alias
    target.mkdir(parents=True, exist_ok=True)
    path = fs / alias
    if not path.exists():
        path.symlink_to('usr/' + alias)
for package in sorted((ROOT / '.build/cache').glob('*.deb')):
    subprocess.run(['dpkg-deb', '-x', str(package), str(fs)], check=True)
for path in ('tmp', 'proc', 'dev', 'work', 'etc', 'root'):
    (fs / path).mkdir(exist_ok=True)
(fs / 'etc/passwd').write_text(f'root:x:0:0:root:/root:/bin/bash\nbuilder:x:{os.getuid()}:{os.getgid()}:Builder:/work:/bin/bash\n')
(fs / 'etc/group').write_text(f'root:x:0:\nbuilder:x:{os.getgid()}:\n')
print('Builder ready:', fs)

for name,target in {"sh":"bash", "cc":"gcc", "c++":"g++", "awk":"gawk", "nawk":"gawk"}.items():
    path=fs/"usr/bin"/name
    if not path.exists(): path.symlink_to(target)

# dpkg extraction may replace usr-merge aliases with directories from older packages.
import shutil
for alias in ('bin','sbin','lib','lib64'):
    path=fs/alias
    if path.is_dir() and not path.is_symlink():
        shutil.copytree(path,fs/'usr'/alias,dirs_exist_ok=True,symlinks=True)
        shutil.rmtree(path)
        path.symlink_to('usr/'+alias)

(fs/"etc/hosts").write_text("127.0.0.1 localhost\n::1 localhost\n")
(fs/"etc/nsswitch.conf").write_text("passwd: files\ngroup: files\nhosts: files dns\n")

origin=fs/"etc/dpkg/origins/default"
if not origin.exists(): origin.symlink_to("ubuntu")

(fs/"etc/machine-id").write_text("00000000000000000000000000000001\n")
