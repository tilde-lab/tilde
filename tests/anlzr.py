#!/usr/bin/env python

# simple analyzer of a given path
# shows an example of using Tilde API

import sys
import os
import time
import pprint

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.api import API
from core.deps.ase.units import Hartree

#from core.deps.pymatgen.core.structure import Structure
#from core.deps.pymatgen.symmetry.bandstructure import HighSymmKpath

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
    print task
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
    
    print calc


