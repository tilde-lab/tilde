
# Tilde project: EXCITING text logs and XML outputs parser
# v140714

import os
import sys
import math
from fractions import Fraction

from xml.etree import ElementTree as ET
import xml.dom.minidom

from ase.units import Bohr, Hartree
from ase import Atoms

from numpy import dot
from numpy import array
from numpy import transpose
from numpy import linalg

from parsers import Output
from core.electron_structure import Edos, Ebands
from core.constants import Constants


# Non-critical parsing exception
class SecondaryParsingError(Exception):
    def __init__(self, value):
        self.value = value

# INFO.OUT parser
class INFOOUT(Output):
    def __init__(self, file, **kwargs):
        Output.__init__(self, file)

        cur_folder = os.path.dirname(file)

        self.info['framework'] = 'EXCITING'
        self.info['finished'] = -1

        # dealing with replicas of INFO.OUT (e.g. in case of phonons) means
        # we need to match corresponding EIGVAL.OUT, xmls etc. for them
        # (not implemented yet)
        if os.path.basename(file) == 'INFO.OUT': INITIAL_CALC = True
        else: INITIAL_CALC = False

        cartesian = False

        atoms_holder = [[]]
        cell = []
        forces, energies, energies_opt = [], [], []
        rmts, mtrps, bsseq = [], [], []
        specienum = 0
        first_cycle_lithium, opt_flag = True, False

        # TODO: relate with schema file?
        H_mapping = {
        1: 'pure HF',
        3: 'LSDAPerdew-Wang',
        22: 'PBEsol',
        20: 'PBE-GGA/PBE-GGA',
        100:'PBE-GGA/PBE-GGA'
        }

        self.data = open(file).readlines()

        # Main loop begin
        for n in range(len(self.data)):
            line = self.data[n]
            if ' EXCITING ' in line:
                if 'started' in line:
                    version = line.split()[2].capitalize()
                    if version not in ['Helium', 'Lithium', 'Beryllium', 'Mortadella', 'Boron']: raise RuntimeError("This Exciting version is currently not supported!")
                    self.info['prog'] = 'Exciting ' + version

            elif 'Convergence targets achieved' in line:
                if not energies_opt: self.info['finished'] = 1

            elif 'Force convergence target achieved' in line:
                self.info['finished'] = 1

            elif 'Lattice vectors' in line:
                for i in range(n+1, n+4):
                    cell.append(  map(lambda x: float(x) * Bohr, self.data[i].split())  )
                n += 3

            elif 'Species : ' in line:
                symb = line.split('(')[-1][:-2].encode('ascii')
                nrepeat = 0
                while 1:
                    n += 1
                    if 'muffin-tin radius' in self.data[n]:
                        rmt = float( self.data[n].split(":")[-1].strip() )
                    elif 'of radial points in muffin-tin' in self.data[n]:
                        mtrp = int( self.data[n].split(":")[-1].strip() )
                    elif 'atomic positions (' in self.data[n]:
                        if not cartesian:
                            if not 'lattice' in self.data[n]: cartesian = True
                        while 1:
                            n += 1
                            a = self.data[n].split()
                            try: int(a[0])
                            except (ValueError, IndexError): break
                            else:
                                atoms_holder[-1].append([symb])
                                atoms_holder[-1][-1].extend( map(float, [a[2], a[3], a[4]]) )
                                nrepeat += 1                                
                        break
                if not energies: # do it only for the first structure!
                    rmts.extend([rmt] * nrepeat)
                    mtrps.extend([mtrp] * nrepeat)
                    bsseq.extend([specienum] * nrepeat)
                    specienum += 1

            elif 'Spin treatment ' in line:
                mark = line.split(":")[-1].strip()
                if len(mark): # Beryllium
                    if 'spin-polarised' in mark:
                        self.info['spin'] = True
                        if 'orbit coupling' in self.data[n+1]: self.info['techs'].append('spin-orbit coupling')

                else: # Lithium
                    if 'spin-polarised' in self.data[n+1]:
                        self.info['spin'] = True
                        if 'orbit coupling' in self.data[n+2]: self.info['techs'].append('spin-orbit coupling')

            elif 'k-point grid ' in line:
                self.info['k'] = "x".join(line.split(":")[-1].split())

            elif 'Smallest muffin-tin radius times maximum |G+k|' in line: # Lithium
                self.electrons['rgkmax'] = float(line.split(":")[-1].strip())

            elif 'R^MT_min * |G+k|_max (rgkmax)' in line: # Beryllium
                self.electrons['rgkmax'] = float(line.split(":")[-1].strip())

            elif 'Smearing scheme ' in line:
                t = line.split(":")[-1].strip()
                if len(t): self.info['smeartype'] = t
                else: self.info['smeartype'] = self.data[n+1].split(":")[-1].strip()

            elif 'Smearing width ' in line:
                self.info['smear'] = float(line.split(":")[-1].strip())

            elif 'orrelation type ' in line:

                #if 'Correlation type :' in line:
                #if 'Exchange-correlation type :' in line:
                #if 'Exchange-correlation type' in line:

                try: h = int(line.split(":")[-1])
                except ValueError: pass # then this is not what we want
                try: self.info['H'] = H_mapping[h]
                except KeyError: self.info['H'] = h

            elif 'otal energy               ' in line:
                try: energies.append(  float(line.split(":")[-1]) * Hartree  )
                except ValueError: energies.append(0.0)

            elif 'Structure-optimization module started' in line:
                opt_flag = True
                # First cycle convergence statuses
                self.info['convergence'] = self.compare_vals(energies)
                self.info['ncycles'].append(len(self.info['convergence']))

            elif '| Updated atomic positions ' in line: # Lithium
                atoms_holder.append([])

                if first_cycle_lithium:
                    # First cycle convergence statuses
                    self.info['convergence'] = self.compare_vals(energies)
                    first_cycle_lithium = False

            elif '| Optimization step ' in line: # Beryllium
                self.info['finished'] = -1
                atoms_holder.append([])
                while 1:
                    n += 1

                    try: self.data[n]
                    except IndexError:
                        atoms_holder.pop()
                        break

                    if ' scf iterations ' in self.data[n]:
                        self.info['ncycles'].append(  int(self.data[n].split(":")[-1].split()[0])  )
                    elif 'Maximum force magnitude' in self.data[n]:
                        f = self.data[n].split(":")[-1].split("(")
                        forces.append( float(f[0]) - float(f[-1][:-2]) )
                    elif 'Total energy' in self.data[n]:
                        try: energies_opt.append(  float(self.data[n].split(":")[-1]) * Hartree  )
                        except ValueError: energies_opt.append(0.0)
                    elif 'Atomic positions' in self.data[n]:
                        while 1:
                            n += 1
                            if 'atom' in self.data[n]:
                                a = self.data[n].split()
                                atoms_holder[-1].append([a[2]])
                                atoms_holder[-1][-1].extend( map(float, a[4:]) )
                            else: break
                        break

            elif 'Timings (CPU seconds) ' in line: # Lithium
                while 1:
                    n += 1
                    if ' total ' in self.data[n]:
                        self.info['duration'] = "%2.2f" % (float(self.data[n].split(":")[-1])/3600)
                        break
                    elif len(self.data[n]) < 4: break
                self.info['duration']

            elif 'Total time spent ' in line: # Beryllium
                self.info['duration'] = "%2.2f" % (float(self.data[n].split(":")[-1])/3600)

            elif line.startswith(' Fermi '):
                try: e_last = float(self.data[n].split(":")[-1]) * Hartree
                except ValueError: raise RuntimeError("Fermi energy is out of physical bounds! Terminating.")

            elif 'Number of empty states' in line:
                self.info['techs'].append( '%s empty states' % int(self.data[n].split(":")[-1]) )
        # Main loop end

        if not cell or not atoms_holder[-1]: raise RuntimeError("Structure not found!")

        if energies_opt: self.info['energy'] = energies_opt[-1]
        else:
            try: self.info['energy'] = energies[-1]
            except IndexError: pass

        if not self.info['convergence']:
            # First cycle convergence statuses
            self.info['convergence'] = self.compare_vals(energies)

        if len(forces) != len(energies_opt) or len(forces) != len(self.info['ncycles']): self.warning("Warning! Unexpected convergence data format!")
        else:
            for n in range(len(energies_opt)):
                self.info['tresholds'].append([forces[n], 0.0, 0.0, 0.0, energies_opt[n]])

        # NB lattice is always the same
        for structure in atoms_holder:
            symbols = []
            pos = []
            for a in structure:
                symbols.append(a[0])
                pos.append(a[1:])
            if cartesian: self.structures.append(Atoms(symbols=symbols, cell=cell, positions=pos, pbc=True))
            else: self.structures.append(Atoms(symbols=symbols, cell=cell, scaled_positions=pos, pbc=True))

        # Check if convergence achieved right away from the first cycle and account that
        if opt_flag and len(self.structures) == 1:
            self.structures.append(self.structures[-1])
            self.info['tresholds'].append([0.0, 0.0, 0.0, 0.0, energies[-1]])
        
        self.structures[-1].new_array('rmt', rmts, float)
        self.structures[-1].new_array('mtrp', mtrps, int)
        self.structures[-1].new_array('bs', bsseq, int)

        # Warnings
        #try: w = map(lambda x: x.strip(), open(cur_folder + '/WARNINGS.OUT').readlines())
        #except IOError: pass
        #else:
        #   # TODO: Get rid of redundant messages
        #   # Warning(charge)
        #   self.warning( " ".join(w) )

        # Electronic properties: the best case, too good
        if INITIAL_CALC:
            # look for full DOS in xml
            if os.path.exists(os.path.join(cur_folder, 'dos.xml')):
                f = open(os.path.join(cur_folder, 'dos.xml'),'r')
                try: self.electrons['dos'] = Edos(parse_dosxml(f, self.structures[-1].get_chemical_symbols()))
                except SecondaryParsingError as e: self.warning("Error in dos.xml file: %s" % e.value)
                except: self.warning("Problems with parsing dos.xml!")
                finally: f.close()

            # look for interpolated bands in xml
            if os.path.exists(os.path.join(cur_folder, 'bandstructure.xml')):
                f = open(os.path.join(cur_folder, 'bandstructure.xml'),'r')
                try: self.electrons['bands'] = Ebands(parse_bandsxml(f))
                except SecondaryParsingError as e: self.warning("Error in bandstructure.xml file: %s" % e.value)
                except: self.warning("Problems with parsing bandstructure.xml!")
                finally: f.close()

        # Electronic properties: the worst case, look for total DOS and raw bands in EIGVAL.OUT
        if os.path.exists(os.path.join(cur_folder, 'EIGVAL.OUT')) and (not self.electrons['dos'] or not self.electrons['bands']) and INITIAL_CALC: # TODO: account all the dispacements
            f = open(os.path.join(cur_folder, 'EIGVAL.OUT'),'r')
            # why such a call? we try to spare RAM
            # so let's look whether these variables are filled
            # and fill them only if needed
            try: kpts, columns = parse_eigvals(f, e_last)
            except SecondaryParsingError as e: self.warning("Error in EIGVAL.OUT file: %s" % e.value)
            else:
                # obviously below should repeat XML data (but note interpolation problems on small k-sets!)
                if not self.electrons['dos']:
                    self.warning("dos.xml is absent, EIGVAL.OUT is taken")
                    for c in columns:
                        for i in c:
                            self.electrons['projected'].append(i)
                    self.electrons['projected'].sort()

                if not self.electrons['bands']:
                    self.warning("bandstructure.xml is absent, EIGVAL.OUT is taken")
                    band_obj = {'ticks': [], 'abscissa': [], 'stripes': []}
                    d = 0.0
                    bz_vec_ref = [0, 0, 0]
                    for k in kpts:
                        bz_vec_cur = dot( k, linalg.inv( self.structures[-1].cell ).transpose() )
                        bz_vec_dir = map(sum, zip(bz_vec_cur, bz_vec_ref))
                        bz_vec_ref = bz_vec_cur
                        d += linalg.norm( bz_vec_dir )
                        band_obj['abscissa'].append(d)
                    band_obj['stripes'] = transpose(columns).tolist()
                    self.electrons['bands'] = Ebands(band_obj)

            finally: f.close()

        if not self.electrons['dos'] and not self.electrons['bands']: self.warning("Electron structure not found!")
        self.electrons['type'] = 'FPLAPW'

        # Input
        if INITIAL_CALC:
            try: inp = xml.dom.minidom.parse(os.path.join(cur_folder, 'input.xml'))
            except: self.warning("Problems with parsing input.xml!")
            else:
                speciespath = inp.getElementsByTagName("structure")[0].attributes['speciespath'].value
                relpath_flag = False if os.path.isabs(speciespath) else True
                species_types = set()
                self.electrons['basis_set'] = []
                
                for sp in inp.getElementsByTagName("species"):
                    species_types.add(sp.attributes['speciesfile'].value)
                for sp in species_types:
                    # TODO: https://docs.python.org/2/library/xml.html#xml-vulnerabilities
                    try_path = os.path.realpath( os.path.join(cur_folder, os.path.join(speciespath, sp)) ) if relpath_flag else os.path.join(speciespath, sp) # WARNING! This may be dangerous!
                    if not os.path.exists(try_path):
                        self.electrons['basis_set'] = None
                        self.warning("No BS available: %s cannot be found!" % try_path)
                        break
                    else:
                        try: self.electrons['basis_set'] += [ parse_specie(try_path) ]
                        except SecondaryParsingError as e:
                            self.electrons['basis_set'] = None
                            self.warning("Error in specie file: %s" % e.value)

                self.info['input'] = inp.toprettyxml(newl="", indent=" ")

        # Phonons
        if os.path.exists(os.path.join(cur_folder, 'PHONON.OUT')) and INITIAL_CALC: # TODO: account all the dispacements
            f = open(os.path.join(cur_folder, 'PHONON.OUT'), 'r')
            linelist = f.readlines()
            filelen = len(linelist)
            n_at = len(self.structures[-1])
            n_line = 0
            while n_line < filelen:
                n_line += 1
                modes, irreps, ph_eigvecs = [], [], []
                k_coords = " ".join(  map(lambda x: "%s" % Fraction(x), linelist[n_line].split()[1:4])  ) # TODO : find weight of every symmetry k-point!

                # next line is empty
                n_line += 2
                for i in range(n_at*3):

                    # read mode number and frequency
                    modes.append( float(linelist[n_line].split()[1]) * Constants.ha2rcm )
                    irreps.append("")
                    n_line += 1

                    # read eigenvectors
                    container = []
                    for atom in range(n_at):
                        for disp in range(3):
                            try: container.append( float(linelist[n_line].split()[3]) )
                            except ValueError: container.append(0.0)
                            #float(linelist[n_line].split()[4])
                            n_line += 1

                    ph_eigvecs.append(container)

                    # two empty lines follow
                    n_line +=1

                self.phonons['modes'][ k_coords ] = modes
                self.phonons['irreps'][ k_coords ] = irreps
                self.phonons['ph_eigvecs'][ k_coords ] = ph_eigvecs

            f.close()

            kset = self.phonons['modes'].keys()
            if kset > 1:
                for i in kset:
                    self.phonons['ph_k_degeneracy'][ i ] = 1 # TODO : find weight of every symmetry k-point!

    def compare_vals(self, vals):
        cmp = []
        for n in range(len(vals)):
            try: cmp.append( int( math.floor( math.log( abs( vals[n] - vals[n+1] ), 10 ) ) )  )
            except (IndexError, ValueError): pass # beware log math domain error when the adjacent values are the same
        return cmp

    @staticmethod
    def fingerprints(test_string):
        if test_string.startswith('All units are atomic (Hartree, Bohr, etc.)') or test_string.startswith('| All units are atomic (Hartree, Bohr, etc.)'): return True
        else: return False

# dos.xml parser
def parse_dosxml(fp, symbols):
    dos_obj = {'x': [],}
    dos = []
    symbol_counter = 0
    first_cyc, new_part = True, True

    for action, elem in ET.iterparse(fp, events=('end',)):
        if elem.tag=='totaldos':
            if len(dos) != len(dos_obj['x']): raise SecondaryParsingError("Data in dos.xml are mismatched!")
            dos_obj['total'] = dos
            dos, new_part = [], True

        elif elem.tag=='partialdos':
            target_atom = elem.attrib['speciessym']
            if not target_atom:
                target_atom = symbols[symbol_counter]
                symbol_counter += 1
            if not target_atom in dos_obj: dos_obj[target_atom] = dos
            else:
                if len(dos) != len(dos_obj[target_atom]): raise SecondaryParsingError("Unexpected data format in dos.xml!")
                dos_obj[target_atom] = [sum(s) for s in zip( dos_obj[target_atom], dos )]
            dos, new_part = [], True

        elif elem.tag=='interstitialdos':
            dos_obj['interstitial'] = dos
            dos, new_part = [], True

        elif elem.tag=='diagram':
            if not new_part:
                # orbital contributions are merged : TODO
                # spins are merged : TODO
                dos = [sum(s) for s in zip( dos[ : len(dos)/2], dos[len(dos)/2 : ] )]

            #spin = {1: 'alpha', 2: 'beta'}
            #target_spin = spin[ int( elem.attrib['nspin'] ) ]
            #if 'n' in elem.attrib: n = elem.attrib['n']
            #if 'l' in elem.attrib: l = elem.attrib['l']

            first_cyc, new_part = False, False

        elif elem.tag=='point':
            if first_cyc: dos_obj['x'].append( float(elem.attrib['e']) * Hartree  )
            dos.append(float(elem.attrib['dos']))

        elem.clear()

    return dos_obj

# bandstructure.xml parser
def parse_bandsxml(fp):
    band_obj = {'ticks': [], 'abscissa': [], 'stripes': [[],]}
    first_cyc = True

    for action, elem in ET.iterparse(fp, events=('end',)):
        if elem.tag=='band':
            band_obj['stripes'].append([])
            first_cyc = False

        elif elem.tag=='point':
            if first_cyc: band_obj['abscissa'].append( float(elem.attrib['distance']) )
            band_obj['stripes'][-1].append(float(elem.attrib['eval']) * Hartree)

        elif elem.tag=='vertex':
            band_obj['ticks'].append( [ float(elem.attrib['distance']), elem.attrib['label'] ] ) # NB : elem.attrib['coord']

        elem.clear()

    if band_obj['ticks'][0][0] != band_obj['abscissa'][0] or band_obj['ticks'][-1][0] != band_obj['abscissa'][-1]: raise SecondaryParsingError("Unexpected data format in bandstructure.xml!")
    band_obj['stripes'].pop() # last []

    return band_obj

# EIGVAL.OUT parser
def parse_eigvals(fp, e_last):
    kpts = []
    columns = []
    while 1:
        s = fp.readline()
        if not s: break
        s = s.strip()
        if len(s) < 20: # first two lines or section dividers
            if not columns:
                columns.append([])
                continue
            if not columns[-1]:
                continue
            else:
                columns[-1] = map(lambda x: x-e_last, columns[-1])
                columns.append([])
        elif len(s) > 45: # k-point coords
            kpts.append(  map(float, s.split()[1:4])  )
        else:
            try: int(s[0])
            except ValueError: # comment
                continue
            else:
                n, e, occ = s.split()
                columns[-1].append(float(e)*Hartree)
    columns.pop() # last []
    columns = array(columns)
    if columns.ndim != 2: raise SecondaryParsingError('Invalid dimensions of columns!')
    return kpts, columns
    
# species parser
def parse_specie(path):
    azimuthal_numbers = {0:'s', 1:'p', 2:'d', 3:'f', 4:'g', 5:'h'}
    basis = {}
    try: specie = xml.dom.minidom.parse(path)
    except: raise SecondaryParsingError("Unable to parse %s" % path)
    else:
        #elem = specie.getElementsByTagName("sp")[0].attributes['chemicalSymbol'].value
        mt = specie.getElementsByTagName("muffinTin")[0]
        basis['rmin'] = float(mt.attributes['rmin'].value) # innermost grid point (!)
        basis['rmt'] = float(mt.attributes['radius'].value) # default rmt
        basis['rinf'] = float(mt.attributes['rinf'].value) # effective infinity
        basis['rmtp'] = int(mt.attributes['radialmeshPoints'].value) # grid points in the muffin tin (!)
        basis['states'] = []
        for atst in specie.getElementsByTagName("atomicState"):
            basis['states'].append({})
            basis['states'][-1]['n'] = int(atst.attributes['n'].value)
            basis['states'][-1]['l'] = azimuthal_numbers[ int(atst.attributes['l'].value) ]
            basis['states'][-1]['kappa'] = int(atst.attributes['kappa'].value)
            basis['states'][-1]['occ'] = int(float(atst.attributes['occ'].value))
            basis['states'][-1]['is_core'] = True if atst.attributes['core'].value.lower() == 'true' else False        
        basis['default'] = {}
        default = specie.getElementsByTagName("default")[0]
        basis['default']['type'] = default.attributes['type'].value
        basis['default']['trialEnergy'] = float(default.attributes['trialEnergy'].value)
        basis['default']['searchE'] = True if default.attributes['searchE'].value.lower() == 'true' else False
        basis['custom'] = []
        for cstm in specie.getElementsByTagName("custom"):
            basis['custom'].append({})
            basis['custom'][-1]['l'] = azimuthal_numbers[ int(cstm.attributes['l'].value) ]
            basis['custom'][-1]['type'] = cstm.attributes['type'].value
            basis['custom'][-1]['trialEnergy'] = float(cstm.attributes['trialEnergy'].value)            
            basis['custom'][-1]['searchE'] = True if cstm.attributes['searchE'].value.lower() == 'true' else False
        basis['lo'] = []
        for lo in specie.getElementsByTagName("lo"):
            basis['lo'].append([ azimuthal_numbers[ int(lo.attributes['l'].value) ] ])            
            for wf in lo.getElementsByTagName("wf"):
                basis['lo'][-1].append({})
                basis['lo'][-1][-1]['deriv'] = int(wf.attributes['matchingOrder'].value)
                basis['lo'][-1][-1]['trialEnergy'] = float(wf.attributes['trialEnergy'].value)
                basis['lo'][-1][-1]['searchE'] = True if wf.attributes['searchE'].value.lower() == 'true' else False
    return basis
    
