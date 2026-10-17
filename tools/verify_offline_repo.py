#!/usr/bin/env python3
"""Resolve the complete installation using ONLY the signed local repository."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
repo=ROOT/'dist/repository'
base=ROOT/'.build/offline-verification';(base/'lists/partial').mkdir(parents=True,exist_ok=True);(base/'cache/partial').mkdir(parents=True,exist_ok=True)
status=base/'status';status.write_text('')
sources=base/'sources.list';sources.write_text(f'deb [signed-by={repo}/larsana-local.gpg] {repo.as_uri()} ./\n')
opts=['-o',f'Dir::Etc::sourcelist={sources}','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={base}/lists','-o',f'Dir::State::status={status}','-o',f'Dir::Cache::archives={base}/cache','-o',f'Dir::Cache::pkgcache={base}/pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={base}/srcpkgcache.bin','-o','Debug::NoLocking=true']
subprocess.run(['apt-get']+opts+['update'],check=True)
subprocess.run(['apt-get']+opts+['--download-only','--yes','--no-install-recommends','install','larsana-full','xterm','xfonts-base','fonts-dejavu-core','pkexec','polkitd'],check=True)
print('PASS signed APT repository and offline dependency closure; no external sources used.')
