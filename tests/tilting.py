#!/usr/bin/env python

# Euler tilting angles extraction test

import os
import sys

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.api import API
from core.settings import EXAMPLE_DIR


# Data for test are published in:
# (1) Surf.Sci.602 3674 (2008) http://dx.doi.org/10.1016/j.susc.2008.10.002
# (2) Evgeny Blokhin's master thesis
# NB: in Euler notation delta is gamma, delta plus/minus phi is alpha
test_data = {
    'check_last_point.cryst.out': {
        'comment': 'Source (1), Table 1, calculated, Euler notation',
        'data': {
            5: [0.04, 12.26, 7.93]
            }
    },
    'y4h4srhfo3_62_pbe0_9hf_cis_go.cryst.out': {
        'comment': 'Source (2), Table 10, HfO2-terminated, dissociative water adsorption, monolayer coverage, Euler notation (bare slab reference data: delta=1.9, phi=9.729, psi=1.867)',
        'data': {
            17: [1.56, 15.07, 8.91]
            }
    },
    'srhfo3_62_pbe0_110_9sr_go.cryst.out': {
        'comment': 'Source (1), Table 5, SrO termination, 110 surface, relaxed, Euler notation',
        'data': {
            13: [14.73, 12.03, 5.24],
            15: [1.54, 8.74, 12.48],
            }
    }
}


work = API()
print '\n\nTilting module test:\n\n'
for k, v in test_data.iteritems():
    if not os.path.exists(EXAMPLE_DIR + os.sep + 'CRYSTAL' + os.sep + k):
        raise RuntimeError(k + ': missed file for test!')
    calc, error = work.parse(EXAMPLE_DIR + os.sep + 'CRYSTAL' + os.sep + k)
    if error:
        raise RuntimeError(k + ': ' + error)
    calc, error = work.classify(calc)
    if error:
        raise RuntimeError(k + ': ' + error)
    modules = work.postprocess(calc)
    if not 'tilting' in modules:
        raise RuntimeError(k + ': invalid result!')
    for corner in v['data'].keys():
        if not corner in modules['tilting']['data']:
            raise RuntimeError(k + ': invalid result!')
        print 'Octahedron N', corner
        print 'expected:', v['data'][corner]
        print 'got     :', modules['tilting']['data'][corner]
