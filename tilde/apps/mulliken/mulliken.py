
# Visualize Mulliken charges from CRYSTAL in player
# using on3d manifest tag
# Author: Evgeny Blokhin

import os, sys

from tilde.core.common import ModuleError

class Mulliken():
    def __init__(self, tilde_calc):
        self.mull = {}

        for n, i in enumerate(tilde_calc.structures[-1].get_initial_charges()):
            self.mull[ n+1 ] = round(i, 2) # atomic index is counted from zero!
