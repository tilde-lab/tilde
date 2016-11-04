#!/usr/bin/env python

import os, sys
import time
import subprocess
import unittest


basedir = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

class Test_GUI_Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daemon = subprocess.Popen([sys.executable, os.path.join(basedir, '../../utils/gui_server.py')])
        time.sleep(2) # wait for initialization

    def test_response(self):
        prcnum = 10
        children = []
        for i in range(prcnum):
            children.append( subprocess.Popen([sys.executable, os.path.join(basedir, 'gui_client.py')]) )
        time.sleep(7)

        for i in children:
            self.assertEqual(i.poll(), 0, "Server response is too slow")

    @classmethod
    def tearDownClass(cls):
        cls.daemon.terminate()
