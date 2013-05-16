
import os
import sys


from core.deps.ase.data import chemical_symbols
from core.deps.ase.data import covalent_radii

# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 30
__properties__ = []


REL = 100

def classify(content_obj, tilde_obj):
    ''' reference single atom in vacuum:
    account of artificial 3 periodic box case '''
    if not len(content_obj['elements']) == 1 or content_obj['contents'][0] != 1: return content_obj
    
    if tilde_obj.structures[-1]['periodicity'] == 0 or \
    float( content_obj['dims'] / covalent_radii[chemical_symbols.index(content_obj['elements'][0])] ) > REL:
        # atomic radius should be REL times less than cell dimensions
        content_obj['tags'].append('isolated atom')
    
    return content_obj