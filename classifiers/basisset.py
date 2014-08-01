
# gives compacted basis set labels as strings for GUI

import os, sys


# hierarchy API: __order__ to apply classifier
__order__ = 5

def classify(tilde_obj):
    if tilde_obj.electrons['basis_set'] is None or tilde_obj.electrons['type'] is None:
        return tilde_obj    
        
    if tilde_obj.electrons['type'] == 'PP_PW':
        i=0
        for k, v in tilde_obj.electrons['basis_set']['ps'].iteritems():
            tilde_obj.info['bs' + str(i)] = k + ':' + v
            i+=1
    
    elif tilde_obj.electrons['type'] == 'LCAO':        
        ps = {}
        for k, v in tilde_obj.electrons['basis_set']['ps'].iteritems():
            ps[k] = ''
            for channel in v:
                ps[k] += channel[0].lower() + '<sup>' + str(len(channel)-1) + '</sup>'

        i=0
        for k, v in tilde_obj.electrons['basis_set']['bs'].iteritems():
            if k == 'Xx': continue

            chk = "".join([a for a in k if a.isdigit()])
            if len(chk): continue

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
            
    elif tilde_obj.electrons['type'] == 'FP_LAPW':
        if not 'bs' in tilde_obj.structures[-1].arrays: return tilde_obj           
        seq = tilde_obj.structures[-1].get_array('bs').tolist()
        symbols = tilde_obj.structures[-1].get_chemical_symbols()
        
        for n, i in enumerate(tilde_obj.electrons['basis_set']):            
            elem = symbols[ seq.index(n) ]
            bs_repr, repeats = [], []
            pseudopotential = ''
            
            for st in i['states']:
                if st['is_core']: pseudopotential += "%s%s<sup>%se</sup>" % (st['n'], st['l'], st['occ'])
            if pseudopotential: pseudopotential = '[' + pseudopotential + ']'
            
            for lo in i.get('lo', []):
                e = lo[0] + '<sup>%s</sup>' % (len(lo)-1)
                if len(bs_repr) and bs_repr[-1] == e: repeats[-1] += 1
                else:
                    bs_repr.append(e)
                    repeats.append(1)
            
            bs_str = ''
            for j in range(len(bs_repr)):
                bs_str += '(%s)<sup>%s</sup>' % (bs_repr[j], repeats[j]) if repeats[j]>1 else bs_repr[j]
                
            tilde_obj.info['bs' + str(n)] = elem + ':' + pseudopotential + bs_str

    return tilde_obj
