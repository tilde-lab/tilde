
# tilda project: EXCITING calculations parser
# Christian Meisenbichler's ASE code is partly used
# v030913

import os
import sys

from numpy import array
from numpy import reshape

from lxml import etree as ET

from ase.atoms import Atoms as ASE_atoms
from ase.lattice.spacegroup.cell import cell_to_cellpar
from ase.units import Bohr, Hartree

from common import deaseize
from parsers import Output


# info.xml parser

class Info_Schema(Output):
    def __init__(self, file, **kwargs):
        Output.__init__(self, file)
        self.data = open(file).read()
        
        # parse file into element tree
        try: doc = ET.parse(file)
        except ET.XMLSyntaxError: raise RuntimeError("This schema has unrecoverable errors!")

        root = doc.getroot()
        
        # Structure
        structure = root.find('groundstate').find('scl').find('structure')
        speciesnodes = structure.getiterator('species') 
     
        symbols = []
        positions = []
        basevects = []
        ase_structure = None        
        
        for speciesnode in speciesnodes:
            symbol = speciesnode.attrib['chemicalSymbol']
            natoms = speciesnode.getiterator('atom')
            for atom in natoms:
                positions.append(map(float, [atom.attrib['x'], atom.attrib['y'], atom.attrib['z']]))
                symbols.append(symbol)
            
        basevectsn = doc.xpath('//basevect/text()') 
        for basevect in basevectsn:
            basevects.append(  array(map(lambda x: float(x) * Bohr, basevect.split()))  )
        ase_structure = ASE_atoms(symbols=symbols, scaled_positions=positions, cell=basevects)
        
        if 'molecule' in structure.attrib.keys():
            ase_structure.set_pbc(False)
        else:
            ase_structure.set_pbc(True)

        self.structures = [deaseize(ase_structure)]
        
        # Total energy & forces
        self.energy = float(doc.xpath('//@totalEnergy')[-1]) * Hartree
        
        forces = []
        forcesnodes = doc.xpath('//structure[last()]/species/atom/forces/totalforce/@*')
        
        for force in forcesnodes:
            forces.append(array(float(force)))
        self.forces = reshape(forces, (-1, 3)) * Hartree / Bohr
        
        if str(doc.xpath('//groundstate/@status')[0]) == 'finished':
			self.info['finished'] = 1
        else:
			self.info['finished'] = -1
        
    @staticmethod
    def fingerprints(test_string):
        if test_string.startswith('<?xml-stylesheet href="http://xml.exciting-code.org/info.xsl" type="text/xsl"?>'): return True
        else: return False
