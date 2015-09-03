#!/usr/bin/env python

# Euler tilting angles extraction test
# Author: Evgeny Blokhin

import os, sys

import set_path
from tilde.core.api import API


data_dir = os.path.realpath(os.path.dirname(__file__) + '/outputs')

# Data for this test are published in:
# (1) Surf.Sci.602 3674 (2008) http://dx.doi.org/10.1016/j.susc.2008.10.002
# (2) Evgeny Blokhin's MSc. thesis
# (3) Phys. Rev. B 83, 134108 (2011), http://dx.doi.org/10.1103/PhysRevB.83.134108
# (4) Phys. Rev. B 88, 241407 (2013), http://dx.doi.org/10.1103/PhysRevB.88.241407
# NB: in Euler notation delta is gamma, delta plus/minus phi is alpha
# or in another terminology: phi is gamma, phi plus/minus psi is alpha
test_data = {
    'check_last_point.cryst.out': {
        'comment': 'Source (1), Table 1, calculated, Euler notation',
        'data': {
            6: [0.04, 12.26, 7.93],
            }
    },
    'y4h4srhfo3_62_pbe0_9hf_cis_go.cryst.out': {
        'comment': 'Source (2), Table 10, HfO2-terminated, dissociative water adsorption, monolayer coverage, Euler notation (bare slab reference data: delta=1.9, phi=9.729, psi=1.867)',
        'data': {
            17: [1.56, 15.07, 8.91],
            }
    },
    'srhfo3_62_pbe0_110_9sr_go.cryst.out': {
        'comment': 'Source (1), Table 5, SrO termination, 110 surface, relaxed, Euler notation',
        'data': {
            13: [14.73, 12.03, 5.24],
            15: [1.54, 8.74, 12.48],
            }
    },
    'sto140afd_f3.cryst.out': {
        'comment': 'Source (3), Table 6, LCAO-PBE0 optimized basis set',
        'data': {
            3: [0.0, 0.0, 0.85],
            }
    },
    '5ti_d_x2_scanned_freqs.cryst.out': {
        'comment': 'Source (4), page 241407-2, at the left, second paragraph',
        'data': {
            9: [0.0, 0.0, 0.36],
            }
    }
}


work = API()
print '\n\nPerovskite tilting module test:\n\n'
for k, v in test_data.iteritems():
    if not os.path.exists(data_dir + os.sep + k):
        raise RuntimeError(k + ': missed file for test!')
    for calc, error in work.parse(data_dir + os.sep + k):
        if error:
            raise RuntimeError(k + ': ' + error)
        calc, error = work.classify(calc)
        if error:
            raise RuntimeError(k + ': ' + error)
        calc = work.postprocess(calc)
        if not 'perovskite_tilting' in calc.apps:
            raise RuntimeError(k + ': invalid result!')
        for corner in v['data'].keys():
            if not corner in calc.apps['perovskite_tilting']['data']:
                raise RuntimeError(k + ': invalid result!')
            print 'Octahedron N', corner
            print 'expected:', v['data'][corner]
            print 'got     :', calc.apps['perovskite_tilting']['data'][corner]
