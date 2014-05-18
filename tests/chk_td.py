#!/usr/bin/env python

# example of data-mining on phonon TD (comparison of TD produced with CRYSTAL and phonopy)
#

import sys
import os
import math
import sqlite3
import json
import time

import numpy
numpy.seterr(all='ignore') # Caution!

starttime = time.time() # benchmarking

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.settings import check_db_version
from core.constants import Constants
from apps.vibtd.thermal_properties import ThermalProperties

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps/'))
from ase.units import Hartree


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

try: cursor.execute( 'SELECT info, phonons, apps FROM results WHERE phonons != "false" AND checksum IN (SELECT checksum FROM tags g INNER JOIN topics s ON g.tid=s.tid WHERE s.categ=22 AND s.topic=?)', ('CRYSTAL',) )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

print "\t\t\t Internal code\t\tExternal code   (eV)"
print "-"*100

while 1:
    row = cursor.fetchone()
    if not row: break
    info = json.loads(row['info'])
    p = json.loads(row['phonons'])
    a = json.loads(row['apps'])['vibtd']
    
    if not a: sys.exit('For ' + info['location'] + ' no TD data was found!')
    
    # gamma-projected eigenvalues
    eigenvalues = []
    for set in p:
        if hasattr(set, 'ph_k_degeneracy'): degeneracy_repeat = set['ph_k_degeneracy']
        else: degeneracy_repeat = 1

        # gamma-projected eigenvalues
        for i in set['freqs']:
            if i>=0: # only real!
                for d in range(0, degeneracy_repeat):
                    eigenvalues.append( (i*Constants.cm2THz)**2 )

    T = ThermalProperties(numpy.array([eigenvalues]), factor=1)
    
    # td property must exist
    if len(a['td']['t']) == 1:
        T.set_thermal_properties(
            t_max=a['td']['t'][0],
            t_min=a['td']['t'][0])
    else:
        T.set_thermal_properties(
            t_step = a['td']['t'][-1] - a['td']['t'][-2],
            t_max=a['td']['t'][-1],
            t_min=a['td']['t'][0])
    temps, vib, _, _ = T.thermal_properties

    # in CRYSTAL: THERMAL CONTRIBUTION TO THE VIBRATIONAL ENERGY + PRESSURE * VOLUME - TEMPERATURE * ENTROPY
    # in ThermalProperties class: ZPE added
    
    for i in range(len(vib)):
        vib[i] = vib[i] - T.zero_point_energy
    
    print info['location'], "x", info['expanded']    
    print 'ZPE\t', T.zero_point_energy / Constants.EvTokJmol, '\t', a['zpe']
    print 'vib.contrib at Tmax\t', vib[-1] / Constants.EvTokJmol, '\t', (a['td']['et'][-1] + a['td']['pv'][-1] - a['td']['ts'][-1]) * Hartree
    print "-"*100
    
print "Done in %1.2f sc" % (time.time() - starttime)
