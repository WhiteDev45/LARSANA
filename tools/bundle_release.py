#!/usr/bin/env python3
"""Assemble local binary/source artifacts and optionally sign a flat APT repository.
The local build key is for this bundle, not an official public release identity.
"""
import argparse
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from target_info import target_info
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'

def bundle(offline=False):
    info=target_info(ROOT)
    suite=info['suite']
    target=DIST/'repository';target.mkdir(exist_ok=True)
    # Rebuild the owned package set so retired app versions are not republished.
    for file in target.glob('larsana*.deb'):file.unlink()
    for file in DIST.glob('*.deb'):shutil.copy2(file,target/file.name)
    (DIST/'README.md').write_text((ROOT/'packaging/RELEASE_README.md.in').read_text().replace('@SUITE@',suite))
    installer=(ROOT/'packaging/install-offline.sh.in').read_text().replace('@SUITE@',suite)
    (DIST/'install-offline.sh').write_text(installer);(DIST/'install-offline.sh').chmod(0o755)
    if offline:
        for file in (ROOT/'.build/offline-cache').glob('*.deb'):
            if not file.name.startswith('larsana'):shutil.copy2(file,target/file.name)
    with (target/'Packages').open('wb') as stream:
        subprocess.run(['dpkg-scanpackages','--multiversion','.','/dev/null'],cwd=target,stdout=stream,check=True)
    packages=(target/'Packages').read_bytes()
    (target/'Packages.gz').write_bytes(gzip.compress(packages,mtime=0))
    release=f'Origin: LARSANA Local Build\nLabel: LARSANA\nSuite: {suite}\nCodename: {suite}\nArchitectures: amd64 all\nDate: '+datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')+'\nSHA256:\n'
    for name in ['Packages','Packages.gz']:
        data=(target/name).read_bytes();release+=f' {hashlib.sha256(data).hexdigest()} {len(data)} {name}\n'
    (target/'Release').write_text(release)
    keyhome=ROOT/'.build/release-key';keyhome.mkdir(exist_ok=True);keyhome.chmod(0o700)
    identity='LARSANA Local Build <local-build@larsana.invalid>'
    if not (keyhome/'pubring.kbx').exists():
        subprocess.run(['gpg','--batch','--pinentry-mode','loopback','--passphrase','','--homedir',str(keyhome),'--quick-generate-key',identity,'ed25519','sign','1y'],check=True)
    common=['gpg','--homedir',str(keyhome),'--batch','--yes','--pinentry-mode','loopback','--passphrase','']
    subprocess.run(common+['--output',str(target/'InRelease'),'--clearsign',str(target/'Release')],check=True)
    subprocess.run(common+['--armor','--output',str(target/'Release.gpg'),'--detach-sign',str(target/'Release')],check=True)
    with (target/'larsana-local.gpg').open('wb') as stream:subprocess.run(common+['--export',identity],stdout=stream,check=True)
    subprocess.run(['gpgv','--keyring',str(target/'larsana-local.gpg'),str(target/'InRelease')],check=True)
    # The LARSANA source is portable; upstream archives and patches accompany it.
    source=DIST/'larsana-source-0.1.1.tar.gz'
    with tarfile.open(source,'w:gz') as tar:
        for name in ['src','tools','tests','packaging','runtimes','docs','.agents','.github','.gitignore','README.md','CONTRIBUTING.md','LICENSE','pyproject.toml']:
            path=ROOT/name
            if path.exists():tar.add(path,arcname='larsana-0.1.1/'+name,filter=lambda info:None if '__pycache__' in info.name else info)
    upstream=DIST/'upstream-sources';upstream.mkdir(exist_ok=True)
    lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
    for item in lock['sources']:
        file=ROOT/'.build/sources'/item['url'].split('/')[-1]
        destination=upstream/file.name
        if not destination.exists():shutil.copy2(file,destination)
    desktop_lock=ROOT/'packaging/desktop-sources.lock.json'
    if desktop_lock.exists():
        desktop=json.loads(desktop_lock.read_text())
        desktop_folder=upstream/'desktop';desktop_folder.mkdir(exist_ok=True)
        for item in desktop['sources']:
            file=ROOT/'.build/desktop-sources'/item['url'].split('/')[-1]
            if hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Desktop source mismatch')
            dest=desktop_folder/file.name
            if not dest.exists():shutil.copy2(file,dest)
        shutil.copy(desktop_lock,DIST/'desktop-sources.lock.json')
    shutil.copy(ROOT/'runtimes/sources.lock.json',DIST/'sources.lock.json')
    manifest={'version':'0.1.1','target':suite+'-amd64','builder':info,'offline_dependency_closure':offline,'components':lock['sources'],'artifacts':[]}
    for file in sorted(DIST.glob('*.deb')):
        manifest['artifacts'].append({'file':file.name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'bytes':file.stat().st_size})
    (DIST/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=[]
    for path in sorted(DIST.rglob('*')):
        if path.is_file() and path.name!='SHA256SUMS':lines.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(DIST)))
    (DIST/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    print('Local signed repository, source archives and checksums:',DIST)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args();bundle(args.offline)
