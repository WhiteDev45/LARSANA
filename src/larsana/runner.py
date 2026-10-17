"""Exec a foreground runtime with Linux parent-death cleanup."""
import ctypes
import os
import signal
import sys


def main():
    expected=int(sys.argv[1])
    args=sys.argv[2:]
    if not args or os.getppid()!=expected:
        return 1
    libc=ctypes.CDLL(None,use_errno=True)
    if libc.prctl(1,signal.SIGTERM,0,0,0)!=0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(),'Cannot arm runtime parent-death signal')
    if os.getppid()!=expected:
        return 1
    os.execv(args[0],args)

if __name__=='__main__':
    raise SystemExit(main())
