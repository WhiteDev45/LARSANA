#!/usr/bin/env python3
"""Create an independent Debian 13 builder using signed official Debian repositories."""
from pathlib import Path
import shutil
import subprocess
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/'.build/targets/debian13'
target.mkdir(parents=True,exist_ok=True)
for name in ['src','tools','tests','packaging','runtimes','docs','.agents']:
    shutil.copytree(ROOT/name,target/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ['LICENSE','README.md','CONTRIBUTING.md','pyproject.toml']:
    shutil.copy(ROOT/name,target/name)
cache=target/'.build/cache';cache.mkdir(parents=True,exist_ok=True)
fs=target/'.build/rootfs';fs.mkdir(exist_ok=True)
apt=target/'.build/apt';(apt/'lists/partial').mkdir(parents=True,exist_ok=True);(apt/'keys').mkdir(exist_ok=True)
for key in ['archive-key-13','archive-key-13-security','release-13']:
    file=apt/'keys'/(key+'.asc')
    if not file.exists():file.write_bytes(urllib.request.urlopen('https://ftp-master.debian.org/keys/'+key+'.asc',timeout=30).read())
main_keys=','.join(str(apt/'keys'/name) for name in ['archive-key-13.asc','release-13.asc'])
security_key=str(apt/'keys/archive-key-13-security.asc')
sources=apt/'sources.list'
sources.write_text(f'deb [signed-by={main_keys}] https://deb.debian.org/debian trixie main\ndeb [signed-by={security_key}] https://security.debian.org/debian-security trixie-security main\n')
empty=target/'.build/empty-status';empty.touch()
opts=['-o',f'Dir::Etc::sourcelist={sources}','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={apt}/lists','-o',f'Dir::State::status={empty}','-o',f'Dir::Cache::archives={cache}','-o',f'Dir::Cache::pkgcache={apt}/pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={apt}/srcpkgcache.bin','-o','Debug::NoLocking=true']
subprocess.run(['apt-get']+opts+['update'],check=True)
packages=(target/'packaging/build-dependencies.txt').read_text().split()
subprocess.run(['apt-get']+opts+['--download-only','--yes','--no-install-recommends','install']+packages,check=True)
(target/'dist').mkdir(exist_ok=True)
sourcecache=target/'.build/sources'
if not sourcecache.exists():sourcecache.symlink_to(ROOT/'.build/sources',target_is_directory=True)
for tool in ['bootstrap_builder.py','builder_database.py']:
    subprocess.run(['python3',str(target/'tools'/tool)],cwd=target,check=True)
# Use the Debian vendor in this builder; both vendors are understood by lintian.
origin=fs/'etc/dpkg/origins/default'
origin.unlink(missing_ok=True);origin.symlink_to('debian')
site=target/'.venv/lib/python3.12/site-packages';site.mkdir(parents=True,exist_ok=True)
for name in ['PySide6','shiboken6']:
    shutil.copytree(ROOT/'.venv/lib/python3.12/site-packages'/name,site/name,dirs_exist_ok=True)
for file in (ROOT/'.venv/lib/python3.12/site-packages').glob('*.dist-info'):
    if file.name.lower().startswith(('pyside6','shiboken6')):shutil.copytree(file,site/file.name,dirs_exist_ok=True)
print('Debian 13 builder ready:',target,flush=True)
