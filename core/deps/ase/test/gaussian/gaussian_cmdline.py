from ase.test import NotAvailable

from ase.calculators.gaussian import Gaussian

if Gaussian().get_command() is None:
    raise NotAvailable('Gaussian required')

from ase.tasks.main import run

atoms, task = run('gaussian molecule O2 O')
atoms, task = run('gaussian molecule O2 O -s')
ae = 2 * task.data['O']['energy'] - task.data['O2']['energy']
print ae
assert abs(ae - 5.664) < 1e-3
