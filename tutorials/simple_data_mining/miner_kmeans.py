#!/usr/bin/env python
"""
Example of data-mining on
band gaps vs. periodic groups
for binary compounds, using k-means clustering
"""
import sys, os
import time

from sqlalchemy import func, and_
from kmeans import Point, kmeans, k_from_n
from element_groups import get_element_group

from set_path import VIS_PATH
from tilde.core.settings import settings, connect_database
from tilde.core import model


points_file = os.path.join(VIS_PATH, "points.csv")
cluster_file = os.path.join(VIS_PATH, "clusters.csv")

starttime = time.time()
db_choice = None
if settings['db']['engine'] == 'sqlite':
    try: db_choice = sys.argv[1]
    except IndexError: db_choice = None
settings['debug_regime'] = False
session = connect_database(settings, db_choice)

emin_query = session.query(
    func.min(model.Energy.total).label('emin'),
    model.Struct_ratios.chemical_formula,
    model.Struct_ratios.formula_units
).filter(model.Energy.checksum == model.Struct_ratios.checksum) \
.group_by(model.Struct_ratios.chemical_formula, model.Struct_ratios.formula_units) \
.subquery()

data = []
i, collected = 0, []
for elnum, gap, formula, e in session.query(func.distinct(model.Atom.number), model.Electrons.gap, model.Struct_ratios.chemical_formula, model.Energy.total) \
    .join(model.Structure, model.Atom.struct_id == model.Structure.struct_id) \
    .join(model.Electrons, model.Electrons.checksum == model.Structure.checksum) \
    .join(model.Struct_ratios, model.Electrons.checksum == model.Struct_ratios.checksum) \
    .join(model.Energy, model.Electrons.checksum == model.Energy.checksum) \
    .join(emin_query, and_(
        model.Energy.total == emin_query.c.emin,
        model.Struct_ratios.chemical_formula == emin_query.c.chemical_formula,
        model.Struct_ratios.formula_units == emin_query.c.formula_units
    )).filter(model.Struct_ratios.nelem == 2, model.Electrons.gap > 0) \
    .order_by(model.Electrons.gap) \
    .all():
    i += 1
    collected.append(get_element_group(elnum))
    if not i % 2:
        collected.sort()
        data.append(Point(collected + [gap], reference=formula))
        collected = []

with open(points_file, "w") as s:
    s.write("x,y,z,label\n")
    for n, pnt in enumerate(data):
        s.write(",".join(map(str, pnt.coords) + [pnt.reference]) + "\n")

clusters = kmeans(data, k_from_n(len(data)))

with open(cluster_file, "w") as s:
    s.write("x,y,z,label\n")
    for n, cluster in enumerate(clusters, 1):
        for pnt in cluster.points:
            s.write(",".join(map(str, pnt.coords) + [pnt.reference]) + "\n")
        s.write("-,-,-,-\n")

print points_file
print cluster_file
print "\nDone in %1.2f sc" % (time.time() - starttime)
