""" 
This module defines an ASE interface to gromacs
http://www.gromacs.org

It is VERY SLOW compared to standard Gromacs 
(due to slow formatted io required here).

Mainly intended to be the MM part in the ase QM/MM

Markus.Kaukonen@iki.fi

See accompanying license files for details.
"""

import os, sys
import glob
from ase import units
import numpy as np
from ase.io.gromos import read_gromos, write_gromos
from ase.io import read
from general import Calculator

string_keys = [
    'define',
    'integrator',
    'nsteps',
    'nstfout',
    'nstlog',
    'nstenergy',
    'energygrps',
    'nstlist',
    'ns_type',
    'pbc',
    'rlist',
    'coulombtype',
    'rcoulomb',
    'vdwtype',
    'rvdw',
    'rvdw_switch',
    'DispCorr',
]

class Gromacs(Calculator):
    """ A calculator using gromacs.org .
    Initializing variables
    and preparing gromacs run input file.

    It is very slow to use gromacs this way, the point is use it as
    MM calculator in QM/MM calculations (ase_qmmm_manyqm.py)
    """
    name = 'Gromacs'
    def __init__(self, init_structure_file='gromacs_init.gro', \
                     structure_file='gromacs_out.g96', \
                     force_field='oplsaa', water_model='tip3p', \
                     base_filename = 'gromacs', \
                     extra_pdb2gmx_parameters = '', \
                     extra_grompp_parameters = '', \
                     extra_mdrun_parameters = '', \
                     doing_qmmm = False, freeze_qm = False, \
                     index_filename = 'index.ndx', \
                     **kwargs):

        """Construct Gromacs-calculator object.

        For example (setting for the MM part of a QM/MM run):
        CALC_MM = Gromacs(
        init_structure_file = infile_name,
        structure_file = 'gromacs_qm.g96', \
        force_field='oplsaa', 
        water_model='tip3p',
        base_filename = 'gromacs_qm',
        doing_qmmm = True, freeze_qm = False,
        index_filename = 'index.ndx',
        extra_mdrun_parameters = ' -nt 1 ',
        define = '-DFLEXIBLE',
        integrator = 'md',
        nsteps = '0',
        nstfout = '1',
        nstlog = '1',
        nstenergy = '1',
        nstlist = '1',
        ns_type = 'grid',
        pbc = 'xyz',
        rlist = '1.15',
        coulombtype = 'PME-Switch',
        rcoulomb = '0.8',
        vdwtype = 'shift',
        rvdw = '0.8',
        rvdw_switch = '0.75',
        DispCorr = 'Ener')


        Parameters
        ==========
        init_structure_file: str
            Name of the input structure file for gromacs
            (only pdb2gmx uses this)
        structure_file: str
            Name of the structure file for gromacs
            (in all other context that the iniial input file)
        force_field: str
            Name of the force field for gromacs
        water_model: str
            Name of the water model for gromacs
        base_filename: str
            The generated Gromacs file names have this string  
            as the common part in their names (except structure files).
        doing_qmmm: logical
            If true we run only sigle step of gromacs 
            (to get MM forces and energies in QM/MM)
        freeze_qm: logical
            If true, the qm atoms will be kept fixed
            (The list of qm atoms is taken from file 'index_filename', below)
        index_filename: string
            Name of the index file for gromacs
        extra_pdb2gmx_parameters: str
            extra parameter(s) to be passed to gromacs programm 'pdb2gmx'
        extra_grompp_parameters: str
            extra parameter(s) to be passed to gromacs programm 'grompp'
        extra_mdrun_parameters: str
            extra parameter(s) to be passed to gromacs programm 'mdrun'
        """

        self.init_structure_file = init_structure_file
        self.structure_file = structure_file
        self.force_field = force_field 
        self.water_model = water_model 
        self.base_filename = base_filename
        self.topology_filename = base_filename+'.top'
        self.doing_qmmm = doing_qmmm
        self.freeze_qm = freeze_qm
        self.index_filename = index_filename
        self.extra_pdb2gmx_parameters = extra_pdb2gmx_parameters
        self.extra_grompp_parameters = extra_grompp_parameters
        self.extra_mdrun_parameters = extra_mdrun_parameters

        self.string_params = {}
        self.string_params_doc = {}
        for key in string_keys:
            self.string_params[key] = None
            self.string_params_doc[key] = None
        #add comments for gromacs input file
        self.string_params_doc['define'] = \
            'flexible/ rigid water'
        self.string_params_doc['integrator'] = \
            'md: molecular dynamics(Leapfrog), \n' + \
            '; md-vv: molecular dynamics(Velocity Verlet), \n' + \
            '; steep: steepest descent minimization, \n' + \
            '; cg: conjugate cradient minimization \n'
        self.positions = None
        self.atoms = None
        # storage for energy and forces
        self.energy = None
        self.forces = None
        
        self.set(**kwargs)
        #delete possible old files before a new calculation
        files = [self.base_filename+ '_confin.gro', 
                 self.base_filename+ '_confout.gro', 
                 self.base_filename+ '.tpr', 
                 self.topology_filename,
                 self.base_filename+ '.mdp',
                 self.base_filename+ '.log',
                 'tmp_force.del', 'tmp_ene.del', 'energy.xvg',
                 'gromacsEnergy.xvg','gromacsForce.xvg']
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
        files = glob.glob('#*')
        for f in files:
            try:
                os.remove(f)
            except OSError:
                pass
        # in qm/mm when also atoms are moving one has to set
        # in gromacs input file:
        # integrator = md and nsteps = 0
        if self.doing_qmmm:
            self.string_params['integrator'] = 'md'
            self.string_params['nsteps'] = '0'
        self.write_parameters()

        # a possible prefix for gromacs programs
        if os.environ.has_key('GMXCMD_PREF'):
            self.prefix = os.environ['GMXCMD_PREF']
        else:
            self.prefix = ''

        # a possible postfix for gromacs programs
        if os.environ.has_key('GMXCMD_POST'):
            self.postfix = os.environ['GMXCMD_POST']
        else:
            self.postfix = ''

        # write input files for gromacs force and energy calculations
        filename = 'inputGenergy.txt'
        output = open(filename,'w')
        output.write('Potential  \n')
        output.write('   \n')
        output.write('   \n')
        output.close()

        filename = 'inputGtraj.txt'
        output = open(filename, 'w')
        output.write('System  \n')
        output.write('   \n')
        output.write('   \n')
        output.close()

    def get_prefix(self):
        return self.prefix

    def get_postfix(self):
        return self.postfix

    def set(self, **kwargs):
        """ Setting values for the parameters of the gromacs calculator """
        for key in kwargs:
            if self.string_params.has_key(key):
                self.string_params[key] = kwargs[key]
            else:
                raise TypeError('Parameter not defined: ' + key)

    def set_init_structure_file(self, init_structure_file):
        """ change the input structure filename for pdb2gmx"""
        self.init_structure_file = init_structure_file

    def set_structure_file(self, structure_file):
        """ change the structure filename (the file that is updated)"""
        self.structure_file = structure_file

    def set_base_filename(self, base_filename):
        """ change the common part of the filenames 
        (except for structure files) """
        self.base_filename = base_filename

    def set_atoms(self, atoms):
        self.atoms = atoms.copy()

    def get_atoms(self):
        atoms = self.atoms.copy()
        atoms.set_calculator(self)
        return atoms

    def read_atoms(self):
        """ read atoms from file """
        self.atoms = read_gromos(self.structure_file) 

    def read_init_atoms(self):
        """ read atoms from file """
        self.atoms = read(self.init_structure_file) 

    def generate_topology_and_g96file(self):
        """ from coordinates (self.structure_file)
            and gromacs run input file (' + self.base_filename + '.mdp)
            generate topology 'self.topology_filename'
            and structure file in .g96 format
        """
        import os.path
        #generate structure and topology files 
        # In case of predefinded topology file this is not done
        command = self.prefix + 'pdb2gmx' + self.postfix + ' '
        os.system(command + \
                      ' -f ' + self.init_structure_file + \
                      ' -o ' + self.structure_file + \
                      ' -p ' + self.topology_filename + \
                      ' -ff ' + self.force_field + \
                      ' -water ' + self.water_model + \
                      ' ' + self.extra_pdb2gmx_parameters +\
                      ' > /dev/null 2>&1')
#                      ' > debug.log 2>&1')

        atoms = read_gromos(self.structure_file)
        self.atoms = atoms.copy()

    def generate_g96file(self):
        """ from current coordinates (self.structure_file)
            write a structure file in .g96 format
        """
        import os.path
        #generate structure file in g96 format 
        write_gromos(self.structure_file, self.atoms)


    def generate_gromacs_run_file(self):
        """ Generates input file for a gromacs mdrun
        based on structure file and topology file
        resulting file is ' + self.base_filename + '.tpr
        """

        import os.path
        #generate gromacs run input file (gromacs.tpr)
        try:
            os.remove(self.base_filename + '.tpr')
        except:
            pass
        command = self.prefix + 'grompp' + self.postfix + ' '
        if os.path.isfile(self.index_filename):
            os.system(command + \
                          ' -f ' + self.base_filename + '.mdp ' + \
                          ' -c ' + self.structure_file + \
                          ' -p ' + self.topology_filename + \
                          ' -n ' + self.index_filename + \
                          ' -o ' + self.base_filename + '.tpr ' + \
                          ' ' + self.extra_grompp_parameters + \
                          ' -maxwarn 100' + ' > /dev/null 2>&1')

        else:
            os.system(command + \
                          ' -f ' + self.base_filename + '.mdp ' + \
                          ' -c ' + self.structure_file + \
                          ' -p ' + self.topology_filename + \
                          ' -o ' + self.base_filename + '.tpr -maxwarn 100' + \
                          ' ' + self.extra_grompp_parameters + \
                          ' > /dev/null 2>&1')

    def get_command(self):
        """Return command string for gromacs mdrun.  """
        command = None
        if os.environ.has_key('GMXCMD'):
            command = self.prefix + os.environ['GMXCMD'] + self.postfix
        return command

    def run(self):
        """ runs a 0-step gromacs-mdrun with the 
        current atom-configuration """
        delnames = glob.glob('#*')
        try:
            for delname in delnames:
                os.remove(delname)
        except:
            pass
        command = self.get_command()
        if self.doing_qmmm:
            os.system(command \
                          + ' -s ' + self.base_filename + '.tpr' \
                          + ' -o ' + self.base_filename + '.trr ' \
                          + ' -e ' + self.base_filename + '.edr ' \
                          + ' -g ' + self.base_filename + '.log -ffout ' \
                          + ' -rerun ' + self.structure_file \
                          + ' ' + self.extra_mdrun_parameters \
                          + ' > mm.log 2>&1')
        else:
            os.system(command \
                          + ' -s ' + self.base_filename + '.tpr' \
                          + ' -o ' + self.base_filename + '.trr' \
                          + ' -e ' + self.base_filename + '.edr' \
                          + ' -g ' + self.base_filename + '.log -ffout ' \
                          + ' -c ' + self.structure_file \
                          + ' ' + self.extra_mdrun_parameters \
                          + '  > MM.log 2>&1')
            atoms = read_gromos(self.structure_file)
            self.atoms = atoms.copy()

    def update(self, atoms):
        """ set atoms and do the calculation """
        # performs an update of the atoms 
        self.atoms = atoms.copy()
        #must be g96 format for accuracy, alternatively binary formats
        write_gromos(self.structure_file, atoms)
        # does run to get forces and energies
        self.calculate()

    def get_potential_energy(self, atoms):
        """ get the gromacs potential energy """
        self.update(atoms)
        return self.energy

    def get_forces(self, atoms):
        """ get the gromacs forces """
        self.update(atoms)
        return self.forces

    def get_stress(self, atoms):
        """Gromacs stress, not implemented"""
        return np.zeros(6)

    def calculate(self):
        """ runs one step gromacs-mdrun and 
        gets energy and forces
        """
        self.run()        
        self.energy = 0.0
        delnames = glob.glob('#*')
        try:
            for delname in delnames:
                os.remove(delname)
        except:
            pass
        # get energy
        try:
            os.remove('tmp_ene.del')
        except:
            pass
        command = self.prefix + 'g_energy' + self.postfix + ' '
        os.system(command +\
                      ' -f ' + self.base_filename + '.edr -dp '+\
                      ' -o ' + self.base_filename + \
                      'Energy.xvg < inputGenergy.txt'+\
                      ' > /dev/null 2>&1')
        os.system('tail -n 1 ' + self.base_filename + \
                      'Energy.xvg > tmp_ene.del')
        line = open('tmp_ene.del', 'r').readline()
        energy = float(line.split()[1])
        #We go for ASE units !
        self.energy = energy * units.kJ / units.mol 
        # energies are about 100 times bigger in Gromacs units 
        # when compared to ase units

        #get forces
        try:
            os.remove('tmp_force.del')
        except:
            pass
        #os.system('gmxdump_d -f gromacs.trr > tmp_force.del 2>/dev/null')
        command = self.prefix + 'g_traj' + self.postfix + ' '
        os.system(command +\
                      ' -f ' + self.base_filename + '.trr -s ' \
                      + self.base_filename + '.tpr -of ' \
                      + ' -fp ' + self.base_filename \
                      + 'Force.xvg < inputGtraj.txt ' \
                      + ' > /dev/null 2>&1')
        lines = open(self.base_filename + 'Force.xvg', 'r').readlines()
        forces = []
        forces.append(np.array\
                          ([float(f) for f in lines[-1].split()[1:]]))
        #We go for ASE units !gromacsForce.xvg
        self.forces = np.array(forces)/ units.nm * units.kJ / units.mol
        self.forces = np.reshape(self.forces, (-1, 3))
        #self.forces = np.array(forces)

    def set_own(self, key, value, docstring=""):
        """Set own gromacs input file parameter."""
        self.string_params[key] = value
        self.string_params_doc[key] = docstring

    def write_parameters(self):
        """ Writes run-input file for gromacs (mdrun) """
        prefix = ';'
        filename = self.base_filename + '.mdp'
        output = open(filename,'w')
        output.write(prefix+\
            '=======================================================\n')
        output.write(prefix+'Gromacs input file \n')
        output.write(prefix+ \
            'Created using the Atomic Simulation Environment (ASE) \n')
        output.write(prefix+\
            '=======================================================\n')
        for key, val in self.string_params.items():
            if val is not None:
                if (self.string_params_doc[key] == None):
                    docstring = ''
                else:
                    docstring = self.string_params_doc[key]
                output.write('%-35s = %s ; %s\n' \
                                 % (key, val, docstring))
        output.close()
        if self.freeze_qm:
            self.add_freeze_group()


    def add_freeze_group(self):
        """ 
        Add freeze group (all qm atoms) to the gromacs index file
        and modify the 'self.base_filename'.mdp file to adopt for freeze group.
        The qm regions are read from the file index.ndx

        This is usefull if one makes many moves in MM 
        and then only a few with both qm and mm moving.

        qse-qm/mm indexing starts from 0
        gromacs indexing starts from 1
        """
        from ase.calculators.ase_qmmm_manyqm import get_qm_atoms

        qms = get_qm_atoms(self.index_filename)
        infile = open(self.index_filename,'r')
        lines = infile.readlines()
        infile.close()
        outfile = open(self.index_filename,'w')
        found = False
        for line in lines:
            if ('freezeGroupQM' in line):
                found = True
            outfile.write(line)
        if not found:
            outfile.write('[ freezeGroupQM ] \n')
            for qm in qms:
                for qmindex in qm:
                    outfile.write(str(qmindex + 1) + ' ')
            outfile.write('\n')
        outfile.close()

        infile = open(self.base_filename + '.mdp','r')
        lines = infile.readlines()
        infile.close()
        outfile = open(self.base_filename + '.mdp','w')
        for line in lines:
            outfile.write(line)
        outfile.write('freezegrps = freezeGroupQM \n')
        outfile.write('freezedim  = Y Y Y  \n')
        outfile.close()
        return
