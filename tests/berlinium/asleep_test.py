#!/usr/bin/env python

import os, sys
import time
import subprocess
import unittest


basedir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

class Test_Async_Sleep_Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daemon = subprocess.Popen([sys.executable, os.path.join(basedir, 'asleep_server.py')])
        time.sleep(2) # wait for initialization

    def test_response(self):
        prcnum = 5
        children = []
        for i in range(prcnum):
            children.append( subprocess.Popen([sys.executable, os.path.join(basedir, 'asleep_client.py')]) )
        time.sleep(7)

        for i in children:
            self.assertEqual(i.poll(), 0, "Server response is too slow")

    @classmethod
    def tearDownClass(cls):
        cls.daemon.terminate()
