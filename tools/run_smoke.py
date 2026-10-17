#!/usr/bin/env python3
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
fs=ROOT/'.build/rootfs'
(fs/'usr/lib/larsana').mkdir(parents=True,exist_ok=True)
cmd=['bwrap','--die-with-parent','--unshare-pid','--unshare-net','--ro-bind',str(fs),'/',
     '--bind',str(ROOT),'/work','--ro-bind',str(ROOT/'.build/runtime-root/usr/lib/larsana'),'/usr/lib/larsana',
     '--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','HOME','/tmp/larsana-home','--setenv','USER','builder',
     '--setenv','XDG_CONFIG_HOME','/tmp/larsana-config','--setenv','XDG_DATA_HOME','/tmp/larsana-data',
     '--setenv','XDG_STATE_HOME','/tmp/larsana-state','--setenv','XDG_RUNTIME_DIR','/tmp/larsana-run',
     '--setenv','LARSANA_RUNTIME_ROOT','/usr/lib/larsana/runtimes','--chdir','/work','/usr/bin/python3','tools/smoke_runtimes.py']
raise SystemExit(subprocess.call(cmd))
