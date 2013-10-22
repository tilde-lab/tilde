#!/usr/bin/env python

# Convert db to json

import os
import sys
import sqlite3
import json
import time

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.settings import DATA_DIR

starttime = time.time()

try:
    workpath = sys.argv[1]
except IndexError:
    raise RuntimeError('No db defined!')
if not os.path.exists(DATA_DIR + os.sep + workpath):
    raise RuntimeError('Invalid path!')

db = sqlite3.connect(DATA_DIR + os.sep + workpath)
db.row_factory = sqlite3.Row
db.text_factory = str
cursor = db.cursor()
f = open(DATA_DIR + os.sep + workpath + '.json', 'w')
for row in cursor.execute('SELECT * FROM results'):
    f.write(json.dumps(dict(row)) + "\n")
f.close()
print "Done in %1.2f sec" % (time.time() - starttime)
