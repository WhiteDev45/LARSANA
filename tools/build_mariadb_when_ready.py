#!/usr/bin/env python3
"""Local orchestration: build each requested GA database as its source finishes downloading."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
for series,version,channel in [('10.11','10.11.19','lts'),('11.8','11.8.9','lts'),('12.3','12.3.3','lts'),('13.0','13.0.2','stable')]:
    file=ROOT/'.build/sources'/f'mariadb-{version}.tar.gz'
    print('Waiting for verified source',file.name,flush=True)
    deadline=time.monotonic()+3600
    while not file.exists():
        if time.monotonic()>deadline:raise RuntimeError('Source download not completed: '+file.name)
        time.sleep(2)
    # Resolver commits the complete lock when all downloads finish. Preserve entries
    # already built while allowing this database to compile before that point.
    lockfile=ROOT/'runtimes/sources.lock.json'
    lock=json.loads(lockfile.read_text())
    if not any(i['id']=='mariadb-'+series for i in lock['sources']):
        import urllib.request
        url=f'https://archive.mariadb.org/mariadb-{version}/source/mariadb-{version}.tar.gz'
        sha=hashlib.sha256(file.read_bytes()).hexdigest()
        checks=urllib.request.urlopen(url.rsplit('/',1)[0]+'/sha256sums.txt',timeout=30).read().decode()
        if sha not in checks:raise RuntimeError('MariaDB checksum mismatch')
        lock['sources'].append(dict(id='mariadb-'+series,kind='mariadb',series=series,version=version,channel=channel,url=url,sha256=sha,verification='SHA256 matched official MariaDB source checksums over HTTPS'))
        lockfile.write_text(json.dumps(lock,indent=2)+'\n')
    subprocess.run(['python3',str(ROOT/'tools/build_runtimes.py'),'mariadb-'+series,'--jobs','4'],check=True)
