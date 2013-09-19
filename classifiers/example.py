
# example classifier: tries to determine whatever you want...

import os
import sys


# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 1000
__properties__ = [ {"category": "demo", "source": "demo", "sort": 3, "descr": "test description"} ]

def classify(tilde_obj):
    return tilde_obj # this means stop trying to classify object in scope of a current classifier
