import os

from ase import units
from ase.tasks.main import run

# warning! parameters are not converged - only an illustration!

# just fit EOS
atoms, task = run('jacapo bulk Li -x bcc -a 3.6 --k-point-density 1.5 -F 5,1.5 -t eos -p symmetry=True,deletenc=True')
atoms, task = run('jacapo bulk Li -x bcc -a 3.6 -t eos -s')
data = task.data['Li']
assert abs(data['B'] / units.kJ * 1.0e24 - 8.93) < 0.02
# minimize stress cell and fit EOS: deletenc=True needed!
# https://listserv.fysik.dtu.dk/pipermail/ase-developers/2012-August/001488.html
atoms, task = run('jacapo bulk Li -x bcc -a 3.6 --k-point-density 1.5 --srelax 0.05 -F 5,1.5 -t seos -p symmetry=True,calculate_stress=True,deletenc=True')
atoms, task = run('jacapo bulk Li -x bcc -a 3.6 -t seos -s')
data = task.data['Li']
assert abs(data['B'] / units.kJ * 1.0e24 - 14.73) < 0.02
