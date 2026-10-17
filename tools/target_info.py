"""Identify the distribution ABI from the isolated builder, not the execution host."""
from pathlib import Path
import shlex

def target_info(root):
    file=Path(root)/'.build/rootfs/usr/lib/os-release'
    fields={}
    for line in file.read_text().splitlines():
        if '=' not in line or line.startswith('#'):continue
        key,value=line.split('=',1)
        parsed=shlex.split(value)
        fields[key]=parsed[0] if parsed else ''
    suite=fields.get('UBUNTU_CODENAME') or fields.get('VERSION_CODENAME')
    if not suite:raise RuntimeError('Builder does not declare a distribution codename')
    return {'suite':suite,'architecture':'amd64','os_release':fields}
