from ase.test.fleur import installed

assert installed()

from ase.tasks.main import run

atoms, task = run("fleur bulk Al -x fcc -a 4.04 --k-point-density=3.0 -p xc=PBE")
atoms, task = run('fleur bulk Al -s')
