#!/usr/bin/env python
import os, sys
import time
import subprocess


if __name__ == "__main__":
    bd = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
    dmn = subprocess.Popen([sys.executable, os.path.join(bd, 'basic_server.py')], env=os.environ.copy())
    time.sleep(2) # wait for initialization

    for i in range(5):
        subprocess.Popen([sys.executable, os.path.join(bd, 'basic_client.py')], env=os.environ.copy())
        time.sleep(0.5)

    time.sleep(7)
    dmn.terminate()
