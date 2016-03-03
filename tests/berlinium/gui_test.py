#!/usr/bin/env python

import os, sys
import time
import subprocess

if __name__ == "__main__":
    try:
        prcnum = int(sys.argv[1])
    except (IndexError, ValueError):
        sys.exit("Usage: script #processes")

    basedir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    daemon = subprocess.Popen([sys.executable, os.path.join(basedir, '../../utils/gui_server.py')])
    time.sleep(2) # wait for initialization

    children = []
    for i in range(prcnum):
        children.append( subprocess.Popen([sys.executable, os.path.join(basedir, 'gui_client.py')]) )

    time.sleep(prcnum + 2)
    daemon.terminate()

    for i in children:
        assert i.poll() == 0
