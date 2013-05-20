from ase.tasks.main import run

atoms, task = run("elk bulk Al -x fcc -a 4.04 --k-point-density=3.0 -p tasks=0,xc=PBE,rgkmax=5.0,tforce=True")
atoms, task = run('elk bulk Al -s')
