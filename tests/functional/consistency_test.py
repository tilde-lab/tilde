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
        '3NTUXI3NWTY2NPCQHWU72JNLES6M3ZSQYADFOGHRJTF3KCI',
        '4LDHSPLVQX6SVFFJBFU722BWLXX4BHNEYGS6NF6RJRZBSCI',
        'CLRENNIUGMPCHF4A54A6PX2E5SAC7P7FUE4O3FJOXPMFECI',
        'FUYFQFNDQS76UGXIUC6PQCFOKRFDQNZ7XBUCN77VZUYCSCI',
        'H6HUBXKHKNHDCRQVTTHLYV6UPLKARNRQ2C67EDN45N6SOCI',
        'RX4B7JCMIALWZXSPVL4JQR37SJL2SZ44VKSSEQQ62X5U6CI'
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
        try:
            self.assertTrue(checksums == self.expected_checksums,
            "Unexpected calculation checksums occured: %s" % str(checksums))
        except:
            TestLayerDB.failed = True
            raise
