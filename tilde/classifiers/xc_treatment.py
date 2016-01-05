
# Checks the classification of the ab initio materials science methods, done by parser,
# currently considers DFT XC treatment,
# however extends it with the post-Hartree-Fock methods
# Author: Evgeny Blokhin

__order__ = 4

xc_types = [                    # see hierarchy values in the file init-data.sql
    0x1, 0x2, 0x3, 0x4,         # main types of the Jacob's ladder, http://dx.doi.org/10.1063/1.1904565
    0x5, 0x6, 0x7,              # Hartree-Fock, +U, vdW
]

def classify(tilde_obj):
    for i in tilde_obj.info['H_types']:
        if not i in xc_types: raise RuntimeError("Unknown xc type: %s (maybe typo?)" % i)

    return tilde_obj
