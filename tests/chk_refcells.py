#!/usr/bin/env python

import sys
import os
import math
import sqlite3
import json
import time

starttime = time.time() # benchmarking

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.settings import check_db_version
from core.common import dict2ase

from core.deps.ase.lattice.spacegroup.cell import cell_to_cellpar

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
    sys.exit('Sorry, database ' + workpath + ' is incompatible.')

# ^^^ above was the obligatory formal code, the actual procedures of interest are below VVV

try: cursor.execute( 'SELECT structures, info, apps FROM results WHERE checksum IN (SELECT checksum FROM tags WHERE tid IN (SELECT tid FROM topics WHERE categ=8 AND topic=?) INTERSECT SELECT checksum FROM tags WHERE tid IN (SELECT tid FROM topics WHERE categ=22 AND topic=?))', ('perovskite', 'CRYSTAL', ) )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

while 1:
    row = cursor.fetchone()
    if not row: break
    
    '''c1 = dict2ase( json.loads(row['structures'])[-1] )
    c2 = dict2ase( json.loads( json.loads(row['info'])['refinedcell'] ) )
    
    print cell_to_cellpar(c1.cell).tolist()
    print cell_to_cellpar(c2.cell).tolist()
    print "-"*50'''
    
    a = json.loads(row['info'])
    print a['standard']
    
print "Done in %1.2f sc" % (time.time() - starttime)
