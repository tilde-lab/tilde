#!/usr/bin/env python

# Repo basic consistency test
# Author: Evgeny Blokhin

import tilde.core.model as model
from tilde.core.settings import EXAMPLE_DIR
from . import TestLayerDB


class Test_Consistency(TestLayerDB):
    __test_calcs_dir__ = EXAMPLE_DIR
    example_calc_count = 6
    expected_performance = 9
    expected_checksums = [
        "OLRUC4GMJKHKOFIEQIDNQBJDII4UH5WQCGQRO5MXD36GSCI",
        "YDRXN2CSNG5V7MWNEJL5ARYUJRULG7NHJUUGKI54GXSLACI",
        "QAUCR3RTS6FKE4SAJE57SWXNJVXMWWJGEXPDRFDRSIODICI",
        "MEVEQ626BA3GJWOYL7FPOWBXPTINKESSZM7YRI3IIAGK4CI",
        "QZAKBZE26UUMBYJBDDG7XBNYN5IZJJAAW3VI5OJ2CJPXCCI",
        "R6BFJTRJUQ3C5QVGQCSGGZC7FHKAPAFHU7GIAT23AEMIMCI"
    ]

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
            "Repo building takes unexpectedly too much time: %s sec against %s sec expected" % (self.perf, self.expected_performance))
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
