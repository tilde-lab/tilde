
# Determines perovskite structures: classifies by vacancy and substitutional defects (impurities)
# Author: Evgeny Blokhin

import os, sys, math
import six

from ase.data import chemical_symbols
from ase.data import covalent_radii
from tilde.core.constants import Perovskite_Structure


# hierarchy API: __order__ to apply classifier
__order__ = 10

def classify(tilde_obj):
    if len(tilde_obj.info['elements']) == 1: return tilde_obj

    C_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.C]
    if not C_site: return tilde_obj
    A_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.A]
    B_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.B]

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
        if round(D) == 3: tilde_obj.info['tags'].append(0x4)
        return tilde_obj
    # all other 2-component systems are not perovskites
    if not A_site or not B_site: return tilde_obj

    if not 1.3 < D < 2.1: return tilde_obj # D ratio grows for 2D adsorption cases (>1.9)

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

    tilde_obj.info['tags'].append(0x4)

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

        elif contents[num][1] in Perovskite_Structure.A:
            A_hosts[ contents[num][1] ] = tilde_obj.info['contents'][ contents[num][0] ]

        elif contents[num][1] in Perovskite_Structure.B:
            B_hosts[ contents[num][1] ] = tilde_obj.info['contents'][ contents[num][0] ]

    #print impurities, A_hosts, B_hosts

    if len(A_hosts) > 1 or len(B_hosts) > 1: return tilde_obj # not for alloys below

    # A site or B site?
    num=0
    for impurity_element, content in six.iteritems(impurities):
        e = tilde_obj.info['elements'].index(impurity_element)
        tilde_obj.info['elements'].pop(e) # TODO
        tilde_obj.info['contents'].pop(e) # TODO
        tilde_obj.info['impurity' + str(num)] = impurity_element + str(content) if content > 1 else impurity_element
        num+=1
        if impurity_element in Perovskite_Structure.A: A_hosts[A_hosts.keys()[0]] += content
        elif impurity_element in Perovskite_Structure.B: B_hosts[B_hosts.keys()[0]] += content

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
