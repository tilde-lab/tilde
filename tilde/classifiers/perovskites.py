
# Determines perovskite structures: classifies by vacancy and substitutional defects (impurities)
# Author: Evgeny Blokhin

import math
import random
import six

from ase.data import chemical_symbols
from ase.data import covalent_radii
from ase.spacegroup import crystal

from tilde.core.constants import Perovskite_Structure
from tilde.apps.perovskite_tilting.perovskite_tilting import Perovskite_tilting


# hierarchy API: __order__ to apply classifier
__order__ = 10

def classify(tilde_obj):
    if len(tilde_obj.info['elements']) == 1: return tilde_obj

    C_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.C]
    if not C_site: return tilde_obj
    A_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.A]
    B_site = [e for e in tilde_obj.info['elements'] if e in Perovskite_Structure.B]

    # proportional content coefficient D_prop
    AB, C = 0, 0
    for i in set(A_site + B_site):
        AB += tilde_obj.info['contents'][ tilde_obj.info['elements'].index(i) ]
    for i in C_site:
        C += tilde_obj.info['contents'][ tilde_obj.info['elements'].index(i) ]

    try: D_prop = float(C) / AB
    except ZeroDivisionError: return tilde_obj

    # 2-component pseudo-perovskites
    # TODO account other pseudo-perovskites e.g. Mn2O3 or binary-metal ones
    if tilde_obj.info['elements'][0] in ['W', 'Re'] and len(tilde_obj.info['elements']) == 2:
        if round(D_prop) == 3: tilde_obj.info['tags'].append(0x4)
        return tilde_obj

    if not A_site or not B_site: return tilde_obj

    if not 1.3 < D_prop < 2.3: return tilde_obj # D_prop grows for 2D adsorption cases (>1.9)

    n_combs, n_offs = 0, 0
    for A in A_site:
        for B in B_site:
            if B == A: continue
            for C in C_site:
                rA = covalent_radii[chemical_symbols.index(A)]
                rB = covalent_radii[chemical_symbols.index(B)]
                rC = covalent_radii[chemical_symbols.index(C)]

                # Goldschmidt tolerance factor
                # t = (rA + rC) / sqrt(2) * (rB + rC)
                # 0.71 =< t =< 1.2
                # t < 0.71 ilmenite, corundum or KNbO3 structure
                # t > 1 hexagonal perovskite polytypes
                # http://en.wikipedia.org/wiki/Goldschmidt_tolerance_factor
                factor = (rA + rC) / (math.sqrt(2) * (rB + rC))
                if not 0.71 <= factor <= 1.4: n_offs += 1
                n_combs += 1
    if n_offs == n_combs: return tilde_obj

    tilde_obj.info['tags'].append(0x4)

    if tilde_obj.structures[-1].periodicity != 3: return tilde_obj # all below is for 3d case : TODO

    contents = []
    impurities, A_hosts, B_hosts = {}, {}, {}

    # What is a defect?
    # Empirical criteria of defect for ab initio modeling: =< 25% of the content
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

    if len(A_hosts) > 1 or len(B_hosts) > 1: return tilde_obj # skip complex perovskites and those where an element may occupy either A or B

    # A site or B site?
    num = 0
    for impurity_element, content in six.iteritems(impurities):
        e = tilde_obj.info['elements'].index(impurity_element)
        tilde_obj.info['elements'].pop(e) # TODO
        tilde_obj.info['contents'].pop(e) # TODO
        tilde_obj.info['impurity' + str(num)] = impurity_element + str(content) if content > 1 else impurity_element
        num += 1
        if impurity_element in Perovskite_Structure.A:
            A_hosts[list(A_hosts.keys())[0]] += content
        elif impurity_element in Perovskite_Structure.B:
            B_hosts[list(B_hosts.keys())[0]] += content

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
            break # TODO

    return tilde_obj

def generate_random_perovskite(lat=None):
    '''
    This generates a random valid perovskite structure in ASE format.
    Useful for testing.
    Binary and organic perovskites are not considered.
    '''
    if not lat:
        lat = round(random.uniform(3.5, Perovskite_tilting.OCTAHEDRON_BOND_LENGTH_LIMIT*2), 3)
    A_site = random.choice(Perovskite_Structure.A)
    B_site = random.choice(Perovskite_Structure.B)
    Ci_site = random.choice(Perovskite_Structure.C)
    Cii_site = random.choice(Perovskite_Structure.C)

    while covalent_radii[chemical_symbols.index(A_site)] - \
        covalent_radii[chemical_symbols.index(B_site)] < 0.05 or \
        covalent_radii[chemical_symbols.index(A_site)] - \
        covalent_radii[chemical_symbols.index(B_site)] > 0.5:

        A_site = random.choice(Perovskite_Structure.A)
        B_site = random.choice(Perovskite_Structure.B)

    return crystal(
        [A_site, B_site, Ci_site, Cii_site],
        [(0.5, 0.25, 0.0), (0.0, 0.0, 0.0), (0.0, 0.25, 0.0), (0.25, 0.0, 0.75)],
        spacegroup=62, cellpar=[lat*math.sqrt(2), 2*lat, lat*math.sqrt(2), 90, 90, 90]
    )
