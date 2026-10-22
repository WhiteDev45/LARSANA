#!/usr/bin/env python3
"""Exercise the SAME unified payload with either target's system libc/desktop."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['noble','trixie','resolute'],required=True);p.add_argument('--gui',action='store_true');p.add_argument('--ldd',action='store_true');p.add_argument('--crypto',action='store_true');p.add_argument('--unit',action='store_true');p.add_argument('--phpmyadmin',action='store_true');p.add_argument('--database-access',action='store_true');p.add_argument('--laravel',action='store_true');p.add_argument('--reload-diagnostic',action='store_true');p.add_argument('--web-regression',action='store_true');args=p.parse_args()
fs=ROOT/'.build/ubuntu-tests/resolute/rootfs' if args.target=='resolute' else (ROOT if args.target=='noble' else ROOT/'.build/targets/debian13')/'.build/rootfs'
(fs/'usr/lib/larsana').mkdir(parents=True,exist_ok=True)
out=ROOT/'.build/unified-tests'/args.target;out.mkdir(parents=True,exist_ok=True)
base=['bwrap','--die-with-parent','--unshare-pid','--unshare-net','--ro-bind',str(fs),'/',
 '--bind',str(ROOT),'/work','--bind',str(out),'/work/dist','--ro-bind',str(ROOT/'.build/unified-stage/usr/lib/larsana'),'/usr/lib/larsana',
 '--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','HOME','/tmp/larsana-home','--setenv','USER','builder',
 '--setenv','XDG_CONFIG_HOME','/tmp/larsana-config','--setenv','XDG_DATA_HOME','/tmp/larsana-data','--setenv','XDG_STATE_HOME','/tmp/larsana-state',
 '--setenv','XDG_RUNTIME_DIR','/tmp/larsana-run','--setenv','QT_QUICK_BACKEND','software','--setenv','PYTHONPATH','/usr/lib/larsana/python','--chdir','/work']
if args.ldd:
 code='''from pathlib import Path
import subprocess
count=0
for file in Path('/usr/lib/larsana/runtimes').rglob('*'):
 if not file.is_file() or file.is_symlink():continue
 with file.open('rb') as f:
  if f.read(4)!=b'\\x7fELF':continue
 result=subprocess.run(['ldd',str(file)],capture_output=True,text=True)
 assert 'not found' not in result.stdout+result.stderr,(file,result.stdout,result.stderr)
 count+=1
print('PASS native ELF dependency resolution',count)
'''
 cmd=['/usr/bin/python3','-c',code]
elif args.unit:
 cmd=['/usr/bin/python3','-c',"import sys;sys.path[:0]=['/work/src','/work/.build/targets/debian13/.build/test-python'];import pytest;raise SystemExit(pytest.main(['-q','-p','no:cacheprovider','/work/tests']))"]
elif args.reload_diagnostic:cmd=['/usr/bin/python3','tools/nginx_reload_diagnostic.py']
elif args.web_regression:cmd=['/usr/bin/python3','tools/web_regression.py']
elif args.database_access:cmd=['/usr/bin/python3','tools/mariadb_access_smoke.py']
elif args.laravel:cmd=['/usr/bin/python3','tools/laravel_smoke.py']
elif args.phpmyadmin:cmd=['/usr/bin/python3','tools/phpmyadmin_smoke.py']
elif args.crypto:cmd=['/usr/bin/python3','tools/unified_crypto_smoke.py']
else:cmd=['/usr/bin/xvfb-run','-a','/usr/bin/python3','tools/gui_smoke.py'] if args.gui else ['/usr/bin/python3','tools/smoke_runtimes.py']
raise SystemExit(subprocess.call(base+cmd))
