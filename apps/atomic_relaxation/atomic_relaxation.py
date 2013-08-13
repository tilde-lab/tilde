
# Calculation of atomic relaxations
# during atomic structure optimization

import os
import sys
import math

from core.common import ModuleError

class Atomic_relaxation():
    def __init__(self, tilde_calc):
        self.ardata = {}
        if len(tilde_calc.structures[0]) != len(tilde_calc.structures[-1]):
            raise ModuleError('Different number of atoms before and after optimization!')
        for n in range(len(tilde_calc.structures[0]['atoms'])):
            # atomic index is counted from zero!
            # NB: in case of relaxation is more than a cell vector
            # a proper centring must be accounted!
            self.ardata[ n+1 ] = round(math.sqrt( \
            (tilde_calc.structures[-1]['atoms'][n][1] - tilde_calc.structures[0]['atoms'][n][1])**2 + \
            (tilde_calc.structures[-1]['atoms'][n][2] - tilde_calc.structures[0]['atoms'][n][2])**2 + \
            (tilde_calc.structures[-1]['atoms'][n][3] - tilde_calc.structures[0]['atoms'][n][3])**2 \
            ), 2)
