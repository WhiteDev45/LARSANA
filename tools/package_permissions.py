"""Normalize private payload permissions without relying on upstream archive modes."""
from pathlib import Path

def normalize(root):
    for file in Path(root).rglob('*'):
        if file.is_symlink():continue
        if file.is_dir():file.chmod(0o755);continue
        if not file.is_file():continue
        with file.open('rb') as stream:magic=stream.read(4)
        library='.so' in file.name
        executable=(magic==b'\x7fELF' and not library) or (magic.startswith(b'#!') and file.suffix not in ('.py','.pm') and bool(file.stat().st_mode & 0o111))
        file.chmod(0o755 if executable else 0o644)
