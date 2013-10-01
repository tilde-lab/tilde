#!/usr/bin/env python

# simple analyzer of a given path
# shows an example of using Tilde API

import sys
import os
import time
import pprint

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../'))  # path to Tilde root folder

from core.api import API
from core.deps.ase.units import Hartree

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

