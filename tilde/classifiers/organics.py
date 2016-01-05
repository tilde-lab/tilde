
# Determines organic molecules by content
# Author: Evgeny Blokhin

import os
import sys


# hierarchy API: __order__ to apply classifier
__order__ = 30

def classify(tilde_obj):
    if not 'C' in tilde_obj.info['elements'] or not 'H' in tilde_obj.info['elements']:
        return tilde_obj
    elif tilde_obj.structures[-1].periodicity in [2, 3]:
        return tilde_obj
    tilde_obj.info['tags'].append(0x1)
    tilde_obj.info['expanded'] = 1 # this means formula reduce is prohibited

    return tilde_obj
