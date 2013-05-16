import os
import numpy as np
from ase import io, units
from ase.optimize import QuasiNewton
from ase.parallel import paropen, rank
from ase.md import VelocityVerlet
from ase.md import MDLogger
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution


class MinimaHopping:
    """Implements the minima hopping method of global optimization outlined
    by S. Goedecker,  J. Chem. Phys. 120: 9911 (2004). Initialize with an
    ASE atoms object. Optional parameters are fed through keywords.
    To run multiple searches in parallel, specify the minima_traj keyword,
    and have each run point to the same path.
    """

    _default_settings = {
        'T0': 1000.,  # K, initial MD 'temperature'
        'beta1': 1.1,  # temperature adjustment parameter
        'beta2': 1.1,  # temperature adjustment parameter
        'beta3': 1. / 1.1,  # temperature adjustment parameter
        'Ediff0': 0.5,  # eV, initial energy acceptance threshold
        'alpha1': 0.98,  # energy threshold adjustment parameter
        'alpha2': 1. / 0.98,  # energy threshold adjustment parameter
        'mdmin': 2,  # criteria to stop MD simulation (no. of minima)
        'logfile': 'hop.log',  # text log
        'minima_threshold': 0.5,  # A, threshold for identical configs
        'timestep': 1.0,  # fs, timestep for MD simulations
        'optimizer': QuasiNewton,  # local optimizer to use
        'minima_traj': 'minima.traj',  # storage file for minima list
                          }

    def __init__(self, atoms, **kwargs):
        """Initialize with an ASE atoms object and keyword arguments."""
        self._atoms = atoms
        for key in kwargs:
            if not key in self._default_settings:
                raise RuntimeError('Unknown keyword: %s' % key)
        for k, v in self._default_settings.items():
            setattr(self, '_%s' % k, kwargs.pop(k, v))

        self._fmax = 0.05  # eV/A, max force for optimizations
        self._passedminimum = PassedMinimum()  # when a MD sim. has passed
                                               # a local minimum
        # Misc storage.
        self._previous_optimum = None
        self._previous_energy = None
        self._temperature = self._T0
        self._Ediff = self._Ediff0

    def __call__(self, totalsteps=None):
        """Run the minima hopping algorithm. The total number of steps can
        be specified, other wise runs indefinitely (or until stopped by
        batching software)."""
        self._startup()
        while True:
            if (totalsteps and self._counter >= totalsteps):
                return
            self._previous_optimum = self._atoms.copy()
            self._previous_energy = self._atoms.get_potential_energy()
            self._molecular_dynamics()
            self._optimize()
            self._counter += 1
            self._check_results()

    def _startup(self):
        """Initiates a run, and determines if running from previous data or
        a fresh run."""
        exists = self._read_minima()
        if not exists:
            # Fresh run with new minima file.
            self._record_minimum(initialize_only=True)
            self._counter = 0
            self._log('init')
            self._log('msg', 'Performing / checking initial optimization.')
            self._optimize()
            self._counter += 1
            self._record_minimum()
            self._log('msg', 'Found a new minimum.')
            self._log('msg', 'Accepted new minimum.')
            self._log('par')
        elif not os.path.exists(self._logfile):
            # Fresh run with existing or shared minima file.
            self._counter = 0
            self._log('init')
            self._log('msg', 'Using existing minima file with %i prior '
                      'minima: %s' % (len(self._minima), self._minima_traj))
            self._log('msg', 'Performing / checking initial optimization.')
            self._optimize()
            self._check_results()
            self._counter += 1
        else:
            # Must be resuming from within a working directory.
            self._resume()

    def _resume(self):
        """Attempt to resume a run, based on information in the log
        file. Note it will almost always be interrupted in the middle of
        either a qn or md run, so it only has been tested in those cases
        currently."""
        f = paropen(self._logfile, 'r')
        lines = f.read().splitlines()
        f.close()
        self._log('msg', 'Attempting to resume stopped run.')
        self._log('msg', 'Using existing minima file with %i prior '
                  'minima: %s' % (len(self._minima), self._minima_traj))
        mdcount, qncount = 0, 0
        for line in lines:
            if (line[:4] == 'par:') and ('Ediff' not in line):
                self._temperature = eval(line.split()[1])
                self._Ediff = eval(line.split()[2])
            elif line[:18] == 'msg: Optimization:':
                qncount = int(line[19:].split('qn')[1])
            elif line[:24] == 'msg: Molecular dynamics:':
                mdcount = int(line[25:].split('md')[1])
        self._counter = max((mdcount, qncount))
        if qncount == mdcount:
            # Probably stopped during local optimization.
            self._log('msg', 'Attempting to resume at qn%05i' % qncount)
            if qncount > 0:
                atoms = io.read('qn%05i.traj' % (qncount - 1), index=-1)
                self._previous_optimum = atoms.copy()
                self._previous_energy = atoms.get_potential_energy()
            atoms = io.read('qn%05i.traj' % qncount, index=-1)
            fmax = np.sqrt((atoms.get_forces()**2).sum(axis=1).max())
            if fmax < self._fmax:
                raise NotImplementedError('Error resuming. qn%05i fmax '
                                          'already less than self._fmax = '
                                          '%.3f.' % (qncount, self._fmax))
            self._atoms.positions = atoms.get_positions()
            self._optimize()
            self._check_results()
            self._counter += 1
        elif qncount < mdcount:
            # Probably stopped during molecular dynamics.
            self._log('msg', 'Attempting to resume at md%05i.' % mdcount)
            atoms = io.read('qn%05i.traj' % qncount, index=-1)
            self._previous_optimum = atoms.copy()
            self._previous_energy = atoms.get_potential_energy()
            self._molecular_dynamics(resume=mdcount)
            self._optimize()
            self._counter += 1
            self._check_results()

    def _check_results(self):
        """Adjusts parameters and positions based on outputs."""
        # Returned to starting position?
        if self._previous_optimum:
            compare = ComparePositions(translate=False)
            dmax = compare(self._atoms, self._previous_optimum)
            self._log('msg', 'Max distance to last minimum: %.3f A' % dmax)
            if dmax < self._minima_threshold:
                self._log('msg', 'Re-found last minimum.')
                self._temperature *= self._beta1
                self._log('par')
                return
        # In a previously found position?
        unique, dmax_closest = self._unique_minimum_position()
        self._log('msg', 'Max distance to closest minimum: %.3f A' %
                  dmax_closest)
        if not unique:
            self._temperature *= self._beta2
            self._log('msg', 'Found previously found minimum.')
            self._log('par')
            if self._previous_optimum:
                self._log('msg', 'Restoring last minimum.')
                self._atoms.positions = self._previous_optimum.positions
            return
        # Must have found a unique minimum.
        self._temperature *= self._beta3
        self._log('msg', 'Found a new minimum.')
        self._log('par')
        if (self._atoms.get_potential_energy() <
            self._previous_energy + self._Ediff):
                self._log('msg', 'Accepted new minimum.')
                self._Ediff *= self._alpha1
                self._log('par')
                self._record_minimum()
        else:
            self._log('msg', 'Rejected new minimum due to energy. '
                             'Restoring last minimum.')
            self._atoms.positions = self._previous_optimum.positions
            self._Ediff *= self._alpha2
            self._log('par')

    def _log(self, cat='msg', message=None):
        """Records the message as a line in the log file."""
        if cat == 'init':
            if rank == 0:
                if os.path.exists(self._logfile):
                    raise RuntimeError('File exists: %s' % self._logfile)
            f = paropen(self._logfile, 'w')
            f.write('par: %12s %12s %12s\n' % ('T (K)', 'Ediff (eV)',
                                               'mdmin'))
            f.write('ene: %12s %12s %12s\n' % ('E_current', 'E_previous',
                                               'Difference'))
            f.close()
            return
        f = paropen(self._logfile, 'a')
        if cat == 'msg':
            line = 'msg: %s' % message
        elif cat == 'par':
            line = ('par: %12.4f %12.4f %12i' %
                    (self._temperature, self._Ediff, self._mdmin))
        elif cat == 'ene':
            current = self._atoms.get_potential_energy()
            if self._previous_optimum:
                previous = self._previous_energy
                line = ('ene: %12.5f %12.5f %12.5f' %
                        (current, previous, current - previous))
            else:
                line = ('ene: %12.5f' % current)
        f.write(line + '\n')
        f.close()

    def _optimize(self):
        """Perform an optimization."""
        self._atoms.set_momenta(np.zeros(self._atoms.get_momenta().shape))
        opt = self._optimizer(self._atoms,
                              trajectory='qn%05i.traj' % self._counter,
                              logfile='qn%05i.log' % self._counter)
        self._log('msg', 'Optimization: qn%05i' % self._counter)
        opt.run(fmax=self._fmax)
        self._log('ene')

    def _record_minimum(self, initialize_only=False):
        """Adds the current atoms configuration to the minima list."""
        traj = io.PickleTrajectory(self._minima_traj, 'a')
        if not initialize_only:
            traj.write(self._atoms)

    def _read_minima(self):
        """Reads in the list of minima from the minima file."""
        exists = os.path.exists(self._minima_traj)
        if exists:
            empty = os.path.getsize(self._minima_traj) == 0
        if os.path.exists(self._minima_traj):
            if not empty:
                traj = io.PickleTrajectory(self._minima_traj, 'r')
                self._minima = [atoms for atoms in traj]
            else:
                self._minima = []
            return True
        else:
            self._minima = []
            return False

    def _molecular_dynamics(self, resume=None):
        """Performs a molecular dynamics simulation, until mdmin is
        exceeded. If resuming, the file number (md%05i) is expected."""
        self._log('msg', 'Molecular dynamics: md%05i' % self._counter)
        mincount = 0
        energies, oldpositions = [], []
        if resume:
            self._log('msg', 'Resuming MD from md%05i.traj' % resume)
            if os.path.getsize('md%05i.traj' % resume) == 0:
                self._log('msg', 'md%05i.traj is empty. Resuming from '
                          'qn%05i.traj.' % (resume, resume - 1))
                atoms = io.read('qn%05i.traj' % (resume - 1), index=-1)
            else:
                images = io.PickleTrajectory('md%05i.traj' % resume, 'r')
                for atoms in images:
                    energies.append(atoms.get_potential_energy())
                    oldpositions.append(atoms.positions.copy())
                    passedmin = self._passedminimum(energies)
                    if passedmin:
                        mincount += 1
            self._atoms.positions = atoms.get_positions()
            self._atoms.set_momenta(atoms.get_momenta())
            self._log('msg', 'Starting MD with %i existing energies.' %
                      len(energies))
        else:
            MaxwellBoltzmannDistribution(self._atoms,
                                         temp=self._temperature * units.kB,
                                         force_temp=True)
        traj = io.PickleTrajectory('md%05i.traj' % self._counter, 'a',
                                self._atoms)
        dyn = VelocityVerlet(self._atoms, dt=self._timestep * units.fs)
        log = MDLogger(dyn, self._atoms, 'md%05i.log' % self._counter,
                       header=True, stress=False, peratom=False)
        dyn.attach(log, interval=1)
        dyn.attach(traj, interval=1)
        while mincount < self._mdmin:
            dyn.run(1)
            energies.append(self._atoms.get_potential_energy())
            passedmin = self._passedminimum(energies)
            if passedmin:
                mincount += 1
            oldpositions.append(self._atoms.positions.copy())
        # Reset atoms to minimum point.
        self._atoms.positions = oldpositions[passedmin[0]]

    def _unique_minimum_position(self):
        """Identifies if the current position of the atoms, which should be
        a local minima, has been found before."""
        unique = True
        dmax_closest = 99999.
        compare = ComparePositions(translate=True)
        self._read_minima()
        for minimum in self._minima:
            dmax = compare(minimum, self._atoms)
            if dmax < self._minima_threshold:
                unique = False
            if dmax < dmax_closest:
                dmax_closest = dmax
        return unique, dmax_closest


class ComparePositions:
    """Class that compares the atomic positions between two ASE atoms
    objects. Returns the maximum distance that any atom has moved, assuming
    all atoms of the same element are indistinguishable. If translate is
    set to True, allows for arbitrary translations within the unit cell,
    as well as translations across any periodic boundary conditions. When
    called, returns the maximum displacement of any one atom."""

    def __init__(self, translate=True):
        self._translate = translate

    def __call__(self, atoms1, atoms2):
        atoms1 = atoms1.copy()
        atoms2 = atoms2.copy()
        if not self._translate:
            dmax = self. _indistinguishable_compare(atoms1, atoms2)
        else:
            dmax = self._translated_compare(atoms1, atoms2)
        return dmax

    def _translated_compare(self, atoms1, atoms2):
        """Moves the atoms around and tries to pair up atoms, assuming any
        atoms with the same symbol are indistinguishable, and honors
        periodic boundary conditions (for example, so that an atom at
        (0.1, 0., 0.) correctly is found to be close to an atom at
        (7.9, 0., 0.) if the atoms are in an orthorhombic cell with
        x-dimension of 8. Returns dmax, the maximum distance between any
        two atoms in the optimal configuration."""
        atoms1.set_constraint()
        atoms2.set_constraint()
        for index in range(3):
            assert atoms1.pbc[index] == atoms2.pbc[index]
        least = self._get_least_common(atoms1)
        indices1 = [atom.index for atom in atoms1 if atom.symbol == least[0]]
        indices2 = [atom.index for atom in atoms2 if atom.symbol == least[0]]
        # Make comparison sets from atoms2, which contain repeated atoms in
        # all pbc's and bring the atom listed in indices2 to (0,0,0)
        comparisons = []
        repeat = []
        for bc in atoms2.pbc:
            if bc == True:
                repeat.append(3)
            else:
                repeat.append(1)
        repeated = atoms2.repeat(repeat)
        moved_cell = atoms2.cell * atoms2.pbc
        for moved in moved_cell:
            repeated.translate(-moved)
        repeated.set_cell(atoms2.cell)
        for index in indices2:
            comparison = repeated.copy()
            comparison.translate(-atoms2[index].position)
            comparisons.append(comparison)
        # Bring the atom listed in indices1 to (0,0,0) [not whole list]
        standard = atoms1.copy()
        standard.translate(-atoms1[indices1[0]].position)
        # Compare the standard to the comparison sets.
        dmaxes = []
        for comparison in comparisons:
            dmax = self._indistinguishable_compare(standard, comparison)
            dmaxes.append(dmax)
        return min(dmaxes)

    def _get_least_common(self, atoms):
        """Returns the least common element in atoms. If more than one,
        returns the first encountered."""
        symbols = [atom.symbol for atom in atoms]
        least = ['', np.inf]
        for element in set(symbols):
            count = symbols.count(element)
            if symbols.count(element) < least[1]:
                least = [element, symbols.count(element)]
        return least

    def _indistinguishable_compare(self, atoms1, atoms2):
        """Finds each atom in atoms1's nearest neighbor with the same
        chemical symbol in atoms2. Return dmax, the farthest distance an
        individual atom differs by."""
        atoms2 = atoms2.copy()  # allow deletion
        atoms2.set_constraint()
        dmax = 0.
        for atom1 in atoms1:
            closest = [np.nan, np.inf]
            for index, atom2 in enumerate(atoms2):
                if atom2.symbol == atom1.symbol:
                    d = np.linalg.norm(atom1.position - atom2.position)
                    if d < closest[1]:
                        closest = [index, d]
            if closest[1] > dmax:
                dmax = closest[1]
            del atoms2[closest[0]]
        return dmax


class PassedMinimum:
    """Simple routine to find if a minimum in the potential energy surface
    has been passed. In its default settings, a minimum is found if the
    sequence ends with two downward points followed by two upward points.
    Initialize with n_down and n_up, integer values of the number of up and
    down points. If it has successfully determined it passed a minimum, it
    returns the value (energy) of that minimum and the number of positions
    back it occurred, otherwise returns None."""

    def __init__(self, n_down=2, n_up=2):
        self._ndown = n_down
        self._nup = n_up

    def __call__(self, energies):
        if len(energies) < (self._nup + self._ndown + 1):
            return None
        status = True
        index = -1
        for i_up in range(self._nup):
            if energies[index] < energies[index - 1]:
                status = False
            index -= 1
        for i_down in range(self._ndown):
            if energies[index] > energies[index - 1]:
                status = False
            index -= 1
        if status:
            return (-self._nup - 1), energies[-self._nup - 1]
