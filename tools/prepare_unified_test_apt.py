#!/usr/bin/env python3
"""Add native APT to disposable test clones only, never to the host/builders."""
from pathlib import Path
import argparse,subprocess,shutil,os
from builder_database import register_package
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['noble','trixie'],required=True);args=p.parse_args()
fs=ROOT/'.build/unified-install'/args.target
cache=ROOT/'.build/apt-test-cache'/args.target;cache.mkdir(parents=True,exist_ok=True)
opts=['-o',f'Dir::State::status={fs}/var/lib/dpkg/status','-o',f'Dir::Cache::archives={cache}','-o','Debug::NoLocking=true']
if args.target=='trixie':
 apt=ROOT/'.build/targets/debian13/.build/apt'
 opts+=['-o',f'Dir::Etc::sourcelist={apt}/sources.list','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={apt}/lists','-o',f'Dir::Cache::pkgcache={cache}/pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={cache}/srcpkgcache.bin']
subprocess.run(['apt-get']+opts+['--yes','--download-only','--no-install-recommends','install','apt'],check=True)
entries={}
for para in (fs/'var/lib/dpkg/status').read_text().strip().split('\n\n'):
 for line in para.splitlines():
  if line.startswith('Package: '):entries[line[9:]]=para+'\n';break
for deb in cache.glob('*.deb'):
 overlay=cache/'overlay'
 if overlay.exists():shutil.rmtree(overlay)
 overlay.mkdir()
 subprocess.run(['dpkg-deb','-x',str(deb),str(overlay)],check=True)
 for source in overlay.rglob('*'):
  rel=source.relative_to(overlay)
  if rel.parts[0] in ['lib','bin','sbin','lib64']:rel=Path('usr')/rel
  dest=fs/rel
  if source.is_dir() and not source.is_symlink():dest.mkdir(parents=True,exist_ok=True)
  elif source.is_symlink():
   if dest.is_symlink():dest.unlink()
   elif dest.exists():raise RuntimeError('Unexpected symlink collision '+str(dest))
   dest.parent.mkdir(parents=True,exist_ok=True);dest.symlink_to(os.readlink(source))
  else:
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
 name,entry=register_package(deb,fs);entries[name]=entry
(fs/'var/lib/dpkg/status').write_text('\n'.join(entries.values()))
print('PASS native APT ready in disposable',args.target,'test root')
