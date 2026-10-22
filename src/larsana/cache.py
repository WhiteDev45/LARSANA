"""Select a fresh Qt disk-cache namespace after every application upgrade."""
import os
from pathlib import Path
from . import __version__


def configure_qml_cache():
    base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache')
    if not base.is_absolute():
        base = Path.home() / '.cache'
    # Never reuse a caller's unversioned QML cache across package upgrades.
    # Retain old caches: another running version may still be using them.
    cache = base / 'larsana' / 'qml' / __version__
    try:
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.environ['QML_DISK_CACHE_PATH'] = str(cache)
    except OSError:
        # A read-only/full cache must not prevent the desktop from launching.
        os.environ.pop('QML_FORCE_DISK_CACHE', None)
        os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    return cache
