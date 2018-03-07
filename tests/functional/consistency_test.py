
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
        'NPMJM53DWUEIKFSY66YC2ZJUF7L64KP2BS2JZGYLFDDTOCI',
        'LZFH3UU7VAKOEBXM523CWFI6HCOXDJ4CQ7J7YGNR3BYZMCI',
        '46AISOZQVLHNZZVZ53PPOTHRNHF3JRYYTECKNJ7QNMQXQCI',
        'ECBBIXBU723RUXCLZBDINU2JGMF53ZWVAXZ2SV62IMIAACI',
        'U6DLJBOGUN5JNT736TBXPCQVQPA4CPWCXWMVACMHLRDZGCI',
        'EPVVPXXAWI6K2D746ETSOSMHE42TKFWRIQJ4SUASFAZAECI'
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
        for checksum in self.db.session.query(model.Calculation.checksum).all():
            checksums.append(checksum[0])
        checksums.sort()
        self.expected_checksums.sort()
        try:
            self.assertTrue(
                checksums == self.expected_checksums,
                "\nExpected:\n%s.\nObtained:\n%s." % ("\n".join(self.expected_checksums), "\n".join(checksums))
            )
        except:
            TestLayerDB.failed = True
            raise
