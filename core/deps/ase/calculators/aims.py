"""This module defines an ASE interface to FHI-aims.

Felix Hanke hanke@liverpool.ac.uk
Jonas Bjork j.bjork@liverpool.ac.uk
"""

import os

import numpy as np

from ase.io.aims import write_aims, read_aims
from ase.data import atomic_numbers
from ase.calculators.calculator import FileIOCalculator, Parameters, kpts2mp, \
    ReadError


float_keys = [
    'charge',
    'charge_mix_param',
    'default_initial_moment',
    'fixed_spin_moment',
    'hartree_convergence_parameter',
    'harmonic_length_scale',
    'ini_linear_mix_param',
    'ini_spin_mix_parma',
    'initial_moment',
    'MD_MB_init',
    'MD_time_step',
    'prec_mix_param',
    'set_vacuum_level',
    'spin_mix_param',
]

exp_keys = [
    'basis_threshold',
    'occupation_thr',
    'sc_accuracy_eev',
    'sc_accuracy_etot',
    'sc_accuracy_forces',
    'sc_accuracy_rho',
    'sc_accuracy_stress',
]

string_keys = [
    'communication_type',
    'density_update_method',
    'KS_method',
    'mixer',
    'output_level',
    'packed_matrix_format',
    'relax_unit_cell',
    'restart',
    'restart_read_only',
    'restart_write_only',
    'spin',
    'total_energy_method',
    'qpe_calc',
    'xc',
    'species_dir',
]

int_keys = [
    'empty_states',
    'ini_linear_mixing',
    'max_relaxation_steps',
    'max_zeroin',
    'multiplicity',
    'n_max_pulay',
    'sc_iter_limit',
    'walltime',
]

bool_keys = [
    'collect_eigenvectors',
    'compute_forces',
    'compute_kinetic',
    'compute_numerical_stress',
    'compute_analytical_stress',
    'distributed_spline_storage',
    'evaluate_work_function',
    'final_forces_cleaned',
    'hessian_to_restart_geometry',
    'load_balancing',
    'MD_clean_rotations',
    'MD_restart',
    'override_illconditioning',
    'override_relativity',
    'restart_relaxations',
    'squeeze_memory',
    'symmetry_reduced_k_grid',
    'use_density_matrix',
    'use_dipole_correction',
    'use_local_index',
    'use_logsbt',
    'vdw_correction_hirshfeld',
]

list_keys = [
    'init_hess',
    'k_grid',
    'k_offset',
    'MD_run',
    'MD_schedule',
    'MD_segment',
    'mixer_threshold',
    'occupation_type',
    'output',
    'cube',
    'preconditioner',
    'relativistic',
    'relax_geometry',
]


class Aims(FileIOCalculator):
    command = 'aims.version.serial.x > aims.out'
    implemented_properties = ['energy', 'forces', 'stress', 'dipole']

    def __init__(self, restart=None, ignore_bad_restart_file=False,
                 label=os.curdir, atoms=None, cubes=None, **kwargs):
        """Construct FHI-aims calculator.
        
        The keyword arguments (kwargs) can be one of the ASE standard
        keywords: 'xc', 'kpts' and 'smearing' or any of FHI-aims'
        native keywords.
        
        Additional arguments:

        cubes: AimsCube object
            Cube file specification.
        """

        FileIOCalculator.__init__(self, restart, ignore_bad_restart_file,
                                  label, atoms, **kwargs)
        self.cubes = cubes

    def set_label(self, label):
        self.label = label
        self.directory = label
        self.prefix = ''
        self.out = os.path.join(label, 'aims.out')

    def check_state(self, atoms):
        system_changes = FileIOCalculator.check_state(self, atoms)
        # Ignore unit cell for molecules:
        if not atoms.pbc.any() and 'cell' in system_changes:
            system_changes.remove('cell')
        return system_changes

    def set(self, **kwargs):
        xc = kwargs.get('xc')
        if xc:
            kwargs['xc'] = {'LDA': 'pw-lda', 'PBE': 'pbe'}.get(xc, xc)

        changed_parameters = FileIOCalculator.set(self, **kwargs)
        
        if changed_parameters:
            self.reset()
        return changed_parameters

    def write_input(self, atoms, properties=None, system_changes=None):
        FileIOCalculator.write_input(self, atoms, properties, system_changes)

        have_lattice_vectors = atoms.pbc.any()
        have_k_grid = ('k_grid' in self.parameters or
                       'kpts' in self.parameters)
        if have_lattice_vectors and not have_k_grid:
            raise RuntimeError('Found lattice vectors but no k-grid!')
        if not have_lattice_vectors and have_k_grid:
            raise RuntimeError('Found k-grid but no lattice vectors!')
        write_aims(os.path.join(self.directory, 'geometry.in'), atoms)
        self.write_control(atoms, os.path.join(self.directory, 'control.in'))
        self.write_species(atoms, os.path.join(self.directory, 'control.in'))
        self.parameters.write(os.path.join(self.directory, 'parameters.ase'))

    def write_control(self, atoms, filename):
        output = open(filename, 'w')
        for line in ['=====================================================',
                     'FHI-aims file: ' + filename,
                     'Created using the Atomic Simulation Environment (ASE)',
                     '',
                     'List of parameters used to initialize the calculator:',
                     '=====================================================']:
            output.write('#' + line + '\n')

        assert not ('kpts' in self.parameters and 'k_grid' in self.parameters)
        assert not ('smearing' in self.parameters and
                    'occupation_type' in self.parameters)

        for key, value in self.parameters.items():
            if key == 'kpts':
                mp = kpts2mp(atoms, self.parameters.kpts)
                output.write('%-35s%d %d %d\n' % (('k_grid',) + tuple(mp)))
                dk = 0.5 - 0.5 / np.array(mp)
                output.write('%-35s%f %f %f\n' % (('k_offset',) + tuple(dk)))
            elif key == 'species_dir':
                continue
            elif key == 'smearing':
                name = self.parameters.smearing[0].lower()
                if name == 'fermi-dirac':
                    name = 'fermi'
                width = self.parameters.smearing[1]
                output.write('%-35s%s %f' % ('occupation_type', name, width))
                if name == 'methfessel-paxton':
                    order = self.parameters.smearing[2]
                    output.write(' %d' % order)
                output.write('\n' % order)
            elif key == 'output':
                for output_type in value:
                    output.write('%-35s%s\n' % (key, output_type))
            elif key == 'vdw_correction_hirshfeld' and value:
                output.write('%-35s\n' % key)
            elif key in bool_keys:
                output.write('%-35s.%s.\n' % (key, repr(bool(value)).lower()))
            elif isinstance(value, (tuple, list)):
                output.write('%-35s%s\n' %
                             (key, ' '.join(str(x) for x in value)))
            elif isinstance(value, str):
                output.write('%-35s%s\n' % (key, value))
            else:
                output.write('%-35s%r\n' % (key, value))
        if self.cubes:
            self.cubes.write(output)
        output.write(
            '#=======================================================\n\n')
        output.close()

    def read(self, label):
        FileIOCalculator.read(self, label)
        geometry = os.path.join(self.directory, 'geometry.in')
        control = os.path.join(self.directory, 'control.in')
                        
        for filename in [geometry, control, self.out]:
            if not os.path.isfile(filename):
                raise ReadError

        self.atoms = read_aims(geometry)
        self.parameters = Parameters.read(os.path.join(self.directory,
                                                       'parameters.ase'))
        self.read_results()

    def read_results(self):
        converged = self.read_convergence()
        if not converged:
            os.system('tail -20 ' + self.out)
            raise RuntimeError('FHI-aims did not converge!\n' +
                               'The last lines of output are printed above ' +
                               'and should give an indication why.')
        self.read_energy()
        if ('compute_forces' in self.parameters or
            'sc_accuracy_forces' in self.parameters):
            self.read_forces()
        if ('compute_numerical_stress' in self.parameters or
            'compute_analytical_stress' in self.parameters):
            self.read_stress()
        if ('dipole' in self.parameters.get('output', []) and
            not self.atoms.pbc.any()):
            self.read_dipole()

    def write_species(self, atoms, filename='control.in'):
        species_path = self.parameters.get('species_dir')
        if species_path is None:
            species_path = os.environ.get('AIMS_SPECIES_DIR')
        if species_path is None:
            raise RuntimeError(
                'Missing species directory!  Use species_dir ' +
                'parameter or set $AIMS_SPECIES_DIR environment variable.')

        control = open(filename, 'a')
        symbols = atoms.get_chemical_symbols()
        symbols2 = []
        for n, symbol in enumerate(symbols):
            if symbol not in symbols2:
                symbols2.append(symbol)
        for symbol in symbols2:
            fd = os.path.join(species_path, '%02i_%s_default' %
                              (atomic_numbers[symbol], symbol))
            for line in open(fd, 'r'):
                control.write(line)
        control.close()

    def get_dipole_moment(self, atoms):
        if ('dipole' not in self.parameters.get('output', []) or
            atoms.pbc.any()):
            raise NotImplementedError
        return FileIOCalculator.get_dipole_moment(self, atoms)

    def get_stress(self, atoms):
        if ('compute_numerical_stress' not in self.parameters and
            'compute_analytical_stress' not in self.parameters):
            raise NotImplementedError
        return FileIOCalculator.get_stress(self, atoms)

    def get_forces(self, atoms):
        if ('compute_forces' not in self.parameters and
            'sc_accuracy_forces' not in self.parameters):
            raise NotImplementedError
        return FileIOCalculator.get_forces(self, atoms)

    def read_dipole(self):
        "Method that reads the electric dipole moment from the output file."
        for line in open(self.out, 'r'):
            if line.rfind('Total dipole moment [eAng]') > -1:
                dipolemoment = np.array([float(f)
                                         for f in line.split()[6:9]])
        self.results['dipole'] = dipolemoment

    def read_energy(self):
        for line in open(self.out, 'r'):
            if line.rfind('Total energy corrected') > -1:
                E0 = float(line.split()[5])
            elif line.rfind('Total energy uncorrected') > -1:
                F = float(line.split()[5])
        self.results['free_energy'] = F
        self.results['energy'] = E0

    def read_forces(self):
        """Method that reads forces from the output file.

        If 'all' is switched on, the forces for all ionic steps
        in the output file will be returned, in other case only the
        forces for the last ionic configuration are returned."""
        lines = open(self.out, 'r').readlines()
        forces = np.zeros([len(self.atoms), 3])
        for n, line in enumerate(lines):
            if line.rfind('Total atomic forces') > -1:
                for iatom in range(len(self.atoms)):
                    data = lines[n + iatom + 1].split()
                    for iforce in range(3):
                        forces[iatom, iforce] = float(data[2 + iforce])
        self.results['forces'] = forces

    def read_stress(self):
        lines = open(self.out, 'r').readlines()
        stress = None
        for n, line in enumerate(lines):
            if (line.rfind('|              Analytical stress tensor') > -1 or
                line.rfind('Numerical stress tensor') > -1):
                stress = []
                for i in [n + 5, n + 6, n + 7]:
                    data = lines[i].split()
                    stress += [float(data[2]), float(data[3]), float(data[4])]
        # rearrange in 6-component form and return
        self.results['stress'] = np.array([stress[0], stress[4], stress[8],
                                           stress[5], stress[2], stress[1]])

    def read_convergence(self):
        converged = False
        lines = open(self.out, 'r').readlines()
        for n, line in enumerate(lines):
            if line.rfind('Have a nice day') > -1:
                converged = True
        return converged


class AimsCube:
    "Object to ensure the output of cube files, can be attached to Aims object"
    def __init__(self, origin=(0, 0, 0),
                 edges=[(0.1, 0.0, 0.0), (0.0, 0.1, 0.0), (0.0, 0.0, 0.1)],
                 points=(50, 50, 50), plots=None):
        """parameters:
        origin, edges, points = same as in the FHI-aims output
        plots: what to print, same names as in FHI-aims """

        self.name = 'AimsCube'
        self.origin = origin
        self.edges = edges
        self.points = points
        self.plots = plots
         
    def ncubes(self):
        """returns the number of cube files to output """
        if self.plots:
            number = len(self.plots)
        else:
            number = 0
        return number

    def set(self, **kwargs):
        """ set any of the parameters ... """
        # NOT IMPLEMENTED AT THE MOMENT!

    def move_to_base_name(self, basename):
        """ when output tracking is on or the base namem is not standard,
        this routine will rename add the base to the cube file output for
        easier tracking """
        for plot in self.plots:
            found = False
            cube = plot.split()
            if (cube[0] == 'total_density' or
                cube[0] == 'spin_density' or
                cube[0] == 'delta_density'):
                found = True
                old_name = cube[0] + '.cube'
                new_name = basename + '.' + old_name
            if cube[0] == 'eigenstate' or cube[0] == 'eigenstate_density':
                found = True
                state = int(cube[1])
                s_state = cube[1]
                for i in [10, 100, 1000, 10000]:
                    if state < i:
                        s_state = '0' + s_state
                old_name = cube[0] + '_' + s_state + '_spin_1.cube'
                new_name = basename + '.' + old_name
            if found:
                os.system('mv ' + old_name + ' ' + new_name)

    def add_plot(self, name):
        """ in case you forgot one ... """
        self.plots += [name]

    def write(self, file):
        """ write the necessary output to the already opened control.in """
        file.write('output cube ' + self.plots[0] + '\n')
        file.write('   cube origin ')
        for ival in self.origin:
            file.write(str(ival) + ' ')
        file.write('\n')
        for i in range(3):
            file.write('   cube edge ' + str(self.points[i]) + ' ')
            for ival in self.edges[i]:
                file.write(str(ival) + ' ')
            file.write('\n')
        if self.ncubes() > 1:
            for i in range(self.ncubes() - 1):
                file.write('output cube ' + self.plots[i + 1] + '\n')
