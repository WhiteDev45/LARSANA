#!/usr/bin/env python3
"""Fetch already-reviewed versions, preserving the source lock unchanged."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
cache=ROOT/'.build/sources';cache.mkdir(parents=True,exist_ok=True)
lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
def fetch(item):
    file=cache/item['url'].split('/')[-1]
    if not file.exists():
        partial=file.with_name(file.name+'.part')
        with (cache/(item['id']+'.download.log')).open('a') as log:
            subprocess.run(['curl','-L','--fail','--retry','5','--retry-all-errors','--connect-timeout','20','--max-time','600','-C','-',item.get('download_url',item['url']),'-o',str(partial)],stdout=log,stderr=log,check=True)
        partial.replace(file)
    if hashlib.sha256(file.read_bytes()).hexdigest()!=item['sha256']:
        raise RuntimeError('Source hash mismatch: '+item['id'])
    print('READY',item['id'],item['version'],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,lock['sources']))
