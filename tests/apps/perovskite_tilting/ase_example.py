'''
An example of using Tilting module with ASE
'''

import unittest

from ase.lattice.spacegroup import crystal

import set_path
from tilde.core.settings import settings
from tilde.core.api import API
from tilde.parsers import Output


crystal_obj = crystal(
    ('Sr', 'Ti', 'O', 'O'),
    basis=[(0, 0.5, 0.25), (0, 0, 0), (0, 0, 0.25), (0.255, 0.755, 0)],
    spacegroup=140, cellpar=[5.511, 5.511, 7.796, 90, 90, 90],
    primitive_cell=True
)

settings['skip_unfinished'], settings['skip_notenergy'] = False, False
work = API(settings)

virtual_calc = Output() # we always consider "calculation" while using tilde
virtual_calc.structures = [ crystal_obj ]
virtual_calc, error = work.classify(virtual_calc)
if error:
    raise RuntimeError(error)

virtual_calc = work.postprocess(virtual_calc)
target_category_num = 4 # perovskite category, pre-defined in /init-data.sql
is_perovskite = target_category_num in virtual_calc.info['tags']


class ASE_Perovskite_Tilting_Test(unittest.TestCase):
    def test_if_perovskite(self):
        self.assertTrue(is_perovskite)

    def test_tilting(self):
        self.assertEqual(
            virtual_calc.apps['perovskite_tilting']['data'],
            {4: [0.0, 0.0, 1.15]}
        )

    def test_errors(self):
        self.assertFalse(virtual_calc.apps['perovskite_tilting']['error'])


if __name__ == "__main__":
    print "Object:", virtual_calc.info['standard']
    print "Is perovskite?", is_perovskite

    assert is_perovskite

    print virtual_calc.apps['perovskite_tilting']['data']

    assert virtual_calc.apps['perovskite_tilting']['data'] == {4: [0.0, 0.0, 1.15]}
