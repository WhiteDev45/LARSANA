import argparse
import json
import os
from pathlib import Path
import sys
from . import __version__
from .core import Manager

def main():
    parser=argparse.ArgumentParser(description='LARSANA · Local development, on Linux')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--doctor', action='store_true', help='Inspect installed runtimes without starting services')
    parser.add_argument('--screenshot', type=Path, help=argparse.SUPPRESS)
    args=parser.parse_args()
    try:
        if os.geteuid() == 0:
            raise RuntimeError("Jalankan LARSANA sebagai pengguna biasa, tanpa sudo.")
        manager=Manager()
        if args.doctor:
            diagnostic=manager.snapshot()
            diagnostic.pop('status',None)
            diagnostic['service_state']='not_inspected'
            print(json.dumps(diagnostic, indent=2))
            return 0
        from .gui import run
        return run(manager, args.screenshot)
    except Exception as exc:
        print(f'LARSANA: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
