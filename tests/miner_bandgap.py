#!/usr/bin/env python

# example of data-mining on minimal-energy band gaps
#

import sys
import os
import math
import psycopg2
import json
import time

starttime = time.time() # benchmarking

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.settings import check_db_version

'''try: workpath = sys.argv[1]
except IndexError: sys.exit('No path defined!')
workpath = os.path.abspath(workpath)
if not os.path.exists(workpath): sys.exit('Invalid path!')'''


db = psycopg2.connect("dbname=tilde user=eb")
#db.row_factory = sqlite3.Row
#db.text_factory = str
cursor = db.cursor()

# check DB_SCHEMA_VERSION
incompatible = check_db_version(db)
if incompatible:
    sys.exit('Sorry, database ' + workpath + ' is incompatible.')

# ^^^ above was the obligatory formal code, the actual procedures of interest are below VVV

try: cursor.execute( 'SELECT info, energy FROM results' )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

objects = {}

while 1:
    row = cursor.fetchone()
    if not row: break
    item = json.loads(row[0])
    item['e'] = row[1]
    if not item['standard'] in objects:
        if 'bandgap' in item and 0 < item['bandgap'] < 15: # avoid non-physical things
            objects[ item['standard'] ] = {'e': item['e'], 'gap': item['bandgap'] }
    else:
        if objects[ item['standard'] ]['e'] > item['e'] and 'bandgap' in item and 0 < item['bandgap'] < 15: # avoid non-physical things:
            objects[ item['standard'] ] = {'e': item['e'], 'gap': item['bandgap'] }

if not objects: sys.exit('DB contents do not satisfy the criteria!')

# sorting
gaps, formulae = [ i['gap'] for i in objects.values() ], objects.keys()
gaps, formulae = zip( *sorted( zip(gaps, formulae) ) ) # sorting in accordance, by first

for n, i in enumerate(formulae):
    if gaps[n]:
        print i, "\t", gaps[n]

print "Done in %1.2f sc" % (time.time() - starttime)
