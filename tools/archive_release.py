#!/usr/bin/env python3
"""Archive a validated per-suite offline release, keeping ABIs separate."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
from target_info import target_info
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
info=target_info(ROOT);name=f"larsana-0.1.1-{info['suite']}-amd64"
report=json.loads((ROOT/'dist/validation/results.json').read_text())
assert all(v['result']=='pass' for v in report['checks'].values())
output=args.output or ROOT/'releases'/(name+'.tar.gz')
output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
if output.is_relative_to(ROOT/'dist'):raise SystemExit('Write the archive outside dist to avoid recursive bundling')
with tarfile.open(output,'w:gz',compresslevel=1) as tar:
 for path in sorted((ROOT/'dist').iterdir()):
  if path.name=='debian13':continue
  tar.add(path,arcname=name+'/'+path.name)
(output.parent/(output.name+'.sha256')).write_text(hashlib.sha256(output.read_bytes()).hexdigest()+'  '+output.name+'\n')
print(output)
