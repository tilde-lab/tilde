
# Try to determine reference atomic calculation in vacuum (an artificial 3-periodic box case)
# Author: Evgeny Blokhin

from numpy.linalg import det

from ase.data import chemical_symbols, covalent_radii


# hierarchy API: __order__ to apply classifier
__order__ = 30


REL = 100

def classify(tilde_obj):
    if not len(tilde_obj.info['elements']) == 1 or tilde_obj.info['contents'][0] != 1: return tilde_obj

    dims = tilde_obj.info['dims'] if tilde_obj.structures[-1].periodicity == 3 else abs(det(tilde_obj.structures[-1].cell))

    if tilde_obj.structures[-1].periodicity == 0 or \
    float( dims / covalent_radii[chemical_symbols.index(tilde_obj.info['elements'][0])] ) > REL:

        # atomic radius should be REL times less than cell dimensions
        tilde_obj.info['periodicity'] = -1
        tilde_obj.structures[-1].periodicity = -1

    return tilde_obj
