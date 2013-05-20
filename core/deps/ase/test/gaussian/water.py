from ase.test import NotAvailable

from ase.calculators.gaussian import Gaussian

if Gaussian().get_command() is None:
    raise NotAvailable('Gaussian required')

from ase.atoms import Atoms
from ase.optimize.lbfgs import LBFGS

# First test to make sure Gaussian works
calc = Gaussian(method='pbepbe', basis='sto-3g', force='force',
                nproc=1, chk='water.chk', label='water')
calc.clean()

water = Atoms('OHH',
              positions=[(0., 0. ,0. ), (1. ,0. ,0. ), (0. ,1. ,0. )],
              calculator=calc)

opt = LBFGS(water)
opt.run(fmax=0.05)

forces = water.get_forces()
energy = water.get_potential_energy()
positions = water.get_positions()

# Then test the IO routines
from ase.io import read
water2 = read('water/water.log')
forces2 = water2.get_forces()
energy2 = water2.get_potential_energy()
positions2 = water2.get_positions()

assert (energy - energy2) < 1e-14
assert (forces.all() - forces2.all()) < 1e-14
assert (positions.all() - positions2.all()) < 1e-14
