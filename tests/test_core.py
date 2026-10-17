import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from larsana.core import Catalog, Manager, Paths, atomic_json, quote
from larsana.hosts import update_hosts

@pytest.fixture
def manager(tmp_path, monkeypatch):
    for name, sub in [('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','run'),('LARSANA_RUNTIME_ROOT','runtimes')]:
        directory=tmp_path/sub;directory.mkdir();monkeypatch.setenv(name,str(directory))
    m=Manager();yield m;m.close()

def fake_runtime(m,kind,series,executables):
    root=m.paths.runtimes/kind/series;root.mkdir(parents=True)
    for role in executables:
        file=root/role;file.write_text('#!/bin/sh\nexit 0\n');file.chmod(0o755)
    atomic_json(root/'runtime.json',dict(kind=kind,series=series,version=series+'.0',channel='stable',executables={k:k for k in executables}))
    return root

def test_catalog_rejects_preview_and_incomplete(manager):
    path=fake_runtime(manager,'php','8.5',['cli','fpm'])
    assert manager.catalog.get('php','8.5')['series']=='8.5'
    data=json.loads((path/'runtime.json').read_text());data['channel']='preview';atomic_json(path/'runtime.json',data)
    assert manager.catalog.installed('php')==[]
    data['channel']='stable';atomic_json(path/'runtime.json',data);(path/'cli').unlink()
    assert manager.catalog.installed('php')==[]

def test_single_instance_lock(manager):
    manager.acquire()
    other=Manager(manager.paths)
    with pytest.raises(RuntimeError,match='sudah berjalan'): other.acquire()
    other.close()

def test_project_creation_preserves_existing_files(manager):
    directory=manager.create_project('hello-world')
    original=(directory/'index.php').read_text()
    with pytest.raises(FileExistsError):manager.create_project('hello-world')
    assert (directory/'index.php').read_text()==original
    for bad in ['../escape','a;rm','a\nhello','_private','hello.world','a/b']:
        with pytest.raises(ValueError):manager.create_project(bad)
    assert manager.projects()==['hello-world']

def test_preferences_validate_before_save(manager):
    original=dict(manager.settings)
    with pytest.raises(ValueError):manager.preferences('/tmp/root',80,3307,False)
    with pytest.raises(ValueError):manager.preferences('/tmp/root',8080,8080,False)
    assert manager.settings==original
    manager.preferences(str(manager.paths.data/'www with spaces'),8081,3308,True)
    assert json.loads(manager.settings_file.read_text())['port']==8081

def test_config_rejects_injection():
    assert quote('/a b')=='"/a b"'
    for text in ['/a\nLoadModule evil','/a$path','/a"','/a;foo']:
        with pytest.raises(ValueError):quote(text)

def test_stop_only_owned_process(manager):
    unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    owned=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    try:
        manager.processes['php']=owned;manager.status['php']='Running'
        manager.stop('php')
        assert owned.poll() is not None
        assert unrelated.poll() is None
    finally:
        unrelated.terminate();unrelated.wait()

def test_selection_failure_restores_settings(manager,monkeypatch):
    fake_runtime(manager,'php','8.4',['cli','fpm']);fake_runtime(manager,'php','8.5',['cli','fpm'])
    manager.settings['php']='8.4'
    active={'php':True,'web':True,'mariadb':False}
    monkeypatch.setattr(manager,'running',lambda kind:active[kind])
    monkeypatch.setattr(manager,'stop',lambda kind:active.update({kind:False}))
    def start_php():
        if manager.settings['php']=='8.5':raise RuntimeError('broken new runtime')
        active['php']=True
    monkeypatch.setattr(manager,'start_php',start_php)
    monkeypatch.setattr(manager,'start_web',lambda:active.update(web=True))
    with pytest.raises(RuntimeError,match='dipulihkan'):manager.select('php','8.5')
    assert manager.settings['php']=='8.4'
    assert active['php'] and active['web']
    active.update(php=False,web=False)

def test_database_selection_does_not_reuse_datadir(manager):
    fake_runtime(manager,'mariadb','10.11',['server','install','admin','client'])
    fake_runtime(manager,'mariadb','12.3',['server','install','admin','client'])
    manager.settings['mariadb']='10.11'
    old=manager.paths.data/'mariadb/10.11';old.mkdir(parents=True);(old/'precious.sql').write_text('keep me')
    manager.select('mariadb','12.3')
    assert (old/'precious.sql').read_text()=='keep me'
    assert not (manager.paths.data/'mariadb/12.3').exists()

def test_hosts_editor_preserves_unrelated_entries():
    original='127.0.0.1 localhost\n192.168.1.3 intranet # shared\n'
    edited=update_hosts(original,'hello.test',1000)
    assert original in edited
    assert update_hosts(edited,'hello.test',1000)==edited
    assert update_hosts(edited,'hello.test',1001,True)==edited
    assert update_hosts(edited,'hello.test',1000,True)==original
    with pytest.raises(ValueError):update_hosts(original,'evil.test\n8.8.8.8 foo',1000)
    with pytest.raises(ValueError):update_hosts('1.2.3.4 hello.test\n','hello.test',1000)

def test_port_check_distinguishes_listener_from_time_wait():
    import socket
    from larsana.core import port_available
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('127.0.0.1',0));listener.listen()
        port=listener.getsockname()[1]
        assert not port_available(port)
    assert port_available(port)


def test_runtime_exits_when_its_parent_dies(tmp_path):
    import time
    runner=Path(__file__).resolve().parents[1]/'src/larsana/runner.py'
    childfile=tmp_path/'child.pid'
    parent_script='''import os,subprocess,sys,time
child=subprocess.Popen([sys.executable,sys.argv[1],str(os.getpid()),sys.executable,'-c','import time;time.sleep(60)'])
open(sys.argv[2],'w').write(str(child.pid))
time.sleep(60)
'''
    parent=subprocess.Popen([sys.executable,'-c',parent_script,str(runner),str(childfile)])
    child_pid=None
    try:
        for _ in range(100):
            if childfile.exists() and childfile.read_text():break
            time.sleep(.02)
        child_pid=int(childfile.read_text());time.sleep(.15)
        parent.terminate();parent.wait(timeout=5)
        for _ in range(100):
            stat=Path(f'/proc/{child_pid}/stat')
            try:
                state=stat.read_text().split()[2]
            except (FileNotFoundError,ProcessLookupError):
                break  # The child may disappear between lookup and read.
            if state=='Z':break
            time.sleep(.02)
        else:pytest.fail('Runtime survived parent exit')
    finally:
        if parent.poll() is None:parent.kill();parent.wait()
        if child_pid:
            try:os.kill(child_pid,15)
            except ProcessLookupError:pass

def test_command_timeout_kills_child_group(manager,tmp_path):
    import time
    marker=tmp_path/'should-not-exist'
    code="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',sys.argv[1]]);time.sleep(10)"
    child=f"import time,pathlib;time.sleep(.8);pathlib.Path({str(marker)!r}).touch()"
    with pytest.raises(RuntimeError,match='Timeout'):
        manager._run([sys.executable,'-c',code,child],timeout=.1)
    time.sleep(.9)
    assert not marker.exists()

def test_database_init_never_overwrites_unrecognized_data(manager):
    fake_runtime(manager,'mariadb','10.11',['server','install','admin','client'])
    directory=manager.paths.data/'mariadb/10.11';directory.mkdir(parents=True)
    (directory/'precious.dat').write_text('existing data')
    with pytest.raises(RuntimeError,match='tidak ditimpa'):manager.start_database()
    assert (directory/'precious.dat').read_text()=='existing data'

@pytest.mark.parametrize('kind,series,channel',[('nginx','1.30','legacy'),('nginx','1.31','mainline'),('mariadb','13.0','legacy'),('mariadb','13.1','rc')])
def test_only_stable_nginx_and_mariadb_enter_catalog(manager,kind,series,channel):
    path=fake_runtime(manager,kind,series,['server'])
    data=json.loads((path/'runtime.json').read_text());data['channel']=channel
    atomic_json(path/'runtime.json',data)
    assert manager.catalog.installed(kind)==[]

def test_existing_workspace_is_not_modified_for_landing_page(manager):
    manager.root.mkdir(parents=True)
    (manager.root/'README.md').write_text('existing workspace')
    manager.prepare_root()
    assert not (manager.root/'index.php').exists()


def test_application_http_error_does_not_mark_server_unhealthy(manager):
    from http.server import HTTPServer,BaseHTTPRequestHandler
    import threading
    class BrokenApplication(BaseHTTPRequestHandler):
        def do_GET(self):self.send_error(500,'Application parse error')
        def log_message(self,*args):pass
    server=HTTPServer(('127.0.0.1',0),BrokenApplication)
    manager.settings['port']=server.server_port
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:assert manager.healthy_web()
    finally:server.shutdown();server.server_close();worker.join()

def test_missing_selected_database_is_not_silently_replaced(manager):
    fake_runtime(manager,'mariadb','12.3',['server','install','admin','client'])
    manager.settings['mariadb']='10.11';manager.save()
    reloaded=Manager(manager.paths)
    try:assert reloaded.settings['mariadb']=='10.11'
    finally:reloaded.close()

@pytest.mark.parametrize('configured,expected', [(None,3306),(3307,3306),(3310,3310)])
def test_database_default_port_migration(manager,configured,expected):
    settings={'php':'8.3'}
    if configured is not None:settings['db_port']=configured
    atomic_json(manager.settings_file,settings)
    updated=Manager(manager.paths)
    assert updated.settings['db_port']==expected
    updated.settings['db_port']=3307
    updated.save()
    assert Manager(manager.paths).settings['db_port']==3307  # Later explicit preference wins.
