#!/usr/bin/env python3
"""Preserve upstream license/copyright/attribution documents from verified sources."""
import hashlib
import json
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'packaging/desktop-sources.lock.json').read_text())
base=ROOT/'packaging/desktop-notices'
for item in lock['sources']:
    archive=ROOT/'.build/desktop-sources'/item['url'].split('/')[-1]
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Source mismatch: '+item['id'])
    count=0
    with tarfile.open(archive,mode='r|*') as tar:
        for member in tar:
            if not member.isfile() or member.size>1024*1024:continue
            path=Path(member.name)
            parts=path.parts[1:]
            if not parts or '..' in parts or path.is_absolute():continue
            name=path.name.upper()
            if not (name.startswith(('LICENSE','COPYING','NOTICE','COPYRIGHT')) or path.name in ('qt_attributions.json','.qt_attributions.json')):continue
            target=base/item['id']/Path(*parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(tar.extractfile(member).read());count+=1
    print('NOTICES',item['id'],count,flush=True)
