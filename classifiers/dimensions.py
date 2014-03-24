
# accounts the surface case (when the PW-based codes are forced to put vacuum in a "non-periodical" direction) and extends ASE object(s)

from numpy import cross
from numpy.linalg import det
from numpy.linalg import norm

# hierarchy API: __order__ to apply classifier
__order__ = 1

L = 3.9 # criterion: a must be L times larger than b and c, ~4x

def classify(tilde_obj):    
    zi, mi = tilde_obj.info['cellpar'].index(max(tilde_obj.info['cellpar'][0:3])), tilde_obj.info['cellpar'].index(min(tilde_obj.info['cellpar'][0:3]))
    cmpveci = [i for i in range(3) if i not in [zi, mi]][0]
    
    if tilde_obj.info['cellpar'][cmpveci] * L < tilde_obj.info['cellpar'][zi]:
    
        tilde_obj.method['technique'].update({'vacuum2d': int(round(tilde_obj.info['cellpar'][zi]))}) # technique

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
