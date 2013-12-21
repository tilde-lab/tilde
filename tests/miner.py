#!/usr/bin/env python

# example of data-mining in Tilde on band gaps
#

import sys
import os
import math
import sqlite3
import json
import time

starttime = time.time() # benchmarking

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.settings import check_db_version

try: workpath = sys.argv[1]
except IndexError: sys.exit('No path defined!')
workpath = os.path.abspath(workpath)
if not os.path.exists(workpath): sys.exit('Invalid path!')


db = sqlite3.connect(os.path.abspath(workpath))
db.row_factory = sqlite3.Row
db.text_factory = str
cursor = db.cursor()

# check DB_SCHEMA_VERSION
incompatible = check_db_version(db)
if incompatible:
    sys.exit('Sorry, database ' + DATA_DIR + os.sep + uc + ' is incompatible.')

try: cursor.execute( 'SELECT info, energy FROM results' )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

objects = {}

while 1:
    row = cursor.fetchone()
    if not row: break
    item = json.loads(row['info'])
    item['e'] = row['energy']
    if not item['standard'] in objects:
        if 'bandgap' in item and 0 < item['bandgap'] < 15: # avoid non-physical things
            objects[ item['standard'] ] = {'e': item['e'], 'gap': item['bandgap'] }
    else:
        if objects[ item['standard'] ]['e'] > item['e'] and 'bandgap' in item and 0 < item['bandgap'] < 15: # avoid non-physical things:
            objects[ item['standard'] ] = {'e': item['e'], 'gap': item['bandgap'] }


gaps, formulae = [ i['gap'] for i in objects.values() ], objects.keys()
gaps, formulae = zip( *sorted( zip(gaps, formulae) ) ) # sorting in accordance, by first

for n, i in enumerate(formulae):
    if gaps[n]:
        print i, gaps[n]

print "Done in %1.2f sc" % (time.time() - starttime)
