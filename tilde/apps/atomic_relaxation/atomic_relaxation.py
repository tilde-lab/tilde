
# Calculation of atomic relaxations
# during atomic structure optimization
# Author: Evgeny Blokhin

import os, sys
import math

from tilde.core.common import ModuleError

class Atomic_relaxation():
    def __init__(self, tilde_calc):
        self.ardata = {}
        if len(tilde_calc.structures[0]) != len(tilde_calc.structures[-1]):
            raise ModuleError('Different number of atoms before and after optimization!')
        for n in range(len(tilde_calc.structures[0])):
            # atomic index is counted from zero!
            # NB: in case of relaxation is more than a cell vector
            # a proper centring must be accounted!
            self.ardata[ n+1 ] = round(math.sqrt( \
            (tilde_calc.structures[-1][n].x - tilde_calc.structures[0][n].x)**2 + \
            (tilde_calc.structures[-1][n].y - tilde_calc.structures[0][n].y)**2 + \
            (tilde_calc.structures[-1][n].z - tilde_calc.structures[0][n].z)**2 \
            ), 2)
