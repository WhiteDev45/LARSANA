#!/usr/bin/env python3
"""Fetch pinned phpMyAdmin distribution and corresponding source at build time."""
from pathlib import Path
import hashlib
import json
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / 'runtimes/phpmyadmin.lock.json').read_text())
for archive_key, url_key, sha_key in [('archive', 'url', 'sha256'), ('source_archive', 'source_url', 'source_sha256')]:
    out = ROOT / '.build/phpmyadmin' / lock[archive_key]
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        temporary = out.with_suffix(out.suffix + '.part')
        urllib.request.urlretrieve(lock[url_key], temporary)
        assert hashlib.sha256(temporary.read_bytes()).hexdigest() == lock[sha_key], 'phpMyAdmin checksum mismatch'
        temporary.replace(out)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == lock[sha_key], 'phpMyAdmin checksum mismatch'
    print('VERIFIED', out)
