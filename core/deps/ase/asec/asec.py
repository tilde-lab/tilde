import sys
import argparse
    
import numpy as np

from ase.parallel import world
from ase.io import read
from ase.utils import devnull, prnt
from ase.data import chemical_symbols, atomic_numbers, covalent_radii
from ase.structure import molecule
from ase.lattice import bulk
from ase.atoms import Atoms, string2symbols
from ase.data import ground_state_magnetic_moments
from ase.asec.plugin import PluginCommand


def expand(names):
    """Expand ranges like H-Li to H, He and Li."""
    i = 0
    while i < len(names):
        name = names[i]
        if name.count('-') == 1:
            s1, s2 = name.split('-')
            Z1 = atomic_numbers.get(s1)
            Z2 = atomic_numbers.get(s2)
            if Z1 is not None and Z2 is not None:
                names[i:i + 1] = chemical_symbols[Z1:Z2 + 1]
                i += Z2 - Z1
        i += 1


class ASEC:
    def __init__(self, args=None):
        if world.rank == 0:
            self.logfile = sys.stdout
        else:
            self.logfile = devnull

        self.command = None
        self.build_function = None
        self.args = args

    def log(self, *args, **kwargs):
        prnt(file=self.logfile, *args, **kwargs)

    def run(self):
        args = self.args

        cls = self.get_command_class(args.subparser_name)
        command = cls(self.logfile, args)

        if args.plugin:
            f = open(args.plugin)
            script = f.read()
            f.close()
            namespace = {}
            exec script in namespace
            if 'names' in namespace and len(args.names) == 0:
                args.names = namespace['names']
            self.build_function = namespace.get('build')
            if 'calculate' in namespace:
                command = PluginCommand(self.logfile, args,
                                        namespace.get('calculate'))

        expand(args.names)

        atoms = None
        for name in args.names:
            if atoms is not None:
                del atoms.calc
            atoms = self.build(name)
            command.run(atoms, name)

        command.finalize()

        return atoms

    def build(self, name):
        args = self.args
        if '.' in name:
            atoms = read(name)
        elif self.build_function:
            atoms = self.build_function(name, self.args)
        elif self.args.crystal_structure:
            atoms = self.build_bulk(name)
        else:
            atoms = self.build_molecule(name)

        if args.magnetic_moment:
            magmoms = np.array(
                [float(m) for m in args.magnetic_moment.split(',')])
            atoms.set_initial_magnetic_moments(
                np.tile(magmoms, len(atoms) // len(magmoms)))

        if args.modify:
            exec args.modify in {'atoms': atoms}

        if args.repeat is not None:
            r = args.repeat.split(',')
            if len(r) == 1:
                r = 3 * r
            atoms = atoms.repeat([int(c) for c in r])

        return atoms

    def build_molecule(self, name):
        args = self.args
        try:
            # Known molecule or atom?
            atoms = molecule(name)
        except NotImplementedError:
            symbols = string2symbols(name)
            if len(symbols) == 1:
                Z = atomic_numbers[symbols[0]]
                magmom = ground_state_magnetic_moments[Z]
                atoms = Atoms(name, magmoms=[magmom])
            elif len(symbols) == 2:
                # Dimer
                if args.bond_length is None:
                    b = (covalent_radii[atomic_numbers[symbols[0]]] +
                         covalent_radii[atomic_numbers[symbols[1]]])
                else:
                    b = args.bond_length
                atoms = Atoms(name, positions=[(0, 0, 0),
                                               (b, 0, 0)])
            else:
                raise ValueError('Unknown molecule: ' + name)
        else:
            if len(atoms) == 2 and args.bond_length is not None:
                atoms.set_distance(0, 1, args.bond_length)

        if args.unit_cell is None:
            atoms.center(vacuum=args.vacuum)
        else:
            a = [float(x) for x in args.unit_cell.split(',')]
            if len(a) == 1:
                cell = [a[0], a[0], a[0]]
            elif len(a) == 3:
                cell = a
            else:
                a, b, c, alpha, beta, gamma = a
                degree = np.pi / 180.0
                cosa = np.cos(alpha * degree)
                cosb = np.cos(beta * degree)
                sinb = np.sin(beta * degree)
                cosg = np.cos(gamma * degree)
                sing = np.sin(gamma * degree)
                cell = [[a, 0, 0],
                        [b * cosg, b * sing, 0],
                        [c * cosb, c * (cosa - cosb * cosg) / sing,
                         c * np.sqrt(
                            sinb**2 - ((cosa - cosb * cosg) / sing)**2)]]
            atoms.cell = cell
            atoms.center()

        return atoms

    def build_bulk(self, name):
        args = self.args
        L = args.lattice_constant.replace(',', ' ').split()
        d = dict([(key, float(x)) for key, x in zip('ac', L)])
        atoms = bulk(name, crystalstructure=args.crystal_structure,
                     a=d.get('a'), c=d.get('c'),
                     orthorhombic=args.orthorhombic, cubic=args.cubic)

        M, X = {'Fe': (2.3, 'bcc'),
                'Co': (1.2, 'hcp'),
                'Ni': (0.6, 'fcc')}.get(name, (None, None))
        if M is not None and args.crystal_structure == X:
            atoms.set_initial_magnetic_moments([M] * len(atoms))

        return atoms

    def parse(self, args):
        # create the top-level parser
        parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
        parser.add_argument('names', nargs='*')
        parser.add_argument('-t', '--tag',
                             help='String tag added to filenames.')
        parser.add_argument('-M', '--magnetic-moment',
                             metavar='M1,M2,...',
                             help='Magnetic moment(s).  ' +
                             'Use "-M 1" or "-M 2.3,-2.3".')
        parser.add_argument(
            '--modify', metavar='...',
            help='Modify atoms with Python statement.  ' +
            'Example: --modify="atoms.positions[-1,2]+=0.1".')
        parser.add_argument('-v', '--vacuum', type=float, default=3.0,
                       help='Amount of vacuum to add around isolated atoms '
                       '(in Angstrom).')
        parser.add_argument('--unit-cell',
                       help='Unit cell.  Examples: "10.0" or "9,10,11" ' +
                       '(in Angstrom).')
        parser.add_argument('--bond-length', type=float,
                       help='Bond length of dimer in Angstrom.')
        parser.add_argument('-x', '--crystal-structure',
                        help='Crystal structure.',
                        choices=['sc', 'fcc', 'bcc', 'hcp', 'diamond',
                                 'zincblende', 'rocksalt', 'cesiumchloride',
                                 'fluorite'])
        parser.add_argument('-a', '--lattice-constant', default='',
                        help='Lattice constant(s) in Angstrom.')
        parser.add_argument('--orthorhombic', action='store_true',
                        help='Use orthorhombic unit cell.')
        parser.add_argument('--cubic', action='store_true',
                        help='Use cubic unit cell.')
        parser.add_argument('-r', '--repeat',
                        help='Repeat unit cell.  Use "-r 2" or "-r 2,3,1".')
        parser.add_argument('--plugin')

        subparsers = parser.add_subparsers(dest='subparser_name',
                                           help='sub-command help')

        for command in ['run', 'optimize', 'eos', 'write',
                        'reaction', 'results', 'view', 'python']:
            cls = self.get_command_class(command)
            cls._calculator = self.calculator
            cls.add_parser(subparsers)

        self.args = parser.parse_args(args)
        
    def get_command_class(self, name):
        classname = name.title() + 'Command'
        module = __import__('ase.asec.' + name, {}, None, [classname])
        cls = getattr(module, classname)
        return cls


def run(args=sys.argv[1:], calculator=None):
    if isinstance(args, str):
        args = args.split(' ')
    runner = ASEC()
    runner.calculator = calculator
    runner.parse(args)
    atoms = runner.run()
    return atoms
