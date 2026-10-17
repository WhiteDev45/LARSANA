#!/usr/bin/env python3
"""Capture raw HTTP around reloads in an isolated instance of the selected source."""
import json,os,socket,sys,time
sys.path.insert(0,os.environ.get('LARSANA_DIAG_SOURCE','/work/src'))
from larsana.core import Manager
m=Manager();m.acquire()
if os.environ.get('LARSANA_DIAG_WRITABLE_LOG'):
    original=m.web_args
    m.web_args=lambda conf,runtime,test=False: original(conf,runtime,test)+['-e',str(m.log_path('web'))]
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
m.settings.update(web='nginx',root='/tmp/reload-repro',port=port)
def request():
    with socket.create_connection(('127.0.0.1',port),timeout=3) as s:
        s.sendall(b'GET /assets/pdfjs/pdf.mjs HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        return s.recv(1024).decode(errors='replace')
try:
    m.prepare_root();assets=m.root/'assets/pdfjs';assets.mkdir(parents=True)
    (assets/'pdf.mjs').write_text('export const value = 42;\n')
    m.start_web();before=request();print('BEFORE',json.dumps(before),flush=True)
    conf,runtime=m.render_web();args=m.web_args(conf,runtime)
    print('PROCESS MODE',next(line for line in conf.read_text().splitlines() if line.startswith('master_process')),flush=True)
    for i in range(3):
        try:
            m._run(args+['-s','reload']);time.sleep(.25)
            print('AFTER RELOAD',i+1,json.dumps(request()),flush=True)
        except Exception as exc:print('RELOAD ERROR',i+1,repr(exc),flush=True);break
    m.restart_web();print('AFTER RESTART',json.dumps(request()),flush=True)
    print('SERVER LOG',m.log_path('web').read_text()[-5000:],flush=True)
finally:m.close()
