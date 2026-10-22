#!/usr/bin/env python3
"""Reject package errors and warnings outside the reviewed phpMyAdmin exceptions."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('package',type=Path);args=p.parse_args();package=args.package.resolve()
result=subprocess.run(['bwrap','--die-with-parent','--unshare-pid','--unshare-net','--ro-bind',str(ROOT/'.build/rootfs'),'/', '--ro-bind',str(ROOT),'/work','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','HOME','/tmp','--setenv','LC_ALL','C','--setenv','PATH','/usr/bin:/bin','lintian','--allow-root','/work/'+str(package.relative_to(ROOT))],capture_output=True,text=True)
value=result.stdout+result.stderr
print(value,end='',flush=True)
assert result.returncode in (0,1),result.returncode
assert not any(line.startswith('E: ') for line in value.splitlines())
allow=json.loads((ROOT/'packaging/phpmyadmin-lintian-allowlist.json').read_text())['warnings']
assert sorted(line for line in value.splitlines() if line.startswith('W: '))==sorted(allow)
with package.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
print('PASS lintian unified package',digest,flush=True)
