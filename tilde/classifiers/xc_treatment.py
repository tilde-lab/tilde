
# Checks the classification of the ab initio materials science methods, done by parser,
# currently considers DFT XC treatment,
# however extends it with the post-Hartree-Fock methods
# Author: Evgeny Blokhin

__order__ = 4

xc_types = [
    'HF', '+U', 'vdW',                          # Hartree-Fock and empiric corrections
    'LDA', 'GGA', 'meta-GGA', 'hybrid',         # Jacob's ladder http://dx.doi.org/10.1063/1.1904565
    'MP', 'CC', 'CI', 'GW'                      # post-Hartree-Fock
]

def classify(tilde_obj):
    for i in tilde_obj.info['H_types']:
        if not i in xc_types: raise RuntimeError("Unknown xc type: %s (maybe typo?)" % i)

    if not tilde_obj.info['H_types']: tilde_obj.info['H_types'] = ['unknown']

    return tilde_obj
