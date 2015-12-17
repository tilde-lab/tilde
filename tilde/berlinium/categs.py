from tilde.core.common import html_formula

def wrap_cell(xml_tag, json_obj, table_view=False):
    '''
    Cell wrappers
    for customizing the GUI data table

    TODO : must coincide with hierarchy!
    TODO : simplify this!
    '''
    html_class = '' # for GUI javascript
    out = ''

    #if 'cell_wrapper' in xml_tag: # TODO : this bound type was defined by apps only
    #    out = xml_tag['cell_wrapper'](json_obj)
    #else:

    if 'multiple' in xml_tag:
        out = ", ".join(  json_obj.get(xml_tag['source'], [])  )

    elif 'is_chem_formula' in xml_tag:
        out = html_formula(json_obj[ xml_tag['source'] ]) if xml_tag['source'] in json_obj else '&mdash;'

    elif xml_tag['source'] == 'bandgap':
        html_class = ' class=_g'
        out = json_obj.get('bandgap')

    # pseudo-source (dynamic determination)
    elif xml_tag['source'] == 'e':
        html_class = ' class=_e'
        out = "%6.5f" % json_obj['energy'] if json_obj['energy'] else '&mdash;'

    elif xml_tag['source'] == 'dims':
        out = "%4.2f" % json_obj['dims'] if json_obj['periodicity'] in [2, 3] else '&mdash;'

    elif xml_tag['source'] == 'finished':
        f = int(json_obj['finished'])
        if f > 0: out = 'yes'
        elif f == 0: out = 'n/a'
        elif f < 0: out = 'no'

    else:
        out = json_obj.get(xml_tag['source'], '&mdash;')

    if table_view:
        return '<td rel=' + str(xml_tag['cid']) + html_class + '>' + str(out) + '</td>'
    elif html_class:
        return '<span' + html_class + '>' + str(out) + '</span>'
    else:
        return str(out)
