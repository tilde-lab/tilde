
# determines organic molecules

import os
import sys


# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 30
__properties__ = []

def classify(content_obj, tilde_obj):
    ''' classification of organic compounds by content '''
    if not 'C' in content_obj['elements'] or not 'H' in content_obj['elements']: return content_obj
    elif tilde_obj.structures[-1]['periodicity'] in [2, 3]: return content_obj
    content_obj['tags'].append('organic')
    content_obj['expanded'] = 1 # this means formula reduce is prohibited
    return content_obj