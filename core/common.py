
# *includable* Tilde routines

import os
import sys
import math
import json

from numpy import dot, array, matrix

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps')) # this is done to have all 3rd party code in core/deps

from deps.ase.atoms import Atoms

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps/ase/lattice'))

from spacegroup.cell import cell_to_cellpar


class ModuleError(Exception): # not working! TODO
    def __init__(self, value):
        self.value = value        

def metric(v):
    ''' Get direction of vector '''
    return map(lambda x: int(math.copysign(1, x)) if x else 0, v)

def u(obj, encoding='utf-8'):
    if not isinstance(obj, unicode):
        return unicode(obj, encoding)
    else: return obj
    
def str2html(i):
    # TODO
    tokens = { \
    '{{units-energy}}': '<span class=units-energy></span>',
    ',,': '<sub>',
    '__': '</sub>',
    '^^': '<sup>',
    '**': '</sup>',
    }
    i = str(i)
    for k, v in tokens.iteritems():
        i = i.replace(k, v)
    return i
    
def html_formula(string):
    sub, html_formula = False, ''
    for n, i in enumerate(string):
        if i.isdigit() or i=='.' or i=='-':
            if not sub and n != 0:
                html_formula += '<sub>'
                sub = True
        else:
            if sub and i != 'd':
                html_formula += '</sub>'
                sub = False
        html_formula += i
    if sub: html_formula += '</sub>'
    return html_formula
    
def is_binary_string(bytes):
    ''' Determine if a string is classified as binary rather than text '''
    nontext = bytes.translate(''.join(map(chr, range(256))), ''.join(map(chr, [7,8,9,10,12,13,27] + range(0x20, 0x100)))) # all bytes and text bytes
    return bool(nontext)
    
def ase2dict(ase_obj):
    return {
    'symbols': ase_obj.get_chemical_symbols(),
    'cell': ase_obj.cell.tolist(),
    'atoms': ase_obj.positions.tolist(),
    'dims': ase_obj.dims,
    'periodicity': int(ase_obj.periodicity),
    'info': ase_obj.info,
    'charges': ase_obj.get_initial_charges().tolist(),
    'magmoms': ase_obj.get_initial_magnetic_moments().tolist()
    }
    
def dict2ase(ase_dict):
    ase_obj = Atoms( \
        symbols=map(lambda x: x.encode('ascii'), ase_dict['symbols']),
        cell=ase_dict['cell'], 
        positions=ase_dict['atoms'],
        pbc=ase_dict['periodicity'], 
        info=ase_dict['info'],
        magmoms=ase_dict['magmoms'],
        charges=ase_dict['charges']
    )
    ase_obj.dims = ase_dict['dims']
    ase_obj.periodicity = ase_dict['periodicity']
    return ase_obj
        
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
    for i in symops: cif_data += i + "\n"
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
