
# yields compacted basis set labels

import os
import sys


# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 5
__properties__ = [ {"category": "basis sets", "source": "bs#"} ]

def classify(content_obj, tilde_obj):
    if tilde_obj.electrons['basis_set'] is None:
        return content_obj
    ps = {}
    i=0
    for k, v in tilde_obj.electrons['basis_set']['ps'].iteritems():
        if type(v) != str: # CRYSTAL
            ps[k] = ''
            for channel in v:
                ps[k] += channel[0].lower() + '<sup>' + str(len(channel)-1) + '</sup>'

        else: # VASP
            content_obj['properties']['bs' + str(i)] = k + ':' + v
            i+=1

    if type(tilde_obj.electrons['basis_set']['bs']) == dict:
        i=0
        for k, v in tilde_obj.electrons['basis_set']['bs'].iteritems():
            if k == 'Xx': continue

            chk = "".join([a for a in k if a.isdigit()])
            if len(chk): continue

            if type(v) == str: # GAUSSIAN
                content_obj['properties']['bs' + str(i)] = k + ':' + v

            else: # CRYSTAL, GAUSSIAN
                bs_repr, repeats = [], []
                for channel in v:
                    if type(channel) not in [list, tuple]: continue
                    e = channel[0].lower() + '<sup>%s</sup>' % (len(channel)-1)
                    if len(bs_repr) and bs_repr[-1] == e: repeats[-1] += 1
                    else:
                        bs_repr.append(e)
                        repeats.append(1)
                pseudopotential = ''
                if k in ps: pseudopotential = '[' + ps[k] + ']'
                
                bs_str = ''
                for n in range(len(bs_repr)):
                    bs_str += '(%s)<sup>%s</sup>' % (bs_repr[n], repeats[n]) if repeats[n]>1 else bs_repr[n]
                content_obj['properties']['bs' + str(i)] = k + ':' + pseudopotential + bs_str

            i+=1

    return content_obj