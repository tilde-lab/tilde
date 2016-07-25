
# Perovskites octahedral tilting extraction
# based on Surf.Sci.602 3674 (2008)
# http://dx.doi.org/10.1016/j.susc.2008.10.002
# Author: Evgeny Blokhin
#
# KNOWN BUG: in some low-symmetry cases ("batio3_lda_hw12d_160_to.out"),
# octahedra are not adjusted with the axes, and their distortion origin is unknown.
# Even if the rotation is absent (i.e. pseudo-cubic structure),
# an "artificial" rotation can be extracted
# FIXME?
from __future__ import division

import os, sys
import math
import copy
import json
from functools import reduce

from numpy.linalg import norm

from ase import Atom, Atoms
from ase.geometry import cell_to_cellpar

from tilde.core.common import ModuleError #, generate_xyz
from tilde.core.constants import Perovskite_Structure
from tilde.core.symmetry import SymmetryFinder


class Perovskite_tilting():
    OCTAHEDRON_BOND_LENGTH_LIMIT = 2.5  # Angstrom
    OCTAHEDRON_ATOMS_Z_DIFFERENCE = 1.6 # Angstrom
    MAX_TILTING_DEGREE = 22.4           # degrees, this is for adjusting, may produce unphysical results

    def __init__(self, tilde_calc):
        self.prec_angles = {}    # non-rounded, non-unique, all-planes angles
        self.angles = {}         # rounded, unique, one-plane angles

        symm = SymmetryFinder()
        symm.refine_cell(tilde_calc)
        if symm.error:
            raise ModuleError("Cell refinement error: %s" % symm.error)

        # check if the longest axis is Z, rotate otherwise
        lengths = list(map(norm, symm.refinedcell.cell))
        if not (lengths[2] - lengths[0] > 1E-6 and lengths[2] - lengths[1] > 1E-6):
            axnames = {0: 'x', 1: 'y'}
            principal_ax = axnames[ lengths.index(max(lengths[0], lengths[1])) ]
            symm.refinedcell.rotate(principal_ax, 'z', rotate_cell = True)

        self.virtual_atoms = symm.refinedcell.copy()

        #f = open('tilting.xyz', 'w')
        #f.write(generate_xyz(self.virtual_atoms))
        #f.close()

        # translate atoms around octahedra in all directions
        shift_dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (1, 1, 0), (1, -1, 0), (-1, -1, 0), (-1, 1, 0), (0, 0, 1), (0, 0, -1)]

        for k, i in enumerate(symm.refinedcell):
            if i.symbol in Perovskite_Structure.C:
                for dir in shift_dirs:
                    self.translate(k, symm.refinedcell.cell, dir, self.virtual_atoms)

        # extract octahedra and their main tilting planes
        for octahedron in self.get_octahedra(symm.refinedcell, symm.refinedcell.periodicity):
            #print 'octahedron:', octahedron[0]+1 #, self.virtual_atoms[octahedron[0]].symbol, self.virtual_atoms[octahedron[0]].x, self.virtual_atoms[octahedron[0]].y, self.virtual_atoms[octahedron[0]].z
            #print 'corners:', [i+1 for i in octahedron[1]]

            # Option 1. Extract only one tilting plane, the closest to perpendicular to Z-axis
            '''tiltplane = self.get_tiltplane(octahedron[1])
            if len(tiltplane) == 4:
                t = self.get_tilting(tiltplane)
                #print 'result:', [i+1 for i in tiltplane], t
                self.prec_angles.update( { octahedron[0]: [ t ] } )'''

            # Option 2. Extract all three possible tilting planes,
            # try to spot the closest to perpendicular to Z-axis
            # and consider the smallest tilting
            plane_tilting = []
            for oplane in self.get_tiltplanes(octahedron[1]):
                t = self.get_tilting(oplane)
                #print "result:", [i+1 for i in oplane], t
                plane_tilting.append( t )
            self.prec_angles.update( { octahedron[0]: plane_tilting } )

        if not self.prec_angles: raise ModuleError("Cannot find any main tilting plane!")

        # uniquify and round self.prec_angles to obtain self.angles
        u, todel = [], []
        for o in self.prec_angles:
            self.prec_angles[o] = reduce(lambda x, y: x if sum(x) <= sum(y) else y, self.prec_angles[o]) # only minimal angles are taken if tilting planes vary!
            self.prec_angles[o] = list(map(lambda x: list(map(lambda y: round(y, 2), x)), [self.prec_angles[o]]))
            for i in self.prec_angles[o]:
                u.append([o] + i)
        u = sorted(u, key=lambda x:x[0])
        u.reverse() # to make index of oct.centers minimal
        for i in u:
            for j in range(u.index(i)+1, len(u)):
                if i[1:] == u[j][1:]:
                    todel.append(u.index(i))
                    continue
        for i in [j for j in u if u.index(j) not in todel]:
            self.angles[ i[0]+1 ] = i[1:] # atomic index is counted from zero!

    def translate(self, num_of_atom, cell, components, reference):
        a_component, b_component, c_component = components
        reference.append(Atom(
            reference[num_of_atom].symbol,
            (reference[num_of_atom].x + a_component * cell[0][0] + b_component * cell[1][0] + c_component * cell[2][0],
            reference[num_of_atom].y + a_component * cell[0][1] + b_component * cell[1][1] + c_component * cell[2][1],
            reference[num_of_atom].z + a_component * cell[0][2] + b_component * cell[1][2] + c_component * cell[2][2])
        ))

    def get_bisector_point(self, num_of_A, num_of_O, num_of_B, reference):
        xA = reference[num_of_A].x
        yA = reference[num_of_A].y
        zA = reference[num_of_A].z
        xO = reference[num_of_O].x
        yO = reference[num_of_O].y
        zO = reference[num_of_O].z
        xB = reference[num_of_B].x
        yB = reference[num_of_B].y
        zB = reference[num_of_B].z
        m = self.virtual_atoms.get_distance(num_of_O, num_of_A)
        n = self.virtual_atoms.get_distance(num_of_O, num_of_B)

        # bisector length
        l = 2*m*n*math.cos(self.virtual_atoms.get_angle([num_of_A, num_of_O, num_of_B])/2) / (m+n)
        v = math.sqrt(n*n - n*l*l/m)
        u = m*v/n
        A = yA*(zO - zB) + yO*(zB - zA) + yB*(zA - zO)
        B = zA*(xO - xB) + zO*(xB - xA) + zB*(xA - xO)
        C = xA*(yO - yB) + xO*(yB - yA) + xB*(yA - yO)
        if C == 0: C = 1E-10 # prevent zero division
        D = xA*(yO*zB - yB*zO) + xO*(yB*zA - yA*zB) + xB*(yA*zO - yO*zA)
        D *= -1

        # from surface analytical equation
        x = (xA + u*xB/v)/(1+u/v)
        y = (yA + u*yB/v)/(1+u/v)
        z = -((A*x + B*y + D) / C)
        return [x, y, z]

    def get_octahedra(self, atoms, periodicity=3):
        ''' extract octahedra as lists of sequence numbers of corner atoms '''

        octahedra = []
        for n, i in enumerate(atoms):
            found = []
            if i.symbol in Perovskite_Structure.B:
                for m, j in enumerate(self.virtual_atoms):
                    if j.symbol in Perovskite_Structure.C and self.virtual_atoms.get_distance(n, m) <= self.OCTAHEDRON_BOND_LENGTH_LIMIT:
                        found.append(m)
            if (periodicity == 3 and len(found) == 6) or (periodicity == 2 and len(found) in [5, 6]):
                octahedra.append([n, found])

        if not len(octahedra): raise ModuleError("Cannot extract valid octahedra: not enough corner atoms found!")
        return octahedra

    def get_tiltplane(self, sequence):
        ''' extract the main tilting plane basing on Z coordinate '''
        sequence = sorted(sequence, key=lambda x: self.virtual_atoms[ x ].z)
        in_plane = []
        for i in range(0, len(sequence)-4):
            if abs(self.virtual_atoms[ sequence[i] ].z - self.virtual_atoms[ sequence[i+1] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE and \
            abs(self.virtual_atoms[ sequence[i+1] ].z - self.virtual_atoms[ sequence[i+2] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE and \
            abs(self.virtual_atoms[ sequence[i+2] ].z - self.virtual_atoms[ sequence[i+3] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE:
                in_plane = [sequence[j] for j in range(i, i+4)]
        return in_plane

    def get_tiltplanes(self, sequence):
        ''' extract tilting planes basing on distance map '''

        tilting_planes = []
        distance_map = []

        for i in range(1, len(sequence)):
            distance_map.append([ sequence[i], self.virtual_atoms.get_distance( sequence[0], sequence[i] ) ])

        distance_map = sorted(distance_map, key=lambda x: x[1])

        if len(distance_map) == 4:
            # surface edge case
            # semi-octahedron at surface edge has only one tilting plane to consider
            sorted_dist = [i[0] for i in distance_map]
            if distance_map[-1][1] - distance_map[-2][1] < 0.5:
                # 1st case: max diff < 0.5 Angstrom,
                # meaning all distances to reference atom are similar,
                # therefore the reference atom is above the searched plane
                # and the searched plane consists of other atoms
                tilting_planes.append( [ i[0] for i in distance_map ] )
            else:
                # 2nd case: reference atom belongs to the searched plane,
                # procedure needs to be repeated with the next atom as reference atom
                candidates = [sequence[0], sorted_dist[-1]]
                next_distance_map = []
                next_distance_map.append([ sorted_dist[1], self.virtual_atoms.get_distance( sorted_dist[0], sorted_dist[1] ) ])
                next_distance_map.append([ sorted_dist[2], self.virtual_atoms.get_distance( sorted_dist[0], sorted_dist[2] ) ])
                next_distance_map = sorted(next_distance_map, key=lambda x: x[1])
                next_sorted_dist = [i[0] for i in next_distance_map]

                # the next reference atom is taken above the plane (distances are similar)
                if next_distance_map[1][1] - next_distance_map[0][1] < 0.5: candidates.extend([ next_sorted_dist[0], next_sorted_dist[1] ])

                # the next reference atom is taken in the plane (distances are different)
                else: candidates.extend([ sorted_dist[0], next_sorted_dist[1] ])
                tilting_planes.append(candidates)

        elif len(distance_map) == 5:
            # full octahedron case
            # full octahedron has 3 different tilting planes (perpendicular in ideal case)
            sorted_dist = [i[0] for i in distance_map]

            # 1st plane is found as:
            first_plane = sorted_dist[0:4]
            tilting_planes.append(first_plane)
            distance_map_first_plane = []
            for i in range(1, 4):
                distance_map_first_plane.append([ first_plane[i], self.virtual_atoms.get_distance( first_plane[0], first_plane[i] ) ])
            distance_map_first_plane = sorted(distance_map_first_plane, key=lambda x: x[1])
            sorted_first_plane = [i[0] for i in distance_map_first_plane]

            # 2nd and 3rd planes are found as:
            tilting_planes.append([ sequence[0], sorted_dist[4], first_plane[0], sorted_first_plane[2] ])
            tilting_planes.append([ sequence[0], sorted_dist[4], sorted_first_plane[0], sorted_first_plane[1] ])

        # filter planes by Z according to octahedral spatial compound
        filtered = list(filter(   lambda x: \
            abs(self.virtual_atoms[ x[0] ].z - self.virtual_atoms[ x[1] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE and \
            abs(self.virtual_atoms[ x[1] ].z - self.virtual_atoms[ x[2] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE and \
            abs(self.virtual_atoms[ x[2] ].z - self.virtual_atoms[ x[3] ].z) < self.OCTAHEDRON_ATOMS_Z_DIFFERENCE,   tilting_planes   ))
        if len(filtered): tilting_planes = filtered

        return tilting_planes

    def get_tilting(self, oplane):
        ''' main procedure '''

        surf_atom1, surf_atom2, surf_atom3, surf_atom4 = oplane

        # divide surface atoms into groups by distance between them
        compare = [surf_atom2, surf_atom3, surf_atom4]
        distance_map = []

        for i in range(0, 3):
            distance_map.append([ compare[i], self.virtual_atoms.get_distance(surf_atom1, compare[i]) ])

        distance_map = sorted(distance_map, key=lambda x: x[1])

        distance_map_keys = [i[0] for i in distance_map]
        surf_atom3 = distance_map_keys[2]
        surf_atom2 = distance_map_keys[1]
        surf_atom4 = distance_map_keys[0]

        if self.virtual_atoms[surf_atom1].z == self.virtual_atoms[surf_atom2].z and \
            self.virtual_atoms[surf_atom2].z == self.virtual_atoms[surf_atom3].z and \
            self.virtual_atoms[surf_atom3].z == self.virtual_atoms[surf_atom4].z:
            # this is done to prevent false zero tilting
            self.virtual_atoms[surf_atom1].z += 1E-10
            self.virtual_atoms[surf_atom2].z += 1E-10
            self.virtual_atoms[surf_atom3].z -= 1E-10
            self.virtual_atoms[surf_atom4].z -= 1E-10

        # new axes will be defined simply as vectors standing on 1 - 3 and 2 - 4 (they are moved to the point of origin)
        self.virtual_atoms.append(Atom('X', (self.virtual_atoms[surf_atom1].x - self.virtual_atoms[surf_atom3].x, self.virtual_atoms[surf_atom1].y - self.virtual_atoms[surf_atom3].y, self.virtual_atoms[surf_atom1].z - self.virtual_atoms[surf_atom3].z)))
        self.virtual_atoms.append(Atom('X', (self.virtual_atoms[surf_atom2].x - self.virtual_atoms[surf_atom4].x, self.virtual_atoms[surf_atom2].y - self.virtual_atoms[surf_atom4].y, self.virtual_atoms[surf_atom2].z - self.virtual_atoms[surf_atom4].z)))
        self.virtual_atoms.append(Atom('X', (0, 0, 0)))

        # redefine tilted axes
        surf_atom_first = len(self.virtual_atoms)-3
        surf_atom_second = len(self.virtual_atoms)-2
        center = len(self.virtual_atoms)-1

        # inverse arbitrary atom
        self.virtual_atoms.append(Atom('X', (-self.virtual_atoms[surf_atom_first].x, -self.virtual_atoms[surf_atom_first].y, -self.virtual_atoms[surf_atom_first].z)))
        inversed_one = len(self.virtual_atoms)-1

        # find and add bisectors, silly swapping
        first_bisector = self.get_bisector_point(surf_atom_first, center, surf_atom_second, self.virtual_atoms)
        sec_bisector = self.get_bisector_point(surf_atom_second, center, inversed_one, self.virtual_atoms)

        swap = True
        if first_bisector[0] < 0 and sec_bisector[0] < 0: swap = False
        if first_bisector[0] < 0:
            first_bisector[0] *= -1
            first_bisector[1] *= -1
            first_bisector[2] *= -1
        if sec_bisector[0] < 0:
            sec_bisector[0] *= -1
            sec_bisector[1] *= -1
            sec_bisector[2] *= -1
        if swap: first_bisector, sec_bisector = sec_bisector, first_bisector
        swap = False
        if first_bisector[0] < sec_bisector[0] and first_bisector[1] < 0:
            first_bisector[0] *= -1
            first_bisector[1] *= -1
            first_bisector[2] *= -1
            swap = True
        if first_bisector[0] < sec_bisector[0] and first_bisector[1] > 0: swap = True
        if first_bisector[0] > sec_bisector[0] and sec_bisector[1] < 0:
            sec_bisector[0] *= -1
            sec_bisector[1] *= -1
            sec_bisector[2] *= -1
        if swap: first_bisector, sec_bisector = sec_bisector, first_bisector

        self.virtual_atoms.append(Atom('X', (first_bisector[0], first_bisector[1], first_bisector[2])))
        self.virtual_atoms.append(Atom('X', (sec_bisector[0], sec_bisector[1], sec_bisector[2])))
        first_bisector = len(self.virtual_atoms)-2
        sec_bisector = len(self.virtual_atoms)-1

        # use vector cross product to define normal which will play Z axis role
        self.virtual_atoms.append(Atom('X', \
           (self.virtual_atoms[first_bisector].y*self.virtual_atoms[sec_bisector].z - self.virtual_atoms[first_bisector].z*self.virtual_atoms[sec_bisector].y, \
            self.virtual_atoms[first_bisector].z*self.virtual_atoms[sec_bisector].x - self.virtual_atoms[first_bisector].x*self.virtual_atoms[sec_bisector].z, \
            self.virtual_atoms[first_bisector].x*self.virtual_atoms[sec_bisector].y - self.virtual_atoms[first_bisector].y*self.virtual_atoms[sec_bisector].x)))
        tilt_z = len(self.virtual_atoms)-1

        # Euler angles ZYZ
        alpha = math.degrees(math.atan2(self.virtual_atoms[sec_bisector].z, self.virtual_atoms[first_bisector].z))
        beta = math.degrees(math.atan2(math.sqrt(self.virtual_atoms[tilt_z].x**2 + self.virtual_atoms[tilt_z].y**2), self.virtual_atoms[tilt_z].z))
        gamma = math.degrees(math.atan2(self.virtual_atoms[tilt_z].y, -self.virtual_atoms[tilt_z].x))

        # angles adjusting
        adjust_angles = [45, 90, 135, 180, 225, 270, 315, 360]
        tilting = [alpha, beta, gamma]
        for i in range(0, 3):
            tilting[i] = abs(tilting[i])
            if tilting[i] in adjust_angles:
                tilting[i] = 0.0
                continue
            if tilting[i] > self.MAX_TILTING_DEGREE:
                for checkpoint in adjust_angles:
                    if checkpoint - self.MAX_TILTING_DEGREE < tilting[i] < checkpoint + self.MAX_TILTING_DEGREE:
                        tilting[i] = abs(tilting[i] - checkpoint)
                        break
        return tilting
