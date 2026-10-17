#!/usr/bin/env python3
"""Install/upgrade the candidate .deb in disposable rootless target filesystems."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--target',choices=['noble','trixie'],required=True)
p.add_argument('--package',type=Path,required=True)
p.add_argument('--previous',type=Path,help='Previous public 1.2.1 installer for the upgrade fixture')
args=p.parse_args()
package=args.package.resolve()
previous=args.previous.resolve() if args.previous else next((file for file in [ROOT/'releases/larsana_1.2.1_amd64.deb',ROOT/'.build/release-history/larsana_1.2.1_amd64.deb'] if file.exists()),None)
assert previous is not None and previous.is_file(),'Provide the previous installer with --previous'
version=subprocess.check_output(['dpkg-deb','-f',str(package),'Version'],text=True).strip()
fs=ROOT/'.build/unified-install'/args.target
assert (fs/'usr/bin/apt-get').exists(),'Prepare isolated APT installation filesystem first'
assert not (fs/'usr/lib/larsana').exists(),'Disposable installation must start purged'
base=['bwrap','--die-with-parent','--unshare-user','--uid','0','--gid','0','--unshare-pid','--unshare-net','--bind',str(fs),'/', '--ro-bind',str(ROOT),'/work','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','PATH','/usr/sbin:/usr/bin:/sbin:/bin','--setenv','LC_ALL','C','--setenv','DEBIAN_FRONTEND','noninteractive','--chdir','/work']
out=ROOT/'.build/webfix-installed'/args.target;out.mkdir(parents=True,exist_ok=True)
user=['bwrap','--die-with-parent','--unshare-pid','--unshare-net','--ro-bind',str(fs),'/', '--ro-bind',str(ROOT),'/work','--bind',str(out),'/artifacts','--dev','/dev','--proc','/proc','--tmpfs','/tmp','--setenv','HOME','/tmp/test-home','--setenv','XDG_CONFIG_HOME','/tmp/test-config','--setenv','XDG_DATA_HOME','/tmp/test-data','--setenv','XDG_STATE_HOME','/tmp/test-state','--setenv','XDG_RUNTIME_DIR','/tmp/test-run','--setenv','QT_QUICK_BACKEND','software','--setenv','PYTHONPATH','/usr/lib/larsana/python','--chdir','/work']
def run(cmd):subprocess.run(base+cmd,check=True)
def install(file,reinstall=False):
    run(['apt-get','-o','Dir::Etc::sourcelist=/dev/null','-o','Dir::Etc::sourceparts=-','--yes','--no-install-recommends']+(['--reinstall'] if reinstall else [])+['install','/work/'+str(file.relative_to(ROOT))])
home=fs/'home/builder'
extra=home/'.config/larsana/nginx-extra.conf'
extra.parent.mkdir(parents=True,exist_ok=True)
custom=b'# Existing workaround, kept byte for byte during upgrade.\ntypes { application/javascript mjs; }\n'
extra.write_bytes(custom)
settings=extra.with_name('settings.json')
settings.write_text('{"web":"nginx","php":"8.5","mariadb":"11.8","root":"/home/builder/Larsana/www","database_defaults_version":1}')
project=home/'Larsana/www/keep/index.php';project.parent.mkdir(parents=True,exist_ok=True);project.write_text('preserve-project')
db=home/'.local/share/larsana/mariadb/11.8/keep.sql';db.parent.mkdir(parents=True,exist_ok=True);db.write_text('preserve-database')
original_settings=settings.read_bytes()
def preserved():
    assert extra.read_bytes()==custom and settings.read_bytes()==original_settings
    assert project.read_text()=='preserve-project' and db.read_text()=='preserve-database'

install(package);preserved()
actual=subprocess.check_output(base+['dpkg-query','-W','-f=${Version}','larsana'],text=True)
assert actual==version,(actual,version)
subprocess.run(user+['/usr/bin/python3','tools/web_regression.py'],check=True)
subprocess.run(user+['/usr/bin/xvfb-run','-a','/usr/bin/larsana','--screenshot','/artifacts/installed-candidate.png'],check=True,timeout=90)
print('PASS actual candidate clean APT installation, installed Apache/Nginx HTTP regressions and GUI',flush=True)
run(['dpkg','--remove','larsana']);preserved()
install(previous);preserved()
install(package);preserved()

# Mount the pre-existing user configuration from the disposable test filesystem.
# Generated configuration may be written; user settings/extra bytes must survive.
# This checks the exact workaround surviving APT upgrade, not a freshly written one.
upgrade_code='''import sys,socket,http.client
from pathlib import Path
sys.path.insert(0,'/usr/lib/larsana')
from larsana.core import Manager
m=Manager();m.acquire()
try:
 with socket.socket() as s:s.bind(('127.0.0.1',0));m.settings['port']=s.getsockname()[1]
 m.settings['root']='/tmp/upgrade-project'
 m.prepare_root()
 for name in ['app.js','pdf.mjs','pdf.worker.mjs']:(m.root/name).write_text('export const ok=true;')
 extra=m.paths.config/'nginx-extra.conf';before=extra.read_bytes()
 m.start_web()
 assert 'duplicate extension' not in m.validate_web(*m.render_web())
 for name in ['app.js','pdf.mjs','pdf.worker.mjs']:
  conn=http.client.HTTPConnection('127.0.0.1',m.settings['port']);conn.request('GET','/'+name)
  r=conn.getresponse();assert r.status==200 and r.getheader('Content-Type') in ('application/javascript','text/javascript');r.read();conn.close()
 assert extra.read_bytes()==before
 print('PASS actual 1.2.1 -> candidate APT upgrade; existing MIME workaround preserved, no duplicates, real js/mjs/worker HTTP')
finally:m.close()
'''
subprocess.run(user+['--bind',str(home/'.config/larsana'),'/tmp/test-config/larsana','/usr/bin/python3','-c',upgrade_code],check=True)
preserved();install(package,reinstall=True);preserved()
run(['dpkg','--purge','larsana']);preserved()
assert not (fs/'usr/lib/larsana').exists()
print('PASS candidate reinstall/purge preserves custom configuration, project and database fixtures',flush=True)
print('TESTED',args.target,version,hashlib.sha256(package.read_bytes()).hexdigest(),flush=True)
