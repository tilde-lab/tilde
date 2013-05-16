
# tries to find vacancy defects

import os
import sys
import fractions

# hierarchy API: __order__ to apply classifier and __properties__ extending basic hierarchy
__order__ = 20
__properties__ = [ {"category": "vacancy content", "source": "vac", "order": 13, "negative_tagging": True, "has_column": True} ]

def classify(content_obj, tilde_obj):
    ''' detect vacant places of host atoms '''
    if len(content_obj['elements']) < 2: return content_obj    
    elif tilde_obj.structures[-1]['periodicity'] in [0, 1, 2]: return content_obj
    content_obj['expanded'] = reduce(fractions.gcd, content_obj['contents'])
    if sum(content_obj['contents']) / content_obj['expanded'] < 15: return content_obj # check for >= 15-atoms
    
    gcds = []
    for i in range(1, 3): # max 2 missing atoms of THE SAME type
        for index in range(len(content_obj['contents'])):
            chk_content = []
            chk_content.extend(content_obj['contents'])
            if content_obj['lack']: try_index = content_obj['elements'].index(content_obj['lack'])
            else: try_index = index
            chk_content[try_index] += i
            gcds.append([try_index, i, reduce(fractions.gcd, chk_content)])
            if content_obj['lack']: break
    m_red = max(gcds, key = lambda a: a[2]) # WARNING: only one of several possible reducing configurations is taken!
    
    #print content_obj['formula']
    #print "--->", m_red
    
    # this structure probably contains defects
    if m_red[2] > content_obj['expanded']:
    
        # check reasonable defect concentration (more than 25% is not a defect anymore!)
        c = float(m_red[1]*100) / m_red[2]
        if c > 25: return content_obj
        
        content_obj['expanded'] = m_red[2]        
        
        content_obj['contents'][ m_red[0] ] += m_red[1]
        for n, i in enumerate(map(lambda x: x/content_obj['expanded'], content_obj['contents'])):
            if i>1: content_obj['standard'] += content_obj['elements'][n] + str(i)
            else: content_obj['standard'] += content_obj['elements'][n]
            if n == m_red[0]:
                if i==1: content_obj['standard'] += '1-d'
                else: content_obj['standard'] += '-d'
                content_obj['properties']['vac'] = '%2.2f' % c + '%'
        content_obj['tags'].append('vacancy defect')
        
    return content_obj
    