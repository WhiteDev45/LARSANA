#!/usr/bin/env python3
"""Real phpMyAdmin cookie login, SQL UI, export/import on every MariaDB series."""
import http.cookiejar
import html
import os
import pwd
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
sys.path.insert(0, '/usr/lib/larsana')
from larsana.core import Manager

def get(opener, url, values=None):
    data = urllib.parse.urlencode(values).encode() if values is not None else None
    with opener.open(url, data, timeout=30) as response:
        body = response.read().decode()
        assert response.status == 200
        if 'text/html' in response.headers.get('Content-Type', ''):
            assert '<b>Fatal error</b>' not in body and 'Uncaught Error:' not in body, body[-2000:]
        return body

def token(body):
    match = re.search(r'name="token"\s+value="([^"]+)"', body)
    if not match: match = re.search(r'"token":"([^"]+)"', body)
    assert match, body[-2000:]
    return match[1]

m = Manager(); m.acquire()
with socket.socket() as s:
    s.bind(('127.0.0.1', 0)); m.settings['db_port'] = s.getsockname()[1]
try:
    for series in ['10.11', '11.8', '12.3', '13.0']:
        m.select('mariadb', series)
        # Project PHP remains independent, including newer versions.
        m.select('php', '8.5')
        url = m.open_database()
        assert m.open_database() == url
        assert m.settings['php'] == '8.5' and not m.running('web')
        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
        body = get(opener, url)
        assert 'phpMyAdmin' in body and 'input_username' in body
        for path in ['config.inc.php','vendor/autoload.php','libraries/config.default.php','setup/','sql/create_tables.sql','sessions/','%2e%2e/config.inc.php']:
            try: opener.open(url + path); raise AssertionError(path)
            except urllib.error.HTTPError as exc: assert exc.code == 404, (path, exc.code)
        body = get(opener, url + 'index.php?route=/', {'pma_username':'root','pma_password':'','server':'1','target':'index.php','token':token(body)})
        print('PASS phpMyAdmin root empty-password login',series,flush=True)
        assert 'input_username' not in body, body[-3000:]
        assert 'LARSANA MariaDB ' + series in body, body[-3000:]
        for asset in re.findall(r'<script[^>]+src="([^"]+)"', body):
            asset = urllib.parse.urljoin(url, html.unescape(asset))
            assert asset.startswith(url), asset
            try: get(opener, asset)
            except Exception as exc: raise AssertionError(asset) from exc
        assert 'var Messages =' in get(opener, url+'js/messages.php?l=en')
        print('PASS phpMyAdmin JavaScript assets and translations',series,flush=True)
        csrf = token(body)
        query = 'CREATE DATABASE IF NOT EXISTS pma_smoke; CREATE TABLE IF NOT EXISTS pma_smoke.probe (value INT); INSERT INTO pma_smoke.probe VALUES (120);'
        sql = get(opener, url+'index.php?route=/import', {'server':'1','token':csrf,'sql_query':query,'show_query':'1','ajax_request':'0'})
        client = m.catalog.executable('mariadb',series,'client')
        assert m._run([client,'--no-defaults',f'--socket={m.paths.run}/mariadb-{series}.sock','-N','-e','SELECT value FROM pma_smoke.probe']).strip() == '120', sql[-2000:]
        export = get(opener, url+'index.php?route=/export', {'server':'1','token':csrf,'db':'pma_smoke','export_type':'database','what':'sql','quick_or_custom':'quick','output_format':'sendit','compression':'none','table_select[]':'probe','table_structure[]':'probe','table_data[]':'probe','sql_type':'INSERT','sql_structure_or_data':'structure_and_data','sql_create_table':'1','sql_insert_syntax':'both','sql_backquotes':'1','filename_template':'@DATABASE@','charset':'utf-8'})
        assert 'CREATE TABLE' in export and 'INSERT INTO' in export and '120' in export, export[-2500:]
        m._run([client,'--no-defaults',f'--socket={m.paths.run}/mariadb-{series}.sock','-e','DROP TABLE pma_smoke.probe'])
        imported = get(opener, url+'index.php?route=/import', {'server':'1','token':csrf,'db':'pma_smoke','sql_query':export,'show_query':'1','ajax_request':'0'})
        assert m._run([client,'--no-defaults',f'--socket={m.paths.run}/mariadb-{series}.sock','-N','-e','SELECT value FROM pma_smoke.probe']).strip() == '120', imported[-2500:]
        print('PASS phpMyAdmin SQL export/import round trip',series,flush=True)
        print('PASS phpMyAdmin cookie login / SQL UI / protected paths / project PHP isolation',series,flush=True)
        m.stop('mariadb')
        assert not m.running('phpmyadmin')
        try: opener.open(url,timeout=1); raise AssertionError('phpMyAdmin survived DB stop')
        except urllib.error.URLError: pass
    print('PASS phpMyAdmin lifecycle and all four MariaDB versions',flush=True)
finally:
    m.close()
