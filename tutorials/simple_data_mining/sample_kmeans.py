#!/usr/bin/env python
"""
Testing k-means clustering
for purely random and normally distributed data
"""
import os
import math
import random
from numpy import array, random as numpy_random
from ase.data import chemical_symbols

from kmeans import Point, kmeans, k_from_n
from element_groups import get_element_group
from set_path import VIS_PATH


DISTRIB = 'GAUSSIAN'
data, ref = [], []
N = 200

def gaussian_distribution(N, k):
    n = float(N)/k
    X = []
    for i in range(k):
        init = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))
        s = random.uniform(0.05, 0.5)
        x = []
        while len(x) < n:
            a, b, c = array([numpy_random.normal(init[0], s), numpy_random.normal(init[1], s), numpy_random.normal(init[2], s)])
            if abs(a) < 1 and abs(b) < 1 and abs(c) < 1:
                x.append([a,b,c])
        X.extend(x)
    X = array(X)[:N]
    return X

if DISTRIB == 'RANDOM':
    set_x, set_y = [random.choice(chemical_symbols) for i in range(N)], [random.choice(chemical_symbols) for i in range(N)]
    set_z = [round(random.uniform(0.1, 15.0), 2) for i in range(N)]
    data, ref = [], []
    for i in range(N):
        formula = set_x[i] + set_y[i]
        set_x[i] = get_element_group(chemical_symbols.index(set_x[i]))
        set_y[i] = get_element_group(chemical_symbols.index(set_y[i]))
        data.append(Point([set_x[i], set_y[i], set_z[i]], formula))
        ref.append([set_x[i], set_y[i], set_z[i]])

else:
    nte = len(chemical_symbols)
    G = gaussian_distribution(N, k_from_n(N))

    set_x = (G[:,0] + 1)/2*nte
    set_x = map(lambda x: int(math.floor(x)), set_x.tolist())

    set_y = (G[:,1] + 1)/2*nte
    set_y = map(lambda x: int(math.floor(x)), set_y.tolist())

    set_z = (G[:,2] + 1)/2*15
    set_z = map(lambda x: round(x, 2), set_z.tolist())

for i in range(N):
    formula = chemical_symbols[set_x[i]] + chemical_symbols[set_y[i]]
    set_x[i] = get_element_group(set_x[i])
    set_y[i] = get_element_group(set_y[i])
    data.append(Point([set_x[i], set_y[i], set_z[i]]))
    ref.append([set_x[i], set_y[i], set_z[i], formula])

clusters = kmeans(data, k_from_n(len(data)))

points_file = os.path.join(VIS_PATH, "points.csv")
cluster_file = os.path.join(VIS_PATH, "clusters.csv")

with open(points_file, "w") as s:
    s.write("x,y,z,label\n")
    for n, i in enumerate(ref):
        s.write(",".join(map(str, i)) + "\n")

with open(cluster_file, "w") as s:
    s.write("x,y,z\n")
    for n, c in enumerate(clusters, 1):
        for p in c.points:
            s.write(",".join(map(str, p.coords)) + "\n")
        s.write("-,-,-\n")

print(points_file)
print(cluster_file)