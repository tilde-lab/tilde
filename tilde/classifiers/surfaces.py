
# Classifies slabs by their structure: determines layers count and adsorption
# Author: Evgeny Blokhin

import os, sys
import math
import fractions
import six
from functools import reduce

# hierarchy API: __order__ to apply classifier
__order__ = 40

def classify(tilde_obj):
    if tilde_obj.structures[-1].periodicity != 2: return tilde_obj

    vectors = []
    for i in range(3):
        vectors.append([i, tilde_obj.info['cellpar'][i]])
    z_axis = sorted(vectors, key = lambda k: k[1])[-1][0]

    z_coords = []
    for i in tilde_obj.structures[-1]:
        if i.symbol == 'X': continue
        z_coords.append([ i.symbol, i.position[z_axis] ])
    z_coords = sorted(z_coords, key = lambda k: k[1])

    content_by_layer = [{}]
    for i in range(len(z_coords)):
        try: content_by_layer[-1][ z_coords[i][0] ]
        except KeyError: content_by_layer[-1][ z_coords[i][0] ] = 1
        else: content_by_layer[-1][ z_coords[i][0] ] += 1

        try: z_coords[i+1]
        except IndexError: break

        if z_coords[i+1][1] - z_coords[i][1] > 0.7: # diff by Z
            content_by_layer.append({})

    adsorbate = {}
    to_delete = []
    if len(content_by_layer) <= 3:
        # TODO
        # we have a very thin slab with an undefined adsorption case
        tilde_obj.info['layers'] = len(content_by_layer)
    else:
        # check adsorbants
        s = range(len(content_by_layer) - 1, int(math.floor( len(content_by_layer)/2 ) - 1), -1)
        sides = [range(0, int(math.floor( len(content_by_layer)/2 )))] + [s]
        side_chk, inversed = False, False

        # run over layers till the middle from both sides
        #print 'SIDES:   ', sides
        for side in sides:
            if side_chk: side_chk = False
            for i in side:

                if side_chk: break
                #print 'layer:', i
                ref_layer = {}

                # Check 1:
                # by content
                for atom, content in six.iteritems(content_by_layer[i]):
                    #print 'content:', float(tilde_obj.info['contents'][ tilde_obj.info['elements'].index(atom) ]) / sum(tilde_obj.info['contents'])
                    if atom == 'H': content_ratio = 0.15 # less than 15%
                    else: content_ratio = 0.1 # less than 10%
                    if float(tilde_obj.info['contents'][ tilde_obj.info['elements'].index(atom) ]) / sum(tilde_obj.info['contents']) <= content_ratio:
                        #print '->got', atom
                        try: adsorbate[atom]
                        except KeyError: adsorbate[atom] = content
                        else: adsorbate[atom] += content
                        to_delete.append([i, atom])
                    else:
                        ref_layer[atom] = content
                        #print "ref layer cur state", ref_layer

                if not len(ref_layer): continue

                # Check 2:
                # by comparing with next layers
                # WARNING! Collision is possible when an adsorbate and host layer have the same atomic content!
                if not inversed: cmp_chk_lr = range(i + 1, len(content_by_layer) - i - 1) # from upside down
                else:
                    cmp_chk_lr, k = [], 1
                    while not len(cmp_chk_lr):
                        cmp_chk_lr = range(i - 1, len(content_by_layer) - i - k, -1) # from downside up
                        k += 1
                #print 'iter->', cmp_chk_lr
                for j in cmp_chk_lr:
                    if ref_layer == content_by_layer[j]:
                        side_chk = True
                        inversed = True
                        break
                    elif ref_layer.keys() == content_by_layer[j].keys():
                        #print "d =", float(sum(ref_layer.values())) / len(ref_layer), float(sum(content_by_layer[j].values())) / len(content_by_layer[j])
                        if len(ref_layer) == 1 or abs( float(sum(ref_layer.values())) / len(ref_layer) - float(sum(content_by_layer[j].values())) / len(content_by_layer[j]) ) <= 1.5:
                            side_chk = True
                            inversed = True
                            break
                else:
                    # happens if a cycle was not broken
                    for atom, content in six.iteritems(ref_layer):
                        if len(to_delete):
                            if to_delete[-1][0] == i and to_delete[-1][1] == atom: continue # this was already done on check 1
                        #print '->got', atom
                        try: adsorbate[atom]
                        except KeyError: adsorbate[atom] = content
                        else: adsorbate[atom] += content
                        to_delete.append([i, atom])
        #print "-"*40
        #print adsorbate
        #print content_by_layer
        #print to_delete

        # prevent all-is-adsorbent case
        if sorted(adsorbate.keys()) == sorted(tilde_obj.info['elements']) and sorted(adsorbate.values()) == sorted(tilde_obj.info['contents']): adsorbate, to_delete = {}, []

        for i in to_delete:
            del content_by_layer[ i[0] ][ i[1] ]
        content_by_layer = list(filter(None, content_by_layer))
        tilde_obj.info['layers'] = len(content_by_layer)

        if len(adsorbate):
            tilde_obj.info['tags'].append(0x3)
            adsorbent_formula = ''
            r = reduce(fractions.gcd, adsorbate.values())

            # sort according to pre-defined element order in a full slab formula
            elems = [x for x in tilde_obj.info['elements'] if x in adsorbate.keys()] + [x for x in adsorbate.keys() if x not in tilde_obj.info['elements']]
            elems_content = [ adsorbate[i] for i in elems ]
            for i, c in enumerate( map(lambda x: x/r, elems_content) ):
                if c == 1: adsorbent_formula += elems[i]
                else: adsorbent_formula += elems[i] + str(c)
            if r>1: adsorbent_formula = str(r) + adsorbent_formula
            tilde_obj.info['adsorbent'] = adsorbent_formula

    if content_by_layer[0] == content_by_layer[-1] and len(content_by_layer) > 1:
        termination_formula = ''
        d = reduce(fractions.gcd, content_by_layer[0].values())
        # sort according to pre-defined element order in a full slab formula
        elems = [x for x in tilde_obj.info['elements'] if x in content_by_layer[0].keys()] + [x for x in content_by_layer[0].keys() if x not in tilde_obj.info['elements']]
        elems_content = [ content_by_layer[0][i] for i in elems ]
        for i, c in enumerate( map(lambda x: x/d, elems_content) ):
            if c == 1: termination_formula += elems[i]
            else: termination_formula += elems[i] + str(c)
        tilde_obj.info['termination'] = termination_formula

    tilde_obj.info['expanded'] = 1 # this means formula reduce is prohibited
    slab_elements = []
    for y in content_by_layer:
        for k, v in six.iteritems(y):
            if not k in slab_elements:
                slab_elements.append(k)
    # sort according to pre-defined element order in a full slab formula
    tilde_obj.info['standard'] = "".join([x for x in tilde_obj.info['elements'] if x in slab_elements] + [x for x in slab_elements if x not in tilde_obj.info['elements']]) + " slab"

    #print content_by_layer
    return tilde_obj
