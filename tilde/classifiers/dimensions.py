
# accounts low-dimensional cases in 3D
# (NB the PW-based codes are forced to put vacuum in a "non-periodical" direction)
# extends ASE object(s)
# Author: Evgeny Blokhin
# TODO: account all "pseudo-periodic" cases for 1d and 0d

import math

from numpy import cross
from numpy.linalg import det
from numpy.linalg import norm

from ase.data import chemical_symbols, covalent_radii


# hierarchy API: __order__ to apply classifier
__order__ = 1

# empirical criteria
L = 3.9                     # a must be L times larger than b and c
r_EC = 0.0                  # additional radius of electron cloud around the atom
ADDED_VACUUM_3D_TOL = 12    # if too much vacuum in 3d

def classify(tilde_obj):
    if sum(tilde_obj.structures[-1].get_pbc()) == 3: # only those initially 3-periodic
        zi, mi = tilde_obj.info['cellpar'].index(max(tilde_obj.info['cellpar'][0:3])), tilde_obj.info['cellpar'].index(min(tilde_obj.info['cellpar'][0:3]))
        cmpveci = [i for i in range(3) if i not in [zi, mi]][0]

        # vacuum per one atom (av)
        atoms_volume = 0.0
        for i in tilde_obj.structures[-1]:
            atoms_volume += 4/3 * math.pi * (covalent_radii[ chemical_symbols.index( i.symbol ) ] + r_EC) ** 3
        av = (abs(det(tilde_obj.structures[-1].cell)) - atoms_volume)/len(tilde_obj.structures[-1])
        #print "av:", av

        # too much vacuum
        if av > ADDED_VACUUM_3D_TOL:
            # 2D
            if tilde_obj.info['cellpar'][cmpveci] * L < tilde_obj.info['cellpar'][zi]:

                tilde_obj.info['techs'].append( 'vacuum %sA' % int(round(tilde_obj.info['cellpar'][zi])) )

                tilde_obj.structures[-1].set_pbc((True, True, False))

            # TODO: 1D ?

            # 0D
            elif av > ADDED_VACUUM_3D_TOL*4: # TODO
                tilde_obj.structures[-1].set_pbc((False, False, False))

    # extend the last ASE object
    tilde_obj.structures[-1].periodicity = int(sum(tilde_obj.structures[-1].get_pbc()))
    tilde_obj.structures[-1].dims = abs(det(tilde_obj.structures[-1].cell))

    # TODO: area for surfaces

    tilde_obj.info['dims'] = tilde_obj.structures[-1].dims
    tilde_obj.info['periodicity'] = tilde_obj.structures[-1].periodicity

    return tilde_obj
