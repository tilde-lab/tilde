
# Compacted basis set labels as strings for GUI
# Author: Evgeny Blokhin

import six


# hierarchy API: __order__ to apply classifier
__order__ = 5

def classify(tilde_obj):
    if not tilde_obj.electrons['basis_set'] or tilde_obj.info['ansatz'] == 0x1:
        return tilde_obj

    if tilde_obj.info['ansatz'] == 0x2:
        if not 'bs' in tilde_obj.structures[-1].arrays:
            return tilde_obj

        seq = tilde_obj.structures[-1].get_array('bs').tolist()
        symbols = tilde_obj.structures[-1].get_chemical_symbols()
        lookup, num = [], 0

        for n, i in enumerate(tilde_obj.electrons['basis_set']):
            elem = symbols[ seq.index(n) ]
            if elem + ':' + i in lookup: continue # WTF: several same PPs per an element
            lookup.append(elem + ':' + i)
            tilde_obj.info['bs' + str(num)] = elem + ':' + i
            num += 1

    elif tilde_obj.info['ansatz'] == 0x3: # TODO
        ps = {}
        for k, v in six.iteritems(tilde_obj.electrons['basis_set']['ps']):
            ps[k] = ''
            for channel in v:
                ps[k] += channel[0].lower() + '<sup>' + str(len(channel)-1) + '</sup>'

        i=0
        for k, v in six.iteritems(tilde_obj.electrons['basis_set']['bs']):
            if k == 'X': continue

            chk = "".join([a for a in k if a.isdigit()])
            if len(chk): continue # TODO: important information is lost here!

            if type(v) == str: # GAUSSIAN
                tilde_obj.info['bs' + str(i)] = k + ':' + v

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
                tilde_obj.info['bs' + str(i)] = k + ':' + pseudopotential + bs_str

            i+=1

    return tilde_obj
