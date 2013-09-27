
# determines perovskite structure
# v220913

import os
import sys
import math

from core.deps.ase.data import chemical_symbols
from core.deps.ase.data import covalent_radii


# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 10
__properties__ = [ {"category": "impurity", "source": "impurity#", "negative_tagging": True, "chem_notation": True, "has_label": True, "sort": 14, "descr": ""} ]

A_site_elems = 'Li, Na, K, Rb, Cs, Fr, Mg, Ca, Sr, Ba, Ra, Sc, Sc, Y, La, Ce, Pr, Nd, Pm, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu, Ag, Pb, Bi, Th'.split(', ')
B_site_elems = 'Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Ga, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd, In, Sn, Sb, Hf, Ta, W, Re'.split(', ')
C_site_elems = 'O, F'.split(', ') # todo: add elements to C site

def classify(tilde_obj):    
    ''' classification by vacancy and substitutional defects in perovskites '''
    
    if len(tilde_obj.info['elements']) == 1: return tilde_obj

    C_site = [e for e in tilde_obj.info['elements'] if e in C_site_elems]
    if not C_site: return tilde_obj
    A_site = [e for e in tilde_obj.info['elements'] if e in A_site_elems]
    B_site = [e for e in tilde_obj.info['elements'] if e in B_site_elems]

    # proportional coefficient D
    AB, C = 0, 0
    for i in (A_site + B_site):
        AB += tilde_obj.info['contents'][ tilde_obj.info['elements'].index(i) ]
    for i in C_site:
        C += tilde_obj.info['contents'][ tilde_obj.info['elements'].index(i) ]

    try: D = float(C) / AB
    except ZeroDivisionError: return tilde_obj

    # 2-component pseudo-perovskites
    if tilde_obj.info['elements'][0] in ['W', 'Re'] and len(tilde_obj.info['elements']) == 2:
        if round(D) == 3: tilde_obj.info['tags'].append('perovskite')
        return tilde_obj
    # all other 2-component systems are not perovskites
    if not A_site or not B_site: return tilde_obj

    if not 1.3 < D < 1.9: return tilde_obj

    # Goldschmidt tolerance factor
    # t = (rA + rC) / sqrt(2) * (rB + rC)
    # 0.71 =< t =< 1.07
    # t < 0.71 ilmenite, corundum or KNbO3 structure
    # t > 1 hexagonal perovskite polytypes
    # http://en.wikipedia.org/wiki/Goldschmidt_tolerance_factor
    for A in A_site:
        for B in B_site:
            for C in C_site:
                try:
                    rA = covalent_radii[chemical_symbols.index(A)]
                    rB = covalent_radii[chemical_symbols.index(B)]
                    rC = covalent_radii[chemical_symbols.index(C)]
                except IndexError: pass
                else:
                    if not 0.71 <= (rA + rC) / (math.sqrt(2) * (rB + rC)) <= 1.07: return tilde_obj

    tilde_obj.info['tags'].append('perovskite')

    if tilde_obj.structures[-1].periodicity != 3: return tilde_obj # all below is for 3d case : TODO

    contents = []
    impurities = {}
    A_hosts = {}
    B_hosts = {}

    # empirical criteria of defect: =< 25% content
    for n, i in enumerate(tilde_obj.info['elements']):
        contents.append( [n, i, float(tilde_obj.info['contents'][n])/sum(tilde_obj.info['contents'])] )
    contents = sorted(contents, key = lambda i: i[2])

    for num in range(len(contents)):
        try: contents[num+1]
        except IndexError: break

        # defect content differs at least 2x from the smallest content; defect partial weight <= 1/16
        if contents[num][2] <= 0.0625 and contents[num][2] / contents[num+1][2] <= 0.5:
            impurities[ contents[num][1] ] = tilde_obj.info['contents'][ contents[num][0] ] # ex: ['Fe', 2]

        elif contents[num][1] in A_site_elems:
            A_hosts[ contents[num][1] ] = tilde_obj.info['contents'][ contents[num][0] ]

        elif contents[num][1] in B_site_elems:
            B_hosts[ contents[num][1] ] = tilde_obj.info['contents'][ contents[num][0] ]

    #print impurities, A_hosts, B_hosts

    # A site or B site?
    ref_coords = tilde_obj.structures[-1].get_positions()
    num=0
    for impurity_element, content in impurities.iteritems():
        e = tilde_obj.info['elements'].index(impurity_element)
        tilde_obj.info['elements'].pop(e) # TODO
        tilde_obj.info['contents'].pop(e) # TODO
        tilde_obj.info['properties']['impurity' + str(num)] = impurity_element + str(content) if content > 1 else impurity_element
        dist_matrix = []        
        num+=1
        for i in tilde_obj.structures[-1]:
            if i.symbol == impurity_element:
                for j in ref_coords:
                    dist_matrix.append( math.sqrt( (i.position[0]-j[0])**2 + (i.position[1]-j[1])**2 + (i.position[2]-j[2])**2 ) )
                dist_matrix = filter(None, dist_matrix) # skip zeros
                dist_matrix.sort()
                
                for k in range(len(dist_matrix)):
                    D_d = abs(dist_matrix[k+1]-dist_matrix[k]) / dist_matrix[k+1] # jump in a distance change allows us to determine A- or B-site

                    # TODO: interstitial defects

                    if 0.12 < D_d < 0.28: #
                        # A-site with coord.number = 12
                        if len(A_hosts) > 1: return tilde_obj # TODO?
                        A_hosts[A_hosts.keys()[0]] += 1
                        break

                    elif D_d >= 0.28:
                        # B-site with coord.number = 6
                        if len(B_hosts) > 1: return tilde_obj # TODO?
                        B_hosts[B_hosts.keys()[0]] += 1
                        break

    for n, i in enumerate(tilde_obj.info['elements']):
        if i in A_hosts:
            tilde_obj.info['contents'][n] = A_hosts[i] # TODO
        elif i in B_hosts:
            tilde_obj.info['contents'][n] = B_hosts[i] # TODO

    for i in C_site:
        c_content = tilde_obj.info['contents'][ tilde_obj.info['elements'].index(i) ]
        tot_content = sum(tilde_obj.info['contents'])
        D_O = float(c_content) / tot_content
        if D_O < 0.6: # C-site lack
            tilde_obj.info['lack'] = i
            break # todo

    return tilde_obj
