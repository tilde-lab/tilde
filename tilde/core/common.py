
# Includable routines
# Author: Evgeny Blokhin

import os, sys
import math, datetime, re
import six

from numpy import dot, array, matrix

from ase.atoms import Atoms
from ase.geometry import cell_to_cellpar

import ujson as json


class ModuleError(Exception):
    def __init__(self, value):
        self.value = value

def num2name(target, rules, mapping):
    return mapping[rules['cid']][int(target)] if rules['enumerated'] else target

def metric(v):
    '''
    Get direction of vector
    '''
    return [int(math.copysign(1, x)) if x else 0 for x in v]

def u(obj, encoding='utf-8'):
    if not isinstance(obj, str):
        return str(obj, encoding)
    else: return obj

def str2html(s, units=True):
    tokens = {
    ',,': '<sub>',
    '__': '</sub>',
    '^^': '<sup>',
    '**': '</sup>',
    '{{units-energy}}': ''
    }
    if units: tokens['{{units-energy}}'] = ', <span class=units-energy></span>'
    for k, v in tokens.items():
        s = s.replace(k, v)
    return s

def html_formula(string):
    sub, html_formula = False, ''
    for n, i in enumerate(string):
        if i.isdigit() or i=='.' or i=='-':
            if not sub:
                html_formula += '<sub>'
                sub = True
        else:
            if sub and i != 'd':
                html_formula += '</sub>'
                sub = False
        html_formula += i
    if sub: html_formula += '</sub>'
    return html_formula

def extract_chemical_symbols(string):
    sub, elems, elem = False, [], ''
    for i in string:
        if i==' ' or i==':': break # for " slab" and basis sets
        if not i.isalpha():
            sub = True
            continue
        if i.isupper():
            if len(elem): elems.append(elem)
            elem = i
            sub = False
        else:
            if not sub: elem += i
    if len(elem): elems.append(elem)
    return elems

def is_binary_string(bytes):
    ''' Determine if a string is classified as binary rather than text '''
    try:
        bytes.decode('ascii')
    except UnicodeDecodeError:
        return True
    return False

def hrsize(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

def get_urlregex():
    # https://github.com/django/django/blob/master/django/core/validators.py
    ul = '\\u00a1-\\uffff' # unicode letters range (must be a unicode string, not a raw string)

    # IP patterns
    ipv4_re = r'(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}'
    ipv6_re = r'\[[0-9a-f:\.]+\]' # (simple regex, validated later)

    # Host patterns
    hostname_re = r'[a-z' + ul + r'0-9](?:[a-z' + ul + r'0-9-]*[a-z' + ul + r'0-9])?'
    domain_re = r'(?:\.[a-z' + ul + r'0-9]+(?:[a-z' + ul + r'0-9-]*[a-z' + ul + r'0-9]+)*)*'
    tld_re = r'\.[a-z' + ul + r']{2,}\.?'
    host_re = '(' + hostname_re + domain_re + tld_re + '|localhost)'

    urlregex = re.compile(
        r'^(?:[a-z0-9\.\-]*)://' # scheme is validated separately
        r'(?:\S+(?::\S*)?@)?' # user:pass authentication
        r'(?:' + ipv4_re + '|' + ipv6_re + '|' + host_re + ')'
        r'(?::\d{2,5})?' # port
        r'(?:[/?#][^\s]*)?' # resource path
        r'$', re.IGNORECASE)
    return urlregex

def cmp_e_conv(vals):
    out = []
    for n in range(len(vals)):
        try: out.append( int( math.floor( math.log( abs( vals[n] - vals[n+1] ), 10 ) ) )  )
        except (IndexError, ValueError): pass # beware log math domain error when the adjacent values are the same
    return out

def generate_cif(structure, comment=None, symops=['+x,+y,+z']):
    parameters = cell_to_cellpar(structure.cell)
    cif_data = "# " + comment + "\n\n" if comment else ''
    cif_data += 'data_tilde_project\n'
    cif_data += '_cell_length_a    ' + "%2.6f" % parameters[0] + "\n"
    cif_data += '_cell_length_b    ' + "%2.6f" % parameters[1] + "\n"
    cif_data += '_cell_length_c    ' + "%2.6f" % parameters[2] + "\n"
    cif_data += '_cell_angle_alpha ' + "%2.6f" % parameters[3] + "\n"
    cif_data += '_cell_angle_beta  ' + "%2.6f" % parameters[4] + "\n"
    cif_data += '_cell_angle_gamma ' + "%2.6f" % parameters[5] + "\n"
    cif_data += "_symmetry_space_group_name_H-M 'P1'" + "\n"
    cif_data += 'loop_' + "\n"
    cif_data += '_symmetry_equiv_pos_as_xyz' + "\n"
    for i in symops:
        cif_data += i + "\n"
    cif_data += 'loop_' + "\n"
    cif_data += '_atom_site_type_symbol' + "\n"
    cif_data += '_atom_site_fract_x' + "\n"
    cif_data += '_atom_site_fract_y' + "\n"
    cif_data += '_atom_site_fract_z' + "\n"
    pos = structure.get_scaled_positions()
    for n, i in enumerate(structure):
        cif_data += "%s   % 1.8f   % 1.8f   % 1.8f\n" % (i.symbol, pos[n][0], pos[n][1], pos[n][2])
    return cif_data

def generate_xyz(atoms):
    xyz_data = "%s" % len(atoms) + "\nXYZ\n"
    for i in range(len(atoms)):
        xyz_data += atoms[i].symbol + " " + "%2.4f" % atoms[i].x + " " + "%2.4f" % atoms[i].y + " " + "%2.4f" % atoms[i].z + "\n"
    return xyz_data[0:-1]

def write_cif(filename, structure, comment=None):
    try:
        file = open(filename, 'w')
        file.write(generate_cif(structure, comment))
        file.close()
    except IOError: return False
    else: return True
