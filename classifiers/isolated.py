
# tries to determine reference atomic calculation in vacuum

import os
import sys

from core.deps.ase.data import chemical_symbols
from core.deps.ase.data import covalent_radii


# hierarchy API: __order__ to apply classifier
__order__ = 30


REL = 100

def classify(tilde_obj):
    ''' reference single atom in vacuum:
    account of artificial 3 periodic box case '''
    if not len(tilde_obj.info['elements']) == 1 or tilde_obj.info['contents'][0] != 1: return tilde_obj

    if tilde_obj.structures[-1].periodicity == 0 or \
    float( tilde_obj.info['dims'] / covalent_radii[chemical_symbols.index(tilde_obj.info['elements'][0])] ) > REL:

        # atomic radius should be REL times less than cell dimensions
        tilde_obj.info['tags'].append('isolated atom')
        tilde_obj.info['dims'] = False

    return tilde_obj
