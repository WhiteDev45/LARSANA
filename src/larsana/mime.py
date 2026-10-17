"""Normalize the shipped Nginx MIME table, never a user's configuration."""
import re

_ROW = re.compile(r'^(\s*)([^#\s{}]+/[^\s{}]+)\s+([^;]+);(.*)$')


def nginx_mime_types(source, exclude=()):
    """Map mjs once, preserving an existing valid JavaScript MIME choice.

    ``exclude`` removes only vendor defaults shadowed by user http/types rules.
    Nginx itself discovers those collisions, including rules in included files.
    """
    rows = []
    for line in source.splitlines(keepends=True):
        match = _ROW.match(line.rstrip('\n'))
        rows.append([line, match, match.group(3).split() if match else []])
    candidates = [r for r in rows if r[1] and r[1].group(2) in ('application/javascript', 'text/javascript')]
    target = next((r for r in candidates if 'mjs' in r[2]), candidates[0] if candidates else None)
    if target is None:
        raise ValueError('The Nginx MIME table has no JavaScript mapping.')
    omitted = set(exclude)
    output = []
    for row in rows:
        line, match, extensions = row
        if not match:
            output.append(line)
            continue
        updated = [ext for ext in extensions if ext != 'mjs' and ext not in omitted]
        if row is target and 'mjs' not in omitted:
            updated.append('mjs')
        if updated == extensions:
            output.append(line)
        elif updated:
            output.append(match.group(1) + match.group(2) + ' ' + ' '.join(updated) + ';' + match.group(4) + ('\n' if line.endswith('\n') else ''))
    return ''.join(output)
