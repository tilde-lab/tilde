import time
import numpy as np

from ase.atom import Atom
from ase.atoms import Atoms
from ase.calculators.lammps import write_lammps_data
from ase.calculators.neighborlist import NeighborList
from ase.data import atomic_masses, chemical_symbols

def twochar(name):
    if len(name) > 1:
        return name[:2]
    else:
        return name + ' '

class BondData:
    def __init__(self, name_value_hash):
        self.nvh = name_value_hash
    
    def name_value(self, aname, bname):
        name1 = twochar(aname)  + '-' + twochar(bname)
        name2 = twochar(bname)  + '-' + twochar(aname)
        if name1 in self.nvh:
            return name1, self.nvh[name1]
        if name2 in self.nvh:
            return name2, self.nvh[name2]
        return None, None

    def value(self, aname, bname):
        return self.name_value(aname, bname)[1]
        
class CutoffList(BondData):
    def max(self):
        return max(self.nvh.values())

class AnglesData:
    def __init__(self, name_value_hash):
        self.nvh = name_value_hash
    
    def name_value(self, aname, bname, cname):
        for name in [
            (twochar(aname) + '-' + twochar(bname) + '-' + twochar(cname)),
            (twochar(aname) + '-' + twochar(cname) + '-' + twochar(bname)),
            (twochar(bname) + '-' + twochar(aname) + '-' + twochar(cname)),
            (twochar(bname) + '-' + twochar(cname) + '-' + twochar(aname)),
            (twochar(cname) + '-' + twochar(aname) + '-' + twochar(bname)),
            (twochar(cname) + '-' + twochar(bname) + '-' + twochar(aname))]:
            if name in self.nvh:
                return name, self.nvh[name]
        return None, None
    
class OPLSff:
    def __init__(self, fileobj=None, warnings=0):
        self.warnings = warnings
        self.data = {}
        if fileobj is not None:
            self.read(fileobj)

    def read(self, fileobj, comments='#'):
        if isinstance(fileobj, str):
            fileobj = open(fileobj)

        def read_block(name, 
                       symlen, # length of the symbol
                       nvalues # of values expected
                       ):
            if name not in self.data:
                self.data[name] = {}
            data = self.data[name]

            def add_line():
                line = fileobj.readline()
                if len(line) <= 1: # end of the block
                    return False
                line = line.split('#')[0] # get rid of comments
                if len(line) > symlen:
                    symbol = line[:symlen]
                    words = line[symlen:].split()
                    if len(words) >=  nvalues:
                        if nvalues == 1:
                            data[symbol] = float(words[0])
                        else:
                            data[symbol] = [float(word) 
                                            for word in words[:nvalues]]
                return True

            while add_line():
                pass
 
        read_block('one',      2, 3)
        read_block('bonds',      5, 2)
        read_block('angles',     8, 2)
        read_block('dihedrals', 11, 3)

        read_block('cutoffs',      5, 1)

        self.bonds = BondData(self.data['bonds'])
        self.angles = AnglesData(self.data['angles'])
        self.cutoffs = CutoffList(self.data['cutoffs'])

    def write_lammps(self, atoms):
        btypes, atypes = self.write_lammps_atoms(atoms)
        self.write_lammps_definitions(atoms, btypes, atypes)

    def write_lammps_atoms(self, atoms):
        """Write atoms infor for LAMMPS"""
        
        fileobj = 'lammps_atoms'
        if isinstance(fileobj, str):
            fileobj = open(fileobj, 'w')
        write_lammps_data(fileobj, atoms, 
                          specorder=atoms.types,
                          speclist=(atoms.get_tags() + 1),
                          )

        # masses
        fileobj.write('\nMasses\n\n')
        for i, typ in enumerate(atoms.types):
            cs = atoms.split_symbol(typ)[0]
            fileobj.write('%6d %g # %s -> %s\n' % 
                          (i + 1, 
                           atomic_masses[chemical_symbols.index(cs)],
                           typ, cs))
  
        # bonds
        btypes, blist = self.get_bonds(atoms)
        fileobj.write('\n' + str(len(btypes)) + ' bond types\n')
        fileobj.write(str(len(blist)) + ' bonds\n')
        fileobj.write('\nBonds\n\n')
        
        for ib, bvals in enumerate(blist):
            fileobj.write('%8d %6d %6d %6d\n' %
                          (ib + 1, bvals[0] + 1, bvals[1] + 1, bvals[2] + 1))

        # angles
        atypes, alist = self.get_angles()
        fileobj.write('\n' + str(len(atypes)) + ' angle types\n')
        fileobj.write(str(len(alist)) + ' angles\n')
        fileobj.write('\nAngles\n\n')
        
        for ia, avals in enumerate(alist):
            fileobj.write('%8d %6d %6d %6d %6d\n' %
                          (ia + 1, avals[0] + 1, 
                           avals[1] + 1, avals[2] + 1, avals[3] + 1))

        return btypes, atypes

    def update_neighbor_list(self, atoms):
        cut = 0.5 * max(self.data['cutoffs'].values())
        self.nl = NeighborList([cut] * len(atoms), skin=0, bothways=True)
        self.nl.update(atoms)
        self.atoms = atoms
    
    def get_bonds(self, atoms):
        """Find bonds and return them and their types"""
        cutoffs = CutoffList(self.data['cutoffs'])
        self.update_neighbor_list(atoms)

        types = atoms.get_types()
        tags = atoms.get_tags()
        cell = atoms.get_cell()
        positions = atoms.get_positions()
        bond_list = []
        bond_types = []
        for i, atom in enumerate(atoms):
            iname = types[tags[i]]
            indices, offsets = self.nl.get_neighbors(i)
            for j, offset in zip(indices, offsets):
                if j <= i:
                    continue # do not double count
                jname = types[tags[j]]
                cut = cutoffs.value(iname, jname)
                if cut is None:
                    if self.warnings > 1:
                        print ('Warning: cutoff %s-%s not found'
                               % (iname, jname))
                    continue # don't have it
                dist = np.linalg.norm(atom.position - atoms[j].position
                                      - np.dot(offset, cell))
                if dist > cut:
                    continue # too far away
                name, val = self.bonds.name_value(iname, jname)
                if name is None:
                    if self.warnings:
                        print ('Warning: potential %s-%s not found'
                               % (iname, jname))
                    continue # don't have it
                if name not in bond_types:
                    bond_types.append(name)
                bond_list.append([bond_types.index(name), i, j])
        return bond_types, bond_list
                
    def get_angles(self, atoms=None):
        cutoffs = CutoffList(self.data['cutoffs'])
        if atoms is not None:
            self.update_neighbor_list(atoms)
        else:
            atoms = self.atoms
         
        types = atoms.get_types()
        tags = atoms.get_tags()
        cell = atoms.get_cell()
        positions = atoms.get_positions()
        ang_list = []
        ang_types = []
        for i, atom in enumerate(atoms):
            iname = types[tags[i]]
            indicesi, offsetsi = self.nl.get_neighbors(i)
            for j, offsetj in zip(indicesi, offsetsi):
                jname = types[tags[j]]
                cut = cutoffs.value(iname, jname)
                if cut is None:
                    continue # don't have it
                dist = np.linalg.norm(atom.position - atoms[j].position
                                      - np.dot(offsetj, cell))
                if dist > cut:
                    continue # too far away
                indicesj, offsetsj = self.nl.get_neighbors(j)
                for k, offsetk in zip(indicesj, offsetsj):
                    if k <= i:
                        continue # avoid double count
                    kname = types[tags[k]]
                    cut = cutoffs.value(jname, kname)
                    if cut is None:
                        continue # don't have it
                    dist = np.linalg.norm(atoms[k].position +
                                          np.dot(offsetk, cell) - 
                                          atoms[j].position)
                    if dist > cut:
                        continue # too far away
                    name, val = self.angles.name_value(iname, jname, 
                                                       kname)
                    if name is None:
                        continue # don't have it
                    if name not in ang_types:
                        ang_types.append(name)
                    ang_list.append([ang_types.index(name), i, j, k])
        return ang_types, ang_list

    def write_lammps_definitions(self, atoms, btypes, atypes):
        """Write force field definitions for LAMMPS."""

        fileobj = 'lammps_opls'
        if isinstance(fileobj, str):
            fileobj = open(fileobj, 'w')

        print >> fileobj, '# OPLS potential'
        print >> fileobj, '# write_lammps', time.asctime(
            time.localtime(time.time()))

        # bonds
        fileobj.write('\n# bonds\n')
        fileobj.write('bond_style      harmonic\n')
        for ib, btype in enumerate(btypes):
            fileobj.write('bond_coeff %6d' % (ib + 1))
            for value in self.bonds.nvh[btype]:
                fileobj.write(' ' + str(value))
            fileobj.write(' # ' + btype + '\n')

        # angles
        fileobj.write('\n# angles\n')
        fileobj.write('angle_style      harmonic\n')
        for ia, atype in enumerate(atypes):
            fileobj.write('angle_coeff %6d' % (ia + 1))
            for value in self.angles.nvh[atype]:
                fileobj.write(' ' + str(value))
            fileobj.write(' # ' + atype + '\n')

        # Lennard Jones settings
        fileobj.write('\n# L-J parameters\n')
        fileobj.write('pair_style lj/cut/coul/long 10.0 7.4' +
                      ' # consider changing these parameters\n')
        fileobj.write('special_bonds lj/coul 0.0 0.0 0.5\n')
        data = self.data['one']
        for ia, atype in enumerate(atoms.types):
            if len(atype) < 2:
                atype = atype + ' '
            fileobj.write('pair_coeff ' + str(ia + 1) + ' ' + str(ia + 1))
            for value in data[atype][:2]:
                fileobj.write(' ' + str(value))
            fileobj.write(' # ' + atype + '\n')
        fileobj.write('pair_modify shift yes mix geometric\n')

        # Charges
        fileobj.write('\n# charges\n')
        for ia, atype in enumerate(atoms.types):
            if len(atype) < 2:
                atype = atype + ' '
            fileobj.write('set type ' + str(ia + 1))
            fileobj.write(' ' + str(data[atype][2]))
            fileobj.write(' # ' + atype + '\n')
            
class OPLSStructure(Atoms):
    default_map = {
        'BR': 'Br',
        'C0': 'Ca',
        }

    def __init__(self, filename=None):
        Atoms.__init__(self)
        if filename:
            self.read_labeled_xyz(filename)

    def append(self, atom):
        """Append atom to end."""
        self.extend(Atoms([atom]))

    def read_labeled_xyz(self, fileobj, map={}):
        """Read xyz like file with labeled atoms."""
        if isinstance(fileobj, str):
            fileobj = open(fileobj)

        translate = dict(OPLSStructure.default_map.items() + map.items())

        lines = fileobj.readlines()
        L1 = lines[0].split()
        if len(L1) == 1:
            del lines[:2]
            natoms = int(L1[0])
        else:
            natoms = len(lines)
        types = []
        types_map = {}
        for line in lines[:natoms]:
            symbol, x, y, z = line.split()[:4]
            element, label = self.split_symbol(symbol, translate)
            if symbol not in types:
                types_map[symbol] = len(types)
                types.append(symbol) 
            self.append(Atom(element, [float(x), float(y), float(z)],
                             tag=types_map[symbol]                       ))
            self.types = types

    def split_symbol(self, string, translate=default_map):

        if string in translate:
            return translate[string], string
        if len(string) < 2:
            return string, None
        return string[0], string[1]

    def get_types(self):
        return self.types

    def colored(self, elements):
        res = Atoms()
        res.set_cell(self.get_cell())
        for atom in self:
            elem = self.types[atom.tag]
            if elem in elements:
                elem = elements[elem]
            res.append(Atom(elem, atom.position))
        return res
