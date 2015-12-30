from tilde.core.common import html_formula, num2name

def wrap_cell(entity, json_obj, mapping, table_view=False):
    '''
    Cell wrappers
    for customizing the GUI data table

    TODO : must coincide with hierarchy!
    TODO : simplify this!
    '''
    html_class = '' # for GUI javascript
    out = ''

    #if 'cell_wrapper' in entity: # TODO : this bound type was defined by apps only
    #    out = entity['cell_wrapper'](json_obj)
    #else:

    if entity['multiple']:
        out = ", ".join(  map(lambda x: num2name(x, entity, mapping), json_obj.get(entity['source'], []))  )

    elif entity['is_chem_formula']:
        out = html_formula(json_obj[ entity['source'] ]) if entity['source'] in json_obj else '&mdash;'

    elif entity['source'] == 'bandgap':
        html_class = ' class=_g'
        out = json_obj.get('bandgap')
        if out is None: out = '&mdash;'

    # dynamic determination below:
    elif entity['source'] == 'energy':
        html_class = ' class=_e'
        out = "%6.5f" % json_obj['energy'] if json_obj['energy'] else '&mdash;'

    elif entity['source'] == 'dims':
        out = "%4.2f" % json_obj['dims'] if json_obj['periodicity'] in [2, 3] else '&mdash;'

    else:
        out = num2name(json_obj.get(entity['source']), entity, mapping) or '&mdash;'

    if table_view:
        return '<td rel=' + str(entity['cid']) + html_class + '>' + str(out) + '</td>'
    elif html_class:
        return '<span' + html_class + '>' + str(out) + '</span>'
    else:
        return str(out)
