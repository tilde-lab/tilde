
# *includable* Tilde routines

import os
import sys
from numpy import dot
from numpy import array
from numpy import matrix

# this is done to have all third-party code in deps folder
# TODO: dealing with sys.path is malpractice
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps'))
from deps.ase.atoms import Atoms as ASE_atoms

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps/ase/lattice'))
from spacegroup.cell import cellpar_to_cell
from spacegroup.cell import cell_to_cellpar


class ModuleError(Exception):
    def __init__(self, value):
        self.value = value

def u(obj, encoding='utf-8'):
    if not isinstance(obj, unicode):
        return unicode(obj, encoding)
    else: return obj
    
def html2str(i):
    return str(i).replace('<sub>', '_').replace('</sub>', '').replace('<sup>', '^').replace('</sup>', '')
        
def generate_cif(parameters, atoms, symops, comment=None):
    if not parameters: parameters = [10, 10, 10, 90, 90, 90]
    reverse = matrix( cellpar_to_cell(parameters) ).I
    cif_data = "# " + comment + "\n\n" if comment else ''
    cif_data += 'data_tilde_project\n'
    cif_data += '_cell_length_a    ' + "%2.6f" % parameters[0] + "\n"
    cif_data += '_cell_length_b    ' + "%2.6f" % parameters[1] + "\n"
    cif_data += '_cell_length_c    ' + "%2.6f" % parameters[2] + "\n"
    cif_data += '_cell_angle_alpha ' + "%2.6f" % parameters[3] + "\n"
    cif_data += '_cell_angle_beta  ' + "%2.6f" % parameters[4] + "\n"
    cif_data += '_cell_angle_gamma ' + "%2.6f" % parameters[5] + "\n"
    cif_data += "_symmetry_space_group_name_H-M ' '" + "\n"
    cif_data += 'loop_' + "\n"
    cif_data += '_symmetry_equiv_pos_as_xyz' + "\n"
    for i in range(0, len(symops)): cif_data += symops[i] + "\n"
    cif_data += 'loop_' + "\n"
    cif_data += '_atom_site_label' + "\n"
    cif_data += '_atom_site_type_symbol' + "\n"
    cif_data += '_atom_site_fract_x' + "\n"
    cif_data += '_atom_site_fract_y' + "\n"
    cif_data += '_atom_site_fract_z' + "\n"
    for i in range(0, len(atoms)):
        x, y, z = dot( array([atoms[i][1], atoms[i][2], atoms[i][3]]), reverse ).tolist()[0]
        cif_data += "%s%s   %s   % 1.8f   % 1.8f   % 1.8f\n" % (atoms[i][0], (i+1), atoms[i][0], x, y, z)
    return cif_data
    
def write_cif(parameters, atoms, symops, filename, comment=None):
    cif_data = generate_cif(parameters, atoms, symops, comment)
    try:
        file = open(filename, 'w')
        file.write(cif_data)
        file.close()
    except IOError: return False
    else: return True
    
def generate_xyz(atoms):
    xyz_data = "%s" % len(atoms) + "\nXYZ\n"
    for i in range(0, len(atoms)):
        xyz_data += atoms[i][0] + " " + "%2.4f" % atoms[i][1] + " " + "%2.4f" % atoms[i][2] + " " + "%2.4f" % atoms[i][3] + "\n"
    return xyz_data[0:-1]

def aseize(tilde_struc):
    ''' Bridge to ASE structure format from Tilde structure format '''
    ase_symbols = []
    for i in tilde_struc['atoms']:
        adata = 'X' if i[0] == 'Xx' else i[0]
        symb = filter(None, adata.split(' '))[-1]
        symb = ''.join([letter for letter in symb if not letter.isdigit()])
        ase_symbols.append(symb.encode('ascii'))
    ase_positions = [(i[1], i[2], i[3]) for i in tilde_struc['atoms']]
    if tilde_struc['periodicity']>0:
        pbc=True
        xyz_matrix = cellpar_to_cell(tilde_struc['cell'])
        descr = {'hm': None, 'a': "%2.3f" % tilde_struc['cell'][0], 'b': "%2.3f" % tilde_struc['cell'][1], 'c': "%2.3f" % tilde_struc['cell'][2], 'alpha': "%2.3f" % tilde_struc['cell'][3], 'beta': "%2.3f" % tilde_struc['cell'][4], 'gamma': "%2.3f" % tilde_struc['cell'][5]} # NB: this is used by player
    else:
        pbc=None
        xyz_matrix=None
        descr=None
    return ASE_atoms(symbols=ase_symbols, positions=ase_positions, cell=xyz_matrix, pbc=pbc, info=descr)

def deaseize(ase_obj):
    ''' Bridge to Tilde structure format from ASE structure format '''
    tilde_values = ['a', 'b', 'c', 'alpha', 'beta', 'gamma']
    atypes = ase_obj.get_chemical_symbols()
    atoms = [ [atypes[n], i[0], i[1], i[2]] for n, i in enumerate(ase_obj.positions) ]
    cell = [ float( ase_obj.info[tilde_key] ) for tilde_key in tilde_values ] if 'hm' in ase_obj.info else cell_to_cellpar( ase_obj.cell ).tolist()
    return {'cell': cell, 'atoms': atoms, 'periodicity':3} # todo
