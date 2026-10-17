#!/usr/bin/env python3
"""Real HTTP regressions for the isolated Apache/Nginx package payload."""
import concurrent.futures
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
sys.path.insert(0, '/work/src' if os.environ.get('LARSANA_TEST_SOURCE') else '/usr/lib/larsana')
from larsana.core import Manager, port_available, quote

m=Manager();m.acquire()
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
m.settings.update(root='/tmp/web-projects',port=port)

def request(path, method='GET', headers=None):
    conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        conn.request(method,path,headers={'Host':'aksara.localhost',**(headers or {})})
        r=conn.getresponse();return r.status,dict((k.lower(),v) for k,v in r.getheaders()),r.read()
    finally:conn.close()

def check_assets():
    for path,types in [('app.js',('application/javascript','text/javascript')),('pdfjs/pdf.mjs',('application/javascript','text/javascript')),('pdfjs/pdf.worker.mjs',('application/javascript','text/javascript')),('style.css',('text/css',)),('sample.pdf',('application/pdf',)),('probe.wasm',('application/wasm',)),('probe.json',('application/json',)),('logo.svg',('image/svg+xml',)),('font.woff2',('font/woff2',))]:
        status,headers,body=request('/assets/'+path)
        assert status==200 and headers.get('content-type','').split(';')[0] in types,(path,status,headers)
        assert body==(public/'assets'/path).read_bytes(),path
    status,headers,body=request('/assets/pdfjs/pdf.worker.mjs','HEAD')
    assert status==200 and not body and int(headers['content-length'])>0
    status,headers,body=request('/assets/sample.pdf',headers={'Range':'bytes=0-15'})
    assert status==206 and len(body)==16 and headers['content-range'].startswith('bytes 0-15/'),(status,headers,body)
    status,headers,body=request('/assets/sample.pdf')
    if 'etag' in headers:
        assert request('/assets/sample.pdf',headers={'If-None-Match':headers['etag']})[0]==304
    for path in ['/.env','/.git/config','/.htaccess']:
        assert request(path)[0] in (403,404),path
    status,headers,body=request('/probe.php')
    data=json.loads(body)
    assert status==200 and data['php']==m.catalog.get('php',m.settings['php'])['version'],body
    assert '<?php' not in body.decode()
    assert request('/missing.php')[0] in (200,404)  # A framework .htaccess may route it to index.php.

try:
    m.prepare_root();project=m.create_project('aksara');public=project/'public';public.mkdir()
    assets=public/'assets';(assets/'pdfjs').mkdir(parents=True)
    files={'app.js':b'export const app=1;', 'pdfjs/pdf.mjs':b'export const pdfjsVersion="fixture";', 'pdfjs/pdf.worker.mjs':b'self.onmessage=()=>self.postMessage("worker-ready");', 'style.css':b'body{color:green}', 'sample.pdf':b'%PDF-1.7\n'+b'0123456789'*1024,'probe.wasm':b'\x00asm\x01\x00\x00\x00','probe.json':b'{"ok":true}','logo.svg':b'<svg xmlns="http://www.w3.org/2000/svg"/>','font.woff2':b'wOF2fixture'}
    for name,data in files.items():(assets/name).write_bytes(data)
    (public/'index.php').write_text('<?php header("Content-Type: application/json"); echo json_encode(["uri"=>$_SERVER["REQUEST_URI"],"query"=>$_GET]);')
    (public/'probe.php').write_text('<?php header("Content-Type: application/json"); echo json_encode(["php"=>PHP_VERSION]);')
    (public/'.env').write_text('PRIVATE_FIXTURE');(public/'.git').mkdir();(public/'.git/config').write_text('PRIVATE_FIXTURE')
    (public/'.htaccess').write_text('RewriteEngine On\nRewriteRule ^apache-route$ index.php?rewrite=ok [L]\nRewriteCond %{REQUEST_FILENAME} !-d\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteRule ^ index.php [L]\n')
    for web in ['apache','nginx']:
        m.select('web',web)
        extra=m.paths.config/f'{web}-extra.conf'
        custom=b'# User-owned configuration; preserve this exact byte sequence.\n'
        extra.write_bytes(custom)
        m.start_web();conf,runtime=m.render_web();output=m.validate_web(conf,runtime)
        assert 'duplicate extension' not in output,output
        check_assets()
        data=json.loads(request('/framework-route?value=121')[2])
        assert data['uri']=='/framework-route?value=121'
        if web=='apache':
            assert json.loads(request('/apache-route')[2])['query']['rewrite']=='ok'
        assert extra.read_bytes()==custom
        m.restart_web();check_assets()
        print('PASS',web,'MIME js/mjs/PDF.js worker + CSS/PDF/WASM/JSON/SVG/WOFF2 / HEAD / Range / conditional / PHP / vhost / hidden files / routes / restart',flush=True)
        if web=='nginx':
            # Preserve the already-proven user workaround, including nested includes.
            include=m.paths.config/'user-types.conf'
            for override in [b'types { application/javascript mjs; }\n',b'types { text/javascript js mjs; }\n',('include '+quote(include)+';\n').encode()]:
                include.write_text('types { application/javascript mjs; }\n')
                extra.write_bytes(custom+override)
                m.restart_web()
                output=m.validate_web(*m.render_web())
                assert 'duplicate extension' not in output,output
                # render_web regenerated defaults; validation above must reconcile again.
                check_assets();assert extra.read_bytes()==custom+override
                assert include.read_text()=='types { application/javascript mjs; }\n'
                print('PASS nginx existing custom MIME rules/includes preserved without duplicate mappings',flush=True)
            extra.write_bytes(custom);m.restart_web()
            master=m.processes['web'].pid
            assert 'master_process on;' in conf.read_text() and 'daemon off;' in conf.read_text()
            assert Path(f'/proc/{master}/task/{master}/children').read_text().strip(),'No Nginx worker'
            for cycle in range(10):
                m._run(m.web_args(conf,runtime,True))
                m._run(m.web_args(conf,runtime)+['-s','reload'])
                with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
                    results=list(pool.map(lambda _:request('/assets/pdfjs/pdf.worker.mjs'),range(36)))
                assert all(status==200 and body==files['pdfjs/pdf.worker.mjs'] for status,headers,body in results),cycle
                assert m.processes['web'].pid==master and m.running('web')
            print('PASS nginx 10 actual reloads / 360 concurrent HTTP responses / master supervised',flush=True)
            # A rejected configuration must leave the last valid worker serving HTTP.
            extra.write_text('this_directive_is_invalid on;\n')
            try:m._run(m.web_args(conf,runtime,True));raise AssertionError('Invalid configuration accepted')
            except RuntimeError as exc:assert 'unknown directive' in str(exc)
            os.kill(master,signal.SIGHUP);time.sleep(.3);check_assets()
            extra.write_bytes(custom);m._run(m.web_args(conf,runtime)+['-s','reload']);time.sleep(.2);check_assets()
            assert not any(s in m.log_path('web').read_text() for s in ['worker_connections are not enough','Read-only file system'])
            print('PASS nginx rejected reload preserves valid service; writable startup log',flush=True)
        children = Path(f'/proc/{m.processes["web"].pid}/task/{m.processes["web"].pid}/children').read_text().split()
        m.stop('web');m.stop('php');assert port_available(port)
        for pid in children:
            stat=Path(f'/proc/{pid}/stat')
            assert not stat.exists() or stat.read_text().split()[2]=='Z',('Worker survived stop',pid)
    # Invalid custom configuration is retained and fails cleanly without leaving a listener.
    m.select('web','nginx');extra=m.paths.config/'nginx-extra.conf';bad=b'unknown_setting on;\n';extra.write_bytes(bad)
    try:m.start_web();raise AssertionError('Invalid startup accepted')
    except RuntimeError as exc:assert 'unknown directive' in str(exc)
    assert extra.read_bytes()==bad and not m.running('web') and not m.running('php') and port_available(port)
    print('PASS invalid user config preserved and clean startup rollback',flush=True)
finally:m.close()

# The foreground Nginx master must also clean up workers if its owner crashes.
source='/work/src' if os.environ.get('LARSANA_TEST_SOURCE') else '/usr/lib/larsana'
code='''import os,sys,socket,json,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from larsana.core import Manager
m=Manager();m.acquire()
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
m.settings.update(web='nginx',root='/tmp/crash-projects',port=port)
m.prepare_root();m.start_web()
pid=m.processes['web'].pid
children=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
Path('/tmp/crash-pids.json').write_text(json.dumps({'port':port,'pids':[pid,m.processes['php'].pid]+[int(p) for p in children]}))
os._exit(0)
'''
env=dict(os.environ,HOME='/tmp/crash-home',XDG_CONFIG_HOME='/tmp/crash-config',XDG_DATA_HOME='/tmp/crash-data',XDG_STATE_HOME='/tmp/crash-state',XDG_RUNTIME_DIR='/tmp/crash-run')
subprocess.run([sys.executable,'-c',code,source],env=env,check=True)
crashed=json.loads(Path('/tmp/crash-pids.json').read_text())
def alive(pid):
    stat=Path(f'/proc/{pid}/stat')
    return stat.exists() and stat.read_text().split()[2]!='Z'
end=time.monotonic()+10
while any(alive(pid) for pid in crashed['pids']) and time.monotonic()<end:time.sleep(.05)
assert not any(alive(pid) for pid in crashed['pids']),crashed
assert port_available(crashed['port'])
print('PASS Nginx master/workers and PHP exit after owner crash; no listener left',flush=True)
