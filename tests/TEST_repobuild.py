#!/usr/bin/env python

# Repo build test

import os, sys, time

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.api import API
from core.settings import settings, connect_database, EXAMPLE_DIR


starttime = time.time()

settings['db']['engine'] == 'sqlite'
dbname = '%s.db' % time.strftime("%m%d_%H%M%S")

session = connect_database(settings, dbname)
work = API(session = session)
tasks = work.savvyize(EXAMPLE_DIR, True) # True means recursive

print 'Repo build test: %s\n\n' % dbname

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
        
    calc = work.postprocess(calc)
    checksum, error = work.save(calc)
    if error:
        print filename, error
        continue

    print filename + " added"

print "\n\nItems added:", work.count()
print "Test repository done in %1.2f sec" % (time.time() - starttime)
