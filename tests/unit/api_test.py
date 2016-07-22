
import os, sys
import unittest

import set_path
from tilde.core.api import API
from tilde.core.settings import BASE_DIR, ROOT_DIR, EXAMPLE_DIR


class Test_API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = API()

    def test_count_classifiers(self):
        available_classifiers = []
        path = os.path.realpath(BASE_DIR + '/../classifiers')
        for classifierpath in os.listdir(path):
            if os.path.isfile(os.path.join(path, classifierpath)) and classifierpath.endswith('.py') and classifierpath != '__init__.py':
                available_classifiers.append(classifierpath)

        self.assertEqual(len(self.sample.Classifiers), len(available_classifiers),
            "Expected to have %s, but got %s modules. May be unused classifier occured since?" % (len(available_classifiers), len(self.sample.Classifiers)))

    def test_formula(self):
        self.assertEqual(self.sample.formula(['H', 'O', 'C', 'H', 'H', 'C', 'H', 'H', 'H' ]), 'C2H6O', "Formula was errorneously generated!")

    def test_savvyize_simple(self):
        path = os.path.join(EXAMPLE_DIR, 'CRYSTAL')
        found = self.sample.savvyize(path)
        self.assertEqual(len(found), 3,
            "Unexpected number of files has been found in %s: %s. May be number of files has been changed since?" % (path, len(found)))

    def test_savvyize_recursive(self):
        path = os.path.join(EXAMPLE_DIR, 'VASP')
        found = self.sample.savvyize(path, recursive=True)
        self.assertEqual(len(found), 2,
            "Unexpected number of files has been found in %s: %s. May be number of files has been changed since?" % (path, len(found)))

    def test_savvyize_stemma(self):
        path = os.path.join(ROOT_DIR, 'utils/bilbao')
        found = self.sample.savvyize(path, recursive=True, stemma=True)
        self.assertEqual(len(found), 2,
            "Unexpected number of files has been found in %s: %s. May be number of files has been changed since?" % (path, len(found)))

