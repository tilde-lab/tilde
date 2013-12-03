
# Tilde project: FHI-aims text logs parser and normalizer
# should contain the code written by Fawzi for the NoMaD project
# v271113

import os
import sys
import re
import math

from numpy import dot, array

# the imports below are handled dynamically

from ase.lattice.spacegroup.cell import cell_to_cellpar
from ase.units import Bohr, Hartree, Rydberg

from parsers import Output


class FHI(Output):
    def __init__(self, file, **kwargs):
        Output.__init__(self, file)
        
        cur_folder = os.path.dirname(file)
        
        self.info['finished'] = -1
        
        self.fh = open(file, 'r')
        while 1:
            str = self.fh.readline()
            if not str: break

    @staticmethod
    def fingerprints(test_string):
        if "FHI-Aims main output file fingerprint to be found in its first 700 lines" in test_string: return True
        else: return False
