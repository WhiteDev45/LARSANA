#!/usr/bin/env python3
"""Register extracted packages for dpkg dependency inspection; no maintainer scripts."""
import io
from pathlib import Path
import subprocess
import tarfile
ROOT=Path(__file__).resolve().parents[1]


def register_package(deb,fs):
    info=fs/'var/lib/dpkg/info';info.mkdir(parents=True,exist_ok=True)
    control=subprocess.check_output(['dpkg-deb','-f',str(deb)],text=True)
    fields=dict(line.split(': ',1) for line in control.splitlines() if ': ' in line and not line.startswith(' '))
    name=fields['Package'];architecture=fields['Architecture']
    identifiers={name}
    if fields.get('Multi-Arch')=='same':identifiers.add(name+':'+architecture)
    data=subprocess.check_output(['dpkg-deb','--ctrl-tarfile',str(deb)])
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar:
            basename=Path(member.name).name
            if basename in ('shlibs','symbols'):
                content=tar.extractfile(member).read()
                for ident in identifiers:(info/(ident+'.'+basename)).write_bytes(content)
    listing=subprocess.check_output(['dpkg-deb','-c',str(deb)],text=True)
    files=[]
    for line in listing.splitlines():
        path=line.split(None,5)[-1].split(' -> ')[0]
        path='/'+path.removeprefix('./').rstrip('/')
        if path=='/':path='/.'
        files.append(path)
        for alias in ('lib','lib64','bin','sbin'):
            if path.startswith('/'+alias+'/'):files.append('/usr'+path)
    for ident in identifiers:(info/(ident+'.list')).write_text('\n'.join(sorted(set(files)))+'\n')
    return name,control+'Status: install ok installed\n'


def main():
    fs=ROOT/'.build/rootfs';status=[]
    for deb in sorted((ROOT/'.build/cache').glob('*.deb')):
        _,entry=register_package(deb,fs);status.append(entry)
    (fs/'var/lib/dpkg/status').write_text('\n'.join(status))
    print('dpkg metadata ready for',len(status),'packages')

if __name__=='__main__':main()
