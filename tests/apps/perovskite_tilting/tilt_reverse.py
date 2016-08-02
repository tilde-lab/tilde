#!/usr/bin/env python

# Euler tilting angles extraction reverse test
# First, distort on the known angle, then extract tilting and check if it is the same
# Author: Evgeny Blokhin

import math
import random
import unittest
import six

from numpy import array

import set_path
from tilde.core.settings import settings
from tilde.core.api import API
from tilde.parsers import Output
from tilde.classifiers.perovskites import generate_random_perovskite
from tilde.apps.perovskite_tilting.perovskite_tilting import Perovskite_tilting

from ase.lattice.spacegroup import crystal


# First, work with ASE
# this is the cubic perovskite given in orthorhombic P n m lat, in order to allow arbitrary octahedral tilting
# NB: in Euler notation delta is gamma, delta plus/minus phi is alpha
# or in another terminology: phi is gamma, phi plus/minus psi is alpha

lat = round(random.uniform(3.5, Perovskite_tilting.OCTAHEDRON_BOND_LENGTH_LIMIT*2), 3)
phi = round(random.uniform(0, Perovskite_tilting.MAX_TILTING_DEGREE), 3)
theta = round(random.uniform(0, Perovskite_tilting.MAX_TILTING_DEGREE), 3)
psi = round(random.uniform(0, Perovskite_tilting.MAX_TILTING_DEGREE), 3)

perovskite = generate_random_perovskite(lat)

# Tilt octahedra
# NB: perovskite.rotate_euler(phi=math.radians(phi), theta=math.radians(theta), psi=math.radians(psi))
# does not suit because of spatial orientation!
perovskite._masked_rotate(center=array([lat*math.sqrt(2)/2, lat, lat*math.sqrt(2)/2]), axis='y', diff=math.radians(phi), mask=[0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1])
perovskite._masked_rotate(center=array([lat*math.sqrt(2)/2, lat, lat*math.sqrt(2)/2]), axis='x', diff=math.radians(theta), mask=[0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1])
perovskite._masked_rotate(center=array([lat*math.sqrt(2)/2, lat, lat*math.sqrt(2)/2]), axis='y', diff=math.radians(psi), mask=[0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 1])

# Second, incorporate ASE into tilde
settings['skip_unfinished'], settings['skip_notenergy'] = False, False
work = API(settings)
virtual_calc = Output() # we always consider "calculation" while using tilde
virtual_calc.structures = [ perovskite ]
virtual_calc, error = work.classify(virtual_calc)
if error: raise RuntimeError(error)

virtual_calc = work.postprocess(virtual_calc)
target_category_num = 4 # perovskite category, pre-defined in init-data.sql
is_perovskite = target_category_num in virtual_calc.info['tags']

class Reverse_Perovskite_Tilting_Test(unittest.TestCase):
    def test_if_perovskite(self):
        self.assertTrue(is_perovskite)

    def test_tilting(self):
        self.assertTrue(virtual_calc.apps.get('perovskite_tilting'))
        for pair in zip(
            list(six.itervalues(virtual_calc.apps['perovskite_tilting']['data']))[0],
            [phi, theta, psi]
        ):
            self.assertAlmostEqual(pair[0], pair[1], delta=0.02)

    def test_errors(self):
        self.assertTrue(virtual_calc.apps.get('perovskite_tilting'))
        self.assertFalse(virtual_calc.apps['perovskite_tilting']['error'])

if __name__ == "__main__":
    print("Test object:", virtual_calc.info['standard'])
    assert is_perovskite
    print("Octahedra tilted on:", phi, theta, psi)
    print("Extracted tilting is:", virtual_calc.apps['perovskite_tilting']['data'])
