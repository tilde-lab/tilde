
# example classifier: tries to determine whatever you want...

import os
import sys


# hierarchy API: __order__ to apply classifier
__order__ = 1000

def classify(tilde_obj):
    return tilde_obj # this means stop trying to classify object in scope of a current classifier
