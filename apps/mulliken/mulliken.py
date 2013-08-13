
# Visualize Mulliken charges from CRYSTAL in player
# using on3d manifest tag

import os
import sys
import math

from core.common import ModuleError

class Mulliken():
    def __init__(self, tilde_calc):
        self.mull = {}
        if len(tilde_calc.structures[0]['atoms']) != len(tilde_calc.charges):
            raise ModuleError('Inconsistent number of charges!')
        for n in range(len(tilde_calc.structures[0]['atoms'])):
            # atomic index is counted from zero!
            if tilde_calc.structures[0]['atoms'][n][0] != tilde_calc.charges[n][0]:
                raise ModuleError('Charges do not match to structure!')
            self.mull[ n+1 ] = round(tilde_calc.charges[n][1], 2)
