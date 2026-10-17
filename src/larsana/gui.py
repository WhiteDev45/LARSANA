"""Qt bridge: background work is serialized; only GUI thread touches Qt objects."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PySide6.QtCore import QCoreApplication, QEvent, QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .core import Manager

class Bridge(QObject):
    changed = Signal()
    completed = Signal(str)
    error = Signal(str)
    detail = Signal(str)
    result = Signal(str, str)
    shutdownReady = Signal()
    databaseReady = Signal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._busy = False
        self._snapshot = manager.snapshot()
        self._closing = False
        self.result.connect(self.finish)
        self.databaseReady.connect(self.showDatabase)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1200)

    @Property(str, notify=changed)
    def state(self):
        return json.dumps(self._snapshot)

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    def refresh(self):
        if not self._busy:
            updated = self.manager.snapshot()
            if updated != self._snapshot:
                self._snapshot = updated
                self.changed.emit()

    def submit(self, fn, success):
        if self._busy or self._closing:
            return
        self._busy = True
        self.changed.emit()
        def work():
            try:
                fn()
                self.result.emit(success, '')
            except Exception as exc:
                self.result.emit('', str(exc))
        self.pool.submit(work)

    @Slot(str, str)
    def finish(self, message, error):
        self._busy = False
        self._snapshot = self.manager.snapshot()
        self.changed.emit()
        if self._closing:
            if message == "__shutdown__":
                self.pool.shutdown(wait=False)
                self.shutdownReady.emit()
            else:
                self._busy = True
                self.changed.emit()
        elif error:
            self.error.emit(error)
        elif message:
            self.completed.emit(message)

    @Slot(str)
    def showDatabase(self, url):
        QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def startAll(self):
        self.submit(self.manager.start_all, 'Semua layanan siap digunakan.')

    @Slot()
    def stopAll(self):
        self.submit(self.manager.stop_all, 'Semua layanan dihentikan.')

    @Slot(str, str)
    def select(self, kind, value):
        self.submit(lambda: self.manager.select(kind, value), 'Runtime diperbarui.')

    @Slot(str, str)
    def service(self, kind, action):
        def run():
            with self.manager.mutex:
                if action in ('stop', 'restart'):
                    self.manager.stop(kind)
                    if kind == 'web' and action == 'stop':
                        self.manager.stop('php')
                if action in ('start', 'restart'):
                    {'web':self.manager.start_web,'php':self.manager.start_php,'mariadb':self.manager.start_database}[kind]()
        self.submit(run, 'Layanan diperbarui.')

    @Slot()
    def extensions(self):
        def inspect():
            ini, _, _ = self.manager.php_config(self.manager.settings['php'])
            exe=self.manager.catalog.executable('php',self.manager.settings['php'],'cli')
            self.detail.emit(self.manager._run([exe,'-c',str(ini),'-m']))
        self.submit(inspect, 'Daftar extension PHP dimuat.')

    @Slot(str)
    def enableDomain(self, name):
        def configure():
            if name not in self.manager.projects():
                raise ValueError('Pilih nama proyek LARSANA yang sudah ada.')
            helper=Path('/usr/lib/larsana/larsana-hosts')
            if not helper.is_file():
                raise RuntimeError('Instal paket desktop .deb untuk mengaktifkan integrasi .test.')
            self.manager._run(['pkexec',str(helper),'add',name+'.test'],timeout=120)
        self.submit(configure, 'Domain .test diaktifkan untuk proyek ini.')

    @Slot(str)
    def createProject(self, name):
        self.submit(lambda: self.manager.create_project(name), 'Proyek dibuat. Akses domain .localhost atau aktifkan .test.')

    @Slot(str, int, int, bool)
    def preferences(self, root, port, db_port, dark):
        self.submit(lambda: self.manager.preferences(root, port, db_port, dark), 'Preferences tersimpan.')

    @Slot(str)
    def open(self, what):
        try:
            if what == 'web':
                QDesktopServices.openUrl(QUrl(f"http://localhost:{self.manager.settings['port']}"))
            elif what == 'root':
                self.manager.prepare_root()
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.root)))
            elif what == 'database':
                def launch():
                    self.databaseReady.emit(self.manager.open_database())
                self.submit(launch, 'phpMyAdmin siap. Login: root — password kosong (default lokal).')
            elif what == 'terminal':
                self.terminal()
            elif what == 'guide':
                QDesktopServices.openUrl(QUrl('https://github.com/search?q=larsana&type=repositories'))
            elif what.startswith('project:'):
                name = what.split(':',1)[1]
                if name not in self.manager.projects():
                    raise ValueError('Proyek tidak ditemukan.')
                QDesktopServices.openUrl(QUrl(f"http://{name}.localhost:{self.manager.settings['port']}"))
            elif what.startswith('log:'):
                path = self.manager.log_path(what.split(':',1)[1])
                path.touch(exist_ok=True)
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            elif what == 'config:php':
                ini, _, _ = self.manager.php_config(self.manager.settings['php'])
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(ini)))
            elif what == 'config:web':
                conf, _ = self.manager.render_web()
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.paths.config / (self.manager.settings["web"] + "-extra.conf"))))
            elif what == 'config:mariadb':
                path=self.manager.paths.config / ('mariadb-' + self.manager.settings['mariadb'] + '-extra.cnf')
                if not path.exists():
                    path.write_text('# Custom MariaDB options. Add a [mysqld] section for server options.\n')
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            elif what == 'runtime-folder':
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.manager.paths.runtimes)))
        except Exception as exc:
            self.error.emit(str(exc))

    def terminal(self, database=False):
        self.manager.prepare_root()
        env = self.manager.environment()
        command = [env.get('SHELL', '/bin/bash')]
        if database:
            series=self.manager.settings['mariadb']
            command=[self.manager.catalog.executable('mariadb',series,'client'), '--no-defaults', f'--socket={self.manager.paths.run}/mariadb-{series}.sock']
        for exe, prefix in [('gnome-terminal',['--']),('mate-terminal',['-x']),('xfce4-terminal',['-x']),('konsole',['-e']),('xterm',['-e']),('x-terminal-emulator',['-e'])]:
            if shutil.which(exe):
                subprocess.Popen([exe]+prefix+command, cwd=self.manager.root, env=env, start_new_session=True)
                return
        raise RuntimeError('Terminal emulator tidak ditemukan. Instal gnome-terminal, konsole, atau xterm.')

    @Slot()
    def shutdown(self):
        if self._closing:
            return
        self._closing = True
        self.timer.stop()
        self._busy = True
        self.changed.emit()
        def close():
            try:
                self.manager.close()
                self.result.emit('__shutdown__', '')
            except Exception as exc:
                self.result.emit('__shutdown__', str(exc))
        self.pool.submit(close)


def run(manager, screenshot=None):
    manager.acquire()
    manager.save()  # Remember the initial selection; package updates must not switch databases.
    app = QApplication(['larsana'])
    app.setApplicationName('LARSANA')
    app.setApplicationVersion('1.2.1')
    app.setOrganizationName('LARSANA')
    app.setDesktopFileName('larsana')
    app.setStyle('Fusion')
    icon = Path(__file__).parent / 'qml/larsana.svg'
    app.setWindowIcon(QIcon(str(icon)))
    bridge = Bridge(manager)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', bridge)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml/Main.qml')))
    if not engine.rootObjects():
        manager.close()
        return 1
    window = engine.rootObjects()[0]
    bridge.shutdownReady.connect(app.quit)
    tray = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray=QSystemTrayIcon(QIcon(str(icon)), app)
        tray.setToolTip('LARSANA · Local development, on Linux')
        menu=QMenu()
        menu.addAction('Show LARSANA', lambda: (window.show(), window.raise_(), window.requestActivate()))
        menu.addSeparator()
        menu.addAction('Start All', bridge.startAll)
        menu.addAction('Stop All', bridge.stopAll)
        for label, key in [('Apache / Nginx', 'web'),('PHP','php'),('MariaDB','mariadb')]:
            sub=menu.addMenu(label)
            for action in ('start','stop','restart'):
                sub.addAction(action.title(), lambda checked=False,k=key,a=action: bridge.service(k,a))
            sub.addAction('Logs', lambda checked=False,k=key: bridge.open('log:'+k))
        menu.addSeparator()
        menu.addAction('phpMyAdmin', lambda: bridge.open('database'))
        menu.addAction('Terminal', lambda: bridge.open('terminal'))
        menu.addAction('Document root', lambda: bridge.open('root'))
        menu.addSeparator()
        menu.addAction('Exit', bridge.shutdown)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: window.show() if reason == QSystemTrayIcon.Trigger else None)
        tray.show()
    if screenshot:
        def capture():
            try:
                window.grabWindow().save(str(screenshot))
            finally:
                bridge.shutdown()
        QTimer.singleShot(1800, capture)
    try:
        return app.exec()
    finally:
        # Destroy QML bindings while their Python context object is still alive.
        engine.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        manager.close()
        bridge.pool.shutdown(wait=True)
