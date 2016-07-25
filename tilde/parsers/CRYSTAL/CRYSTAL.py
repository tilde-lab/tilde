
# CRYSTAL cryst.out parser
# Author: Evgeny Blokhin

from __future__ import division

import os, sys
import math
import re
import time
import copy
from fractions import Fraction

from numpy import dot, array, cross

from ase.data import chemical_symbols, atomic_numbers
from ase.geometry import cellpar_to_cell
from ase.units import Hartree
from ase import Atoms

from tilde.parsers import Output
from tilde.core.common import metric


def find_all(a_str, sub):
    ''' str finder iterator '''
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1: return
        yield start
        start += len(sub)

class CRYSTOUT(Output):
    patterns = {
    'Etot' :                    re.compile(r"\n\sTOTAL ENERGY\(.{2,3}\)\(.{2}\)\(.{3,4}\)\s(\S{20})\s{1,10}DE(?!.*\n\sTOTAL ENERGY\(.{2,3}\)\(.{2}\)\(.{3,4}\)\s)", re.DOTALL),
    'pEtot' :                   re.compile(r"\n\sTOTAL ENERGY\s(.+?)\sCONVERGENCE"),
    'syminfos' :                re.compile(r"SYMMOPS - TRANSLATORS IN FRACTIONA\w{1,2} UNITS(.+?)\n\n", re.DOTALL),
    'frac_primitive_cells' :    re.compile(r"\n\sPRIMITIVE CELL(.+?)ATOM BELONGING TO THE ASYMMETRIC UNIT", re.DOTALL),
    'molecules' :               re.compile(r"\n\sATOMS IN THE ASYMMETRIC UNIT(.+?)ATOM BELONGING TO THE ASYMMETRIC UNIT", re.DOTALL),
    'cart_vectors' :            re.compile(r"DIRECT LATTICE VECTORS CARTESIAN COMPONENTS \(ANGSTROM\)(.+?)\n\n", re.DOTALL),
    'crystallographic_cell' :   re.compile(r"\n\sCRYSTALLOGRAPHIC(.+?)\n\sT\s=", re.DOTALL),
    'at_str' :                  re.compile(r"^\s{0,3}\d{1,4}\s"),
    'charges' :                 re.compile(r"ALPHA\+BETA ELECTRONS\n\sMULLIKEN POPULATION ANALYSIS(.+?)OVERLAP POPULATION CONDENSED TO ATOMS", re.DOTALL),
    'magmoms' :                 re.compile(r"ALPHA-BETA ELECTRONS\n\sMULLIKEN POPULATION ANALYSIS(.+?)OVERLAP POPULATION CONDENSED TO ATOMS", re.DOTALL),
    'icharges' :                re.compile(r"\n\sATOMIC NUMBER(.{4}),\sNUCLEAR CHARGE(.{7}),"),
    'starting' :                re.compile(r"EEEEEEEEEE STARTING(.+?)\n"),
    'ending' :                  re.compile(r"EEEEEEEEEE TERMINATION(.+?)\n"),
    'freqs' :                   re.compile(r"DISPERSION K POINT(.+?)FREQ\(CM\*\*\-1\)", re.DOTALL),
    'gamma_freqs' :             re.compile(r"\(HARTREE\*\*2\)   \(CM\*\*\-1\)     \(THZ\)             \(KM\/MOL\)(.+?)NORMAL MODES NORMALIZED TO CLASSICAL AMPLITUDES", re.DOTALL),
    'ph_eigvecs' :              re.compile(r"NORMAL MODES NORMALIZED TO CLASSICAL AMPLITUDES(.+?)\*{79}", re.DOTALL),
    'needed_disp' :             re.compile(r"\d{1,4}\s{2,6}(\d{1,4})\s{1,3}\w{1,2}\s{11,12}(\w{1,2})\s{11,12}\d{1,2}"),
    'symdisps' :                re.compile(r"N   LABEL SYMBOL DISPLACEMENT     SYM.(.*)NUMBER OF IRREDUCIBLE ATOMS", re.DOTALL),
    'ph_k_degeneracy' :         re.compile(r"K       WEIGHT       COORD(.*)AND RECIPROCAL LATTICE VECTORS", re.DOTALL),
    'supmatrix' :               re.compile(r"EXPANSION MATRIX OF PRIMITIVE CELL(.+?)\sNUMBER OF ATOMS PER SUPERCELL", re.DOTALL),
    'cyc' :                     re.compile(r"\n\sCYC\s(.+?)\n"),
    'enes' :                    re.compile(r"\n\sTOTAL ENERGY\((.+?)\n"),
    'k1' :                      re.compile(r"\n\sMAX\sGRADIENT(.+?)\n"),
    'k2' :                      re.compile(r"\n\sRMS\sGRADIENT(.+?)\n"),
    'k3' :                      re.compile(r"\n\sMAX\sDISPLAC.(.+?)\n"),
    'k4' :                      re.compile(r"\n\sRMS\sDISPLAC.(.+?)\n"),
    'version' :                 re.compile(r"\s\s\s\s\sCRYSTAL\d{2}(.*)\*\n", re.DOTALL),
    'pv' :                      re.compile(r"\n PV            :\s(.*)\n"),
    'ts' :                      re.compile(r"\n TS            :\s(.*)\n"),
    'et' :                      re.compile(r"\n ET            :\s(.*)\n"),
    'T' :                       re.compile(r"\n AT \(T =(.*)MPA\):\n"),
    }

    def __init__(self, filename, **kwargs):
        Output.__init__(self, filename)
        self.properties_calc, self.crystal_calc = False, False

        # this is the limiting distance, after which the direction is considered non-periodic
        # be careful, as this has no physical meaning and may vary
        # NB non-periodic component(s) are assigned 500 in CRYSTAL
        self.PERIODIC_LIMIT = 50

        '''if kwargs:
            if not 'basis_set' in kwargs or not 'atomtypes' in kwargs:
                raise RuntimeError( 'Invalid missing properties defined!' )
            missing_props = kwargs
        else:
            missing_props = None

        # If we have got pure PROPERTIES output,
        # we shouldn't process it right away
        # Instead we postpone parsing until
        # it matches other (parent) CRYSTAL output
        # by _coupler_ property (E_tot).
        # However if we have received *missing_props*,
        # we do parse them now
        if not missing_props: self._coupler_ = self.is_coupling(filename)'''

        # normalize breaks and get rid of possible odd MPI incusions in important data
        raw_data = open(filename).read().replace('\r\n', '\n').replace('\r', '\n').replace('FORTRAN STOP\n', '')
        parts_pointer = list(find_all(raw_data, "*                              MAIN AUTHORS"))

        # determine whether to deal with CRYSTAL and/or PROPERTIES output formats
        if len(parts_pointer) > 1:
            if not self.is_properties(raw_data[ parts_pointer[1]: ]) and \
            len(raw_data[ parts_pointer[1]: ]) > 2000: # in case of empty properties outputs
                raise RuntimeError( 'File contains several merged outputs, currently not supported!' )
            else:
                self.data = raw_data[ parts_pointer[0] : parts_pointer[1] ]
                self.pdata = raw_data[ parts_pointer[1]: ]
                self.properties_calc, self.crystal_calc = True, True
        else:
            if not self.is_properties(raw_data[ parts_pointer[0]: ]):
                self.data = raw_data[ parts_pointer[0]: ]
                self.crystal_calc = True
            else:
                self.pdata = raw_data[ parts_pointer[0]: ]
                self.properties_calc = True

        if not self.crystal_calc and not self.properties_calc: raise RuntimeError( 'Though this file looks similar to CRYSTAL output, its format is unknown!' )

        if self.crystal_calc:
            self.info['duration'] = self.get_duration()
            self.info['finished'] = self.is_finished()

            self.info['framework'] = 0x3
            self.info['ansatz'] = 0x3

            self.comment, self.info['input'], self.info['prog'] = self.get_input_and_version(raw_data[ 0:parts_pointer[0] ])
            self.molecular_case = False if not ' MOLECULAR CALCULATION' in self.data else True

            self.info['energy'] = self.get_etot()
            self.structures = self.get_structures()

            self.set_charges()

            self.electrons['basis_set'] = self.get_bs()

            self.phonons['ph_k_degeneracy'] = self.get_k_degeneracy()
            self.phonons['modes'], self.phonons['irreps'], self.phonons['ir_active'], self.phonons['raman_active'] = self.get_phonons()
            self.phonons['ph_eigvecs'] = self.get_ph_eigvecs()
            self.phonons['dfp_disps'], self.phonons['dfp_magnitude'] = self.get_ph_sym_disps()
            self.phonons['dielectric_tensor'] = self.get_static_dielectric_tensor()

            self.convergence, self.ncycles, self.tresholds = self.get_convergence()

            self.set_method()

            # extract zero-point energy, depending on phonons presence
            if self.phonons['modes']:
                self.phonons['zpe'] = self.get_zpe()
                self.phonons['td'] = self.get_td()

            # format ph_k_degeneracy
            if self.phonons['ph_k_degeneracy']:
                bz, d = [], []
                for k, v in self.phonons['ph_k_degeneracy'].items():
                    bz.append( self.phonons['ph_k_degeneracy'][k]['bzpoint'] )
                    d.append( self.phonons['ph_k_degeneracy'][k]['degeneracy'] )
                self.phonons['ph_k_degeneracy'] = {}
                for i in range(len(bz)):
                    self.phonons['ph_k_degeneracy'][bz[i]] = d[i]

        if self.properties_calc and not self.crystal_calc: raise RuntimeError( 'PROPERTIES output with insufficient information omitted!' )

        '''if self.properties_calc:
            if not missing_props:
                missing_props = {
                    'atomtypes': [i[0] for i in self.structures[-1]['atoms']],
                    'basis_set': self.electrons['basis_set']['bs']
                    }

            # TODO: this should be workaround-ed with iterative parsing
            #try: self.electrons['eigvals'] = self.get_e_eigvals()
            #except MemoryError: raise RuntimeError( 'Sorry, the file is too large!' )

            #self.electrons['proj_eigv_impacts'] = self.get_e_impacts(self.get_e_eigvecs(), missing_props['atomtypes'], missing_props['basis_set'])

            #if self.electrons['proj_eigv_impacts'] and self.crystal_calc:
            #    self.info['prog'] += '+PROPERTIES'
        '''

        self.related_files.append(filename)
        cur_folder = os.path.dirname(filename)
        check_files = []
        if filename.endswith('.cryst.out'):
            check_files = [filename.replace('.cryst.out', '') + '.d12', filename.replace('.cryst.out', '') + '.gui']
        elif filename.endswith('.out'):
            check_files = [filename.replace('.out', '') + '.d12', filename.replace('.out', '') + '.gui']
        for check in check_files:
            if os.path.exists(os.path.join(cur_folder, check)): self.related_files.append(os.path.join(cur_folder, check))

    @staticmethod
    def fingerprints(test_string):
        if "*                              MAIN AUTHORS" in test_string: return True
        else: return False

    def is_coupling(self, filename):
        '''
        determines if this output should be *coupled* with another one, i.e. needed information is present there (which may be expensive to extract).
        This should be done as fast as possible because the file may be very large. So there are 4 criteria:
        (1) PROPERTIES-type output
        (2) present eigenvalues
        (3) present eigenvectors
        (4) absent CRYSTAL-type output
        '''
        e, crit_1, crit_2, crit_3 = None, False, False, False
        f = open(filename, 'r')
        while True:
            str = f.readline()
            if not str: break

            if " BASIS SET" in str: return None # CRYSTAL-type output marker
            elif not e and str.startswith(" TOTAL ENERGY "): e = float( str.split("CONVERGENCE")[0][-23:] )
            elif not crit_1 and self.is_properties(str): crit_1 = True
            elif not crit_2 and " EIGENVALUES - K=" in str: crit_2 = True
            elif not crit_3 and " HAMILTONIAN EIGENVECTORS - K=" in str: crit_3 = True

            if e and crit_1 and crit_2 and crit_3: return e
        return None

    def is_properties(self, piece_of_data):
        if " RESTART WITH NEW K POINTS NET" in piece_of_data or " CRYSTAL - PROPERTIES" in piece_of_data or "Wavefunction file can not be found" in piece_of_data: return True
        else: return False

    '''def get_symops(self):
        syms = self.patterns['syminfos'].findall(self.data)
        if not syms:
            self.warning( 'No sym info found, assuming P1!' )
            return ['+x,+y,+z']
        lines = syms[-1].splitlines()
        symops = []
        for line in lines:
            elems = line.split()
            if len(elems) != 14: continue
            sym_pos = ['', '', '']
            for i in range(2, 14):
                try: elems[i] = float(elems[i])
                except ValueError:
                    if i==2: break
                    else: raise RuntimeError( 'Sym info contains invalid rotational matrix!' )
            for i in range(2, 11):
                if elems[i] != 0:
                    if elems[i]>0: s = '+'
                    else: s = '-'

                    if i == 2 or i == 5 or i == 8:  s += 'x'
                    if i == 3 or i == 6 or i == 9:  s += 'y'
                    if i == 4 or i == 7 or i == 10: s += 'z'

                    if 1<i<5:  sym_pos[0] += s
                    if 4<i<8:  sym_pos[1] += s
                    if 7<i<11: sym_pos[2] += s
            if elems[11] != 0: sym_pos[0] += '+'+str(elems[11])
            if elems[12] != 0: sym_pos[1] += '+'+str(elems[12])
            if elems[13] != 0: sym_pos[2] += '+'+str(elems[13])

            sym_pos = ",".join(sym_pos)
            symops.append(sym_pos)
        if len(symops) == 0:
            raise RuntimeError( 'Sym info is invalid!' )
        return symops'''

    def get_cart2frac(self):
        matrix = []
        vectors = self.patterns['cart_vectors'].findall(self.data)

        if vectors:
            lines = vectors[-1].splitlines()
            for line in lines:
                vector = line.split()
                try: vector[0] and float(vector[0])
                except (ValueError, IndexError): continue
                for i in range(0, 3):
                    vector[i] = float(vector[i])
                    # check whether angstroms are used instead of fractions
                    if vector[i] > self.PERIODIC_LIMIT: vector[i] = self.PERIODIC_LIMIT
                matrix.append( vector )
        else:
            if not self.molecular_case: raise RuntimeError( 'Unable to extract cartesian vectors!' )

        return matrix

    def get_structures(self):
        structures = []
        if self.molecular_case: compiled_pattern = self.patterns['molecules']
        else: compiled_pattern = self.patterns['frac_primitive_cells']

        strucs = compiled_pattern.findall(self.data)

        if not strucs: raise RuntimeError( 'No structure was found!' )

        for crystal_data in strucs:
            symbols, parameters, atoms = [], [], []
            pbc = [True, True, True]

            if self.molecular_case: pbc = False

            crystal_data = re.sub( ' PROCESS(.{32})WORKING\n', '', crystal_data) # warning! MPI statuses may spoil valuable data

            # this is to account correct cart->frac atomic coords conversion using cellpar_to_cell ASE routine
            # 3x3 cell is used only here to obtain ab_normal and a_direction
            cell = self.get_cart2frac()
            ab_normal = [0,0,1] if self.molecular_case else metric(cross(cell[0], cell[1]))
            a_direction = None if self.molecular_case else metric(cell[0])

            oth = self.patterns['crystallographic_cell'].search(crystal_data)
            if oth is not None: crystal_data = crystal_data.replace(oth.group(), "") # delete other cells info except primitive cell

            lines = crystal_data.splitlines()
            for li in range(len(lines)):
                if 'ALPHA      BETA       GAMMA' in lines[li]:
                    parameters = lines[li+1].split()
                    try: parameters = [float(i) for i in parameters]
                    except ValueError: raise RuntimeError( 'Cell data are invalid: ' + lines[li+1] )
                elif self.patterns['at_str'].search(lines[li]):
                    atom = lines[li].split()
                    if len(atom) in [7, 8] and len(atom[-2]) > 7:
                        for i in range(4, 7):
                            try: atom[i] = round(float(atom[i]), 10)
                            except ValueError: raise RuntimeError('Atomic coordinates are invalid!')

                        # Warning: we lose here the non-equivalency in the same atom types, denoted by integer! For magmoms refer to corresp. property!
                        atom[3] = ''.join([letter for letter in atom[3] if not letter.isdigit()]).capitalize()
                        if atom[3] == 'Xx': atom[3] = 'X'
                        symbols.append( atom[3] )
                        atomdata = atom[4:7]
                        #atomdata.append(atom[1]) # irreducible (T or F)
                        atoms.append(atomdata)

            if len(atoms) == 0: raise RuntimeError('No atoms found, cell info is corrupted!')
            if parameters and len([x for x in parameters if x > 0.75]) < 6: raise RuntimeError('Cell is collapsed!') # prevent cell collapses known in CRYSTAL RESTART outputs

            # check whether angstroms are used instead of fractions
            if pbc:
                for i in range(0, 3):
                    if parameters[i] > self.PERIODIC_LIMIT:
                        parameters[i] = self.PERIODIC_LIMIT
                        pbc[i] = False

                        # TODO : account case with not direct angles
                        for j in range(0, len(atoms)):
                            atoms[j][i] /= self.PERIODIC_LIMIT

                matrix = cellpar_to_cell(parameters, ab_normal, a_direction) # TODO : ab_normal, a_direction may in some cases belong to completely other structure!
                structures.append( Atoms(symbols=symbols, cell=matrix, scaled_positions=atoms, pbc=pbc) )
            else:
                structures.append( Atoms(symbols=symbols, cell=[self.PERIODIC_LIMIT, self.PERIODIC_LIMIT, self.PERIODIC_LIMIT], positions=atoms, pbc=False) )

        return structures

    def get_etot(self):
        e = self.patterns['Etot'].search(self.data)
        if e is not None: return float(e.groups()[0]) * Hartree
        else:
            if '  CENTRAL POINT ' in self.data:
                phonon_e = self.data.split('  CENTRAL POINT ')[-1].split("\n", 1)[0]
                phonon_e = phonon_e.split()[0]
                return float(phonon_e) * Hartree
            else:
                self.warning( 'No energy found!' )
                return None

    '''def get_etot_props(self):
        e = self.patterns['pEtot'].search(self.pdata)
        if e is not None: return float(e.groups()[0])
        else:
            self.warning( 'No energy in PROPERTIES output!' )
            return None'''

    def get_phonons(self):
        if not "U   U  EEEE  N   N   CCC  Y   Y" in self.data: return None, None, None, None
        freqdata = []
        freqsp = self.patterns['freqs'].findall(self.data)
        if freqsp:
            for i in freqsp:
                freqdata.append( [_f for _f in i.strip().splitlines() if _f] )
        else:
            freqsp = self.patterns['gamma_freqs'].search(self.data)
            if freqsp is None: return None, None, None, None
            else:   freqdata.append( [_f for _f in freqsp.group(1).strip().splitlines() if _f] )
        bz_modes, bz_irreps, kpoints = {}, {}, []
        ir_active, raman_active = [], []
        for set in freqdata:
            modes, irreps = [], []
            for line in set:
                if " R( " in line or " C( " in line: # k-coords!
                    coords = line[20:-18].strip().split()
                    kpoints.append( " ".join(coords) )
                    continue
                if "(" in line and ")" in line: # filter lines with freqs: condition 1 from 3
                    val = line.split()
                    if len(val) < 5: continue # filter lines with freqs: condition 2 from 3
                    try: float(val[2]) + float(val[3])
                    except ValueError: continue # filter lines with freqs: condition 3 from 3
                    nmodes = [_f for _f in val[0].split("-") if _f]
                    if len(nmodes) == 1: # silly CRYSTAL output with fixed place for numericals
                        mplr = int(val[1]) - int(val[0].replace("-", "")) + 1
                        for i in range( 0, mplr ):
                            modes.append(float(val[3]))
                            irrep = val[5].replace("(", "").replace(")", "").strip()
                            if irrep == '': irrep = val[6].replace("(", "").replace(")", "").strip()
                            irreps.append(irrep)
                    else: # silly CRYSTAL output with fixed place for numericals
                        mplr = int(nmodes[1]) - int(nmodes[0]) + 1
                        for i in range( 0, mplr ):
                            modes.append(float(val[2]))
                            irrep = val[4].replace("(", "").replace(")", "").strip()
                            if irrep == '': irrep = val[5].replace("(", "").replace(")", "").strip()
                            irreps.append(irrep)
                    # IR / RAMAN data ( * mplr )
                    c = 0
                    for i in range(-4, 0):
                        if val[i] in ['A', 'I']:
                            if c == 0: ir_active.extend([val[i]] * mplr)
                            else: raman_active.extend([val[i]] * mplr)
                            c += 1

            if not kpoints: BZ_point_coord = '0 0 0'
            else: BZ_point_coord = kpoints[-1]

            # normalize special symmerty point coords, if exist
            if self.phonons['ph_k_degeneracy']:
                BZ_point_coord = self.phonons['ph_k_degeneracy'][BZ_point_coord]['bzpoint']

            bz_modes[BZ_point_coord] = modes
            bz_irreps[BZ_point_coord] = irreps
        return bz_modes, bz_irreps, ir_active, raman_active

    def get_ph_eigvecs(self):
        if not self.phonons['modes']: return None
        eigvecdata = []
        eigvecsp = self.patterns['ph_eigvecs'].search(self.data)
        if eigvecsp:
            eigvecsp = eigvecsp.group(1)
            parts = eigvecsp.split("DISPERSION K POINT")
            parts[0] = parts[0].split("LO-TO SPLITTING")[0] # no lo-to splitting account at the moment
            for bzpoint in parts:
                eigvecdata.append( bzpoint.split("FREQ(CM**-1)") )
        else: return None

        natseq = list(range(1, len(self.structures[-1])+1))
        bz_eigvecs, kpoints = {}, []
        for set in eigvecdata:
            ph_eigvecs = []
            for i in set:
                rawdata = [_f for _f in i.strip().splitlines() if _f]
                freqs_container = []
                involved_atoms = []
                for j in rawdata:
                    if " R( " in j or " C( " in j: # k-coords!
                        coords = j[20:-18].strip().split()
                        kpoints.append( " ".join(coords) )
                        continue
                    vectordata = j.split()
                    if vectordata[0] == 'AT.':
                        involved_atoms.append(int(vectordata[1]))
                        vectordata = vectordata[4:]
                    elif vectordata[0] == 'Y' or vectordata[0] == 'Z': vectordata = vectordata[1:]
                    else: continue

                    if not len(freqs_container):
                        for d in range(0, len(vectordata)): freqs_container.append([]) # 6 (or 3) columns
                    for k in range(0, len(vectordata)):
                        freqs_container[k].append( float(vectordata[k]) )

                for fn in range(0, len(freqs_container)):
                    for a in natseq:
                        if a not in involved_atoms: # insert fake zero vectors for atoms which are not involved in a vibration
                            for h in range(3): freqs_container[fn].insert((a-1)*3, 0)
                    ph_eigvecs.append( freqs_container[fn] )

                if 'ANTI-PHASE' in i:
                    self.warning( 'Phase and anti-phase eigenvectors found at k=(%s), the latter will be omitted' % kpoints[-1] )
                    break
            if len(ph_eigvecs) != len(self.phonons['modes']['0 0 0']):
                raise RuntimeError( 'Fatal error! Number of eigenvectors does not correspond to the number of freqs!' )

            if not kpoints: BZ_point_coord = '0 0 0'
            else: BZ_point_coord = kpoints[-1]

            # normalize special symmerty point coords, if exist
            if self.phonons['ph_k_degeneracy']:
                BZ_point_coord = self.phonons['ph_k_degeneracy'][BZ_point_coord]['bzpoint']
            bz_eigvecs[BZ_point_coord] = ph_eigvecs
        return bz_eigvecs

    def get_k_degeneracy(self):
        ph_k_degeneracy = self.patterns['ph_k_degeneracy'].search(self.data)
        if ph_k_degeneracy is None: return None
        k_degeneracy_data = {}
        lines = ph_k_degeneracy.group(1).splitlines()
        shr_fact = []
        k_vectors = []
        orig_coords = []
        degenerated = []
        for n in lines:
            if 'WITH SHRINKING FACTORS' in n:
                k = n.split()
                for j in k:
                    if j.isdigit(): shr_fact.append(int(j))
            else:
                k = [_f for _f in n.split("   ") if _f]
                if len(k)==4:
                    orig_coord = k[2].strip().split()
                    orig_coords.append( " ".join(orig_coord) )
                    k_coords = [int(i) for i in orig_coord]
                    degenerated.append( int( k[1].replace('.', '') ) )
                    k_vectors.append(k_coords)
        if shr_fact is None or k_vectors is None: raise RuntimeError('Invalid format in phonon k-vector degeneracy data!')
        for vi in range(len(k_vectors)):
            norm_coord = []
            for i in range(len(k_vectors[vi])):
                norm_coord.append( "%s" % Fraction( k_vectors[vi][i], shr_fact[i] ) )
            k_degeneracy_data[ orig_coords[vi] ] = { 'bzpoint' : " ".join(norm_coord), 'degeneracy' : degenerated[vi] }
        return k_degeneracy_data

    def set_charges(self):
        charges, magmoms = [], []
        atomcharges = self.patterns['charges'].search(self.data)
        atommagmoms = self.patterns['magmoms'].search(self.data)

        if not atomcharges and self.properties_calc: atomcharges = self.patterns['charges'].search(self.pdata)
        if not atommagmoms and self.properties_calc: atommagmoms = self.patterns['magmoms'].search(self.pdata)

        # obtain formal charges from pseudopotentials
        iatomcharges = self.patterns['icharges'].findall(self.data)
        pseudo_charges = copy.deepcopy(atomic_numbers)
        for i in range(len(iatomcharges)):
            try:
                Z = int( iatomcharges[i][0].strip() )
                P = float( iatomcharges[i][1].strip() )
            except: raise RuntimeError('Error in pseudopotential info: ' + sys.exc_info()[1] )
            p_element = [key for key, value in pseudo_charges.items() if value == Z]
            if len(p_element): pseudo_charges[p_element[0].capitalize()] = P
        symbols = list(pseudo_charges.keys())

        if atomcharges is not None:
            parts = atomcharges.group().split("ATOM    Z CHARGE  SHELL POPULATION")
            chargedata = parts[1].splitlines()
            for i in chargedata:
                if self.patterns['at_str'].match(i):
                    val = i.split()
                    val[1] = val[1].capitalize()
                    val[3] = val[3][:6] # erroneous by stars
                    if val[1] in symbols: val[3] = pseudo_charges[val[1]] - float(val[3])
                    elif val[1] == 'Xx': val[3] = -float(val[3]) # this needs checking! TODO
                    else: raise RuntimeError('Unexpected atomic symbol: ' + val[1] )
                    charges.append(val[3])
            try: self.structures[-1].set_initial_charges(charges)
            except ValueError: self.warning('Number of atoms and found charges does not match!') # some issues with CRYSTAL03
        else: self.warning( 'No charges available!' )

        if atommagmoms is not None:
            parts = atommagmoms.group().split("ATOM    Z CHARGE  SHELL POPULATION")
            chargedata = parts[1].splitlines()
            for i in chargedata:
                if self.patterns['at_str'].match(i):
                    val = i.split()
                    val[3] = val[3][:6] # erroneous by stars
                    magmoms.append(float(val[3]))
            try: self.structures[-1].set_initial_magnetic_moments(magmoms)
            except ValueError: self.warning('Number of atoms and found magmoms does not match!') # some issues with CRYSTAL03
        else: self.warning( 'No magmoms available!' )

    def get_input_and_version(self, inputdata):
        # get version
        version = ''
        inputdata = re.sub( ' PROCESS(.{32})WORKING\n', '', inputdata) # warning! MPI statuses may spoil valuable data
        v = self.patterns['version'].search(inputdata)
        if v:
            v = v.group().split("\n")
            major, minor = v[0], v[1]
            # beware of MPI inclusions!
            if '*' in major: major = major.replace('*', '').strip()
            if '*' in minor:
                minor = minor.replace('*', '').strip()
                if ':' in minor: minor = minor.split(':')[1].split()[0]
                else: minor = minor.split()[1]
            version = major.replace('CRYSTAL', '') + ' ' + minor

        # get input data
        inputdata = inputdata.splitlines()
        keywords = []
        keywords_flag = False
        trsh_line_flag = False
        trsh_line_cnt = 0
        for i in range(len(inputdata)):
            if trsh_line_flag: trsh_line_cnt += 1
            if keywords_flag: keywords.append(inputdata[i].strip())
            if inputdata[i].strip() in ["CRYSTAL", "SLAB", "POLYMER", "HELIX", "MOLECULE", "EXTERNAL"]:
                keywords_flag = True
                keywords.extend([inputdata[i-1].strip(), inputdata[i].strip()])
            if inputdata[i].startswith("END"):
                trsh_line_flag = True
                trsh_line_cnt = 0
        if not keywords:
            #self.warning( 'No d12-formatted input data in the beginning found!' )
            return None, None, version
        keywords = keywords[:-trsh_line_cnt]
        comment = keywords[0]
        keywords = "\n".join(keywords)
        return comment, keywords, version

    def is_finished(self):
        if self.info['duration'] and not 'TTTTTTTTTTTTTTTTTTTTTTTTTTTTTT ERR' in self.data: return 0x2
        else: return 0x1

    def get_ph_sym_disps(self):
        symdisps = self.patterns['symdisps'].search(self.data)
        if symdisps is None: return None, None
        else:
            lines = symdisps.group().splitlines()
            plusminus = False
            if 'NUMERICAL GRADIENT COMPUTED WITH A SINGLE DISPLACEMENT (+-dx) FOR EACH' in self.data: plusminus = True
            disps, magnitude = [], 0
            for n in lines:
                r=self.patterns['needed_disp'].search(n)
                if r:
                    disps.append([ int(r.group(1)), r.group(2).replace('D', '').lower() ])
                    if plusminus:
                        disps.append([ int(r.group(1)), r.group(2).replace('D', '-').lower() ])
                elif '= ' in n: # TODO CRYSTAL06 !
                    magnitude = float(n.split()[1])
            if magnitude == 0: raise RuntimeError( 'Cannot find displacement magnitude in FREQCALC output!')
            if not len(disps): raise RuntimeError( 'Cannot find valid displacement data in FREQCALC output!')
            return disps, magnitude

    def get_static_dielectric_tensor(self):
        return "\n VIBRATIONAL CONTRIBUTIONS TO THE STATIC DIELECTRIC TENSOR:\n" in self.data or \
        "\n VIBRATIONAL CONTRIBUTIONS TO THE STATIC POLARIZABILITY TENSOR:\n" in self.data

    def __float(self, number):
        number = number.replace("D","E")
        return float(number)

    def get_bs(self):
        gbasis = { 'bs': {}, 'ps': {} }

        if " ATOM   X(AU)   Y(AU)   Z(AU)  N. TYPE" in self.data: bs = self.data.split(" ATOM   X(AU)   Y(AU)   Z(AU)  N. TYPE") # CRYSTAL<14
        else: bs = self.data.split(" ATOM  X(AU)  Y(AU)  Z(AU)    NO. TYPE  EXPONENT ") # CRYSTAL14

        if len(bs) == 1:
            return self.get_bs_input() # Basis set is absent in output, input may be not enough!
        bs = bs[-1].split("*******************************************************************************\n", 1)[-1] # NO BASE FIXINDEX IMPLEMENTED!
        bs = re.sub( ' PROCESS(.{32})WORKING\n', '', bs) # warning! MPI statuses may spoil valuable data
        bs = bs.splitlines()

        atom_order = []

        for line in bs:
            if line.startswith(" "*20): # gau type or exponents
                if line.startswith(" "*40): # exponents
                    line = line.strip()
                    if line[:1] != '-': line = ' ' + line
                    n=0
                    gaussians = []
                    for s in line:
                        if not n % 10: gaussians.append(' ')
                        gaussians[-1] += s
                        n+=1
                    gaussians = [x for x in map( float, gaussians ) if x != 0]
                    #for i in range(len(gaussians)-1, -1, -1):
                    #    if gaussians[i] == 0: gaussians.pop()
                    #    else: break
                    gbasis['bs'][ atom_type ][-1].append( tuple(gaussians) )

                else: # gau type
                    symb = line.split()[-1]

                    if bs_concurrency:
                        atom_type += '1'
                        bs_concurrency = False
                        try: gbasis['bs'][ atom_type ]
                        except KeyError: gbasis['bs'][ atom_type ] = []
                        else: raise RuntimeError( 'More than two different basis sets for one element - not supported case!' ) # TODO
                    gbasis['bs'][ atom_type ].append( [ symb ] )

            else: # atom No or end
                test = line.split()
                if test and test[0] == 'ATOM': continue # C03: can be odd string ATOM  X(AU)  Y(AU)  Z(AU)
                try: float(test[0])
                except (ValueError, IndexError): break # endb, e.g. void space or INFORMATION **** READM2 **** FULL DIRECT SCF (MONO AND BIEL INT) SELECTED

                atom_type = test[1][:2].capitalize()
                if atom_type == 'Xx': atom_type = 'X'
                atom_order.append(atom_type)

                try: gbasis['bs'][ atom_type ]
                except KeyError:
                    gbasis['bs'][ atom_type ] = []
                    bs_concurrency = False
                else:
                    bs_concurrency = True

        # PSEUDOPOTENTIALS
        ps = self.data.split(" *** PSEUDOPOTENTIAL INFORMATION ***")
        if len(ps) > 1:
            ps = ps[-1].split("*******************************************************************************\n", 2)[-2] # NO BASE FIXINDEX IMPLEMENTED
            ps = re.sub( ' PROCESS(.{32})WORKING\n', '', ps) # warning! MPI statuses may spoil valuable data
            ps = ps.splitlines()
            for line in ps:
                if 'PSEUDOPOTENTIAL' in line:
                    atnum = int( line.split(',')[0].replace('ATOMIC NUMBER', '') )
                    # int( nc.replace('NUCLEAR CHARGE', '') )
                    if 200 < atnum < 1000: atnum = int(str(atnum)[-2:])
                    atom_type = chemical_symbols[ atnum ]
                    try: gbasis['ps'][ atom_type ]
                    except KeyError: gbasis['ps'][ atom_type ] = []
                    else:
                        atom_type += '1'
                        try: gbasis['ps'][ atom_type ]
                        except KeyError: gbasis['ps'][ atom_type ] = []
                        else: raise RuntimeError( 'More than two pseudopotentials for one element - not supported case!' )
                else:
                    lines = line.split()
                    try: float(lines[-2])
                    except (ValueError, IndexError): continue
                    else:
                        if 'TMS' in line:
                            gbasis['ps'][ atom_type ].append( [ lines[0] ] )
                            lines = lines[2:]
                        lines = list(map(float, lines))
                        for i in range(len(lines)//3):
                            gbasis['ps'][ atom_type ][-1].append( tuple( [lines[0 + i*3], lines[1 + i*3], lines[2 + i*3]] ) )

        # sometimes ghost basis set is printed without exponents and we should determine what atom was replaced
        if 'X' in gbasis['bs'] and not len(gbasis['bs']['X']):
            replaced = atom_order[ atom_order.index('X') - 1 ]
            gbasis['bs']['X'] = copy.deepcopy(gbasis['bs'][replaced])

        return self.__correct_bs_ghost(gbasis)

    def get_bs_input(self):
        # input is scanned only if nothing in output found
        # input may contain comments (not expected by CRYSTAL, but user anyway can cheat it) WARNING! block /* */ comments will fail!
        gbasis = { 'bs': {}, 'ps': {} }

        comment_signals = '#/*<!'
        bs_sequence = {0:'S', 1:'SP', 2:'P', 3:'D', 4:'F'}
        bs_type =     {1: 'STO-nG(nd) type ', 2: '3(6)-21G(nd) type '}
        bs_notation = {1:'n-21G outer valence shell', 2: 'n-21G inner valence shell', 3: '3-21G core shell', 6: '6-21G core shell'}
        ps_sequence = ['W0', 'P0', 'P1', 'P2', 'P3', 'P4']
        ps_keywords = {'INPUT':None, 'HAYWLC':'Hay-Wadt large core', 'HAYWSC':'Hay-Wadt small core', 'BARTHE':'Durand-Barthelat', 'DURAND':'Durand-Barthelat'}
        if not self.info['input']:
            self.warning('No basis set found!')
            return gbasis

        read = False
        read_pseud, read_bs = False, False

        for line in self.info['input'].splitlines():
            if line.startswith('END'):
                read = True
                continue

            if not read: continue

            for s in comment_signals:
                pos = line.find(s)
                if pos != -1:
                    line = line[:pos]
                    break

            parts = line.split()

            if len(parts) == 1 and parts[0].upper() in list(ps_keywords.keys()):
                # pseudo
                try: gbasis['ps'][ atom_type ]
                except KeyError: gbasis['ps'][ atom_type ] = []
                else:
                    atom_type += '1'
                    try: gbasis['ps'][ atom_type ]
                    except KeyError: gbasis['ps'][ atom_type ] = []
                    else: raise RuntimeError( 'More than two pseudopotentials for one element - not supported case!' )

                if parts[0] != 'INPUT':
                    gbasis['ps'][ atom_type ].append( ps_keywords[ parts[0].upper() ] )

            elif len(parts) == 0: continue

            else:
                try: list(map(self.__float, line.split())) # sanitary check
                except ValueError:
                    read = False
                    continue

            if len(parts) in [2, 3]:
                # what is this ---- atom, exit, ps exponent or bs exponent?
                if parts[0] == '99' and parts[1] == '0': break # this is ---- exit

                elif '.' in parts[0] or '.' in parts[1]:
                    # this is ---- ps exponent or bs exponent
                    parts = list(map(self.__float, parts))

                    if read_pseud:
                        # distribute exponents into ps-types according to counter, that we now calculate
                        if distrib in list(ps_indeces_map.keys()):
                            gbasis['ps'][ atom_type ].append( [ ps_indeces_map[distrib] ] )
                        gbasis['ps'][ atom_type ][-1].append( tuple( parts ) )
                        distrib += 1
                    elif read_bs:
                        # distribute exponents into orbitals according to counter, that we already defined
                        gbasis['bs'][ atom_type ][-1].append( tuple( parts ) )

                else:
                    # this is ---- atom
                    if len(parts[0]) > 2: parts[0] = parts[0][-2:]
                    if int(parts[0]) == 0: atom_type = 'X'
                    else: atom_type = chemical_symbols[ int(parts[0]) ]

                    try: gbasis['bs'][ atom_type ]
                    except KeyError: gbasis['bs'][ atom_type ] = []
                    else:
                        atom_type += '1'
                        try: gbasis['bs'][ atom_type ]
                        except KeyError: gbasis['bs'][ atom_type ] = []
                        else: raise RuntimeError( 'More than two different basis sets for one element - not supported case!' )
                    continue

            elif len(parts) == 5:
                # this is ---- orbital
                gbasis['bs'][ atom_type ].append( [ bs_sequence[ int(parts[1]) ] ] )
                parts = list(map(int, parts[0:3]))
                if parts[0] == 0:
                    # insert from data given in input
                    read_pseud, read_bs = False, True
                elif parts[0] in list(bs_type.keys()): # 1 = Pople standard STO-nG (Z=1-54); 2 = Pople standard 3(6)-21G (Z=1-54(18)) + standard polarization functions
                    # pre-defined insert
                    if parts[2] in list(bs_notation.keys()):
                        gbasis['bs'][ atom_type ][-1].append( bs_type[ parts[0] ] + bs_notation[ parts[2] ] )
                    else:
                        gbasis['bs'][ atom_type ][-1].append( bs_type[ parts[0] ] + 'n=' + str(parts[2]) )

            elif len(parts) in [6, 7]:
                # this is ---- pseudo - INPUT
                parts.pop(0)
                ps_indeces = list(map(int, parts))
                ps_indeces_map = {}
                accum = 1
                for c, n in enumerate(ps_indeces):
                    if n == 0: continue
                    ps_indeces_map[accum] = ps_sequence[c]
                    accum += n
                distrib = 1
                read_pseud, read_bs = True, False

        if not gbasis['bs']:
            self.warning('No basis set found!')
            return gbasis

        return self.__correct_bs_ghost(gbasis)

    def __correct_bs_ghost(self, gbasis):
        # ghost cannot be in pseudopotential
        atoms = []
        for atom in self.structures[-1].get_chemical_symbols():
            if not atom in atoms: atoms.append( atom )

        for k, v in gbasis['bs'].items():
            # sometimes no BS for host atom is printed when it is replaced by Xx: account it
            if not len(v) and k != 'X' and 'X' in gbasis['bs']:
                gbasis['bs'][k] = copy.deepcopy(gbasis['bs']['X'])

        # actually no GHOST deletion will be performed as it breaks orbitals order for band structure plotting!
        '''cmp_atoms = []
        for cmp_atom in gbasis['bs'].keys():
            if cmp_atom[0:2] != 'X':
                cmp_atom = ''.join([letter for letter in cmp_atom if not letter.isdigit()]) # remove doubling types with numbers (all GHOSTs will be deleted anyway!)
            if not cmp_atom in cmp_atoms: cmp_atoms.append( cmp_atom )

        diff = list(set(atoms) - set(cmp_atoms)) + list(set(cmp_atoms) - set(atoms)) # difference between two lists
        print "diff in atoms and bs:", diff
        if diff:
            if len(diff) == 1 and diff[0] == 'X':
                del gbasis['bs']['X']
            elif len(diff) == 2 and 'X' in diff:
                replace = [i for i in diff if i != 'X'][0]
                if replace == 'X1':
                    # if two ghosts, both will be deleted without proper replacement! TODO: fixme
                    for i in diff:
                        del gbasis['bs'][i]
                else:
                    gbasis['bs'][replace] = gbasis['bs']['X']
                    del gbasis['bs']['X']
            elif len(diff) >= 3:
                # if two ghosts, both will be deleted without proper replacement! TODO: fixme
                for i in diff:
                    if i[0:2] == 'X': del gbasis['bs'][i]'''
        return gbasis

    def set_method(self):

        # Hamiltonian part
        hamiltonian_parts = { # TODO CRYSTAL14
        'DIRAC-SLATER LDA':         {'name': 'LDA',             'type': 0x1},
        'PERDEW-ZUNGER':            {'name': 'PZ_LDA',          'type': 0x1},
        'VOSKO-WILK-NUSAIR':        {'name': 'WVN_LDA',         'type': 0x1},
        'PERDEW-WANG LSD':          {'name': 'PW_LDA',          'type': 0x1},
        'VON BARTH-HEDIN':          {'name': 'VBH_LDA',         'type': 0x1},

        'PERDEW-WANG GGA':          {'name': 'PW_GGA',          'type': 0x2},
        'BECKE':                    {'name': 'B_GGA',           'type': 0x2},
        'LEE-YANG-PARR':            {'name': 'LYP_GGA',         'type': 0x2},
        'PERDEW-BURKE-ERNZERHOF':   {'name': 'PBE_GGA',         'type': 0x2},
        'SOGGA':                    {'name': 'SOGGA',           'type': 0x2},
        'PERDEW86':                 {'name': 'P86_GGA',         'type': 0x2},
        'PBEsol':                   {'name': 'PBESOL_GGA',      'type': 0x2},
        'WILSON-LEVY':              {'name': 'WL_GGA',          'type': 0x2},
        'WU-COHEN GGA':             {'name': 'WC_GGA',          'type': 0x2},
        }
        exch, corr = '', ''

        if ' HARTREE-FOCK HAMILTONIAN\n' in self.data:
            self.info['H'] = 'Hartree-Fock'
            self.info['H_types'].append(0x5)

        elif ' (EXCHANGE)[CORRELATION] FUNCTIONAL:' in self.data:
            exch, corr = self.data.split(' (EXCHANGE)[CORRELATION] FUNCTIONAL:', 1)[-1].split("\n", 1)[0].split(')[')
            exch = exch.replace("(", "")
            corr = corr.replace("]", "")
            try:
                self.info['H_types'].append(hamiltonian_parts[exch]['type'])
                exch = hamiltonian_parts[exch]['name']
            except KeyError: self.warning( 'Unknown potential: %s' % exch )
            try:
                if not hamiltonian_parts[corr]['type'] in self.info['H_types']:
                    self.info['H_types'].append(hamiltonian_parts[corr]['type'])
                corr = hamiltonian_parts[corr]['name']
            except KeyError: self.warning( 'Unknown potential: %s' % corr )

            if exch == 'PBE_GGA' and corr == 'PBE_GGA':
                self.info['H'] = 'PBE'
            elif exch == 'PBESOL_GGA' and corr == 'PBESOL_GGA':
                self.info['H'] = 'PBEsol'
            else:
                self.info['H'] = "%s/%s" % (exch, corr)

        elif '\n THE CORRELATION FUNCTIONAL ' in self.data:
            corr = self.data.split('\n THE CORRELATION FUNCTIONAL ', 1)[-1].split("\n", 1)[0].replace("IS ACTIVE", "").strip()
            name = corr
            try:
                name = hamiltonian_parts[corr]['name']
                self.info['H_types'].append(hamiltonian_parts[corr]['type'])
            except KeyError: self.warning( 'Unknown potential: %s' % corr )
            self.info['H'] = "%s (pure corr.)" % name

        elif '\n THE EXCHANGE FUNCTIONAL ' in self.data:
            exch = self.data.split('\n THE EXCHANGE FUNCTIONAL ', 1)[-1].split("\n", 1)[0].replace("IS ACTIVE", "").strip()
            name = exch
            try:
                name = hamiltonian_parts[exch]['name']
                self.info['H_types'].append(hamiltonian_parts[exch]['type'])
            except KeyError: self.warning( 'Unknown potential: %s' % exch )
            self.info['H'] = "%s (pure exch.)" % name

        if '\n HYBRID EXCHANGE ' in self.data:
            self.info['H_types'].append(0x4)
            hyb = self.data.split('\n HYBRID EXCHANGE ', 1)[-1].split("\n", 1)[0].split()[-1]
            hyb = int(math.ceil(float(hyb)))

            if hyb == 25 and self.info['H'] == 'PBE':
                self.info['H'] = 'PBE0'
            elif hyb == 20 and exch == 'B_GGA' and corr == 'LYP_GGA':
                self.info['H'] = 'B3LYP'
            elif hyb == 20 and exch == 'B_GGA' and corr == 'PW_GGA':
                self.info['H'] = 'B3PW'
            else:
                h = self.info['H'].split('/')
                h[0] += " (+" + str(hyb) + "%HF)"
                self.info['H'] = '/'.join( h )

        if not self.info['H']:
            self.warning( 'Potential not found!' )
            self.info['H'] = "unknown"

        # Spin part
        if ' TYPE OF CALCULATION :  UNRESTRICTED OPEN SHELL' in self.data:
            self.info['spin'] = True
            if '\n ALPHA-BETA ELECTRONS LOCKED TO ' in self.data:
                spin_info = self.data.split('\n ALPHA-BETA ELECTRONS LOCKED TO ', 1)[-1].split("\n", 1)[0].replace('FOR', '').split()
                cyc = int(spin_info[1])
                if self.ncycles:
                    if self.ncycles[0] < cyc:
                        self.info['lockstate'] = int( spin_info[0] )

        # K-points part
        if '\n SHRINK. FACT.(MONKH.) ' in self.data:
            kset = self.data.split('\n SHRINK. FACT.(MONKH.) ', 1)[-1].split()
            if len(kset) < 4: self.warning( 'Unknown k-points format!' )
            self.info['k'] = "x".join( kset[:3] )

        # Perturbation part
        if "* *        COUPLED-PERTURBED KOHN-SHAM CALCULATION (CPKS)         * *" in self.data:
            self.info['techs'].append('perturbation: analytical')
        elif "\n F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F F\n" in self.data:
            self.info['techs'].append('perturbation: numerical')

        # Tolerances part
        if 'COULOMB OVERLAP TOL         (T1)' in self.data:
            t = []
            t.append( int( self.data.split('COULOMB OVERLAP TOL         (T1)', 1)[-1].split("\n", 1)[0].split('**')[-1] ) )
            t.append( int( self.data.split('COULOMB PENETRATION TOL     (T2)', 1)[-1].split("\n", 1)[0].split('**')[-1] ) )
            t.append( int( self.data.split('EXCHANGE OVERLAP TOL        (T3)', 1)[-1].split("\n", 1)[0].split('**')[-1] ) )
            t.append( int( self.data.split('EXCHANGE PSEUDO OVP (F(G))  (T4)', 1)[-1].split("\n", 1)[0].split('**')[-1] ) )
            t.append( int( self.data.split('EXCHANGE PSEUDO OVP (P(G))  (T5)', 1)[-1].split("\n", 1)[0].split('**')[-1] ) )
            for n, i in enumerate(t):
                if i>0:
                    self.warning( 'Tolerance T%s > 0, assuming default.' % n )
                    if n==4: t[n] = -12
                    else: t[n] = -6
            #self.info['tol'] = "biel.intgs 10<sup>" + ",".join(map(str, t)) + "</sup>"
            self.info['techs'].append("biel.intgs 10<sup>" + ",".join(map(str, t)) + "</sup>") # TODO!!!

        # Speed-up techniques part
        if '\n WEIGHT OF F(I) IN F(I+1)' in self.data:
            f = int( self.data.split('\n WEIGHT OF F(I) IN F(I+1)', 1)[-1].split('%', 1)[0] )
             # TODO CRYSTAL14 default fmixing!
            if   0<f<=25: self.info['techs'].append('mixing<25%')
            elif 25<f<=50:self.info['techs'].append('mixing 25-50%')
            elif 50<f<=75:self.info['techs'].append('mixing 50-75%')
            elif 75<f<=90:self.info['techs'].append('mixing 75-90%')
            elif 90<f:    self.info['techs'].append('mixing>90%')

        if ' ANDERSON MIX: BETA= ' in self.data:
            self.info['techs'].append('mixing by anderson')

        if '\n % OF FOCK/KS MATRICES MIXING WHEN BROYDEN METHOD IS ON' in self.data:
            # mixing percentage, parameter and number of activation cycle
            f = int( self.data.split('\n % OF FOCK/KS MATRICES MIXING WHEN BROYDEN METHOD IS ON', 1)[-1].split("\n", 1)[0] )
            f2 = float( self.data.split('\n WO PARAMETER(D.D. Johnson, PRB38, 12807,(1988)', 1)[-1].split("\n", 1)[0] )
            f3 = int( self.data.split('\n NUMBER OF SCF ITERATIONS AFTER WHICH BROYDEN METHOD IS ACTIVE', 1)[-1].split("\n", 1)[0] )
            if    0<f<=25: type='broyden<25%'
            elif 25<f<=50: type='broyden 25-50%'
            elif 50<f<=75: type='broyden 50-75%'
            elif 75<f<=90: type='broyden 75-90%'
            elif 90<f:     type='broyden>90%'
            if round(f2, 4) == 0.0001: type += ' (std.)' # broyden parameter
            else: type += ' ('+str(round(f2, 5))+')'
            if f3 < 5: type += ' start'
            else: type += ' defer.'
            self.info['techs'].append(type)

        if '\n EIGENVALUE LEVEL SHIFTING OF ' in self.data:
            f = float( self.data.split('\n EIGENVALUE LEVEL SHIFTING OF ', 1)[-1].split("\n", 1)[0].replace('HARTREE', '') )
            if     0<f<=0.5:self.info['techs'].append('shifter<0.5au')
            elif 0.5<f<=1:  self.info['techs'].append('shifter 0.5-1au')
            elif   1<f<=2.5:self.info['techs'].append('shifter 1-2.5au')
            elif 2.5<f:     self.info['techs'].append('shifter>2.5au')

        if '\n FERMI SMEARING - TEMPERATURE SMEARING OF FERMI SURFACE ' in self.data:
            f = float( self.data.split('\n FERMI SMEARING - TEMPERATURE SMEARING OF FERMI SURFACE ', 1)[-1].split("\n", 1)[0] )
            self.info['smear'] = f
            self.info['smeartype'] = 'Mermin'
            if       0<f<=0.005:self.info['techs'].append('smearing<0.005au')
            elif 0.005<f<=0.01: self.info['techs'].append('smearing 0.005-0.01au')
            elif  0.01<f:       self.info['techs'].append('smearing>0.01au')

    def get_duration(self):
        starting = self.patterns['starting'].search(self.data)
        ending = self.patterns['ending'].search(self.data)
        if ending is None and self.properties_calc: ending = self.patterns['ending'].search(self.pdata)
        if starting is not None and ending is not None:
            starting = starting.group(1).replace("DATE", "").replace("TIME", "").strip()[:-2]
            ending = ending.group(1).replace("DATE", "").replace("TIME", "").strip()[:-2]

            start = time.strptime(starting, "%d %m %Y  %H:%M:%S")
            end = time.strptime(ending, "%d %m %Y  %H:%M:%S")
            duration = "%2.2f" % (  (time.mktime(end) - time.mktime(start))/3600  )
        else:
            duration = None
        return duration

    def get_convergence(self):
        if self.info['input'] is not None and "ONELOG" in self.info['input']:
            self.warning("ONELOG keyword is not supported!")
            return [], [], []
        convergdata = []
        ncycles = []
        energies = []
        criteria = [[], [], [], []]
        tresholds = []
        zpcycs = self.patterns['cyc'].findall(self.data)
        if zpcycs is not None:
            for i in zpcycs:
                numdata = i.split(" DETOT ")
                num = numdata[1].split()
                try: f = float(num[0]) * Hartree
                except ValueError: f = 0
                if f != 0 and not math.isnan(f): convergdata.append(   int( math.floor( math.log( abs( f ), 10 ) ) )   )
        else: self.warning( 'SCF not found!' )

        enes = self.patterns['enes'].findall(self.data)
        if enes is not None:
            for i in enes:
                i = i.replace("DFT)(AU)(", "").replace("HF)(AU)(", "").split(")")
                s = i[0]
                if "*" in s: s=1000
                else: s=int(s)
                ncycles.append(s)
                ene = i[1].split("DE")[0].strip()
                try: ene = float(ene) * Hartree
                except ValueError: ene = None
                energies.append(ene)
        n = 0
        for cr in [self.patterns['k1'], self.patterns['k2'], self.patterns['k3'], self.patterns['k4']]:
            kd = cr.findall(self.data)
            if kd is not None:
                for i in kd:
                    p = i.split("THRESHOLD")
                    p2 = p[1].split("CONVERGED")
                    try: k = float(p[0]) - float(p2[0])
                    except ValueError: k=999
                    if k<0: k=0
                    criteria[n].append(k)
                n += 1
        #print len(criteria[0]), len(criteria[1]), len(criteria[2]), len(criteria[3]), len(energies)
        # ORDER of values: geometry, then energy, then tolerances
        if criteria[-1]:
            if len(criteria[0]) - len(criteria[2]) == 1 and len(criteria[1]) - len(criteria[3]) == 1: # if no restart, then 1st cycle has no treshold k3 and k4
                criteria[2].insert(0, 0)
                criteria[3].insert(0, 0)
            if len(criteria[0]) - len(criteria[2]) == 2 and len(criteria[1]) - len(criteria[3]) == 2: # convergence achieved without k3 and k4 at the last cycle
                criteria[2].insert(0, 0)
                criteria[2].append(criteria[2][-1])
                criteria[3].insert(0, 0)
                criteria[3].append(criteria[3][-1])
            if len(criteria[0]) - len(energies) == 1: # ??
                self.warning( 'Energy was not printed at intermediate step, so the correspondence is partly lost (tried to fix)!' )
                energies.insert(0, energies[0])
                ncycles.insert(0, ncycles[0])
            if len(criteria[1]) - len(criteria[2]) > 1: # ??
                raise RuntimeError( 'Number of tresholds during optimization is inconsistent!' )
            for i in range(0, len(criteria[0])):
                tresholds.append([ criteria[0][i], criteria[1][i], criteria[2][i], criteria[3][i], energies[i] ])
        return convergdata, ncycles, tresholds

    def get_zpe(self):
        if "\n E0            :" in self.data:
            zpe = self.data.split("\n E0            :")[1].split("\n", 1)[0].split()[0] # AU
            try: zpe = float(zpe)
            except ValueError: return None
            else: return zpe * Hartree
        else: return None

    def get_td(self):
        td = {'t':[], 'pv':[], 'ts':[], 'et':[]}
        t = self.patterns['T'].findall(self.data)
        if t is not None:
            for i in t:
                td['t'].append(float(i.split('K,')[0]))
        pv = self.patterns['pv'].findall(self.data)
        if pv is not None:
            for i in pv:
                td['pv'].append(float(i.split()[0])) # AU/CELL
        ts = self.patterns['ts'].findall(self.data)
        if ts is not None:
            for i in ts:
                i = i.split()[0]
                try:
                    i = float(i)
                    if math.isnan(i): i = 0.0
                except ValueError: i = 0.0
                td['ts'].append(float(i)) # AU/CELL
        et = self.patterns['et'].findall(self.data)
        if et is not None:
            for i in et:
                i = i.split()[0]
                try:
                    i = float(i)
                    if math.isnan(i): i = 0.0
                except ValueError: i = 0.0
                td['et'].append(float(i)) # AU/CELL
        if td['t'] and td['pv'] and td['ts'] and td['et']:
            return td
        else:
            self.warning( 'Errors in thermodynamics!' )
            return None
