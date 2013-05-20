from ase.tasks.main import run

atoms, task = run('abinit bulk Al -x fcc -a 4.04 --k-point-density=3.0 ' +
                  '-p xc=PBE,ecut=340,toldfe=1e-5,chksymbreak=0')
atoms, task = run('abinit bulk Al -s')
