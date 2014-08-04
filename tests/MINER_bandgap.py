#!/usr/bin/env python

# example to query minimal-total-energy band gaps
# v040814

import sys, os, math, json, time

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.settings import settings, connect_database
from core import model

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps'))
from sqlalchemy import func # NB subpackages use causes bug here


starttime = time.time()

db_choice = None
if settings['db']['engine'] == 'sqlite':
    try: db_choice = sys.argv[1]
    except IndexError: db_choice = settings['default_sqlite_db']

settings['debug_regime'] = False
session = connect_database(settings, db_choice)

print "DB: %s" % db_choice

# ^^^ the preparations above, the data-mining below VVV

for i, j, k, l in session.query(func.min(model.Energy.total), model.Structure, model.Struct_ratios, model.Electrons) \
    .filter(model.Energy.sid == model.Structure.sid, model.Energy.sid == model.Struct_ratios.sid, model.Energy.sid == model.Electrons.sid, model.Structure.final == True, model.Electrons.is_direct != 0, 0 < model.Electrons.gap, model.Electrons.gap < 15) \
    .group_by(model.Struct_ratios.chemical_formula) \
    .order_by(model.Electrons.gap) \
    .all():
    print k.chemical_formula, "\t", l.gap

print "Done in %1.2f sc" % (time.time() - starttime)
