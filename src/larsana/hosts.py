"""Narrow hosts-file editor for explicitly authenticated .test domain setup."""
import fcntl
import os
from pathlib import Path
import re
import sys


def update_hosts(text, domain, uid, remove=False):
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,47}\.test', domain):
        raise ValueError('Invalid LARSANA .test domain')
    if not str(uid).isdigit() or int(uid) < 1000:
        raise ValueError('Invalid caller UID')
    marker=f'# LARSANA uid={uid} domain={domain}'
    lines=[line for line in text.splitlines() if not line.endswith(marker)]
    if not remove:
        # Never silently conflict with an existing mapping owned elsewhere.
        for line in lines:
            words=line.split('#',1)[0].split()
            if domain in words[1:]:
                if words[0]!='127.0.0.1':
                    raise ValueError('Domain already maps to another address')
                return '\n'.join(lines)+'\n'
        lines.append(f'127.0.0.1\t{domain}\t{marker}')
    return '\n'.join(lines)+'\n'


def main():
    if os.geteuid()!=0 or not os.environ.get('PKEXEC_UID'):
        raise SystemExit('Run this helper through pkexec.')
    if len(sys.argv)!=3 or sys.argv[1] not in ('add','remove'):
        raise SystemExit('Usage: larsana-hosts add|remove project.test')
    domain=sys.argv[2]
    # /etc/hosts can be a bind mount, so update the locked inode in place.
    fd=os.open('/etc/hosts',os.O_RDWR|os.O_NOFOLLOW)
    with os.fdopen(fd,'r+') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        result=update_hosts(stream.read(),domain,os.environ['PKEXEC_UID'],sys.argv[1]=='remove')
        stream.seek(0)
        stream.write(result)
        stream.truncate()
        stream.flush()
        os.fsync(stream.fileno())

if __name__=='__main__':
    main()
