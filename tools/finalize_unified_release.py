#!/usr/bin/env python3
"""Release one installer only after identical-payload and cross-suite checks pass."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'.build';STAGE=BUILD/'unified-stage'
VERSION='1.2.0'
package=BUILD/'unified-artifacts'/f'larsana_{VERSION}_amd64.deb'
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
before=json.loads((BUILD/'unified-functional-before.json').read_text())
assert all(sha(STAGE/name)==digest for name,digest in before.items()),'Functional payload changed since integration tests'
logs={}
for suite in ['noble','trixie']:
 for kind,markers in {
  'smoke':['PASS live PHP switching','PASS DB persistence/PDO/backup/restore 11.8.9','PASS DB persistence/PDO/backup/restore 13.0.2'],
  'phpmyadmin':['PASS phpMyAdmin lifecycle and all four MariaDB versions','PASS phpMyAdmin SQL export/import round trip 11.8','PASS phpMyAdmin JavaScript assets and translations 13.0'],
  'gui':['PASS desktop phpMyAdmin button opens selected database','PASS desktop MariaDB 11.8 selector','PASS desktop Stop All','no QML warnings'],
  'elf':['PASS native ELF dependency resolution 496'],
  'crypto':['PASS private ICU/JPEG/cURL TLS 8.1.34','PASS private ICU/JPEG/cURL TLS 8.5.11'],
  'unit':['20 passed'],
  'install':['PASS clean installation from exactly one .deb','PASS active runtime removal guard','PASS modular 0.1.1 -> one-package 1.2.0 migration; only larsana remains installed','PASS unified 0.2.0 -> 1.2.0 upgrade with phpMyAdmin and preserved data','PASS single-package reinstall','PASS single-package purge and user data/preferences preservation'],
 }.items():
  file=BUILD/f'unified-{suite}-{kind}.log';value=file.read_text()
  assert all(s in value for s in markers),file
  assert 'Traceback (most recent call last)' not in value and 'TypeError:' not in value,file
  logs[file.name]=sha(file)
file=BUILD/'unified-lintian.log';value=file.read_text()
assert 'PASS lintian unified package' in value and not any(line.startswith('E: ') for line in value.splitlines()),value
lintian_exceptions=json.loads((ROOT/'packaging/phpmyadmin-lintian-allowlist.json').read_text())
assert sorted(line for line in value.splitlines() if line.startswith('W: '))==sorted(lintian_exceptions['warnings']),value
logs[file.name]=sha(file)
payload_check=BUILD/'unified-payload-check-1.2.log'
assert 'PASS packaged application/runtime/phpMyAdmin match tested payload 7737 files' in payload_check.read_text()
logs[payload_check.name]=sha(payload_check)
for name,marker in {
 'unified-notice-identity.log':'PASS control and maintainer scripts identical to installation-tested package',
 'unified-notice-lintian.log':'PASS final notice/control/md5/package-format lintian checks',
 'unified-notice-repack-1.2.log':'PASS notice-only debhelper repack',
}.items():
 file=BUILD/name;value=file.read_text()
 assert marker in value and 'Traceback' not in value and not any(line.startswith(('E: ','W: ')) for line in value.splitlines()),name
 logs[name]=sha(file)
integration_package=json.loads((BUILD/'unified-integration-package.json').read_text())
notice_proof=json.loads((BUILD/'unified-notice-proof.json').read_text())
assert notice_proof['installation_tested_sha256']==integration_package['sha256']
assert notice_proof['final_sha256']==sha(package)
logs['unified-notice-proof.json']=sha(BUILD/'unified-notice-proof.json')
source_manifest=BUILD/'compat-sources/manifest.json';sources=json.loads(source_manifest.read_text())
for item in sources['files']:assert sha(source_manifest.parent/item['file'])==item['sha256'],item['file']
info=subprocess.check_output(['dpkg-deb','-f',str(package)],text=True)
assert 'Package: larsana\n' in info and f'Version: {VERSION}\n' in info
assert 'larsana-' not in next(s for s in info.splitlines() if s.startswith('Depends: '))
expected={'./usr/lib/larsana/larsana/'+name:(ROOT/'src/larsana'/name).read_bytes() for name in ['__init__.py','core.py','gui.py','qml/Main.qml','phpmyadmin-router.php']}
seen=set();runtime_count=0
proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(package)],stdout=subprocess.PIPE)
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for member in tar:
  assert not member.name.endswith('.deb'),'Nested component package found'
  if member.name.endswith('/runtime.json'):runtime_count+=1
  if member.name in expected:
   assert tar.extractfile(member).read()==expected[member.name],member.name
   seen.add(member.name)
assert proc.wait()==0
assert seen==set(expected) and runtime_count==11
validation=ROOT/'dist/unified-validation';validation.mkdir(exist_ok=True)
for name in logs:shutil.copy2(BUILD/name,validation/name)
for suite in ['noble','trixie']:
 dest=validation/suite;dest.mkdir(exist_ok=True)
 for file in (BUILD/'unified-tests'/suite).iterdir():
  if file.is_file():shutil.copy2(file,dest/file.name)
report={'version':VERSION,'installer':package.name,'sha256':sha(package),'bytes':package.stat().st_size,'targets':['Ubuntu 24.04 amd64','Linux Mint 22.x amd64','Debian 13 amd64'],'same_binary_for_all_targets':True,'runtime_count':11,'private_library_count':72,'corresponding_distro_source_packages':len(sources['sources']),'checks':logs,'functional_payload_matches_integration_tests':True,'phpmyadmin_version':'5.2.3','lintian_reviewed_warnings':lintian_exceptions,'installation_tested_package_sha256':integration_package['sha256'],'final_changes_after_integration':'Exactly five documentation/license files; functional files, permissions, symlinks, control and maintainer scripts identical. Final documentation/control/md5/package-format lintian checks repeated.','limits':['No full desktop VM/reboot/native Polkit-agent verification','Other distro releases and arm64 unverified','APT may download missing system desktop dependencies']}
(validation/'results.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copy2(ROOT/'docs/UNIFIED_PACKAGE.md',validation/'BUILD_REPORT.md')
# Corresponding source is separate from the one-file installer, and optional to install.
source_dir=ROOT/'dist/unified-sources';source_dir.mkdir(exist_ok=True)
compat=source_dir/'compat';compat.mkdir(exist_ok=True)
for item in sources['files']:shutil.copy2(source_manifest.parent/item['file'],compat/item['file'])
shutil.copy2(source_manifest,compat/'manifest.json')
shutil.copytree(ROOT/'dist/upstream-sources',source_dir/'upstream',dirs_exist_ok=True)
pma=json.loads((ROOT/'runtimes/phpmyadmin.lock.json').read_text())
for field,checksum in [('archive','sha256'),('source_archive','source_sha256')]:
 file=BUILD/'phpmyadmin'/pma[field]
 assert sha(file)==pma[checksum]
 shutil.copy2(file,source_dir/'upstream'/file.name)
with tarfile.open(source_dir/f'larsana-source-{VERSION}.tar.gz','w:gz') as tar:
 for name in ['src','tools','tests','packaging','runtimes','docs','.github','.gitignore','README.md','CONTRIBUTING.md','LICENSE','pyproject.toml']:
  tar.add(ROOT/name,arcname=f'larsana-{VERSION}/'+name,filter=lambda member:None if '__pycache__' in member.name else member)
(source_dir/'SHA256SUMS').write_text(''.join(sha(p)+'  '+str(p.relative_to(source_dir))+'\n' for p in sorted(source_dir.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
release=ROOT/'releases';release.mkdir(exist_ok=True)
for old in release.iterdir():
 if old.name==package.name:continue
 assert old.is_file() and old.suffix=='.deb',old
 history=BUILD/'release-history';history.mkdir(exist_ok=True)
 saved=history/old.name
 if saved.exists():
  assert sha(saved)==sha(old)
  old.unlink()
 else:shutil.move(old,saved)
shutil.copy2(package,release/package.name)
assert sha(release/package.name)==report['sha256']
assert len(list(release.iterdir()))==1
print('PASS released exactly ONE installer:',release/package.name)
print('SHA256',report['sha256'])
print('Verified same payload on noble and trixie; source and validation under dist/unified-*')
