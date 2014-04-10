from ase.test import cli, require
from ase.db import connect

require('gaussian')
cli("""\
ase-build O | ase-run gaussian -d oxygen.json &&
ase-build O2 | ase-run gaussian -d oxygen.json""")
conn = connect('oxygen.json')
e1 = conn['O'].get_potential_energy()
e2 = conn['O2'].get_potential_energy()
ae = 2 * e1 - e2
print(ae)
assert abs(ae - 5.664) < 1e-3
