
# accounts the 2d surface case
# (when the PW-based codes are forced to put vacuum in a "non-periodical" direction)
# extends ASE object(s)

# TODO: account all "pseudo-periodic" cases for 1d and 0d

import math

from numpy import cross
from numpy.linalg import det
from numpy.linalg import norm

from ase.data import chemical_symbols, covalent_radii


# hierarchy API: __order__ to apply classifier
__order__ = 1

L = 3.9 # empirical criterion: a must be L times larger than b and c
r_EC = 0.0 # empirical criterion: radius of electron cloud around the atom
#ADDED_VACUUM1D_TOL = 12 # empirical criterion: if too much vacuum in 1d
ADDED_VACUUM3D_TOL = 12 # empirical criterion: if too much vacuum in 3d

def classify(tilde_obj):    
    if sum(tilde_obj.structures[-1].get_pbc()) == 3: # only those initially 3-periodic
        zi, mi = tilde_obj.info['cellpar'].index(max(tilde_obj.info['cellpar'][0:3])), tilde_obj.info['cellpar'].index(min(tilde_obj.info['cellpar'][0:3]))
        cmpveci = [i for i in range(3) if i not in [zi, mi]][0]
            
        # 1. First step: based on vacuum per one atom (av)
        atoms_volume = 0.0
        for i in tilde_obj.structures[-1]:
            atoms_volume += 4/3 * math.pi * (covalent_radii[ chemical_symbols.index( i.symbol ) ] + r_EC) ** 3
        av = (abs(det(tilde_obj.structures[-1].cell)) - atoms_volume)/len(tilde_obj.structures[-1])
        #print "av:", av
        
        # 2. Second step: too much vacuum
        if av > ADDED_VACUUM3D_TOL:
            if tilde_obj.info['cellpar'][cmpveci] * L < tilde_obj.info['cellpar'][zi]:
            
                tilde_obj.info['techs'].append( 'vacuum %sA' % int(round(tilde_obj.info['cellpar'][zi])) )

                # FOR surfaces:
                for i in range(len(tilde_obj.structures)):
                    tilde_obj.structures[i].set_pbc((True, True, False))
                    
    # extend the last ASE object with the new useful info (TODO: FOR ALL?)
    for n in range(len(tilde_obj.structures)):
        tilde_obj.structures[n].periodicity = sum(tilde_obj.structures[n].get_pbc())
        tilde_obj.structures[n].dims = None
        if n == len(tilde_obj.structures)-1:         
            if tilde_obj.structures[n].periodicity == 3: tilde_obj.structures[n].dims = abs(det(tilde_obj.structures[n].cell))
            elif tilde_obj.structures[n].periodicity == 2:
                # area for surfaces
                v = [norm(i) for i in tilde_obj.structures[n].cell]
                zi, mi = v.index(max(v)), v.index(min(v))
                ni = [i for i in range(3) if i not in [zi, mi]][0]
                tilde_obj.structures[n].dims = norm(cross(tilde_obj.structures[n].cell[mi], tilde_obj.structures[n].cell[ni])) # http://mathworld.wolfram.com/Parallelogram.html
                
    tilde_obj.info['dims'] = tilde_obj.structures[-1].dims
        
    return tilde_obj
