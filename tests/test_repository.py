#!/usr/bin/env python

# Sqlite repo
# build test

import os
import sys
import time

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.api import API
from core.settings import settings, EXAMPLE_DIR, DATA_DIR

try: import sqlite3
except: from pysqlite2 import dbapi2 as sqlite3


starttime = time.time()

db = sqlite3.connect(os.path.abspath(DATA_DIR + os.sep + settings['default_sqlite_db']))
db.row_factory = sqlite3.Row
db.text_factory = str

work = API(db_conn=db)

tasks = work.savvyize(EXAMPLE_DIR, True)  # True means recursive

print '\n\nRepo build test:\n\n'

for task in tasks:
    filename = os.path.basename(task)

    calc, error = work.parse(task)
    if error:
        print filename, error
        continue

    calc, error = work.classify(calc)
    if error:
        print filename, error
        continue
        
    calc = work.postprocess(calc)
    checksum, error = work.save(calc)
    if error:
        print filename, error
        continue

    print filename + " added"
    
print "Test repository done in %1.2f sec" % (time.time() - starttime)
