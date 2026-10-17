#!/usr/bin/env python3
"""Validate cross-suite results, package identity and corresponding source; release one .deb."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.build';STAGE=BUILD/'unified-stage'
VERSION=re.search(r'__version__ = "([^"]+)"',(ROOT/'src/larsana/__init__.py').read_text())[1]
package=BUILD/'unified-artifacts'/f'larsana_{VERSION}_amd64.deb'
def sha(file):
 with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
manifest=json.loads((BUILD/f'release-{VERSION}-functional.json').read_text())
assert all(sha(STAGE/name)==digest for name,digest in manifest.items()),'Tested functional payload changed'
checks={
 'smoke':['PASS live PHP switching','PASS DB persistence/PDO/backup/restore 11.8.9','PASS DB persistence/PDO/backup/restore 13.0.2'],
 'phpmyadmin':['PASS phpMyAdmin lifecycle and all four MariaDB versions','PASS phpMyAdmin root empty-password login 11.8','PASS phpMyAdmin SQL export/import round trip 13.0'],
 'access':['PASS MariaDB access migration acceptance matrix','PASS legacy 1.2.0 migration / TCP root / socket root / all five PHP PDO / port 3306 / preserved SQL 11.8','PASS existing root passwords survive bootstrap retry and restart 13.0'],
 'laravel':['PASS actual Laravel framework','all four databases and PHP 8.2-8.5'],
 'gui':['PASS desktop root login guidance updated','PASS desktop MariaDB 11.8 selector','PASS desktop Stop All','no QML warnings'],
 'elf':['PASS native ELF dependency resolution 496'],
 'crypto':['PASS private ICU/JPEG/cURL TLS 8.1.34','PASS private ICU/JPEG/cURL TLS 8.5.11'],
 'unit':['28 passed'],
 'web':['PASS apache MIME js/mjs/PDF.js worker','PASS nginx MIME js/mjs/PDF.js worker','PASS nginx 10 actual reloads / 360 concurrent HTTP responses','PASS Nginx master/workers and PHP exit after owner crash'],
 'install':['PASS actual candidate clean APT installation','PASS actual 1.2.1 -> candidate APT upgrade','PASS candidate reinstall/purge preserves custom configuration'],
}
logs={}
for suite in ['noble','trixie']:
 for kind,markers in checks.items():
  file=BUILD/f'release-{VERSION}-{suite}-{kind}.log';value=file.read_text()
  assert all(marker in value for marker in markers),str(file)
  assert 'Traceback (most recent call last)' not in value and 'TypeError:' not in value,str(file)
  logs[file.name]=sha(file)
file=BUILD/f'release-{VERSION}-lintian.log';value=file.read_text()
assert 'PASS lintian unified package' in value and not any(line.startswith('E: ') for line in value.splitlines()),value
exceptions=json.loads((ROOT/'packaging/phpmyadmin-lintian-allowlist.json').read_text())
assert sorted(line for line in value.splitlines() if line.startswith('W: '))==sorted(exceptions['warnings']),value
logs[file.name]=sha(file)
control=subprocess.check_output(['dpkg-deb','-f',str(package)],text=True)
assert f'Version: {VERSION}\n' in control and 'Package: larsana\n' in control
assert 'larsana-' not in next(line for line in control.splitlines() if line.startswith('Depends: '))
expected={name:digest for name,digest in manifest.items() if name.startswith('usr/lib/larsana/')}
seen=set();runtime_count=0
proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(package)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for member in tar:
  name=member.name.removeprefix('./')
  assert not name.endswith('.deb'),'Nested package'
  if name.endswith('/runtime.json'):runtime_count+=1
  if member.isfile() and name in expected:
   assert hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest()==expected[name],name
   seen.add(name)
assert proc.wait()==0 and seen==set(expected) and runtime_count==11
print('PASS packaged application/runtime/phpMyAdmin match tested payload',len(seen),'files',flush=True)
source_manifest=BUILD/'compat-sources/manifest.json';sources=json.loads(source_manifest.read_text())
for item in sources['files']:assert sha(source_manifest.parent/item['file'])==item['sha256']
validation=ROOT/'dist/unified-validation';validation.mkdir(exist_ok=True)
for name in logs:shutil.copy2(BUILD/name,validation/name)
for suite in ['noble','trixie']:
 dest=validation/suite;dest.mkdir(exist_ok=True)
 for file in (BUILD/'unified-tests'/suite).iterdir():
  if file.is_file():shutil.copy2(file,dest/file.name)
report={'version':VERSION,'installer':package.name,'sha256':sha(package),'bytes':package.stat().st_size,'targets':['Ubuntu 24.04 amd64','Linux Mint 22.x amd64','Debian 13 amd64'],'same_binary_for_all_targets':True,'runtime_count':runtime_count,'functional_files_verified':len(seen),'checks':logs,'db_default_port':3306,'db_default_user':'root','phpmyadmin_version':'5.2.3','lintian_reviewed_warnings':exceptions,'limits':['No full desktop VM/reboot/native Polkit-agent verification','Other distro releases and arm64 unverified','APT may download missing OS libraries','Existing custom ports and account passwords preserved']}
(validation/'results.json').write_text(json.dumps(report,indent=2)+'\n')
# A separate corresponding-source asset is optional to install, provided with binaries.
source_dir=ROOT/'dist'/f'sources-{VERSION}';source_dir.mkdir(exist_ok=True)
compat=source_dir/'compat';compat.mkdir(exist_ok=True)
for item in sources['files']:shutil.copy2(source_manifest.parent/item['file'],compat/item['file'])
shutil.copy2(source_manifest,compat/'manifest.json')
shutil.copytree(ROOT/'dist/upstream-sources',source_dir/'upstream',dirs_exist_ok=True)
pma=json.loads((ROOT/'runtimes/phpmyadmin.lock.json').read_text())
for field,checksum in [('archive','sha256'),('source_archive','source_sha256')]:
 file=BUILD/'phpmyadmin'/pma[field];assert sha(file)==pma[checksum]
 shutil.copy2(file,source_dir/'upstream'/file.name)
with tarfile.open(source_dir/f'larsana-source-{VERSION}.tar.gz','w:gz') as tar:
 for name in ['src','tools','tests','packaging','runtimes','.github','.gitignore','README.md','README.id.md','CONTRIBUTING.md','LICENSE','pyproject.toml']:
  tar.add(ROOT/name,arcname=f'larsana-{VERSION}/'+name,filter=lambda member:None if '__pycache__' in member.name else member)
(source_dir/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(source_dir))+'\n' for p in sorted(source_dir.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
release=ROOT/'releases';release.mkdir(exist_ok=True)
for old in release.iterdir():
 if old.name==package.name:continue
 assert old.is_file() and old.suffix=='.deb',old
 history=BUILD/'release-history';history.mkdir(exist_ok=True)
 saved=history/old.name
 if saved.exists():
  assert sha(saved)==sha(old);old.unlink()
 else:shutil.move(old,saved)
shutil.copy2(package,release/package.name)
assert sha(release/package.name)==report['sha256'] and len(list(release.iterdir()))==1
print('PASS released exactly ONE installer:',release/package.name,flush=True)
print('SHA256',report['sha256'],flush=True)
