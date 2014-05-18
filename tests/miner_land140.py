#!/usr/bin/env python

import sys
import os
import math
import json
import time

starttime = time.time() # benchmarking

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.settings import settings, connect_database, check_db_version
from core.common import dict2ase
from ase.lattice.spacegroup.cell import cell_to_cellpar

db_choice = None
if settings['db']['type'] == 'sqlite':
    try: db_choice = sys.argv[1]
    except IndexError: sys.exit('No DB name defined!')
    
db = connect_database(settings, db_choice)
if not db: sys.exit('Connection to DB failed!')

# check DB_SCHEMA_VERSION
incompatible = check_db_version(db)
if incompatible:
    sys.exit('Sorry, database ' + workpath + ' is incompatible.')

# ^^^ the obligatory code above, the actual procedures of interest below VVV

cursor = db.cursor()
sql = 'SELECT info, apps, structures, energy FROM results ORDER BY energy ASC LIMIT 10'
try: cursor.execute( sql )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

min_val, max_val = [], []
min_names, max_names = [], []

print "Landscape optimisation results:"
while 1:
    row = cursor.fetchone()
    if not row: break
    item = json.loads(row[0])
    apps = json.loads(row[1])
    s = json.loads(row[2])[-1]
    r = dict2ase(json.loads(item['refinedcell']))
    c = cell_to_cellpar(r.cell)
    
    print row[3], apps['tilting'], item['location']
    if item['ng'] == 140: print (c[2]/2)/(c[0]/math.sqrt(2))
