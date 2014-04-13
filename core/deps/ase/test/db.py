from ase.test import cli
from ase.db import connect

cmd = """
ase-build H | ase-run emt -d y.json &&
ase-build H2O | ase-run emt -d y.json &&
ase-build O2 | ase-run emt -d y.json &&
ase-build H2 | ase-run emt -f 0.02 -d y.json &&
ase-build O2 | ase-run emt -f 0.02 -d y.json &&
ase-build -x fcc Cu | ase-run emt -E 5 -d y.json &&
ase-db y.json id=H --delete --yes &&
ase-db y.json "H>0" -k hydro"""

for name in ['y.json', 'y.db']:#, 'postgres://localhost']:
    cli(cmd.replace('y.json', name))
    con = connect(name)
    assert len(list(con.select())) == 4
    assert len(list(con.select('hydro'))) == 2

