#!/usr/bin/env python3
"""Download the target distribution dependency closure without host installation."""
from pathlib import Path
import subprocess
from build_desktop import VERSION
from target_info import target_info
import json
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.build';cache=BUILD/'offline-cache';cache.mkdir(exist_ok=True)
status=BUILD/'offline-empty-status';status.write_text('')
opts=['-o',f'Dir::State::status={status}','-o',f'Dir::Cache::archives={cache}','-o','Debug::NoLocking=true']
apt=BUILD/'apt'
if (apt/'sources.list').exists():
    opts+=['-o',f'Dir::Etc::sourcelist={apt}/sources.list','-o','Dir::Etc::sourceparts=-','-o',f'Dir::State::lists={apt}/lists','-o',f'Dir::Cache::pkgcache={apt}/offline-pkgcache.bin','-o',f'Dir::Cache::srcpkgcache={apt}/offline-srcpkgcache.bin']
items=json.loads((ROOT/'runtimes/sources.lock.json').read_text())['sources']
files=[ROOT/'dist'/f'larsana_{VERSION}_amd64.deb',ROOT/'dist'/f'larsana-full_{VERSION}_all.deb']
files += [ROOT/'dist'/f"larsana-{i['id']}_{i['version']}-1larsana1_amd64.deb" for i in items]
for file in files:
    subprocess.run(['dpkg-deb','--info',str(file)],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['apt-get']+opts+['--download-only','--yes','--no-install-recommends','install','xterm','xfonts-base','pkexec','polkitd','fonts-dejavu-core']+[str(f) for f in files],check=True)
print('Offline dependency closure downloaded for',target_info(ROOT)['suite'])
