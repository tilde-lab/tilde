""" test run for gromacs calculator """

from ase.test import NotAvailable

from ase.calculators.gromacs import Gromacs

if Gromacs().get_command() is None:
    raise NotAvailable('Gromacs required')

import sys, os, glob
from ase.io import read, write

GRO_INIT_FILE = 'hise_box.gro'

#write structure file 
outfile=open('hise_box.gro','w')
outfile.write('HISE for testing  \n')
outfile.write('   20 \n')
outfile.write('    3HISE     N    1   1.966   1.938   1.722 \n')
outfile.write('    3HISE    H1    2   2.053   1.892   1.711 \n')
outfile.write('    3HISE    H2    3   1.893   1.882   1.683 \n')
outfile.write('    3HISE    H3    4   1.969   2.026   1.675 \n')
outfile.write('    3HISE    CA    5   1.939   1.960   1.866 \n')
outfile.write('    3HISE    HA    6   1.934   1.869   1.907 \n')
outfile.write('    3HISE    CB    7   2.055   2.041   1.927 \n')
outfile.write('    3HISE   HB1    8   2.141   2.007   1.890 \n')
outfile.write('    3HISE   HB2    9   2.043   2.137   1.903 \n')
outfile.write('    3HISE   ND1   10   1.962   2.069   2.161 \n')
outfile.write('    3HISE    CG   11   2.065   2.032   2.077 \n')
outfile.write('    3HISE   CE1   12   2.000   2.050   2.287 \n')
outfile.write('    3HISE   HE1   13   1.944   2.069   2.368 \n')
outfile.write('    3HISE   NE2   14   2.123   2.004   2.287 \n')
outfile.write('    3HISE   HE2   15   2.177   1.981   2.369 \n')
outfile.write('    3HISE   CD2   16   2.166   1.991   2.157 \n')
outfile.write('    3HISE   HD2   17   2.256   1.958   2.128 \n')
outfile.write('    3HISE     C   18   1.806   2.032   1.888 \n')
outfile.write('    3HISE   OT1   19   1.736   2.000   1.987 \n')
outfile.write('    3HISE   OT2   20   1.770   2.057   2.016 \n')
outfile.write('   4.00000   4.00000   4.00000 \n')
outfile.close()

## a possible prefix for gromacs programs
#if os.environ.has_key('GMXCMD_PREF'):
#    prefix = os.environ['GMXCMD_PREF']
#else:
#    prefix = ''
#
## a possible postfix for gromacs programs
#if os.environ.has_key('GMXCMD_PREF'):
#    postfix = os.environ['GMXCMD_PREF']
#else:
#    postfix = ''
#
#make index groups
#outfile=open("tmp.del",'w')
#outfile.write('q \n')
#outfile.close()
#program_command = prefix + 'make_ndx' + postfix
#command = program_command + ' -f ethanol_waterbox.gro < tmp.del '
#os.system(command)

CALC_MM_RELAX = Gromacs(
    init_structure_file = GRO_INIT_FILE,
    structure_file = 'gromacs_mm-relax.g96',
    force_field='charmm27', 
    water_model='tip3p',    
    base_filename = 'gromacs_mm-relax',
    doing_qmmm = False, freeze_qm = False,
    index_filename = 'index.ndx',
    extra_mdrun_parameters = ' -nt 1 ',
    define = '-DFLEXIBLE',
    integrator = 'cg',
    nsteps = '10000',
    nstfout = '10',
    nstlog = '10',
    nstenergy = '10',
    nstlist = '10',
    ns_type = 'grid',
    pbc = 'xyz',
    rlist = '0.7',
    coulombtype = 'PME-Switch',
    rcoulomb = '0.6',
    vdwtype = 'shift',
    rvdw = '0.6',
    rvdw_switch = '0.55',
    DispCorr = 'Ener')

#pdb2gmx -ff charmm27 -f hise_box.gro -o gromacs_mm-relax.g96 -p gromacs_mm-relax.top  
CALC_MM_RELAX.generate_topology_and_g96file()
#grompp -f gromacs_mm-relax.mdp -c gromacs_mm-relax.g96 -p gromacs_mm-relax.top -n index.ndx -o gromacs_mm-relax.tpr -maxwarn 100
CALC_MM_RELAX.generate_gromacs_run_file()
CALC_MM_RELAX.run()
atoms = CALC_MM_RELAX.get_atoms()
final_energy = CALC_MM_RELAX.get_potential_energy(atoms)
#print "final energy", final_energy
# clean 
files = glob.glob('gromacs_mm-relax*')
files.append('hise_box.gro')
files.append('inputGenergy.txt')
files.append('inputGtraj.txt')
files.append('mdout.mdp')
files.append('MM.log')
files.append('posre.itp')
files.append('tmp_ene.del')
for file in files:
    try:
        os.remove(file)
    except OSError:
        pass

assert abs(final_energy + 4.06503308131) < 5e-3

