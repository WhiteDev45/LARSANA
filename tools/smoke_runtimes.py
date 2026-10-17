#!/usr/bin/env python3
"""Run inside builder with private /tmp HOME. Exercises real servers and DBs."""
import json
import os
from pathlib import Path
import socket
import sys
import urllib.request
import urllib.error
sys.path.insert(0,'/work/src')
from larsana.core import Manager

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]

m=Manager();m.acquire()
m.settings.update(root='/tmp/larsana-projects',port=free_port(),db_port=free_port())
result=[]
try:
    m.prepare_root()
    (m.root/'probe.php').write_text("<?php header('Content-Type: application/json'); echo json_encode(['version'=>PHP_VERSION, 'modules'=>get_loaded_extensions()]);")
    (m.root/'.git').mkdir(exist_ok=True)
    (m.root/'.git/config').write_text('private fixture')
    for php in m.catalog.installed('php'):
        m.select('php',php['series'])
        cli=m._run([m.catalog.executable('php',php['series'],'cli'),'-r','echo PHP_VERSION;'])
        assert cli.strip()==php['version'],cli
        for web in ('apache','nginx'):
            if not m.catalog.installed(web):continue
            m.select('web',web)
            m.start_web()
            with urllib.request.urlopen(f"http://localhost:{m.settings['port']}/probe.php") as response:
                probe=json.load(response)
            assert probe['version']==php['version'],probe
            try:
                urllib.request.urlopen(f"http://localhost:{m.settings['port']}/.git/config")
                raise AssertionError('Hidden project metadata was exposed')
            except urllib.error.HTTPError as denied:
                assert denied.code in (403,404),denied.code
            expected={'mysqli','pdo_mysql','mbstring','intl','curl','zip','gd','bcmath','sockets','openssl','dom','xml','fileinfo','Zend OPcache'}
            missing=expected-set(probe['modules'])
            assert not missing,missing
            print('PASS HTTP/FPM',web,php['version'],flush=True)
            result.append({'web':web,'php':php['version'],'extensions':'passed'})
            m.stop('web');m.stop('php')
    installed=m.catalog.installed('php')
    if len(installed)>1:
        m.select('web','nginx');m.select('php',installed[0]['series']);m.start_web()
        for item in installed[1:]+installed[:1]:
            m.select('php',item['series'])
            with urllib.request.urlopen(f"http://localhost:{m.settings['port']}/probe.php") as r:assert json.load(r)['version']==item['version']
        print('PASS live PHP switching',flush=True)
        m.stop('web');m.stop('php')
    for database in m.catalog.installed('mariadb'):
        m.select('mariadb',database['series']);m.start_database()
        client=m.catalog.executable('mariadb',database['series'],'client')
        sock=m.paths.run/f"mariadb-{database['series']}.sock"
        args=[client,'--no-defaults',f'--socket={sock}','--batch','--skip-column-names']
        actual_version=m._run(args+['-e','SELECT VERSION();']).strip()
        assert actual_version.split('-',1)[0]==database['version'],actual_version
        m._run(args+['-e','CREATE DATABASE IF NOT EXISTS larsana_smoke; CREATE TABLE IF NOT EXISTS larsana_smoke.checks (value INT); INSERT INTO larsana_smoke.checks VALUES (42);'])
        m.stop('mariadb');m.start_database()
        assert m._run(args+['-e','SELECT value FROM larsana_smoke.checks;']).strip()=='42'
        # A PHP request performs an actual socket-authenticated database connection.
        series=m.settings['php']
        (m.root/'db.php').write_text("<?php $db=new PDO('mysql:unix_socket="+str(sock)+";dbname=larsana_smoke',get_current_user(),''); echo $db->query('SELECT value FROM checks')->fetchColumn();")
        m.start_web()
        with urllib.request.urlopen(f"http://localhost:{m.settings['port']}/db.php") as r:assert r.read()==b'42'
        m.stop('web');m.stop('php')
        dump=m.catalog.executable('mariadb',database['series'],'client').replace('/mariadb','/mariadb-dump')
        # replace only final basename (prefix contains mariadb too).
        dump=str(Path(client).with_name('mariadb-dump'))
        backup=m._run([dump,'--no-defaults',f'--socket={sock}','larsana_smoke'])
        m._run(args+['-e','DROP TABLE larsana_smoke.checks;'])
        m._run(args+['larsana_smoke'],input=backup)
        assert m._run(args+['-e','SELECT value FROM larsana_smoke.checks;']).strip()=='42'
        print('PASS DB persistence/PDO/backup/restore',database['version'],flush=True)
        result.append({'mariadb':database['version'],'server_version':actual_version,'persistence':'passed','pdo':'passed','backup_restore':'passed'})
        m.stop('mariadb')
    Path('/work/dist/runtime-test-results.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
    m.close()
