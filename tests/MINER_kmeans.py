#!/usr/bin/env python

# example of data-mining on band gaps and periodic table element groups (binary compounds)
# using k-means as implemented in scikit-learn
# v040814

import sys, os, math, json, time

from sklearn.cluster import KMeans

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.settings import settings, connect_database
from core import model

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps'))
from sqlalchemy import func # NB subpackages use causes bug here
from ase.data import chemical_symbols

from pymatgen.core.periodic_table import Element


starttime = time.time()

db_choice = None
if settings['db']['engine'] == 'sqlite':
    try: db_choice = sys.argv[1]
    except IndexError: db_choice = settings['default_sqlite_db']

settings['debug_regime'] = False
session = connect_database(settings, db_choice)

print "DB: %s" % db_choice

# ^^^ the preparations above, the data-mining below VVV

data, ref = [], []
i, collected = 0, []

for n, s, e, r in session.query(func.distinct(model.Atom.number), model.Structure, model.Electrons, model.Struct_ratios) \
    .filter(model.Structure.id == model.Atom.struct_id, model.Electrons.sid == model.Structure.sid, model.Electrons.sid == model.Struct_ratios.sid, model.Structure.final == True, model.Struct_ratios.nelem == 2, model.Electrons.is_direct != 0, 0 < model.Electrons.gap, model.Electrons.gap < 15) \
    .order_by(model.Structure.sid) \
    .all():
    i += 1
    el = Element(chemical_symbols[n])
    group = 3 if el.is_lanthanoid or el.is_actinoid else el.group
    collected.append(group)
    if not i % 2:
        item = [e.gap]
        collected.sort()
        item.extend(collected)
        data.append(item)
        ref.append([r.chemical_formula, e.gap])

        collected = []

kmeans = KMeans(n_clusters=10)
kmeans.fit(data)
clusters = {}
for n, i in enumerate(kmeans.labels_):
    try: clusters[i].append(ref[n])
    except KeyError: clusters[i] = [ ref[n] ]

for k, v in clusters.iteritems():
    print "-"*100
    print 'Cluster', (k+1)
    print "-"*100

    formulae_gaps = {}
    for i in v:
        try: formulae_gaps[i[0]].append(i[1])
        except KeyError: formulae_gaps[i[0]] = [ i[1] ]
        #print "\t", i[0], i[1]
    for kk, vv in formulae_gaps.iteritems():
        print "\t", kk, min(vv), "----", max(vv), "eV"

print "Done in %1.2f sc" % (time.time() - starttime)
