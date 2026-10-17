#!/usr/bin/env python3
"""Install/upgrade/remove/reinstall/purge in a disposable rootless filesystem."""
from pathlib import Path
import argparse
import json
import subprocess
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--label',default='final');parser.add_argument('--resume',action='store_true');parser.add_argument('--previous',type=Path);args=parser.parse_args()
if not args.label.replace('-','').isalnum():raise SystemExit('Invalid test label')
target=ROOT/'.build'/('install-root-'+args.label)
if target.exists() and not args.resume:raise SystemExit('Lifecycle filesystem already exists; choose a fresh test directory.')
if not target.exists():subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'.build/rootfs'),str(target)],check=True)
(target/'var/lib/dpkg/updates').mkdir(exist_ok=True)
(target/'var/lib/dpkg/triggers').mkdir(exist_ok=True)
# The test data belongs outside package-owned directories.
sample=target/'home/builder/.local/share/larsana/mariadb/10.11/keep.sql'
sample.parent.mkdir(parents=True,exist_ok=True);sample.write_text('preserve-user-database')
project=target/'home/builder/Larsana/www/keep/index.php'
project.parent.mkdir(parents=True,exist_ok=True);project.write_text('<?php echo "preserve-project";')
packages=sorted((ROOT/'dist').glob('*.deb'))
names=[subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip() for p in packages]
base=['bwrap','--die-with-parent','--unshare-user','--uid','0','--gid','0','--unshare-pid','--unshare-net',
      '--bind',str(target),'/', '--ro-bind',str(ROOT),'/work','--dev','/dev','--proc','/proc','--tmpfs','/tmp',
      '--setenv','PATH','/usr/sbin:/usr/bin:/sbin:/bin','--setenv','LC_ALL','C','--chdir','/work']
if args.previous:
    previous=args.previous.resolve()
    assert previous.is_dir(),previous
    (target/'previous').mkdir(exist_ok=True)
    base+=['--ro-bind',str(previous),'/previous']
def run(args):subprocess.run(base+args,check=True)
if args.previous:
    old=sorted(previous.glob('*.deb'))
    assert len(old)==2,'Expected previous desktop and metapackage'
    baseline=['/work/dist/'+p.name for p,n in zip(packages,names) if n not in ('larsana','larsana-full','larsana-mariadb-11.8')]
    run(['dpkg','--install']+baseline+['/previous/'+p.name for p in old])
    print('PASS previous 0.1.0 installation before upgrade',flush=True)
for action in ('install','upgrade','remove','reinstall','purge'):
    if action in ('install','upgrade','reinstall'):
        run(['dpkg','--install']+['/work/dist/'+p.name for p in packages])
        if action=='install' and args.previous:
            print('PASS upgrade from previous release 0.1.0 to 0.1.1 with MariaDB 11.8',flush=True)
    else:
        run(['dpkg','--'+action]+names)
    if action=='install':
        run(['env','PKEXEC_UID=1000','/usr/lib/larsana/larsana-hosts','add','lifecycle.test'])
        assert 'lifecycle.test' in (target/'etc/hosts').read_text()
        run(['env','PKEXEC_UID=1000','/usr/lib/larsana/larsana-hosts','remove','lifecycle.test'])
        assert 'lifecycle.test' not in (target/'etc/hosts').read_text()
        print('PASS constrained .test helper in disposable root',flush=True)
        (target/'artifacts').mkdir(exist_ok=True)
        userbase=['bwrap','--die-with-parent','--unshare-pid','--unshare-net',
            '--ro-bind',str(target),'/', '--bind',str(ROOT/'dist'),'/artifacts',
            '--dev','/dev','--proc','/proc','--tmpfs','/tmp',
            '--setenv','HOME','/tmp/larsana-user','--setenv','XDG_RUNTIME_DIR','/tmp/larsana-run',
            '--setenv','XDG_CONFIG_HOME','/tmp/larsana-config','--setenv','XDG_DATA_HOME','/tmp/larsana-data',
            '--setenv','XDG_STATE_HOME','/tmp/larsana-state',
            '--setenv','QT_QUICK_BACKEND','software','--chdir','/tmp']
        diagnostic=subprocess.run(userbase+['/usr/bin/larsana','--doctor'],capture_output=True,text=True)
        assert diagnostic.returncode==0,diagnostic.stderr
        assert json.loads(diagnostic.stdout)['service_state']=='not_inspected'
        rendered=subprocess.run(userbase+['/usr/bin/xvfb-run','-a','/usr/bin/larsana','--screenshot','/artifacts/larsana-installed.png'],capture_output=True,text=True,timeout=45)
        assert rendered.returncode==0,rendered.stderr
        assert 'TypeError' not in rendered.stderr and 'Traceback' not in rendered.stderr,rendered.stderr
        print('PASS installed launcher, doctor, rendered desktop and clean GUI shutdown',flush=True)
    assert sample.read_text()=='preserve-user-database'
    assert project.read_text()=='<?php echo "preserve-project";'
    print('PASS package lifecycle',action,'and user data preserved',flush=True)
print('Lifecycle test passed; host packages untouched.')
