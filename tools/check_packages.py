#!/usr/bin/env python3
"""Structural artifact checks independent of package installation."""
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
for item in lock['sources']:
    name='larsana-'+item['id']
    deb=ROOT/'dist'/f"{name}_{item['version']}-1larsana1_amd64.deb"
    info=subprocess.check_output(['dpkg-deb','-f',str(deb)],text=True)
    assert f'Package: {name}\n' in info
    assert 'Depends: ' in info
    listing=subprocess.check_output(['dpkg-deb','-c',str(deb)],text=True)
    assert 'runtime.json' in listing
    assert '/home/' not in listing
    assert '/etc/apache2' not in listing and '/etc/mysql' not in listing
    assert 'root/root' in listing
    archive=ROOT/'.build/sources'/item['url'].split('/')[-1]
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==item['sha256']
    subprocess.run(['dpkg-deb','--info',str(deb)],check=True,stdout=subprocess.DEVNULL)
    print('PASS artifact',deb.name,flush=True)
