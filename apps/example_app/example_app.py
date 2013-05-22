
# Tilde API demo
# calculates molecular weight for organic molecules

import os
import sys

# deps third-party code and common routines
# here are already available:
from ase.data import chemical_symbols
from ase.data import atomic_masses
from core.common import ModuleError


class Example_app():
    # this determines how the data should be represented in a table cell
    @staticmethod
    def cell_wrapper(obj, colnum):
        selfname = __name__.split('.')[-1]
        if not selfname in obj['apps']:
            return "<td rel=%s><div class=tiny>n/a</div></td>" % colnum
        return "<td rel=%s class=your_own_code>%s</td>" % (colnum, obj['apps'][selfname])

    # this is a main class code
    def __init__(self, tilde_calc):
        self.weight = 0
        for a in [atom[0] for atom in tilde_calc.structures[-1]['atoms']]:
            if not a in chemical_symbols:
                raise ModuleError('Unexpected atom has been found!')
            try:
                self.weight += atomic_masses[chemical_symbols.index(a)]
            except IndexError:
                raise ModuleError('Application error!')
        self.weight = round(self.weight)
