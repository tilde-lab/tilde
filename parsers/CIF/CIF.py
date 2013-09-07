
# Tilde project: PyCIfRW CIF outputs parser
# v030913

import re

from ase.atoms import Atoms as ASE_atoms
from ase.lattice.spacegroup.cell import cellpar_to_cell

from PyCifRW import CifFile

from parsers import Output
from core.common import deaseize

class CIF(Output):
	def __init__(self, file, **kwargs):
		Output.__init__(self, file)
		self.data = open(file).read()
		CIF_instance = CifFile.ReadCif(file)
		main = CIF_instance.first_block()
		
		try: main['_atom_site_occupancy']
		except KeyError: pass
		else: raise RuntimeError('Site_occupancy not implemented, sorry')

		cell_parameters, ase_symbols = [], []

		for i in ['_cell_length_a', '_cell_length_b', '_cell_length_c', '_cell_angle_alpha', '_cell_angle_beta', '_cell_angle_gamma']:
			try:
				cell_parameters.append(float( re.sub(r'\(.*\)', '', main[i]) ))
			except (KeyError, ValueError):
				raise RuntimeError('CIF has unknown / unconventional format!')
		
		xyz_matrix = cellpar_to_cell(cell_parameters)
		
		try: main['_atom_site_fract_x']
		except KeyError:
			try: main['_atom_site_Cartn_x']
			except KeyError:
				raise RuntimeError('CIF has unknown / unconventional format!')
			else:
				format_keys = ['_atom_site_Cartn_x', '_atom_site_Cartn_y', '_atom_site_Cartn_z']
		else:
			format_keys = ['_atom_site_fract_x', '_atom_site_fract_y', '_atom_site_fract_z']
			
		coords = [[], [], []] # x, y, z
		try:
			for n, key in enumerate(format_keys):
				coords[n] = map(  lambda i: float( re.sub(r'\(.*\)', '', i) ), main[key]  )
		except ValueError:
			raise RuntimeError('CIF has unknown / unconventional format!')
		
		ase_positions = [(coords[0][i], coords[1][i], coords[2][i]) for i in range(len(coords[0]))]	
		
		try:
			symb = main['_atom_site_type_symbol']
		except KeyError:
			symb = main['_atom_site_label']
		except:
			raise RuntimeError('CIF has unknown / unconventional format!')		
		
		for i in symb:
			i = re.sub('[^a-zA-Z]+', '', i)
			i = i.encode('ascii').capitalize()
			if i == 'Xx': i = 'X'
			ase_symbols.append(i)
		
		ase_structure = ASE_atoms(symbols=ase_symbols, cell=xyz_matrix, pbc=True)
		
		if format_keys[0] == '_atom_site_fract_x': ase_structure.set_scaled_positions(ase_positions)
		else: ase_structure.set_positions(ase_positions)
		
		self.structures = [deaseize(ase_structure)]
		
		# TODO: parse symmetry and do not invoke symmetry finder
		# TODO: parse _atom_site_occupancy

	@staticmethod
	def fingerprints(test_string):
		if test_string.startswith("_cell_length_a "): return True
		else: return False
