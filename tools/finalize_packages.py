#!/usr/bin/env python3
"""Apply final packaging policy to source-built payloads without recompilation."""
import argparse
import json
from pathlib import Path
import subprocess
from build_runtimes import ROOT, BUILD, package
parser=argparse.ArgumentParser();parser.add_argument('--available',action='store_true');parser.add_argument('runtime',nargs='*');args=parser.parse_args()
items=json.loads((ROOT/'runtimes/sources.lock.json').read_text())['sources']
if args.runtime:
    unknown=set(args.runtime)-{i['id'] for i in items}
    if unknown:parser.error('Unknown runtime: '+', '.join(sorted(unknown)))
    items=[i for i in items if i['id'] in args.runtime]
for item in items:
    out=ROOT/'dist'/f"larsana-{item['id']}_{item['version']}-1larsana1_amd64.deb"
    if args.available and (not out.exists() or subprocess.run(['dpkg-deb','--info',str(out)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode):
        continue
    package(item,BUILD/'stage'/item['id'])
