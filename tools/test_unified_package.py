#!/usr/bin/env python3
"""Install exactly one .deb, migrate modular installs, and preserve test data."""
from pathlib import Path
import argparse,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['noble','trixie'],required=True);p.add_argument('--reuse',action='store_true');args=p.parse_args()
origin=ROOT if args.target=='noble' else ROOT/'.build/targets/debian13'
fs=ROOT/'.build/unified-install'/args.target
if fs.exists() and not args.reuse:raise SystemExit('Test filesystem already exists: '+str(fs))
fs.parent.mkdir(exist_ok=True)
if not fs.exists():subprocess.run(['cp','-a','--reflink=auto',str(origin/'.build/rootfs'),str(fs)],check=True)
if not (fs/'usr/bin/apt-get').exists():subprocess.run(['python3',str(ROOT/'tools/prepare_unified_test_apt.py'),'--target',args.target],check=True)
for path in ['var/lib/dpkg/updates','var/lib/dpkg/triggers','artifacts']:(fs/path).mkdir(parents=True,exist_ok=True)
out=ROOT/'.build/unified-tests'/args.target;out.mkdir(parents=True,exist_ok=True)
keep=fs/'home/builder/.local/share/larsana/mariadb/11.8/keep.sql';keep.parent.mkdir(parents=True,exist_ok=True);keep.write_text('preserve-database')
project=fs/'home/builder/Larsana/www/keep/index.php';project.parent.mkdir(parents=True,exist_ok=True);project.write_text('preserve-project')
settings=fs/'home/builder/.config/larsana/settings.json';settings.parent.mkdir(parents=True,exist_ok=True);settings.write_text('{"mariadb":"11.8","php":"8.3"}')
base=['bwrap','--die-with-parent','--unshare-user','--uid','0','--gid','0','--unshare-pid','--unshare-net','--bind',str(fs),'/', '--ro-bind',str(ROOT),'/work','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','PATH','/usr/sbin:/usr/bin:/sbin:/bin','--setenv','LC_ALL','C','--setenv','DEBIAN_FRONTEND','noninteractive','--chdir','/work']
user=['bwrap','--die-with-parent','--unshare-pid','--unshare-net','--ro-bind',str(fs),'/', '--ro-bind',str(ROOT),'/work','--bind',str(out),'/artifacts','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','HOME','/tmp/larsana-home','--setenv','XDG_CONFIG_HOME','/tmp/larsana-config','--setenv','XDG_DATA_HOME','/tmp/larsana-data','--setenv','XDG_STATE_HOME','/tmp/larsana-state','--setenv','XDG_RUNTIME_DIR','/tmp/larsana-run','--setenv','QT_QUICK_BACKEND','software','--chdir','/tmp']
def run(cmd):subprocess.run(base+cmd,check=True)
def install(reinstall=False):
 command=['apt-get','-o','Dir::Etc::sourcelist=/dev/null','-o','Dir::Etc::sourceparts=-','--yes','--no-install-recommends']
 if reinstall:command+=['--reinstall']
 run(command+['install','/work/.build/unified-artifacts/larsana_1.2.0_amd64.deb'])
def preserved():
 assert keep.read_text()=='preserve-database' and project.read_text()=='preserve-project'
 assert json.loads(settings.read_text())=={'mariadb':'11.8','php':'8.3'}
def desktop():
 result=subprocess.run(user+['/usr/bin/larsana','--doctor'],capture_output=True,text=True)
 assert result.returncode==0,result.stderr
 catalog=json.loads(result.stdout)['installed']
 assert len(catalog['php'])==5 and len(catalog['mariadb'])==4
 rendered=subprocess.run(user+['/usr/bin/xvfb-run','-a','/usr/bin/larsana','--screenshot','/artifacts/larsana-installed.png'],capture_output=True,text=True,timeout=60)
 assert rendered.returncode==0,rendered.stderr
 assert 'TypeError' not in rendered.stderr and 'Traceback' not in rendered.stderr,rendered.stderr
 print('PASS installed single-package launcher/catalog/GUI',flush=True)
install();preserved();desktop()
print('PASS clean installation from exactly one .deb',flush=True)
# The removal guard must reject an actual executable from this package.
guard="""import subprocess,time
child=subprocess.Popen(['/usr/lib/larsana/runtimes/php/8.5/bin/php','-r','sleep(30);'])
try:
 time.sleep(.3)
 result=subprocess.run(['dpkg','--remove','larsana'],capture_output=True,text=True)
 assert result.returncode!=0 and 'Stop and close LARSANA' in result.stderr,(result.returncode,result.stderr)
finally:child.terminate();child.wait()
print('PASS active runtime removal guard')
"""
run(['/usr/bin/python3','-c',guard])
run(['dpkg','--remove','larsana']);preserved()
# Upgrade the exact previous public unified installer too.
run(['apt-get','-o','Dir::Etc::sourcelist=/dev/null','-o','Dir::Etc::sourceparts=-','--yes','--no-install-recommends','install','/work/.build/release-history/larsana_0.2.0_amd64.deb'])
install();preserved();desktop()
assert (fs/'usr/lib/larsana/phpmyadmin/index.php').is_file()
assert '1.2.0' in (fs/'usr/lib/larsana/larsana/__init__.py').read_text()
print('PASS unified 0.2.0 -> 1.2.0 upgrade with phpMyAdmin and preserved data',flush=True)
run(['dpkg','--remove','larsana']);preserved()
old=sorted((origin/'dist').glob('*.deb'))
assert len(old)==13
run(['dpkg','--install']+['/work/'+str(p.relative_to(ROOT)) for p in old])
install();preserved();desktop()
status=subprocess.check_output(base+['dpkg-query','-W','-f=${binary:Package} ${db:Status-Status}\n'],text=True)
installed=[line.split()[0] for line in status.splitlines() if line.endswith(' installed') and line.startswith('larsana')]
assert installed==['larsana'],installed
print('PASS modular 0.1.1 -> one-package 1.2.0 migration; only larsana remains installed',flush=True)
install(reinstall=True);preserved()
print('PASS single-package reinstall',flush=True)
run(['dpkg','--purge','larsana']);preserved()
assert not (fs/'usr/lib/larsana').exists(),'Unowned files remain after purge'
print('PASS single-package purge and user data/preferences preservation',flush=True)
