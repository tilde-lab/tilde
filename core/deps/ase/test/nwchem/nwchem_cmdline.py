from ase.test.nwchem import installed

assert installed()

from ase.tasks.main import run

atoms, task = run("nwchem molecule O2 O -l -p task=gradient")
atoms, task = run('nwchem molecule O2 O -s')
ae = 2 * task.data['O']['energy'] - task.data['O2']['energy']
assert abs(ae - 6.605) < 1e-3
