#!/usr/bin/env python3
"""Exercise the rendered Start/Stop button with real runtimes under Xvfb."""
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, '/usr/lib/larsana' if Path('/usr/lib/larsana/phpmyadmin/index.php').exists() else '/work/src')
from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQml import QQmlApplicationEngine
from larsana.core import Manager
from larsana.gui import Bridge
from larsana import __version__
from larsana.cache import configure_qml_cache
os.environ['XDG_CACHE_HOME']='/tmp/larsana-cache'
old_cache=Path('/tmp/larsana-cache/larsana/qml/1.2.2')
old_cache.mkdir(parents=True,exist_ok=True)
(old_cache/'Main.qmlc').write_bytes(b'corrupted previous-release cache')
os.environ['QML_DISK_CACHE_PATH']=str(old_cache)
cache=configure_qml_cache()
assert cache.name==__version__ and cache!=old_cache
assert os.environ['QML_DISK_CACHE_PATH']==str(cache)
app=QApplication([])
m=Manager();m.acquire()
bridge=Bridge(m)
engine=QQmlApplicationEngine()
engine.rootContext().setContextProperty('backend',bridge)
errors=[];warnings=[];messages=[]
bridge.completed.connect(messages.append)
bridge.error.connect(errors.append)
engine.warnings.connect(lambda items:warnings.extend([str(i.toString()) for i in items]))
engine.load(str(Path(sys.path[0])/'larsana/qml/Main.qml'))
assert engine.rootObjects(),'QML did not load'
assert (old_cache/'Main.qmlc').read_bytes()==b'corrupted previous-release cache'
print('PASS desktop upgrade uses fresh QML cache and preserves previous cache',flush=True)
window=engine.rootObjects()[0]

def settled(timeout=180):
    end=time.monotonic()+timeout
    while bridge.busy and time.monotonic()<end:QTest.qWait(100)
    assert not bridge.busy,'UI action timeout'
    assert not errors,errors
    QTest.qWait(200)
try:
    QTest.qWait(700)
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(100,437))
    settled()
    assert all(v=='Running' for v in m.snapshot()['status'].values()),m.snapshot()['status']
    window.grabWindow().save('/work/dist/larsana-running.png')
    print('PASS desktop Start All, real web/PHP/MariaDB, running screenshot',flush=True)
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(280,229))
    QTest.qWait(150)
    QTest.keyClick(window,Qt.Key_Home)
    QTest.keyClick(window,Qt.Key_Return)
    settled()
    assert m.settings['php']==m.catalog.installed('php')[0]['series']
    assert m.running('web') and m.running('php')
    print('PASS desktop PHP selector switches the live runtime',flush=True)
    if any(item['series']=='11.8' for item in m.catalog.installed('mariadb')):
        QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(280,292))
        QTest.qWait(150)
        QTest.keyClick(window,Qt.Key_Home)
        QTest.keyClick(window,Qt.Key_Down)
        QTest.keyClick(window,Qt.Key_Return)
        settled()
        assert m.settings['mariadb']=='11.8' and m.running('mariadb')
        window.grabWindow().save('/work/dist/larsana-running.png')
        print('PASS desktop MariaDB 11.8 selector',flush=True)
    urls=[]
    bridge.databaseReady.disconnect(bridge.showDatabase)
    bridge.databaseReady.connect(urls.append)
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(335,437))
    settled()
    assert urls and urls[0].startswith('http://127.0.0.1:') and m.running('phpmyadmin'), (urls,m.snapshot())
    assert any('root' in msg and 'password kosong' in msg for msg in messages),messages
    assert not any('nama pengguna Linux' in msg for msg in messages),messages
    print('PASS desktop phpMyAdmin button opens selected database',flush=True)
    print('PASS desktop root login guidance updated',flush=True)
    QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,QPoint(100,437))
    settled()
    assert all(v=='Stopped' for v in m.snapshot()['status'].values())
    print('PASS desktop Stop All',flush=True)
    bridge.createProject('desktop-smoke');settled()
    assert 'desktop-smoke' in m.projects()
    bridge.preferences(str(m.root),m.settings['port'],m.settings['db_port'],True);settled()
    window.grabWindow().save('/work/dist/larsana-dark.png')
    assert not warnings,warnings
    print('PASS desktop project creation, dark theme, no QML warnings',flush=True)
finally:
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    m.close();bridge.pool.shutdown(wait=True)
    assert not warnings,warnings
