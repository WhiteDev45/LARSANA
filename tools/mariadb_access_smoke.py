#!/usr/bin/env python3
"""Test existing 1.2.0 data migration, TCP/PDO root login, defaults and credentials."""
import importlib.util
import json
from pathlib import Path
import os
import socket
import sys
sys.path.insert(0,'/usr/lib/larsana')
from larsana.core import Manager
spec=importlib.util.spec_from_file_location('legacy_core','/work/.build/legacy-1.2.0/larsana/core.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
# The old socket-only databases are genuine initialized 1.2.0 instances.
for series in ['10.11','11.8','12.3','13.0']:
    old=legacy.Manager();old.acquire()
    old.settings.pop('database_defaults_version',None)
    old.settings.update(mariadb=series,db_port=3307)
    old.save()
    try:
        old.start_database()
        client=old.catalog.executable('mariadb',series,'client')
        sock=old.paths.run/f'mariadb-{series}.sock'
        cli=[client,'--no-defaults',f'--socket={sock}','-N']
        old._run(cli+['-e','CREATE DATABASE access_test; CREATE TABLE access_test.saved(value INT); INSERT INTO access_test.saved VALUES(121);'])
    finally:old.close()
    m=Manager();m.acquire()
    try:
        assert m.settings['db_port']==3306
        m.start_database();m.save()
        tcp=[client,'--no-defaults','--protocol=tcp','--skip-ssl','--host=127.0.0.1','--port=3306','--user=root','--password=','-N']
        local=[client,'--no-defaults',f'--socket={sock}','--user=root','--password=','-N']
        for connection in [tcp,local]:
            actual=m._run(connection+['-e','SELECT value FROM access_test.saved']).strip()
            assert actual=='121',repr(actual)
            assert 'GRANT ALL PRIVILEGES' in m._run(connection+['-e','SHOW GRANTS'])
        assert m._run(tcp+['-e','SELECT @@port']).strip()=='3306'
        for php in m.catalog.installed('php'):
            program="$p=new PDO('mysql:host=127.0.0.1;port=3306;dbname=access_test','root',''); echo $p->query('SELECT value FROM saved')->fetchColumn();"
            assert m._run([m.catalog.executable('php',php['series'],'cli'),'-n','-r',program]).strip()=='121'
        print('PASS legacy 1.2.0 migration / TCP root / socket root / all five PHP PDO / port 3306 / preserved SQL',series,flush=True)
        # Authentication is not reset on restart, even if the local marker is absent.
        for connection,host in [(tcp,'127.0.0.1'),(local,'localhost')]:
            m._run(connection+['-e',f"ALTER USER 'root'@'{host}' IDENTIFIED BY 'test-preserved-121';"])
        marker=m.paths.data/'mariadb'/series/'.larsana-local-root-v1.json'
        m.stop('mariadb');marker.unlink();m.start_database()
        for connection in [tcp,local]:
            with_password=[arg if arg!='--password=' else '--password=test-preserved-121' for arg in connection]
            assert m._run(with_password+['-e','SELECT value FROM access_test.saved']).strip()=='121'
        m.stop('mariadb');m.start_database()
        assert m._run(with_password+['-e','SELECT value FROM access_test.saved']).strip()=='121'
        print('PASS existing root passwords survive bootstrap retry and restart',series,flush=True)
        m.stop('mariadb')
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(('127.0.0.1',3306));listener.listen()
            try:m.start_database();raise AssertionError('Occupied port accepted')
            except RuntimeError as exc:assert '3306 sedang dipakai' in str(exc),str(exc)
        print('PASS occupied 3306 rejected without fallback or stopping other services',series,flush=True)
    finally:m.close()
print('PASS MariaDB access migration acceptance matrix',flush=True)
