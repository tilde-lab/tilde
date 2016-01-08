#!/usr/bin/env python
"""
Query band gaps for those calculations,
which possess the minimal total energy
of those sharing the same chemical formula
(wrt unit cell), from a Tilde database
"""
import sys, os
import time

from sqlalchemy import func, and_

import set_path
from tilde.core.settings import settings, connect_database
from tilde.core import model


starttime = time.time()
db_choice = None
if settings['db']['engine'] == 'sqlite':
    try: db_choice = sys.argv[1]
    except IndexError: db_choice = None
settings['debug_regime'] = False
session = connect_database(settings, db_choice)

print "Formula (per cell)  band gap, eV  tfile"

emin_query = session.query(
    func.min(model.Energy.total).label('emin'),
    model.Struct_ratios.chemical_formula,
    model.Struct_ratios.formula_units
).filter(model.Energy.checksum == model.Struct_ratios.checksum) \
.group_by(model.Struct_ratios.chemical_formula, model.Struct_ratios.formula_units) \
.subquery()

for checksum, e, formula, cell_units, gap, fname in session.query(
    model.Energy.checksum,
    model.Energy.total,
    model.Struct_ratios.chemical_formula,
    model.Struct_ratios.formula_units,
    model.Electrons.gap,
    model.Metadata.location
    ).join(model.Struct_ratios, model.Energy.checksum == model.Struct_ratios.checksum) \
    .join(model.Electrons, model.Energy.checksum == model.Electrons.checksum) \
    .join(model.Metadata, model.Energy.checksum == model.Metadata.checksum) \
    .join(emin_query, and_(
        model.Energy.total == emin_query.c.emin,
        model.Struct_ratios.chemical_formula == emin_query.c.chemical_formula,
        model.Struct_ratios.formula_units == emin_query.c.formula_units
    )) \
    .filter(model.Electrons.gap > 0) \
    .order_by(model.Electrons.gap) \
    .all():
    print "%s(%s)    %s    %s" % (formula, cell_units, gap, fname)

print "Done in %1.2f sc" % (time.time() - starttime)
