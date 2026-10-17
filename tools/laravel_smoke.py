#!/usr/bin/env python3
"""Run actual Laravel 12 artisan migrations against every bundled MariaDB over TCP."""
from pathlib import Path
import json
import os
import shutil
import sys
sys.path.insert(0,'/usr/lib/larsana')
from larsana.core import Manager
project=Path('/tmp/laravel12')
shutil.copytree('/work/.build/laravel12-fixture',project)
(project/'.env').write_text('''APP_NAME=LarsanaTest
APP_ENV=testing
APP_KEY=base64:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=
APP_DEBUG=true
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel_access
DB_USERNAME=root
DB_PASSWORD=
CACHE_STORE=array
SESSION_DRIVER=array
QUEUE_CONNECTION=sync
''')
env=dict(os.environ)
for name in list(env):
    if name.startswith(('DB_','DATABASE_','APP_','CACHE_','SESSION_','QUEUE_')):env.pop(name)
m=Manager();m.acquire()
try:
    assert m.settings['db_port']==3306
    for database in m.catalog.installed('mariadb'):
        series=database['series'];m.select('mariadb',series);m.start_database()
        client=m.catalog.executable('mariadb',series,'client')
        m._run([client,'--no-defaults','--protocol=tcp','--skip-ssl','--host=127.0.0.1','--port=3306','--user=root','--password=','-e','CREATE DATABASE laravel_access'])
        for php in ['8.2','8.3','8.4','8.5']:
            binary=m.catalog.executable('php',php,'cli')
            args=[binary,'-n','-d','memory_limit=512M',str(project/'artisan')]
            m._run(args+['config:clear','--no-interaction'],cwd=project,env=env)
            output=m._run(args+['migrate:fresh','--force','--no-interaction'],cwd=project,env=env)
            assert 'DONE' in output,output
            m._run(args+['migrate:status','--no-interaction'],cwd=project,env=env)
            actual=m._run([client,'--no-defaults','--protocol=tcp','--skip-ssl','--host=127.0.0.1','--port=3306','--user=root','--password=','-N','-e','SELECT COUNT(*) FROM laravel_access.migrations']).strip()
            assert int(actual)>=3,actual
            print('PASS Laravel 12 artisan migrate via TCP root 3306 / MariaDB',series,'/ PHP',php,flush=True)
        m.stop('mariadb')
    lock=json.loads((project/'composer.lock').read_text())
    version=next(p['version'] for p in lock['packages'] if p['name']=='laravel/framework')
    print('PASS actual Laravel framework',version,'all four databases and PHP 8.2-8.5',flush=True)
finally:m.close()
