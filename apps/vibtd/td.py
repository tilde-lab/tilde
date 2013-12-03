#!/usr/bin/env python

# Tilde project: vibrational TD contribution calculator
# CURRENTLY NOT PLUGGED IN INSIDE TILDE!
# v161111

import os
import sys

try: import json
except ImportError: import simplejson as json

import numpy as np
from thermal_properties import ThermalProperties

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../../'))
from core.api import API

'''
import sqlite3
sys.path.append(os.path.realpath(os.path.dirname(__file__)) + '/../../core')
from settings import settings
np.seterr(all='raise')
try:
    hash = sys.argv[1]
except IndexError: raise RuntimeError('No input defined!')
conn = sqlite3.connect(settings['db_path'])
c = conn.cursor()
try: c.execute( 'SELECT phonons, energy FROM results WHERE checksum = ?', (hash,) )
except: raise RuntimeError('SQLite error: ' + str( sys.exc_info()[1] ))
finally: row = c.fetchone()
if not row: raise RuntimeError('No data found!')

freqs = json.loads(row[0])
try: e = float( row[1] )
except TypeError: e = 0.0
'''

try:
    workpath = sys.argv[1]
except IndexError:
    raise RuntimeError('No file / folder defined!')
if not os.path.exists(os.path.abspath(workpath)):
    raise RuntimeError('Invalid path!')

work = API()

tasks = work.savvyize(workpath, False)  # False means non-recursive
filename = os.path.basename(tasks[0])

calc, error = work.parse(tasks[0])
if error:
    if not 'nothing found' in error:
        print filename, error

        
factor = 1
cm2THz = 0.0299792458
EvTokJmol = 96.4853910
kJmolToAucel = 0.00038088

# prepare gamma-projected eigvals according to phonopy format
eigenvalues = []
for k, set in calc.phonons['modes'].iteritems():
    try: calc.phonons['ph_k_degeneracy'][k]
    except (KeyError, TypeError):
        calc.phonons['ph_k_degeneracy'] = {k: 1}
    for f in set:
        for d in range(0, calc.phonons['ph_k_degeneracy'][k]):
            if f<0: eigenvalues.append( -(f*cm2THz)**2 )
            else: eigenvalues.append( (f*cm2THz)**2 )

T = ThermalProperties(np.array([eigenvalues]), factor=factor)
print T.zero_point_energy * kJmolToAucel / 8

#T.set_thermal_properties(t_step=16, t_max=2005, t_min=5)
#temps, vib, entropy, heat = T.thermal_properties

'''
# vib should be THERMAL CONTRIBUTION TO THE VIBRATIONAL ENERGY + PRESSURE * VOLUME - TEMPERATURE * ENTROPY
# but phonopy defines it with ZPE, so workaround is needed
for i in range(len(vib)):
    vib[i] = (vib[i] - T.zero_point_energy) / EvTokJmol

td = {'t': temps.tolist(), 'zpe': T.zero_point_energy, 'etot': e, 'evib': vib.tolist(), 'c': heat.tolist()}
'''
