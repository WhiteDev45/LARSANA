#!/usr/bin/env python3
"""Publish evidence only after every local release validation has completed."""
import json
from pathlib import Path
import shutil
from target_info import target_info
ROOT=Path(__file__).resolve().parents[1]
lock=json.loads((ROOT/'runtimes/sources.lock.json').read_text())
checks={
 'unit-final.log':['20 passed'],
 'smoke-final.log':['PASS live PHP switching','PASS DB persistence/PDO/backup/restore 13.0.2'],
 'gui-smoke-final.log':['PASS desktop Start All','PASS desktop Stop All','no QML warnings'],
 'lifecycle-final.log':['PASS installed launcher','PASS constrained .test helper','PASS package lifecycle upgrade','PASS package lifecycle purge','Lifecycle test passed'],
 'check-packages-final.log':['PASS artifact larsana-php-8.1','PASS artifact larsana-mariadb-13.0'],
 'lintian-final.log':['PASS lintian final'],
 'offline-verification.log':['PASS signed APT repository and offline dependency closure'],
}
checks['smoke-final.log'] += ['PASS DB persistence/PDO/backup/restore '+i['version'] for i in lock['sources'] if i['kind']=='mariadb']
checks['check-packages-final.log'] += ['PASS artifact larsana-'+i['id'] for i in lock['sources']]
checks['lintian-final.log'] += ['PASS lintian LARSANA 0.1.1 and MariaDB 11.8']
checks['lifecycle-final.log'] += ['PASS upgrade from previous release 0.1.0 to 0.1.1 with MariaDB 11.8']
checks['gui-smoke-final.log'] += ['PASS desktop MariaDB 11.8 selector']
out=ROOT/'dist/validation';out.mkdir(exist_ok=True)
summary={'version':'0.1.1','target':target_info(ROOT),'checks':{}}
for name,markers in checks.items():
 file=ROOT/'.build'/name
 value=file.read_text()
 for marker in markers:
  if marker not in value:raise RuntimeError(f'Missing success evidence {marker!r} in {file}')
 if 'Traceback (most recent call last)' in value or 'TypeError:' in value:
  raise RuntimeError('Validation log contains an error: '+str(file))
 if name=='lintian-final.log' and any(line.startswith('E: ') for line in value.splitlines()):
  raise RuntimeError('Lintian errors remain')
 shutil.copy2(file,out/name)
 summary['checks'][name]={'result':'pass','warnings':sum(line.startswith('W: ') for line in value.splitlines())}
(out/'results.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS all local release checks:',summary['target']['suite'])
