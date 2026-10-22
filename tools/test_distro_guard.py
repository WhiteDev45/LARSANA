#!/usr/bin/env python3
"""Exercise the actual installer guard with os-release fixtures in Bubblewrap."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
fixtures=[('ubuntu','24.04','noble',True),('ubuntu','24.10','oracular',True),('ubuntu','25.04','plucky',True),('ubuntu','25.10','questing',True),('ubuntu','26.04','resolute',True),('ubuntu','22.04','jammy',False),('ubuntu','26.10','stonking',False),('debian','13','trixie',True),('debian','12','bookworm',False),('fedora','44','',False)]
with tempfile.TemporaryDirectory() as tmp:
 file=Path(tmp)/'os-release'
 for ident,version,code,expected in fixtures:
  file.write_text(f'ID={ident}\nVERSION_ID={version}\nVERSION_CODENAME={code}\n')
  result=subprocess.run(['bwrap','--ro-bind','/','/','--ro-bind',str(file),'/etc/os-release','/bin/sh',str(ROOT/'packaging/preinst'),'install'],capture_output=True,text=True)
  assert (result.returncode==0)==expected,(ident,version,result.stderr)
 for base in ['noble','resolute','jammy']:
  file.write_text(f'ID=linuxmint\nVERSION_ID=22.3\nVERSION_CODENAME=zena\nUBUNTU_CODENAME={base}\n')
  result=subprocess.run(['bwrap','--ro-bind','/','/','--ro-bind',str(file),'/etc/os-release','/bin/sh',str(ROOT/'packaging/preinst'),'install'],capture_output=True,text=True)
  assert (result.returncode==0)==(base!='jammy'),result.stderr
 for base in ['trixie','bookworm']:
  file.write_text(f'ID=linuxmint\nVERSION_ID=7\nVERSION_CODENAME=gigi\nDEBIAN_CODENAME={base}\n')
  result=subprocess.run(['bwrap','--ro-bind','/','/','--ro-bind',str(file),'/etc/os-release','/bin/sh',str(ROOT/'packaging/preinst'),'install'],capture_output=True,text=True)
  assert (result.returncode==0)==(base=='trixie'),result.stderr
print('PASS installer guard: Ubuntu 24.04–26.04, Mint base detection, Debian; older/unrelated bases rejected')
