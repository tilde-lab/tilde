
# this is an example classifier: tries to determine whatever you want...

import os
import sys

# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 1000
__properties__ = [ {"category": "demo", "source": "demo", "order": 3} ]

def classify(content_obj, tilde_obj):
    return content_obj