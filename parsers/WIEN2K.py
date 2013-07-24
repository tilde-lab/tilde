#!/usr/bin/env python
# tilda project: WIEN2k scf and STRUCT parser
# v230513

import os
import sys
import re
import math

from numpy import dot
from numpy import array

from ase.lattice.spacegroup.cell import cell_to_cellpar

from parsers import Output


Bohr = 0.5291772
Hartree = 27.211398
Rydberg = Hartree / 2

class SCF(Output):
    def __init__(self, file, **kwargs):
        Output.__init__(self, file)
        self.data = open(file).readlines()
        cell = []
        atoms = []
        natoms = []
        poses = {}
        mwarn = False

        for n, line in enumerate(self.data):
            if line.startswith(':LAT'):
                vdata = line.replace(':LAT  : LATTICE CONSTANTS=', '').split(' ')
                vdata = filter(None, vdata)
                cell = [ [float(vdata[0]) * Bohr, 0, 0], [0, float(vdata[1]) * Bohr, 0], [0, 0, float(vdata[2]) * Bohr] ]

            elif line.startswith(':POS'):
                if not 'MULTIPLICITY =  1' in line: mwarn = True
                adata = line.replace(':POS', '').replace('\r', '').replace('\n', '').split(':')
                try: poses[ int(adata[0]) ]
                except KeyError:
                    atom = filter(None, adata[1][22:47].split(' '))
                    atom = [float(i) for i in atom]
                    poses[ int(adata[0]) ] = [atom[0], atom[1], atom[2]]

            elif 'ATOMNUMBER=' in line:
                aparts = filter(None, line.split(' '))
                aparts[2] = ''.join([letter for letter in aparts[2] if not letter.isdigit()])
                natoms.append( aparts[1:3] )

            elif line.startswith(':ENE'):
                self.energy = float(line[43:]) * Rydberg/Hartree

        # uniquify natoms
        seen = []
        for a in natoms:
            a[0] = int(a[0])
            if a[0] not in seen:
                atom = [ a[1] ]
                atom.extend( poses[a[0]] )
                atoms.append( atom )
                seen.append(a[0])
        
        # TODO:
        # is it possible to re-create symmetry-equivalent atoms without STRUCT?
        # if yes, that would be preferable!
        if len(atoms) != len(poses): raise RuntimeError("Cannot find all atomic positions!")
        
        # de-fractionize
        xyz_atoms = []
        for i in atoms:
            R = dot( array([i[1], i[2], i[3]]), cell )
            xyz_atoms.append( [i[0], R[0], R[1], R[2]] )
        
        self.structures = [{'cell': cell_to_cellpar( cell ).tolist(), 'atoms': xyz_atoms, 'periodicity':3}]

        self.warning('Warning, at the moment only cells with the direct angles are supported!')
        if mwarn: self.warning('Warning, some symmetry-equivalent atoms were not restored!')
        
        self.data = "\n".join(self.data)
        self.info['prog'] = "WIEN2K"

    @staticmethod
    def fingerprints(test_string):
        if ":LAT  : " in test_string: return True # using Wien2
        else: return False
