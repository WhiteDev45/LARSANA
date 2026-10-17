#!/usr/bin/env python3
"""Verify source hashes against official metadata and the Nginx signing key."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
lockfile=ROOT/'runtimes/sources.lock.json'
lock=json.loads(lockfile.read_text())
cache=ROOT/'.build/sources'
home=ROOT/'.build/gnupg';home.mkdir(exist_ok=True);home.chmod(0o700)

def get(url):
    return urllib.request.urlopen(url,timeout=60).read()

for item in lock['sources']:
    archive=cache/item['url'].split('/')[-1]
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest==item['sha256'],item['id']
    if item['kind']=='php':
        meta=json.loads(get('https://www.php.net/releases/?json&version='+item['version']))
        assert any(s['sha256']==digest for s in meta['source']),item['id']
        item['verification']='SHA256 matched official PHP release API over HTTPS'
    elif item['kind']=='nginx':
        key=home/'pluknet.key';key.write_bytes(get('https://nginx.org/keys/pluknet.key'))
        subprocess.run(['gpg','--homedir',str(home),'--import',str(key)],check=True)
        asc=archive.with_name(archive.name+'.asc');asc.write_bytes(get(item['url']+'.asc'))
        check=subprocess.run(['gpg','--homedir',str(home),'--status-fd','1','--verify',str(asc),str(archive)],capture_output=True,text=True,check=True)
        fingerprint='D6786CE303D9A9022998DC6CC8464D549AF75C0A'
        assert 'VALIDSIG '+fingerprint in check.stdout,'Unexpected Nginx signer; review official upstream key rotation'
        item['verification']='OpenPGP signature verified; official pluknet key '+fingerprint
    else:
        url=item['url']+'.sha256' if item['kind']=='apache' else item['url'].rsplit('/',1)[0]+'/sha256sums.txt'
        assert digest in get(url).decode(),item['id']
        item['verification']='SHA256 matched official upstream source checksums over HTTPS'
    print('VERIFIED',item['id'],item['version'],flush=True)
lockfile.write_text(json.dumps(lock,indent=2)+'\n')
