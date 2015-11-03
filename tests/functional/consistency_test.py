#!/usr/bin/env python

# Repo basic consistency test
# Author: Evgeny Blokhin

import os, sys
import logging

import set_path
import tilde.core.model as model
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


logger = logging.getLogger('tilde')
logger.setLevel(logging.INFO)

class Test_Consistency(TestLayerDB):
    __test_calcs_dir__ = EXAMPLE_DIR
    example_calc_count = 6
    expected_performance = 5
    expected_checksums = ["HKQI3PNB4SJKFKVKEZG4QMKOYPWF7N6N4H2ZWM3KGRY5QCI", "DIJZ5IMV3OXIISTLIOAHCWZG6T5ANWRWFP75MNCDDCSGUCI", "V3MYGXYORMRSAYFR4WN4MSX3L6JI2DE7E3QRC4KYTXMDGCI", "HYO6KU4ZBQWJJIGLO3DFO44DBO2LVZGYEHTPEIDEK2WGMCI", "2IW5NGDADU5OOPBG2GMYKRJ7UR567QAKK6P53DAJB3UGICI", "VRJEXXLLDTSSIQEV3KJWDERFCXZBDDIH7VT2C7TGFU2U4CI"]

    @classmethod
    def setUpClass(cls):
        super(Test_Consistency, cls).setUpClass(dbname=__name__.split('.')[-1])

    def test_repocount(self):
        cnt = self.engine.count(self.db.session)
        try: self.assertEqual(cnt, self.example_calc_count,
            "Unexpected number of calculations in DB: %s. Expected: %s. May be number of example calculations has been changed since?" % (cnt, self.example_calc_count))
        except:
            TestLayerDB.failed = True
            raise

    def test_perf(self):
        try: self.assertTrue(self.perf < self.expected_performance,
            "Repo building takes unexpectedly too much time!")
        except:
            TestLayerDB.failed = True
            raise

    def test_checksums(self):
        checksums = []
        for i in self.db.session.query(model.Calculation.checksum).all():
            checksums.append(i[0])
        checksums.sort()
        self.expected_checksums.sort()
        try: self.assertTrue(checksums == self.expected_checksums,
            "Unexpected calculation checksums occured!")
        except:
            TestLayerDB.failed = True
            raise
