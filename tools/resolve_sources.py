#!/usr/bin/env python3
"""Resolve official upstream release metadata into a reviewed source lock."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.build/sources'
CACHE.mkdir(parents=True, exist_ok=True)

def get(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return r.read()

def fetch(item):
    path = CACHE / item['url'].split('/')[-1]
    if not path.exists():
        print('Downloading', item['id'], flush=True)
        partial=path.with_name(path.name+'.part')
        log=CACHE/(item['id']+'.download.log')
        with log.open('a') as stream:
            subprocess.run(['curl','-L','--fail','--retry','5','--retry-all-errors','--connect-timeout','20','--max-time','600','-C','-',item.get('download_url',item['url']),'-o',str(partial)],stdout=stream,stderr=stream,check=True)
        partial.replace(path)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if item.get('sha256') and sha != item['sha256']:
        raise ValueError(f"Checksum mismatch: {item['id']}")
    item['sha256'] = sha
    if item['kind']=='mariadb':
        checks=get(item['url'].rsplit('/',1)[0]+'/sha256sums.txt').decode()
        if sha not in checks:
            raise ValueError(f"Official MariaDB checksum mismatch: {item['id']}")
        item['verification']='SHA256 matched official MariaDB source checksums over HTTPS'
    elif item['kind']=='apache':
        checks=get(item['url']+'.sha256').decode()
        if sha not in checks:
            raise ValueError('Official Apache checksum mismatch')
        item['verification']='SHA256 matched official Apache source checksum over HTTPS'
    item['verification'] = item.get('verification', 'Official upstream HTTPS; SHA256 pinned on first retrieval')
    print('Locked', item['id'], item['version'], sha, flush=True)
    return item

items = []
for series in ['8.1', '8.2', '8.3', '8.4', '8.5']:
    data = json.loads(get('https://www.php.net/releases/?json&version=' + series))
    src = next(x for x in data['source'] if x['filename'].endswith('.tar.xz'))
    items.append(dict(id='php-' + series, kind='php', series=series, version=data['version'], channel='legacy' if series=='8.1' else 'stable', url='https://www.php.net/distributions/' + src['filename'], sha256=src['sha256'], verification='SHA256 from official PHP release API over HTTPS'))
html = get('https://nginx.org/en/download.html').decode()
stable = html.split('Stable version')[1].split('Legacy versions')[0]
version = re.search(r'nginx-(\d+\.\d+\.\d+)\.tar.gz', stable)[1]
items.append(dict(id='nginx', kind='nginx', series='.'.join(version.split('.')[:2]), version=version, channel='stable', url=f'https://nginx.org/download/nginx-{version}.tar.gz'))
html = get('https://httpd.apache.org/download.cgi').decode()
version = re.search(r'httpd-(2\.4\.\d+)\.tar.bz2', html)[1]
items.append(dict(id='apache-2.4', kind='apache', series='2.4', version=version, channel='stable', url=f'https://archive.apache.org/dist/httpd/httpd-{version}.tar.bz2'))
# These GA/LTS releases were verified against mariadb.org release listings.
for version, channel in [('10.11.19','lts'), ('11.8.9','lts'), ('12.3.3','lts'), ('13.0.2','stable')]:
    series='.'.join(version.split('.')[:2])
    items.append(dict(download_url=f'https://mirror.mariadb.org/mariadb-{version}/source/mariadb-{version}.tar.gz', id='mariadb-' + series, kind='mariadb', series=series, version=version, channel=channel, url=f'https://archive.mariadb.org/mariadb-{version}/source/mariadb-{version}.tar.gz'))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    locked=list(pool.map(fetch, items))
(ROOT / 'runtimes/sources.lock.json').write_text(json.dumps({'schema':1,'sources':locked}, indent=2)+'\n')
