#!/usr/bin/env python3
"""Gate 1.2.3 publication on recorded cross-distro tests and archive its sources."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[1];BUILD=ROOT/'.build';VERSION='1.2.3'
package=BUILD/'unified-artifacts'/f'larsana_{VERSION}_amd64.deb'
def sha(file):
 with file.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
checks={
 'web':['PASS apache MIME','PASS nginx MIME','PASS Nginx master/workers'],
 'smoke':['PASS HTTP/FPM apache 8.1.34','PASS HTTP/FPM nginx 8.5.11','PASS live PHP switching','PASS DB persistence/PDO/backup/restore 13.0.2'],
 'elf':['PASS native ELF dependency resolution 496'],
 'crypto':['PASS private ICU/JPEG/cURL TLS 8.1.34','PASS private ICU/JPEG/cURL TLS 8.5.11'],
 'install':['PASS actual candidate clean APT installation','PASS actual previous -> candidate APT upgrade','PASS candidate reinstall/purge','TESTED'],
 'gui':['PASS desktop upgrade uses fresh QML cache','PASS desktop Stop All','no QML warnings'],
 'phpmyadmin':['PASS phpMyAdmin lifecycle and all four MariaDB versions'],
}
logs={}
for target in ['noble','trixie','resolute']:
 for kind,markers in checks.items():
  file=BUILD/f'release-{VERSION}-{target}-{kind}.log';value=file.read_text()
  assert all(m in value for m in markers),file
  assert 'Traceback (most recent call last)' not in value,file
  if kind=='install':assert sha(package) in value,file
  logs[file.name]=sha(file)
for kind,marker in [('unit','30 passed'),('guard','PASS installer guard'),('lintian','PASS lintian')]:
 file=BUILD/f'release-{VERSION}-{kind}.log';assert marker in file.read_text(),file;logs[file.name]=sha(file)
 if kind=='lintian':assert sha(package) in file.read_text()
file=BUILD/f'release-{VERSION}-resolute-unit.log';assert '30 passed' in file.read_text();logs[file.name]=sha(file)
# Application files in the exact tested installer must match this source tree.
proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(package)],stdout=subprocess.PIPE)
seen=set();runtimes=0
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for member in tar:
  name=member.name.removeprefix('./')
  assert not name.endswith('.deb'),'Nested installer'
  if name.endswith('/runtime.json'):runtimes+=1
  prefix='usr/lib/larsana/larsana/'
  if member.isfile() and name.startswith(prefix):
   rel=name[len(prefix):];source=ROOT/'src/larsana'/rel
   assert sha(source)==hashlib.file_digest(tar.extractfile(member),'sha256').hexdigest(),rel
   seen.add(rel)
assert proc.wait()==0 and runtimes==11
expected={str(p.relative_to(ROOT/'src/larsana')) for p in (ROOT/'src/larsana').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert expected==seen
out=ROOT/'dist/release-1.2.3';out.mkdir(exist_ok=True)
validation=out/'validation';validation.mkdir(exist_ok=True)
for name in logs:shutil.copy2(BUILD/name,validation/name)
report={'version':VERSION,'installer':package.name,'sha256':sha(package),'same_installer_all_targets':True,'runtime_count':runtimes,'tests':logs,'tested_bases':['Ubuntu 24.04 noble','Ubuntu 26.04 resolute','Debian 13 trixie'],'fixtures_only':['Mint Ubuntu-base detection','Ubuntu 24.10/25.04/25.10 installer guard'],'limits':['No native Mint desktop VM','No full desktop reboot/tray/Polkit-agent verification','No ARM64','Debian releases newer than 13 not runtime-tested']}
(validation/'results.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open(out/f'larsana-validation-{VERSION}.tar.gz','w:gz') as tar:tar.add(validation,arcname='validation')
source=out/'sources';source.mkdir(exist_ok=True)
previous=ROOT/'dist/sources-1.2.2'
for line in (previous/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1)
 assert sha(previous/name)==digest,name
# The runtime/Qt/phpMyAdmin payload is unchanged; reuse corresponding upstream
# source archives from 1.2.2, while replacing the application source snapshot.
for folder in ['compat','upstream']:shutil.copytree(ROOT/'dist/sources-1.2.2'/folder,source/folder,dirs_exist_ok=True)
with tarfile.open(source/f'larsana-source-{VERSION}.tar.gz','w:gz') as tar:
 for name in ['src','tools','tests','packaging','runtimes','.github','.gitignore','README.md','README.id.md','RELEASE-1.2.3.md','CONTRIBUTING.md','LICENSE','pyproject.toml']:
  tar.add(ROOT/name,arcname=f'larsana-{VERSION}/'+name,filter=lambda m:None if '__pycache__' in m.name else m)
(source/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(source)}\n' for p in sorted(source.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
with tarfile.open(out/f'larsana-corresponding-source-{VERSION}.tar','w') as tar:tar.add(source,arcname='sources')
shutil.copy2(package,out/package.name)
shutil.copy2(ROOT/'RELEASE-1.2.3.md',out/'RELEASE-1.2.3.md')
(out/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
release=ROOT/'releases';history=BUILD/'release-history';history.mkdir(exist_ok=True)
for old in release.glob('*.deb'):
 if old.name==package.name:continue
 dest=history/old.name
 if dest.exists():assert sha(old)==sha(dest);old.unlink()
 else:shutil.move(old,dest)
shutil.copy2(package,release/package.name)
print('PASS validated ONE installer, matching application source, corresponding sources and checksums',sha(package),flush=True)
