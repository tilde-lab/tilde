#!/usr/bin/env python

# Convert Tilde sqlite database to json file
# for insertion in other type of database

import os
import sys
import time

try:
    import sqlite3
    import json
except ImportError: sys.exit('\n\nPlease, install sqlite3 and json modules!\n\n')

starttime = time.time()

try: workpath = sys.argv[1]
except IndexError: sys.exit('No db defined!')
workpath = os.path.abspath(workpath)
if not os.path.exists(workpath): sys.exit('Invalid path!')

db = sqlite3.connect(workpath)
db.row_factory = sqlite3.Row
db.text_factory = str
cursor = db.cursor()
f = open(workpath + '.json', 'w')
for row in cursor.execute('SELECT * FROM results'):
    f.write(json.dumps(dict(row)) + "\n")
f.close()
print "%s.json done in %1.2f sec" % (workpath, time.time() - starttime)
