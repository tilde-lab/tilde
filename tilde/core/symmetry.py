
# *SymmetryFinder*: platform-independent symmetry finder, wrapping Spglib code
# *SymmetryHandler*: symmetry inferences for 0D-, 1D-, 2D- and 3D-systems
# Author: Evgeny Blokhin
# v080416

import os, sys

from numpy import array, zeros
from numpy.linalg import det

from ase.atoms import Atoms
from ase.geometry import cell_to_cellpar

import spglib as spg


class SymmetryFinder:
    accuracy = 1e-04 # recommended accuracy value = 0.0001

    def __init__(self, accuracy=None):
        self.error = None
        self.accuracy=accuracy if accuracy else SymmetryFinder.accuracy
        self.angle_tolerance=4

    def get_spacegroup(self, tilde_obj):
        try:
            symmetry = spg.get_spacegroup(tilde_obj['structures'][-1], symprec=self.accuracy, angle_tolerance=self.angle_tolerance)
        except Exception as ex:
            self.error = 'Symmetry finder error: %s' % ex
        else:
            symmetry = symmetry.split()
            self.i = symmetry[0]
            try: self.n = int( symmetry[1].replace("(", "").replace(")", "") )
            except (ValueError, IndexError): self.n = 0
            if self.n == 0:
                self.error = 'Symmetry finder error (probably, coinciding atoms)'

    def refine_cell(self, tilde_obj):
        '''
        NB only used for perovskite_tilting app
        '''
        try: lattice, positions, numbers = spg.refine_cell(tilde_obj['structures'][-1], symprec=self.accuracy, angle_tolerance=self.angle_tolerance)
        except Exception as ex:
            self.error = 'Symmetry finder error: %s' % ex
        else:
            self.refinedcell = Atoms(numbers=numbers, cell=lattice, scaled_positions=positions, pbc=tilde_obj['structures'][-1].get_pbc())
            self.refinedcell.periodicity = sum(self.refinedcell.get_pbc())
            self.refinedcell.dims = abs(det(tilde_obj['structures'][-1].cell))

"""
# Dummy class for testing purposes
class SymmetryFinder:
    accuracy = 1e-04
    def __init__(self, tilde_obj, accuracy=None):
        self.error = None
        self.accuracy=accuracy if accuracy else SymmetryFinder.accuracy
    def get_spacegroup(self, tilde_obj):
        self.n = 1
        self.i = 'P1'
"""

class SymmetryHandler(SymmetryFinder):
    def __init__(self, tilde_obj, accuracy=None):
        self.i = None
        self.n = None
        self.symmetry = None
        self.pg = None
        self.dg = None

        SymmetryFinder.__init__(self, accuracy)
        SymmetryFinder.get_spacegroup(self, tilde_obj)

        # Data below are taken from Table 2.3 of the book
        # Robert A. Evarestov, Quantum Chemistry of Solids,
        # LCAO Treatment of Crystals and Nanostructures, 2nd Edition,
        # Springer, 2012, http://dx.doi.org/10.1007/978-3-642-30356-2
        # NB 7 crystal systems != 7 lattice systems

        # space group to crystal system conversion
        if   195 <= self.n <= 230: self.symmetry = 'cubic'
        elif 168 <= self.n <= 194: self.symmetry = 'hexagonal'
        elif 143 <= self.n <= 167: self.symmetry = 'trigonal'
        elif 75  <= self.n <= 142: self.symmetry = 'tetragonal'
        elif 16  <= self.n <= 74:  self.symmetry = 'orthorhombic'
        elif 3   <= self.n <= 15:  self.symmetry = 'monoclinic'
        elif 1   <= self.n <= 2:   self.symmetry = 'triclinic'

        # space group to point group conversion
        if   221 <= self.n <= 230: self.pg = 'O<sub>h</sub>'
        elif 215 <= self.n <= 220: self.pg = 'T<sub>d</sub>'
        elif 207 <= self.n <= 214: self.pg = 'O'
        elif 200 <= self.n <= 206: self.pg = 'T<sub>h</sub>'
        elif 195 <= self.n <= 199: self.pg = 'T'
        elif 191 <= self.n <= 194: self.pg = 'D<sub>6h</sub>'
        elif 187 <= self.n <= 190: self.pg = 'D<sub>3h</sub>'
        elif 183 <= self.n <= 186: self.pg = 'C<sub>6v</sub>'
        elif 177 <= self.n <= 182: self.pg = 'D<sub>6</sub>'
        elif 175 <= self.n <= 176: self.pg = 'C<sub>6h</sub>'
        elif        self.n == 174: self.pg = 'C<sub>3h</sub>'
        elif 168 <= self.n <= 173: self.pg = 'C<sub>6</sub>'
        elif 162 <= self.n <= 167: self.pg = 'D<sub>3d</sub>'
        elif 156 <= self.n <= 161: self.pg = 'C<sub>3v</sub>'
        elif 149 <= self.n <= 155: self.pg = 'D<sub>3</sub>'
        elif 147 <= self.n <= 148: self.pg = 'C<sub>3i</sub>'
        elif 143 <= self.n <= 146: self.pg = 'C<sub>3</sub>'
        elif 123 <= self.n <= 142: self.pg = 'D<sub>4h</sub>'
        elif 111 <= self.n <= 122: self.pg = 'D<sub>2d</sub>'
        elif 99 <= self.n <= 110:  self.pg = 'C<sub>4v</sub>'
        elif 89 <= self.n <= 98:   self.pg = 'D<sub>4</sub>'
        elif 83 <= self.n <= 88:   self.pg = 'C<sub>4h</sub>'
        elif 81 <= self.n <= 82:   self.pg = 'S<sub>4</sub>'
        elif 75 <= self.n <= 80:   self.pg = 'C<sub>4</sub>'
        elif 47 <= self.n <= 74:   self.pg = 'D<sub>2h</sub>'
        elif 25 <= self.n <= 46:   self.pg = 'C<sub>2v</sub>'
        elif 16 <= self.n <= 24:   self.pg = 'D<sub>2</sub>'
        elif 10 <= self.n <= 15:   self.pg = 'C<sub>2h</sub>'
        elif 6 <= self.n <= 9:     self.pg = 'C<sub>s</sub>'
        elif 3 <= self.n <= 5:     self.pg = 'C<sub>2</sub>'
        elif self.n == 2:          self.pg = 'C<sub>i</sub>'
        elif self.n == 1:          self.pg = 'C<sub>1</sub>'

        # space group to layer group conversion
        if tilde_obj.structures[-1].periodicity == 2:
            if self.n in [25, 26, 28, 51]:
                tilde_obj.warning('Warning! Diperiodical group setting is undefined!')
            DIPERIODIC_MAPPING = {3:8, 4:9, 5:10, 6:11, 7:12, 8:13, 10:14, 11:15, 12:16, 13:17, 14:18, 16:19, 17:20, 18:21, 21:22, 25:23, 25:24, 26:25, 26:26, 27:27, 28:28, 28:29, 29:30, 30:31, 31:32, 32:33, 35:34, 38:35, 39:36, 47:37, 49:38, 50:39, 51:40, 51:41, 53:42, 54:43, 55:44, 57:45, 59:46, 65:47, 67:48, 75:49, 81:50, 83:51, 85:52, 89:53, 90:54, 99:55, 100:56, 111:57, 113:58, 115:59, 117:60, 123:61, 125:62, 127:63, 129:64, 143:65, 147:66, 149:67, 150:68, 156:69, 157:70, 162:71, 164:72, 168:73, 174:74, 175:75, 177:76, 183:77, 187:78, 189:79, 191:80}

            cellpar = cell_to_cellpar( tilde_obj.structures[-1].cell ).tolist()
            if cellpar[3] != 90 or cellpar[4] != 90 or cellpar[5] != 90:
                DIPERIODIC_MAPPING.update({1:1, 2:2, 3:3, 6:4, 7:5, 10:6, 13:7})
            try: self.dg = DIPERIODIC_MAPPING[self.n]
            except KeyError: tilde_obj.warning('No diperiodical group found because rotational axes inconsistent with 2d translations!')
            else:
                if   65 <= self.dg <= 80: self.symmetry = '2d-hexagonal'
                elif 49 <= self.dg <= 64: self.symmetry = '2d-square'
                elif 8  <= self.dg <= 48: self.symmetry = '2d-rectangular'
                elif 1  <= self.dg <= 7:  self.symmetry = '2d-oblique'
