
# Perovskites octahedral tilting extraction
# based on Surf.Sci.602 3674 (2008)
# http://dx.doi.org/10.1016/j.susc.2008.10.002
# initial version created in php 20.04.09 by Evgeny Blokhin
# v220513

import os
import sys
import math
import copy
from numpy import dot
from numpy import array
from numpy import matrix

from ase.lattice.spacegroup.cell import cellpar_to_cell
from core.common import ModuleError, write_cif

from core.settings import DATA_DIR


class Tilting():
    OCTAHEDRON_BOND_LENGTH_LIMIT = 2.5           # Angstrom
    OCTAHEDRON_ATOMS_Z_ORIENT_DIFFERENCE = 1.7   # Angstrom
    MAX_TILTING_DEGREE = 22.4                    # degree
    CENTER_ATOM_TYPES = tuple('Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Ga, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd, In, Sn, Sb, Hf, Ta, W, Re'.split(', '))
    CORNER_ATOM_TYPES = tuple('O, F'.split(', '))

    @staticmethod
    def cell_wrapper(obj, colnum):
        repr = ''
        selfname = __name__.split('.')[-1]

        if not selfname in obj['apps']: return "<td rel=%s>&mdash;</td>" % colnum

        for k in obj['apps'][selfname]:
            for i in obj['apps'][selfname][k]:
                repr += str(i) + ', '
            repr = repr[:-2]
            if sum(obj['apps'][selfname][k]): repr += ' (' + str(k) + ')'
            repr += '<br />'
        return "<td rel=%s><div class=sml>%s</div></td>" % (colnum, repr)

    def __init__(self, tilde_calc):
        self.prec_angles = {}    # non-rounded, non-uniquified, all-planes angles
        self.angles = {}         # rounded, uniquified, one-plane angles
        self.cell = cellpar_to_cell(tilde_calc.structures[-1]['cell'])
        self.virtual_atoms = copy.deepcopy(tilde_calc.structures[-1]['atoms'])

        # translate atoms around octahedra
        centers = [[i[1], i[2], i[3]] for i in tilde_calc.structures[-1]['atoms'] if i[0] in self.CENTER_ATOM_TYPES]
        centers = map(lambda x: sum(x)/len(x), zip(*centers))
        centers = dot( array(centers), matrix( self.cell ).I ).tolist()[0]
        centers = map(lambda x: 0 if abs(x) < 0.4 else int(math.copysign(1, x)), centers)

        shift_dirs = []
        ones = sum(map(abs, centers))
        if ones == 3: # [x, x, x] 7 shift directions
            shift_dirs.append(centers)
            for i in range(3):
                c = copy.deepcopy(centers)
                c[i] = 0
                shift_dirs.append(c)
                c = [0, 0, 0]
                c[i] = centers[i]
                shift_dirs.append(c)
        else: # [0, 0, 0] or [x, 0, 0] or [x, x, 0] 5 or 6 shift directions
            for i in range(3):
                if centers[i] == 0:
                    if ones == 2:
                        c = [0, 0, 0]
                        c[i] = 1
                        shift_dirs.append(c)
                        c = [0, 0, 0]
                        c[i] = -1
                        shift_dirs.append(c)
                    c = copy.deepcopy(centers)
                    c[i] = -1
                    shift_dirs.append(c)
                    c = copy.deepcopy(centers)
                    c[i] = 1
                    shift_dirs.append(c)
            if len(shift_dirs) < 6: shift_dirs.append(centers)

        for k, i in enumerate(tilde_calc.structures[-1]['atoms']):
            if i[0] in self.CORNER_ATOM_TYPES:
                for dir in shift_dirs:
                    self.translate(k, dir, self.virtual_atoms)
        #print write_cif(tilde_calc.structures[-1]['cell'], self.virtual_atoms, ['+x,+y,+z'], DATA_DIR + "/test.cif")

        # extract octahedra
        for octahedron in self.get_octahedra(tilde_calc.structures[-1]['atoms'], tilde_calc.structures[-1]['periodicity']):
            #print 'center:', octahedron[0]+1
            #print 'corners:', [i+1 for i in octahedron[1]]
            oplanes = self.get_tiltplanes(octahedron[1])
            otilting = []
            for oplane in oplanes:
                otilting.append( self.get_tilting(oplane) )
                self.prec_angles.update( { octahedron[0]: otilting } )

        # uniquify and round
        u, todel = [], []
        for o in self.prec_angles:
            self.prec_angles[o] = reduce(lambda x, y: x if sum(x) <= sum(y) else y, self.prec_angles[o]) # only minimal angles are taken if tilting planes vary!
            self.prec_angles[o] = map(lambda x: map(lambda y: round(y, 2), x), [self.prec_angles[o]])
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

    def bisector_point(self, num_of_A, num_of_O, num_of_B, reference):
        xA = reference[num_of_A][1]
        yA = reference[num_of_A][2]
        zA = reference[num_of_A][3]
        xO = reference[num_of_O][1]
        yO = reference[num_of_O][2]
        zO = reference[num_of_O][3]
        xB = reference[num_of_B][1]
        yB = reference[num_of_B][2]
        zB = reference[num_of_B][3]
        m = self.distance(num_of_O, num_of_A, self.virtual_atoms)
        n = self.distance(num_of_O, num_of_B, self.virtual_atoms)

        # bisector length
        l = (2*m*n*math.cos(math.radians( self.angle(num_of_A, num_of_O, num_of_B, self.virtual_atoms)/2 ))) / (m+n)
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
        z = 0-((A*x + B*y + D) / C)
        return [x, y, z]

    def det3x3(self, a11, a12, a13, a21, a22, a23, a31, a32, a33):
        return a11*a22*a33 + a12*a23*a31 + a13*a21*a32 - a13*a22*a31 - a12*a21*a33 - a11*a23*a32

    def distance(self, n1, n2, reference):
        return math.sqrt((reference[n2][1]-reference[n1][1])**2 + (reference[n2][2]-reference[n1][2])**2 + (reference[n2][3]-reference[n1][3])**2)

    def angle(self, num_of_atom1, num_of_atom2, num_of_atom3, reference):
        x1 = reference[num_of_atom1][1]
        y1 = reference[num_of_atom1][2]
        z1 = reference[num_of_atom1][3]
        x2 = reference[num_of_atom2][1]
        y2 = reference[num_of_atom2][2]
        z2 = reference[num_of_atom2][3]
        x3 = reference[num_of_atom3][1]
        y3 = reference[num_of_atom3][2]
        z3 = reference[num_of_atom3][3]
        X1 = x1-x2
        X2 = x3-x2
        Y1 = y1-y2
        Y2 = y3-y2
        Z1 = z1-z2
        Z2 = z3-z2
        return math.degrees(math.acos(  (X1*X2 + Y1*Y2 + Z1*Z2) / math.sqrt((X1*X1 + Y1*Y1 + Z1*Z1)*(X2*X2 + Y2*Y2 + Z2*Z2))  ))

    def translate(self, num_of_atom, components, reference):
        a_component, b_component, c_component = components
        reference.append([
            reference[num_of_atom][0],
            reference[num_of_atom][1] + a_component * self.cell[0][0] + b_component * self.cell[1][0] + c_component * self.cell[2][0],
            reference[num_of_atom][2] + a_component * self.cell[0][1] + b_component * self.cell[1][1] + c_component * self.cell[2][1],
            reference[num_of_atom][3] + a_component * self.cell[0][2] + b_component * self.cell[1][2] + c_component * self.cell[2][2]
        ])

    def get_octahedra(self, atoms, periodicity=3):
        octahedra = []
        if periodicity == 2:
            #z_cr = []
            for k, i in enumerate(atoms):
                found = []
                if i[0] in self.CENTER_ATOM_TYPES:
                    #z_cr.append([k, i[3]])
                    for m, j in enumerate(self.virtual_atoms):
                        if j[0] in self.CORNER_ATOM_TYPES and self.distance(k, m, self.virtual_atoms) <= self.OCTAHEDRON_BOND_LENGTH_LIMIT:
                            found.append(m)
                if len(found) in [5, 6]:
                    octahedra.append([k, found])

        elif periodicity == 3:
            for k, i in enumerate(atoms):
                found = []
                if i[0] in self.CENTER_ATOM_TYPES:
                    for m, j in enumerate(self.virtual_atoms):
                        if j[0] in self.CORNER_ATOM_TYPES and self.distance(k, m, self.virtual_atoms) <= self.OCTAHEDRON_BOND_LENGTH_LIMIT:
                            found.append(m)
                if len(found) == 6:
                    octahedra.append([k, found])

        if not len(octahedra): raise ModuleError("Cannot extract valid octahedra: not enough corner atoms found!")
        return octahedra

    def get_tiltplanes(self, sequence):

        # extract tilting planes basing on distance map
        distance_map = []
        tilting_planes = []

        for i in range(1, len(sequence)):
            distance_map.append([ sequence[i], self.distance( sequence[0], sequence[i], self.virtual_atoms ) ])

        distance_map = sorted(distance_map, key=lambda x: x[1])

        if len(distance_map) == 4:

            # semi-octahedron at surface edge has only 1 tilting plane to consider
            sorted_dist = [i[0] for i in distance_map]
            if distance_map[-1][1] - distance_map[-2][1] < 0.5:

                # 1st case: max diff < 0.5 Angstrom, meaning all distances to reference atom are similar,
                # therefore the reference atom is above the searched plane and the searched plane consists of other atoms
                tilting_planes.append( [ i[0] for i in distance_map ] )
            else:

                # 2nd case: reference atom belongs to the searched plane, procedure needs to be repeated with the next atom as reference atom
                candidates = [sequence[0], sorted_dist[-1]]
                next_distance_map = []
                next_distance_map.append([ sorted_dist[1], self.distance( sorted_dist[0], sorted_dist[1], self.virtual_atoms ) ])
                next_distance_map.append([ sorted_dist[2], self.distance( sorted_dist[0], sorted_dist[2], self.virtual_atoms ) ])
                next_distance_map = sorted(next_distance_map, key=lambda x: x[1])
                next_sorted_dist = [i[0] for i in next_distance_map]

                # the next reference atom is taken above the plane (distances are similar)
                if next_distance_map[1][1] - next_distance_map[0][1] < 0.5: candidates.extend([ next_sorted_dist[0], next_sorted_dist[1] ])

                # the next reference atom is taken in the plane (distances are different)
                else: candidates.extend([ sorted_dist[0], next_sorted_dist[1] ])
                tilting_planes.append(candidates)

        elif len(distance_map) == 5:

            # full octahedron has 3 different tilting planes (perpendicular in ideal case)
            sorted_dist = [i[0] for i in distance_map]

            # 1st plane is found as:
            first_plane = sorted_dist[0:4]
            tilting_planes.append(first_plane)
            distance_map_first_plane = []
            for i in range(1, 4):
                distance_map_first_plane.append([ first_plane[i], self.distance( first_plane[0], first_plane[i], self.virtual_atoms ) ])
            distance_map_first_plane = sorted(distance_map_first_plane, key=lambda x: x[1])
            sorted_first_plane = [i[0] for i in distance_map_first_plane]

            # 2nd and 3rd planes are found as:
            tilting_planes.append([ sequence[0], sorted_dist[4], first_plane[0], sorted_first_plane[2] ])
            tilting_planes.append([ sequence[0], sorted_dist[4], sorted_first_plane[0], sorted_first_plane[1] ])

        # filter planes by Z according to octahedral spatial compound
        filtered = filter(   lambda x: \
            abs(self.virtual_atoms[ x[0] ][3] - self.virtual_atoms[ x[1] ][3]) < self.OCTAHEDRON_ATOMS_Z_ORIENT_DIFFERENCE and \
            abs(self.virtual_atoms[ x[1] ][3] - self.virtual_atoms[ x[2] ][3]) < self.OCTAHEDRON_ATOMS_Z_ORIENT_DIFFERENCE and \
            abs(self.virtual_atoms[ x[2] ][3] - self.virtual_atoms[ x[3] ][3]) < self.OCTAHEDRON_ATOMS_Z_ORIENT_DIFFERENCE,   tilting_planes   )
        if len(filtered): tilting_planes = filtered

        #for plane in tilting_planes:
        #    print [i+1 for i in plane]

        return tilting_planes

    def get_tilting(self, oplane):

        # main procedure
        surf_atom1, surf_atom2, surf_atom3, surf_atom4 = oplane

        # divide surface atoms into groups by distance between them
        compare = [surf_atom2, surf_atom3, surf_atom4]
        distance_map = []
        for i in range(0, 3):
            distance_map.append([ compare[i], self.distance(surf_atom1, compare[i], self.virtual_atoms) ])
        distance_map = sorted(distance_map, key=lambda x: x[1])
        distance_map_keys = [i[0] for i in distance_map]
        surf_atom3 = distance_map_keys[2]
        surf_atom2 = distance_map_keys[1]
        surf_atom4 = distance_map_keys[0]

        if self.virtual_atoms[surf_atom1][3] == self.virtual_atoms[surf_atom2][3] and \
            self.virtual_atoms[surf_atom2][3] == self.virtual_atoms[surf_atom3][3] and \
            self.virtual_atoms[surf_atom3][3] == self.virtual_atoms[surf_atom4][3]:
            # this is done to prevent false zero tilting
            self.virtual_atoms[surf_atom1][3] += 1E-10
            self.virtual_atoms[surf_atom2][3] += 1E-10
            self.virtual_atoms[surf_atom3][3] -= 1E-10
            self.virtual_atoms[surf_atom4][3] -= 1E-10

        # new axes will be defined simply as vectors standing on 1 - 3 and 2 - 4 (they are moved into the point of origin)
        self.virtual_atoms.append([ 'Axs', self.virtual_atoms[surf_atom1][1] - self.virtual_atoms[surf_atom3][1], self.virtual_atoms[surf_atom1][2] - self.virtual_atoms[surf_atom3][2], self.virtual_atoms[surf_atom1][3] - self.virtual_atoms[surf_atom3][3] ])
        self.virtual_atoms.append([ 'Axs', self.virtual_atoms[surf_atom2][1] - self.virtual_atoms[surf_atom4][1], self.virtual_atoms[surf_atom2][2] - self.virtual_atoms[surf_atom4][2], self.virtual_atoms[surf_atom2][3] - self.virtual_atoms[surf_atom4][3] ])
        self.virtual_atoms.append([ 'Axs', 0, 0, 0 ])

        # redefine tilted axes
        surf_atom_first = len(self.virtual_atoms)-3
        surf_atom_second = len(self.virtual_atoms)-2
        center = len(self.virtual_atoms)-1

        # inverse arbitrary atom
        self.virtual_atoms.append([ 'Inv', -self.virtual_atoms[surf_atom_first][1], 0-self.virtual_atoms[surf_atom_first][2], 0-self.virtual_atoms[surf_atom_first][3] ])
        inversed_one = len(self.virtual_atoms)-1

        # find bisectors, silly swapping, todo
        first_bisector = self.bisector_point(surf_atom_first, center, surf_atom_second, self.virtual_atoms)
        sec_bisector = self.bisector_point(surf_atom_second, center, inversed_one, self.virtual_atoms)
        swap = True
        if first_bisector[0] < 0 and sec_bisector[0] < 0: swap = False
        if first_bisector[0] < 0:
            first_bisector[0] = -first_bisector[0]
            first_bisector[1] = -first_bisector[1]
            first_bisector[2] = -first_bisector[2]
        if sec_bisector[0] < 0:
            sec_bisector[0] = -sec_bisector[0]
            sec_bisector[1] = -sec_bisector[1]
            sec_bisector[2] = -sec_bisector[2]
        if swap: first_bisector, sec_bisector = sec_bisector, first_bisector
        swap = False
        if first_bisector[0] < sec_bisector[0] and first_bisector[1] < 0:
            first_bisector[0] = -first_bisector[0]
            first_bisector[1] = -first_bisector[1]
            first_bisector[2] = -first_bisector[2]
            swap = True
        if first_bisector[0] < sec_bisector[0] and first_bisector[1] > 0: swap = True
        if first_bisector[0] > sec_bisector[0] and sec_bisector[1] < 0:
            sec_bisector[0] = -sec_bisector[0]
            sec_bisector[1] = -sec_bisector[1]
            sec_bisector[2] = -sec_bisector[2]
        if swap: first_bisector, sec_bisector = sec_bisector, first_bisector

        self.virtual_atoms.append([ 'Bis', first_bisector[0], first_bisector[1], first_bisector[2] ])
        self.virtual_atoms.append([ 'Bis', sec_bisector[0], sec_bisector[1], sec_bisector[2] ])
        first_bisector = len(self.virtual_atoms)-2
        sec_bisector = len(self.virtual_atoms)-1

        # use vector cross product to define normal which will play Z axis role
        self.virtual_atoms.append([ 'AxZ', \
            self.virtual_atoms[first_bisector][2]*self.virtual_atoms[sec_bisector][3] - self.virtual_atoms[first_bisector][3]*self.virtual_atoms[sec_bisector][2], \
            self.virtual_atoms[first_bisector][3]*self.virtual_atoms[sec_bisector][1] - self.virtual_atoms[first_bisector][1]*self.virtual_atoms[sec_bisector][3], \
            self.virtual_atoms[first_bisector][1]*self.virtual_atoms[sec_bisector][2] - self.virtual_atoms[first_bisector][2]*self.virtual_atoms[sec_bisector][1] ])
        tilt_z = len(self.virtual_atoms)-1

        # Euler angles ZYZ
        alpha = math.degrees(math.atan2(self.virtual_atoms[sec_bisector][3], self.virtual_atoms[first_bisector][3]))
        beta = math.degrees(math.atan2(math.sqrt(self.virtual_atoms[tilt_z][1]*self.virtual_atoms[tilt_z][1] + self.virtual_atoms[tilt_z][2]*self.virtual_atoms[tilt_z][2]), self.virtual_atoms[tilt_z][3]))
        gamma = math.degrees(math.atan2(self.virtual_atoms[tilt_z][2], -self.virtual_atoms[tilt_z][1]))

        # angles adjusting procedure
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
