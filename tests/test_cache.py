from larsana import __version__
from larsana.cache import configure_qml_cache


def test_upgrade_ignores_stale_cache_preserves_data(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_CACHE_HOME',str(tmp_path))
    old=tmp_path/'larsana/qml/1.2.2';old.mkdir(parents=True)
    stale=old/'Main.qmlc';stale.write_bytes(b'invalid stale cache')
    monkeypatch.setenv('QML_DISK_CACHE_PATH',str(old))
    cache=configure_qml_cache()
    assert cache==tmp_path/'larsana/qml'/__version__
    assert cache.is_dir() and not list(cache.iterdir())
    assert stale.read_bytes()==b'invalid stale cache'
    assert configure_qml_cache()==cache


def test_unwritable_cache_allows_launch(tmp_path,monkeypatch):
    blocker=tmp_path/'file';blocker.write_text('keep')
    monkeypatch.setenv('XDG_CACHE_HOME',str(blocker))
    monkeypatch.setenv('QML_FORCE_DISK_CACHE','1')
    configure_qml_cache()
    import os
    assert os.environ['QML_DISABLE_DISK_CACHE']=='1'
    assert 'QML_FORCE_DISK_CACHE' not in os.environ
