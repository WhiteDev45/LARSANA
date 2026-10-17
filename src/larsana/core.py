"""Unprivileged runtime management. No dependency on Qt."""
from __future__ import annotations
import contextlib
import fcntl
import json
import os
import secrets
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import urllib.error

SERIES = {"php": ["8.1", "8.2", "8.3", "8.4", "8.5"], "mariadb": ["10.11", "11.4", "11.8", "12.3", "13.0"]}


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".write-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def port_available(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def quote(path):
    """Quote a path in Apache/Nginx configs, rejecting config metacharacters."""
    value = str(path)
    if any(c in value for c in '\n\r\x00"\\$;{}'):
        raise ValueError("Path mengandung karakter yang tidak didukung konfigurasi server.")
    return '"' + value + '"'


class Paths:
    def __init__(self):
        home = Path.home()
        self.config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "larsana"
        self.data = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")) / "larsana"
        self.state = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "larsana"
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", self.state))
        self.run = runtime / "larsana"
        self.runtimes = Path(os.environ.get("LARSANA_RUNTIME_ROOT", "/usr/lib/larsana/runtimes"))
        for path in (self.config, self.data, self.state, self.run):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            if path.stat().st_uid != os.getuid():
                raise RuntimeError(f"Direktori bukan milik pengguna: {path}")
            path.chmod(0o700)


class Catalog:
    def __init__(self, root):
        self.root = Path(root)

    def installed(self, kind):
        result = []
        for path in sorted((self.root / kind).glob("*/runtime.json")):
            try:
                data = json.loads(path.read_text())
                if data["kind"] != kind or data.get("channel") not in ("stable", "lts", "legacy"):
                    continue
                if kind == "nginx" and data["channel"] != "stable":
                    continue
                if kind == "mariadb" and data["channel"] not in ("stable", "lts"):
                    continue
                if data["series"] != path.parent.name:
                    continue
                if not all((path.parent / x).is_file() for x in data["executables"].values()):
                    continue
                data["root"] = str(path.parent.resolve())
                result.append(data)
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result, key=lambda d: tuple(map(int, d["series"].split("."))))

    def get(self, kind, series=None):
        choices = self.installed(kind)
        if series:
            choices = [x for x in choices if x["series"] == series]
        if not choices:
            raise RuntimeError(f"Runtime {kind} {series or ''} belum terpasang. Instal paket larsana-{kind} yang sesuai.")
        return choices[-1]

    def executable(self, kind, series, role):
        item = self.get(kind, series)
        return str(Path(item["root"]) / item["executables"][role])


class Manager:
    def __init__(self, paths=None):
        self.paths = paths or Paths()
        self.catalog = Catalog(self.paths.runtimes)
        self.settings_file = self.paths.config / "settings.json"
        try:
            self.settings = json.loads(self.settings_file.read_text())
        except FileNotFoundError:
            self.settings = {}
        configured = set(self.settings)
        self.settings.setdefault("web", "apache")
        self.settings.setdefault("php", "8.5")
        lts = [r for r in self.catalog.installed("mariadb") if r["channel"] == "lts"]
        self.settings.setdefault("mariadb", lts[-1]["series"] if lts else "10.11")
        self.settings.setdefault("port", 8080)
        self.settings.setdefault("db_port", 3307)
        self.settings.setdefault("root", str(Path.home() / "Larsana/www"))
        self.settings.setdefault("dark", False)
        for kind in ("php", "mariadb"):
            choices = self.catalog.installed(kind)
            if choices and kind not in configured and self.settings[kind] not in [x["series"] for x in choices]:
                self.settings[kind] = choices[-1]["series"]
        self.processes = {}
        self.status = {"web": "Stopped", "php": "Stopped", "mariadb": "Stopped"}
        self.mutex = threading.RLock()
        self._lock = None

    def acquire(self):
        self._lock = open(self.paths.run / "instance.lock", "a+")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock.close()
            self._lock = None
            raise RuntimeError("LARSANA sudah berjalan untuk pengguna ini.")

    @property
    def root(self):
        return Path(self.settings["root"]).expanduser().resolve()

    def save(self):
        atomic_json(self.settings_file, self.settings)

    def prepare_root(self):
        self.root.mkdir(parents=True, exist_ok=True)
        landing = self.root / "index.php"
        if not any(self.root.iterdir()):
            landing.write_text('''<!doctype html><html><meta charset="utf-8"><title>LARSANA</title>
<style>body{background:#faf8f4;color:#28251f;font:18px system-ui;max-width:700px;margin:15vh auto;padding:24px}b{color:#d9683d}h1{font-size:64px;margin-bottom:12px}code{background:#eee9df;padding:8px;border-radius:8px}</style>
<b>LOCAL DEVELOPMENT, ON LINUX</b><h1>You're ready.</h1><p>LARSANA is serving your local workspace.</p>
<p>PHP <code><?= htmlspecialchars(PHP_VERSION) ?></code></p><p>Add a project from the desktop app to get started.</p></html>''')

    def projects(self):
        if not self.root.exists():
            return []
        return [x.name for x in sorted(self.root.iterdir()) if x.is_dir() and not x.is_symlink() and re.fullmatch(r"[a-z][a-z0-9-]{0,47}", x.name)]

    def create_project(self, name):
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", name):
            raise ValueError("Nama proyek: huruf kecil, angka, tanda -, diawali huruf, maksimal 48 karakter.")
        self.prepare_root()
        target = self.root / name
        target.mkdir(mode=0o755)  # Never overwrite an existing project.
        (target / "index.php").write_text("<?php echo '<h1>" + name + "</h1><p>Built with LARSANA · PHP ' . htmlspecialchars(PHP_VERSION) . '</p>';\n")
        if self.running("web"):
            self.restart_web()
        return target

    def log_path(self, kind):
        return self.paths.state / f"{kind}.log"

    def running(self, kind):
        proc = self.processes.get(kind)
        alive = proc is not None and proc.poll() is None
        if proc is not None and not alive and self.status[kind] == "Running":
            self.status[kind] = "Failed"
        return alive

    def snapshot(self):
        with self.mutex:
            for kind in self.status:
                self.running(kind)
            return {"settings": dict(self.settings), "status": dict(self.status),
                    "installed": {k: self.catalog.installed(k) for k in ("apache", "nginx", "php", "mariadb")},
                    "projects": self.projects(), "root": str(self.root)}

    def _run(self, args, **kwargs):
        timeout = kwargs.pop("timeout", 60)
        input_text = kwargs.pop("input", None)
        proc = subprocess.Popen(args, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                start_new_session=True, **kwargs)
        try:
            output, _ = proc.communicate(input=input_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise RuntimeError(f"Timeout saat menjalankan {Path(args[0]).name}")
        if proc.returncode:
            raise RuntimeError(output[-5000:] or f"Command gagal: {args[0]}")
        return output

    def _spawn(self, kind, args, ready, timeout=20):
        if self.running(kind):
            return
        self.status[kind] = "Starting"
        with open(self.log_path(kind), "ab") as log:
            command = [sys.executable, str(Path(__file__).with_name("runner.py")), str(os.getpid())] + list(args)
            try:
                proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            except OSError:
                self.status[kind] = "Failed"
                raise
        self.processes[kind] = proc
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                self.status[kind] = "Failed"
                raise RuntimeError(self.log_path(kind).read_text(errors="replace")[-4000:])
            if ready():
                self.status[kind] = "Running"
                return
            time.sleep(.1)
        self.stop(kind)
        self.status[kind] = "Failed"
        raise RuntimeError(f"{kind}: timeout saat menunggu layanan. Lihat {self.log_path(kind)}")

    def stop(self, kind):
        if kind == "mariadb":
            self.stop("phpmyadmin")
        proc = self.processes.get(kind)
        if proc and proc.poll() is None:
            self.status[kind] = "Stopping"
            # Popen owns and reaps the process, so PID cannot be recycled while alive.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        self.processes.pop(kind, None)
        self.status[kind] = "Stopped"

    def php_config(self, series):
        conf = self.paths.config / f"php-{series}"
        conf.mkdir(exist_ok=True)
        sock = self.paths.run / f"php-{series}.sock"
        ini = conf / "php.ini"
        if not ini.exists():
            runtime = Path(self.catalog.get("php", series)["root"])
            opcache = list(runtime.glob("lib/php/extensions/*/opcache.so"))
            ini.write_text(f"date.timezone = UTC\ndisplay_errors = On\nlog_errors = On\nerror_log = {self.log_path('php')}\nmemory_limit = 256M\nupload_max_filesize = 64M\npost_max_size = 64M\n" + (f"zend_extension={opcache[0]}\n" if opcache else ""))
        fpm = conf / "fpm.conf"
        fpm.write_text(f"[global]\npid = {self.paths.run}/php-{series}.pid\nerror_log = {self.log_path('php')}\ndaemonize = no\n[www]\nlisten = {sock}\nlisten.mode = 0600\npm = ondemand\npm.max_children = 4\npm.process_idle_timeout = 10s\ncatch_workers_output = yes\nclear_env = no\n")
        return ini, fpm, sock

    def start_php(self, series=None):
        series = series or self.settings["php"]
        exe = self.catalog.executable("php", series, "fpm")
        ini, fpm, sock = self.php_config(series)
        self._run([exe, "-t", "-y", str(fpm), "-c", str(ini)])
        self._spawn("php", [exe, "-F", "-y", str(fpm), "-c", str(ini)], lambda: sock.exists())

    def render_web(self, series=None):
        self.prepare_root()
        web = self.settings["web"]
        runtime = self.catalog.get(web)
        runtime_root = Path(runtime["root"])
        sock = self.paths.run / f"php-{series or self.settings['php']}.sock"
        port = self.settings["port"]
        hosts = [("localhost", self.root)]
        for name in self.projects():
            project = self.root / name
            public = project / "public"
            hosts.append((f"{name}.test {name}.localhost", public if public.is_dir() else project))
        conf = self.paths.config / f"{web}.conf"
        extra = self.paths.config / f"{web}-extra.conf"
        if not extra.exists():
            extra.write_text("# LARSANA custom web server directives. Preserved across restarts.\n")
        if web == "nginx":
            blocks = []
            for hostname, root in hosts:
                blocks.append(f'''server {{
 listen 127.0.0.1:{port}; server_name {hostname};
 root {quote(root)}; index index.php index.html;
 location / {{ try_files $uri $uri/ /index.php?$query_string; }}
 location ~ /\\. {{ deny all; }}
 location ~ \\.php$ {{
  try_files $uri =404;
  include {quote(runtime_root / 'conf/fastcgi_params')};
  fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
  fastcgi_pass unix:{sock};
 }}
}}''')
            text = f'''daemon off;
master_process off;
worker_processes 1;
pid {quote(self.paths.run / 'nginx.pid')};
error_log {quote(self.log_path('web'))};
events {{ worker_connections 256; }}
http {{
 include {quote(runtime_root / 'conf/mime.types')};
 default_type application/octet-stream;
 access_log {quote(self.paths.state / 'access.log')};
 client_body_temp_path {quote(self.paths.run / 'nginx-body')};
 proxy_temp_path {quote(self.paths.run / 'nginx-proxy')};
 fastcgi_temp_path {quote(self.paths.run / 'nginx-fastcgi')};
 scgi_temp_path {quote(self.paths.run / 'nginx-scgi')};
 uwsgi_temp_path {quote(self.paths.run / 'nginx-uwsgi')};
 include {quote(extra)};
 {chr(10).join(blocks)}
}}
'''
        else:
            modules = ["authz_core", "authz_host", "unixd", "dir", "mime", "log_config", "proxy", "proxy_fcgi", "rewrite"]
            loads = "\n".join(f"LoadModule {m}_module {quote(runtime_root / 'modules' / ('mod_' + m + '.so'))}" for m in modules)
            blocks = []
            for hostname, root in hosts:
                names = hostname.split()
                blocks.append(f'''<VirtualHost 127.0.0.1:{port}>
 ServerName {names[0]}
 {('ServerAlias ' + ' '.join(names[1:])) if len(names) > 1 else ''}
 DocumentRoot {quote(root)}
 <Directory {quote(root)}>
  Require all granted
  AllowOverride All
  Options FollowSymLinks
  DirectoryIndex index.php index.html
 </Directory>
 <FilesMatch "\\.php$">
  SetHandler "proxy:unix:{sock}|fcgi://localhost/"
 </FilesMatch>
 <FilesMatch "^\\.">
  Require all denied
 </FilesMatch>
</VirtualHost>''')
            text = f'''ServerRoot {quote(runtime_root)}
{loads}
Listen 127.0.0.1:{port}
ServerName localhost
PidFile {quote(self.paths.run / 'apache.pid')}
DefaultRuntimeDir {quote(self.paths.run)}
ErrorLog {quote(self.log_path('web'))}
LogLevel warn
IncludeOptional {quote(extra)}
TypesConfig {quote(runtime_root / 'conf/mime.types')}
<LocationMatch "(^|/)\\.">
 Require all denied
</LocationMatch>
<Directory />
 Require all denied
</Directory>
{chr(10).join(blocks)}
'''
        conf.write_text(text)
        return conf, runtime

    def web_args(self, conf, runtime, test=False):
        root = Path(runtime["root"])
        exe = str(root / runtime["executables"]["server"])
        if self.settings["web"] == "nginx":
            return [exe, "-p", str(root) + "/", "-c", str(conf)] + (["-t"] if test else [])
        return [exe, "-f", str(conf)] + (["-t"] if test else ["-DFOREGROUND"])

    def healthy_web(self):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.settings['port']}/", timeout=1) as r:
                return True
        except urllib.error.HTTPError:
            # A developer's application may return 403/404/500 while the server
            # itself is healthy. Keep the runtime available for debugging.
            return True
        except Exception:
            return False

    def start_web(self):
        if self.running("web"):
            return
        if not port_available(self.settings["port"]):
            raise RuntimeError(f"Port {self.settings['port']} sedang dipakai. Ubah port di Preferences.")
        started_php = not self.running("php")
        try:
            self.start_php()
            conf, runtime = self.render_web()
            self._run(self.web_args(conf, runtime, True))
            self._spawn("web", self.web_args(conf, runtime), self.healthy_web)
        except Exception:
            if started_php:
                self.stop("php")
            raise

    def restart_web(self):
        self.stop("web")
        self.start_web()

    def start_database(self):
        if self.running("mariadb"):
            return
        series = self.settings["mariadb"]
        item = self.catalog.get("mariadb", series)
        root = Path(item["root"])
        directory = self.paths.data / "mariadb" / series
        directory.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if directory.exists():
            directory.chmod(0o700)
        if not port_available(self.settings["db_port"]):
            raise RuntimeError(f"Port database {self.settings['db_port']} sedang dipakai.")
        if not (directory / "mysql").is_dir():
            if directory.exists() and any(directory.iterdir()):
                raise RuntimeError(f"Datadir belum valid dan berisi file; tidak ditimpa: {directory}")
            init = root / item["executables"]["install"]
            temporary = Path(tempfile.mkdtemp(prefix=f".{series}-init-", dir=directory.parent))
            self._run([str(init), "--no-defaults", f"--basedir={root}", f"--datadir={temporary}", "--auth-root-authentication-method=socket", "--skip-test-db"], timeout=180)
            if directory.exists():
                directory.rmdir()  # Only an empty directory is replaceable.
            temporary.rename(directory)
        sock = self.paths.run / f"mariadb-{series}.sock"
        conf = self.paths.config / f"mariadb-{series}.cnf"
        extra = self.paths.config / f"mariadb-{series}-extra.cnf"
        if not extra.exists():
            extra.write_text("# Custom MariaDB options. Add a [mysqld] section for server options.\n")
        conf.write_text(f"[mysqld]\nbasedir={root}\ndatadir={directory}\nsocket={sock}\npid-file={self.paths.run}/mariadb-{series}.pid\nport={self.settings['db_port']}\nbind-address=127.0.0.1\nskip-name-resolve\nlog-error={self.log_path('mariadb')}\n!include {extra}\n[client]\nsocket={sock}\n")
        exe = str(root / item["executables"]["server"])
        admin = str(root / item["executables"]["admin"])
        def ready():
            if not sock.exists():
                return False
            try:
                self._run([admin, "--no-defaults", f"--socket={sock}", "ping"], timeout=2)
                return True
            except (RuntimeError, subprocess.TimeoutExpired):
                return False
        self._spawn("mariadb", [exe, f"--defaults-file={conf}"], ready, timeout=90)

    def open_database(self):
        """Serve the bundled database UI on loopback, using its supported PHP 8.3.

        A separate process keeps project PHP selections independent. Cookie login
        uses the selected MariaDB socket; changing/stopping DB closes this server.
        """
        with self.mutex:
            source = Path(__file__).resolve().parent.parent / "phpmyadmin"
            if not (source / "index.php").is_file():
                raise RuntimeError("phpMyAdmin belum terpasang. Instal paket lengkap LARSANA 1.2.")
            self.start_database()
            if self.running("phpmyadmin"):
                return self._phpmyadmin_url
            directory = self.paths.data / "phpmyadmin"
            directory.mkdir(exist_ok=True, mode=0o700)
            for name in ("tmp", "sessions"):
                (directory / name).mkdir(exist_ok=True, mode=0o700)
            # Root-owned application files stay immutable; only config/cache is per user.
            for file in source.iterdir():
                link = directory / file.name
                if file.name != "config.inc.php" and not link.exists():
                    link.symlink_to(file, target_is_directory=file.is_dir())
            secret = self.paths.config / "phpmyadmin-secret.json"
            if not secret.exists():
                atomic_json(secret, {"secret": secrets.token_hex(16)})
            config = {
                "secret": json.loads(secret.read_text())["secret"],
                "socket": str(self.paths.run / f"mariadb-{self.settings['mariadb']}.sock"),
                "tmp": str(directory / "tmp"),
                "name": "LARSANA MariaDB " + self.settings["mariadb"],
            }
            # JSON inside a PHP single-quoted string avoids PHP code interpolation.
            literal = json.dumps(config).replace("\\", "\\\\").replace("'", "\\'")
            (directory / "config.inc.php").write_text("<?php\n$larsana = json_decode('" + literal + "', true);\n" + """
$cfg['blowfish_secret'] = $larsana['secret'];
$cfg['Servers'][1]['auth_type'] = 'cookie';
$cfg['Servers'][1]['host'] = 'localhost';
$cfg['Servers'][1]['socket'] = $larsana['socket'];
$cfg['Servers'][1]['verbose'] = $larsana['name'];
$cfg['Servers'][1]['AllowNoPassword'] = true;
$cfg['AllowArbitraryServer'] = false;
$cfg['VersionCheck'] = false;
$cfg['TempDir'] = $larsana['tmp'];
$cfg['LoginCookieRecall'] = false;
""")
            (directory / "config.inc.php").chmod(0o600)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            self._phpmyadmin_url = f"http://127.0.0.1:{port}/"
            exe = self.catalog.executable("php", "8.3", "cli")
            def ready():
                try:
                    with urllib.request.urlopen(self._phpmyadmin_url, timeout=2) as response:
                        return response.status == 200
                except (OSError, urllib.error.URLError):
                    return False
            self._spawn("phpmyadmin", [exe, "-n", "-d", "memory_limit=256M",
                "-d", "upload_max_filesize=64M", "-d", "post_max_size=64M",
                "-d", "session.save_path=" + str(directory / "sessions"),
                "-d", "display_errors=Off", "-d", "log_errors=On",
                "-S", f"127.0.0.1:{port}", "-t", str(directory),
                str(Path(__file__).with_name("phpmyadmin-router.php"))], ready)
            return self._phpmyadmin_url

    def start_all(self):
        with self.mutex:
            started = []
            try:
                for kind, fn in [("php", self.start_php), ("web", self.start_web), ("mariadb", self.start_database)]:
                    was_running = self.running(kind)
                    fn()
                    if not was_running:
                        started.append(kind)
            except Exception:
                for kind in reversed(started):
                    self.stop(kind)
                raise

    def stop_all(self):
        with self.mutex:
            for kind in ("web", "php", "mariadb"):
                self.stop(kind)

    def select(self, kind, value):
        with self.mutex:
            if kind not in ("web", "php", "mariadb"):
                raise ValueError("Pilihan runtime tidak valid.")
            if kind == "web":
                if value not in ("apache", "nginx"):
                    raise ValueError("Server tidak valid.")
                self.catalog.get(value)
            else:
                self.catalog.get(kind, value)
            previous = self.settings[kind]
            if previous == value:
                return
            web_alive = self.running("web")
            php_alive = self.running("php")
            db_alive = self.running("mariadb")
            if kind == "mariadb" and db_alive:
                self.stop("mariadb")
            if kind in ("php", "web") and web_alive:
                self.stop("web")
            if kind == "php" and php_alive:
                self.stop("php")
            self.settings[kind] = value
            try:
                if kind == "mariadb" and db_alive:
                    self.start_database()
                elif kind == "php":
                    if php_alive:
                        self.start_php()
                    if web_alive:
                        self.start_web()
                elif kind == "web" and web_alive:
                    self.start_web()
                self.save()
            except Exception as original:
                if kind == "mariadb":
                    self.stop("mariadb")
                else:
                    self.stop("web")
                    if kind == "php":
                        self.stop("php")
                self.settings[kind] = previous
                try:
                    if kind == "mariadb" and db_alive:
                        self.start_database()
                    elif kind in ("web", "php"):
                        if php_alive:
                            self.start_php()
                        if web_alive:
                            self.start_web()
                except Exception as rollback:
                    raise RuntimeError(f"Pergantian gagal: {original}\nPemulihan gagal: {rollback}") from original
                raise RuntimeError(f"Pergantian dibatalkan; versi sebelumnya dipulihkan.\n{original}") from original

    def preferences(self, root, port, db_port, dark):
        with self.mutex:
            if any(self.running(x) for x in self.status):
                raise RuntimeError("Stop All sebelum mengubah direktori atau port.")
            for value in (port, db_port):
                if not 1024 <= int(value) <= 65535:
                    raise ValueError("Port harus berada antara 1024 dan 65535.")
            if int(port) == int(db_port):
                raise ValueError("Port web dan database harus berbeda.")
            path = Path(root).expanduser()
            if not path.is_absolute():
                raise ValueError("Gunakan path absolut untuk document root.")
            quote(path)
            self.settings.update(root=str(path), port=int(port), db_port=int(db_port), dark=bool(dark))
            self.save()

    def environment(self):
        env = dict(os.environ)
        dirs = []
        for kind, roles in [("php", ["cli"]), ("mariadb", ["client"])]:
            with contextlib.suppress(RuntimeError):
                for role in roles:
                    dirs.append(str(Path(self.catalog.executable(kind, self.settings[kind], role)).parent))
        env["PATH"] = os.pathsep.join(dirs + [env.get("PATH", "/usr/bin:/bin")])
        if self.catalog.installed("php"):
            ini, _, _ = self.php_config(self.settings["php"])
            env["PHPRC"] = str(ini)
        return env

    def close(self):
        self.stop_all()
        if self._lock:
            self._lock.close()
            self._lock = None
