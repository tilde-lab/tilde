#!/usr/bin/env python

# simple analyzer of a given path
# shows an example of using Tilde API

import sys
import os
import time
import pprint

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))  # path to Tilde root folder

import traceback

from core.api import API
from core.deps.ase.units import Hartree

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../core'))
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../core/deps'))
from core.deps.pymatgen.core.structure import Structure
from core.deps.pymatgen.symmetry.bandstructure import HighSymmKpath

from numpy import dot
from numpy import array
from numpy import cross

starttime = time.time()

try:
    workpath = sys.argv[1]
except IndexError:
    raise RuntimeError('No file / folder defined!')
if not os.path.exists(os.path.abspath(workpath)):
    raise RuntimeError('Invalid path!')

work = API()

tasks = work.savvyize(workpath, True)  # False means non-recursive

#print len(tasks)
#print "Done in %1.2f sc" % (time.time() - starttime)

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

    subprograms = work.postprocess(calc)
    
    # Mulliken test
    #mull_sum = round(sum(calc.structures[-1].get_initial_charges()), 2)
    #assert mull_sum == 0.0, "Sum of charges is %s" % mull_sum
        
    # bridge with pymatgen k-point finder
    # currently serves the only aim to determine the labels of k-points


    PMGS = Structure(calc.structures[-1].get_cell(), calc.structures[-1].get_chemical_symbols(), calc.structures[-1].get_positions(), coords_are_cartesian=True)
        
    try: k = HighSymmKpath(PMGS)
    except:
        #exc_type, exc_value, exc_tb = sys.exc_info()
        #error = "".join(traceback.format_exception( exc_type, exc_value, exc_tb ))
        #raise RuntimeError("Pymatgen exception:\n" + error)
        raise RuntimeError("Pymatgen exception!")
    
    kpts, klbl = k.get_kpoints(1)
    pathway = []
    for i in klbl:
        print i, k.kpath['kpoints'][i]
    
    #for k, v in k.kpath['kpoints'].iteritems():
    #   print k, 
        
    
    #e = calc.electrons['bands'].todict()
    #print calc.electrons['bands'].todict()
    #print e['abscissa']
    #for i in e['stripes']:
    #    print i

