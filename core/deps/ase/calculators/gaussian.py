"""
Gaussian calculator for ASE written by:

    Glen R. Jenness
    University of Wisconsin - Madison

Based off of code written by:

    Glen R. Jenness
    Kuang Yu
    Torsten Kerber, Ecole normale superieure de Lyon (*)
    Paul Fleurat-Lessard, Ecole normale superieure de Lyon (*)
    Martin Krupicka

(*) This work is supported by Award No. UK-C0017, made by King Abdullah
University of Science and Technology (KAUST), Saudi Arabia.

See accompanying license files for details.
"""
import os
import glob
import numpy as np

from ase.calculators.general import Calculator

"""
Gaussian has two generic classes of keywords:  link0 and route.
Since both types of keywords have different input styles, we will
distinguish between both types, dividing each type into str's, int's
etc.

For more information on the Link0 commands see:
    http://www.gaussian.com/g_tech/g_ur/k_link0.htm
For more information on the route section keywords, see:
    http://www.gaussian.com/g_tech/g_ur/l_keywords09.htm
"""
link0_str_keys = ['chk',
                  'mem',
                  'rwf',
                  'int',
                  'd2e',
                  'lindaworkers',
                  'kjob',
                  'subst',
                  'save',
                  'nosave',
                 ]

link0_int_keys = ['nprocshared',
                  'nproc',
                 ]

# Multiplicity isn't really a route keyword, but we will put it here anyways
route_int_keys = ['multiplicity',
                  'cachesize',
                  'cbsextrapolate',
                  'constants',
                 ]

route_str_keys = ['method',
                  'functional',
                  'basis',
                  'maxdisk',
                  'cphf',
                  'density',
                  'densityfit',
                  'ept',
                  'field',
                  'geom',
                  'guess',
                  'gvb',
                  'integral',
                  'irc',
                  'ircmax',
                  'name',
                  'nmr',
                  'nodensityfit',
                  'oniom',
                  'output',
                  'punch',
                  'scf',
                  'symmetry',
                  'td',
                  'units',
                 ]

# This one is a little strange.  Gaussian has several keywords where you just
# specify the keyword, but the keyword itself has several options.
# Ex:  Opt, Opt=QST2, Opt=Conical, etc.
# These keywords are given here.
route_self_keys = ['opt',
                   'force',
                   'freq',
                   'complex',
                   'fmm',
                   'genchk',
                   'polar',
                   'prop',
                   'pseudo',
                   'restart',
                   'scan',
                   'scrf',
                   'sp',
                   'sparse',
                   'stable',
                   'volume',
                  ]

route_float_keys = ['pressure',
                    'scale',
                    'temperature',
                   ]

route_bool_keys = [
                  ]


class Gaussian(Calculator):
    """
    Gaussian calculator
    """
    name = 'Gaussian'
    def __init__(self, label='ase', ioplist=list(), basisfile=None,
                 directory=None, **kwargs):
        Calculator.__init__(self)

# Form a set of dictionaries for each input variable type
        self.link0_int_params = dict()
        self.link0_str_params = dict()
        self.route_str_params = dict()
        self.route_int_params = dict()
        self.route_float_params = dict()
        self.route_bool_params = dict()
        self.route_self_params = dict()

        for key in link0_int_keys:
            self.link0_int_params[key] = None
        for key in link0_str_keys:
            self.link0_str_params[key] = None
        for key in route_str_keys:
            self.route_str_params[key] = None
        for key in route_int_keys:
            self.route_int_params[key] = None
        for key in route_float_keys:
            self.route_float_params[key] = None
        for key in route_bool_keys:
            self.route_bool_params[key] = None
        for key in route_self_keys:
            self.route_self_params[key] = None

        self.set(**kwargs)

        self.atoms = None
        self.positions = None
        self.old_positions = None
        self.old_link0_str_params = None
        self.old_link0_int_params = None
        self.old_route_str_params = None
        self.old_route_int_params = None
        self.old_route_float_params = None
        self.old_route_bool_params = None
        self.old_route_self_params = None
        self.old_basisfile = None
        self.old_label = None
        self.old_ioplist = None

        self.basisfile = basisfile
        self.label = label
        self.ioplist = list(ioplist)[:]
        self.directory = directory
        self.multiplicity = 1
        self.converged = False

    def set(self, **kwargs):
        """Assigns values to dictionary keys"""
        for key in kwargs:
            if key in self.link0_str_params:
                self.link0_str_params[key] = kwargs[key]
            elif key in self.link0_int_params:
                self.link0_int_params[key] = kwargs[key]
            elif key in self.route_str_params:
                self.route_str_params[key] = kwargs[key]
            elif key in self.route_int_params:
                self.route_int_params[key] = kwargs[key]
            elif key in self.route_float_params:
                self.route_float_params[key] = kwargs[key]
            elif key in self.route_bool_params:
                self.route_bool_params[key] = kwargs[key]
            elif key in self.route_self_params:
                self.route_self_params[key] = kwargs[key]

    def initialize(self, atoms):
        if (self.route_int_params['multiplicity'] is None):
            self.multiplicity = 1
        else:
            self.multiplicity = self.route_int_params['multiplicity']

# Set some default behavior
        if (self.route_str_params['method'] is None):
            self.route_str_params['method'] = 'hf'

        if (self.route_str_params['basis'] is None):
            self.route_str_params['basis'] = '6-31g*'

        if (self.route_self_params['force'] is None):
            self.route_self_params['force'] = 'force'

        self.converged = None

    def write_input(self, filename, atoms):
        """Writes the input file"""
        inputfile = open(filename, 'w')

# First print the Link0 commands
        for key, val in self.link0_str_params.items():
            if val is not None:
                inputfile.write('%%%s=%s\n' % (key, val))

        for key, val in self.link0_int_params.items():
            if val is not None:
                inputfile.write('%%%s=%i\n' % (key, val))

# Print the route commands.  By default we will always use "#p" to start.
        route = '#p %s/%s' % (self.route_str_params['method'],
                              self.route_str_params['basis'])

# Add keywords and IOp options
# For the 'self' keywords, there are several suboptions available, and if more
# than 1 is given, then they are wrapped in ()'s and separated by a ','.
        for key, val in self.route_self_params.items():
            if val is not None:
                if (val == key):
                    route += (' ' + val)
                else:
                    if ',' in val:
                        route += ' %s(%s)' % (key, val)
                    else:
                        route += ' %s=%s' % (key, val)

        for key, val in self.route_float_params.items():
            if val is not None:
                route += ' %s=%f' % (key, val)

        for key, val in self.route_int_params.items():
            if (val is not None) and (key is not 'multiplicity'):
                route += ' %s=%i' % (key, val)

        for key, val in self.route_str_params.items():
            if (val is not None) and (key is not 'method') and \
                (key is not 'basis'):
                route += ' %s=%s' % (key, val)

        for key, val in self.route_bool_params.items():
            if val is not None:
                route += ' %s=%s' % (key, val)

        if (self.ioplist):
            route += ' IOp('
            for iop in self.ioplist:
                route += (' ' + iop)
                if (len(self.ioplist) > 1) and (iop != len(self.ioplist) - 1):
                    route += ','
            route += ')'

        inputfile.write(route)
        inputfile.write(' \n\n')
        inputfile.write('Gaussian input prepared by ASE\n\n')

        charge = sum(atoms.get_charges())
        inputfile.write('%i %i\n' % (charge, self.multiplicity))

        symbols = atoms.get_chemical_symbols()
        coordinates = atoms.get_positions()
        for i in range(len(atoms)):
            inputfile.write('%-10s' % symbols[i])
            for j in range(3):
                inputfile.write('%20.10f' % coordinates[i, j])
            inputfile.write('\n')

        inputfile.write('\n')

        if (self.route_str_params['basis'].lower() == 'gen'):
            if (self.basisfile is None):
                raise RuntimeError('Please set basisfile.')
            elif (not os.path.isfile(self.basisfile)):
                raise RuntimeError('Basis file %s does not exist.' \
                % self.basisfile)
            else:
                f2 = open(self.basisfile, 'r')
                inputfile.write(f2.read())
                f2.close()

        if atoms.get_pbc().any():
            cell = atoms.get_cell()
            line = str()
            for v in cell:
                line += 'TV %20.10f%20.10f%20.10f\n' % (v[0], v[1], v[2])
            inputfile.write(line)

        inputfile.write('\n\n')

        inputfile.close()

    def read_output(self, filename, quantity):
        """Reads the output file using GaussianReader"""
        from ase.io.gaussian import read_gaussian_out
        if (quantity == 'energy'):
            return read_gaussian_out(filename, quantity='energy')
        elif (quantity == 'forces'):
            forces = read_gaussian_out(filename, quantity='forces')
            return forces
        elif (quantity == 'dipole'):
            return read_gaussian_out(filename, quantity='dipole')
        elif (quantity == 'version'):
            return read_gaussian_out(filename, quantity='version')

    def read_energy(self):
        """Reads and returns the energy"""
        energy = self.read_output(self.label + '.log', 'energy')
        return [energy, energy]

    def read_forces(self, atoms):
        """Reads and returns the forces"""
        forces = self.read_output(self.label + '.log', 'forces')
        return forces

    def read_dipole(self):
        """Reads and returns the dipole"""
        dipole = self.read_output(self.label + '.log', 'dipole')
        return dipole

    def read_fermi(self):
        """No fermi energy, so return 0.0"""
        return 0.0

    def read_stress(self):
        raise NotImplementedError

    def update(self, atoms):
        """Updates and does a check to see if a calculation is required"""
        if self.calculation_required(atoms, ['energy']):
            if (self.atoms is None or
                self.atoms.positions.shape != atoms.positions.shape):
                self.clean()

            if (self.directory is not None):
                curdir = os.getcwd()
                if not os.path.exists(self.directory):
                    os.makedirs(self.directory)
                os.chdir(self.directory)
                self.calculate(atoms)
                os.chdir(curdir)
            else:
                self.calculate(atoms)

    def calculation_required(self, atoms, quantities):
        """Checks if a calculation is required"""
        if (self.positions is None or
           (self.atoms != atoms) or
           (self.link0_str_params != self.old_link0_str_params) or
           (self.link0_int_params != self.old_link0_int_params) or
           (self.route_str_params != self.old_route_str_params) or
           (self.route_int_params != self.old_route_int_params) or
           (self.route_float_params != self.old_route_float_params) or
           (self.route_bool_params != self.old_route_bool_params) or
           (self.route_self_params != self.old_route_self_params) or
           (self.basisfile != self.old_basisfile) or
           (self.label != self.old_label) or
           (self.ioplist != self.old_ioplist)):

            return True
        return False

    def clean(self):
        """Cleans up from a previous run"""
        extensions = ['.chk', '.com', '.log']

        for ext in extensions:
            f = self.label + ext
            try:
                if (self.directory is not None):
                    os.remove(os.path.join(self.directory, f))
                else:
                    os.remove(f)
            except OSError:
                pass

    def get_command(self):
        """Return command string if program installed, otherwise None.  """
        command = None
        if ('GAUSS_EXEDIR' in os.environ) \
                and ('GAUSSIAN_COMMAND' in os.environ):
            command = os.environ['GAUSSIAN_COMMAND']
        return command

    def run(self):
        """Runs Gaussian"""

        command = self.get_command()
        if command is None:
            raise RuntimeError('GAUSS_EXEDIR or GAUSSIAN_COMMAND not set')
        exitcode = os.system('%s < %s > %s'
                             % (command, self.label + '.com', self.label + '.log'))

        if (exitcode != 0):
            raise RuntimeError('Gaussian exited with error code' % exitcode)

    def calculate(self, atoms):
        """initializes calculation and runs Gaussian"""
        self.initialize(atoms)
        self.write_input(self.label + '.com', atoms)
        self.run()
        self.converged = self.read_convergence()
        self.set_results(atoms)

    def read_convergence(self):
        """Determines if calculations converged"""
        converged = False

        gauss_dir = os.environ['GAUSS_EXEDIR']
        test = '(Enter ' + gauss_dir + '/l9999.exe)'

        f = open(self.label + '.log', 'r')
        lines = f.readlines()
        f.close()

        for line in lines:
            if (line.rfind(test) > -1):
                converged = True
            else:
                converged = False

        return converged

    def set_results(self, atoms):
        """Sets results"""
        self.read(atoms)
        self.atoms = atoms.copy()
        self.old_positions = atoms.get_positions().copy()
        self.old_link0_str_params = self.link0_str_params.copy()
        self.old_link0_int_params = self.link0_int_params.copy()
        self.old_route_str_params = self.route_str_params.copy()
        self.old_route_int_params = self.route_int_params.copy()
        self.old_route_float_params = self.route_float_params.copy()
        self.old_route_bool_params = self.route_bool_params.copy()
        self.old_route_self_params = self.route_self_params.copy()
        self.old_basisfile = self.basisfile
        self.old_label = self.label
        self.old_ioplist = self.ioplist[:]

    def get_version(self):
        return self.read_output(self.label + '.log', 'version')
