
# refines cell and stores it for further investigations

import os, sys

from core.symmetry import SymmetryFinder


# hierarchy API: __order__ to apply classifier
__order__ = 1

def classify(tilde_obj):
    symm = SymmetryFinder()
    symm.refine_cell(tilde_obj)
    if symm.error:
        raise RuntimeError(symm.error)
    else:
        tilde_obj.info['properties']['refinedcell'] = symm.refinedcell
        
    return tilde_obj
