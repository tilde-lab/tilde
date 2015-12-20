
import os, sys
import unittest
from numpy import inf

import set_path
import tilde.core.common as common


class Test_common(unittest.TestCase):
    def test_metric_values(self):
        self.assertEqual(common.metric([0, 0, 0]), [0, 0, 0])
        self.assertEqual(common.metric([-5, 5, 0]), [-1, 1, 0])
        self.assertEqual(common.metric([-inf, inf, 0]), [-1, 1, 0])

    def test_html_formula_values(self):
        self.assertEqual(common.html_formula('SrTiO3-d'), 'SrTiO<sub>3-d</sub>')
        self.assertEqual(common.html_formula('C11H22O5NS2'), 'C<sub>11</sub>H<sub>22</sub>O<sub>5</sub>NS<sub>2</sub>')

    def test_hrsize_values(self):
        self.assertEqual(common.hrsize(512*1024*1024*1020), '510.0GB')

    def test_urlregex_match_values(self):
        self.assertTrue(common.get_urlregex().match('ftp://test.test.test.test:8080/test?test=test#test/test'))

    def test_cmp_e_conv_values(self):
        self.assertEqual(common.cmp_e_conv([10000, 1000, 100, 99]), [3, 2, 0])
