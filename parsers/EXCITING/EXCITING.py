
# tilda project: EXCITING calculations parser
# v250913

import os
import sys
import math

from lxml import etree

from ase.lattice.spacegroup.cell import cell_to_cellpar
from ase.units import Bohr, Hartree
from ase import Atoms

from parsers import Output
from core.electron_structure import Edos, Ebands

# INFO.OUT parser

class INFOOUT(Output):
    def __init__(self, file, **kwargs):
        Output.__init__(self, file)
        self.data = open(file).readlines()
        
        cur_folder = os.path.dirname(file)
        
        self.info['finished'] = -1
        
        fracts_holder = [[]]
        cell = []
        forces, energies, energies_opt, optmethods = [], [], [], []
        
        first_cycle_lithium, opt_flag = True, False
        
        H_mapping = {
        1: 'pure HF',
        3: 'LSDAPerdew-Wang',
        22: 'PBEsol',
        20: 'PBE-GGA/PBE-GGA',
        100:'PBE-GGA/PBE-GGA'
        }
        
        for n in range(len(self.data)):
            line = self.data[n]
            if ' EXCITING ' in line:
                if 'started' in line:
                    version = line.split()[2].capitalize()
                    if version not in ['Helium', 'Lithium', 'Beryllium']: raise RuntimeError("This Exciting version is currently not supported!")
                    self.info['prog'] = 'Exciting ' + version
                #elif 'stopped' in line:
                #   self.info['finished'] = 1
                    
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
                while 1:                    
                    n += 1
                    if 'atomic positions (lattice)' in self.data[n]:
                        while 1:
                            n += 1
                            a = self.data[n].split()
                            try: int(a[0])
                            except (ValueError, IndexError): break
                            else:
                                fracts_holder[-1].append([symb])
                                fracts_holder[-1][-1].extend( map(float, [a[2], a[3], a[4]]) )
                        break
                    #elif 'muffin-tin radius' in self.data[n]:
                
            elif 'Spin treatment ' in line:
                mark = line.split(":")[-1].strip()
                if len(mark): # Beryllium
                    if 'spin-polarised' in mark:
                        self.method['spin'] = True
                        if 'orbit coupling' in self.data[n+1]: self.method['technique'].update({'spin-orbit':True})
                        
                else: # Lithium
                    if 'spin-polarised' in self.data[n+1]:
                        self.method['spin'] = True
                        if 'orbit coupling' in self.data[n+2]: self.method['technique'].update({'spin-orbit':True})
                
            elif 'k-point grid ' in line:
                self.method['k'] = "x".join(line.split(":")[-1].split())
                
            elif 'Smallest muffin-tin radius times maximum |G+k|' in line: # Lithium
                self.method['tol'] = 'rkmax %s' % float(line.split(":")[-1].strip())
                
            elif 'R^MT_min * |G+k|_max (rgkmax)' in line: # Beryllium
                self.method['tol'] = 'rkmax %s' % float(line.split(":")[-1].strip())
                
            elif 'orrelation type :' in line:
                
                #if 'Correlation type :' in line:                   
                #if 'Exchange-correlation type :' in line:                  
                
                h = int(line.split(":")[-1])
                try: self.method['H'] = H_mapping[h]
                except KeyError: self.method['H'] = h
                
            elif 'otal energy               ' in line:
                try: energies.append(  float(line.split(":")[-1]) * Hartree  )
                except ValueError: energies.append(0.0)

            elif 'Structure-optimization module started' in line:
                opt_flag = True
                # First cycle convergence statuses
                for n in range(len(energies)):
                    try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
                    except IndexError: pass
                self.ncycles.append(len(self.convergence))              
                
            elif '| Updated atomic positions ' in line: # Lithium
                fracts_holder.append([])
                
                if first_cycle_lithium:
                    # First cycle convergence statuses
                    for n in range(len(energies)):
                        try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
                        except IndexError: pass
                    first_cycle_lithium = False             
            
            elif '| Optimization step ' in line: # Beryllium
                self.info['finished'] = -1
                fracts_holder.append([])
                optmethods.append(line.split('method =')[-1][:-2])
                while 1:
                    n += 1
                    
                    try: self.data[n]
                    except IndexError:
                        fracts_holder.pop()
                        optmethods.pop()
                        break
                    
                    if ' scf iterations ' in self.data[n]:
                        self.ncycles.append(  int(self.data[n].split(":")[-1].split()[0])  )
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
                                fracts_holder[-1].append([a[2]])
                                fracts_holder[-1][-1].extend( map(float, a[4:]) )
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
                
            #elif line.startswith(' Fermi '):
            #    e_last = float(self.data[n].split(":")[-1]) * Hartree
                
            elif 'Number of empty states' in line:
                self.method['technique'].update({ 'empty_states': int(self.data[n].split(":")[-1]) })
        
        if not cell or not fracts_holder[-1]: raise RuntimeError("Structure not found!")
        
        if energies_opt: self.energy = energies_opt[-1]
        else:
            try: self.energy = energies[-1]
            except IndexError: pass
        
        if not self.convergence:
            # First cycle convergence statuses
            for n in range(len(energies)):
                try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
                except (IndexError, ValueError): pass
        
        if len(forces) != len(energies_opt) or len(forces) != len(optmethods) or len(forces) != len(self.ncycles): self.warning("Warning! Unexpected convergence data format!")
        else:
            for n in range(len(energies_opt)):
                self.tresholds.append([forces[n], 0.0, 0.0, 0.0, energies_opt[n]])
        
        # special structural case adjusting (WTF?)
        '''if ab_normal == metric(cell[2]):
            # Default `a_direction` is (1,0,0), unless this is parallel to
            # `ab_normal`, in which case default `a_direction` is (0,0,1).
            a_direction = None'''
            
        # lattice is always the same
        for structure in fracts_holder:
            symbols = []
            pos = []
            for a in structure:
                symbols.append(a[0])
                pos.append(a[1:])
            self.structures.append(Atoms(symbols=symbols, cell=cell, scaled_positions=pos, pbc=True))
        
        # Check if convergence achieved right away from the first cycle and account that
        if opt_flag and len(self.structures) == 1:
            self.structures.append(self.structures[-1])
            self.tresholds.append([0.0, 0.0, 0.0, 0.0, energies[-1]])
        
        # Forces
        
        # Warnings
        #try: w = map(lambda x: x.strip(), open(cur_folder + '/WARNINGS.OUT').readlines())
        #except IOError: pass
        #else:
        #   # TODO: Get rid of redundant messages
        #   # Warning(charge)
        #   self.warning( " ".join(w) )
        
        # special slab case
        # account periodicity (vacuum creation method)
        # TODO
        cellpar = cell_to_cellpar( cell ).tolist()
        if cellpar[2] > 2 * cellpar[0] * cellpar[1]:
            self.method['technique'].update({'vacuum2d': int(round(cellpar[2]))})
            for i in range(len(self.structures)):
                self.structures[i].set_pbc((True, True, False))
                    
        # Electronic properties
        if os.path.exists(os.path.join(os.path.dirname(file), 'dos.xml')):
            f = open(os.path.join(os.path.dirname(file), 'dos.xml'),'r')
            self.electrons['dos'] = Edos(parse_dosxml(f, self.structures[-1].get_chemical_symbols()))
            f.close()
            
        if os.path.exists(os.path.join(os.path.dirname(file), 'bandstructure.xml')):
            f = open(os.path.join(os.path.dirname(file), 'bandstructure.xml'),'r')
            self.electrons['bands'] = Ebands(parse_bandsxml(f))
            f.close()
        
    @staticmethod
    def fingerprints(test_string):
        if test_string.startswith('All units are atomic (Hartree, Bohr, etc.)') or test_string.startswith('| All units are atomic (Hartree, Bohr, etc.)'): return True
        else: return False


def parse_dosxml(fp, symbols):
    dos_obj = {'x': [],}
    dos = []
    symbol_counter = 0
    first_cyc, new_part = True, True
        
    context = etree.iterparse(fp, events=('end',))
    
    for action, elem in context:
        if elem.tag=='totaldos':
            if len(dos) != len(dos_obj['x']): raise RuntimeError("Data in dos.xml are mismatched!")
            dos_obj['total'] = dos
            dos, new_part = [], True
            
        elif elem.tag=='partialdos':
            target_atom = elem.attrib['speciessym']
            if not target_atom:
                target_atom = symbols[symbol_counter]
                symbol_counter += 1
            if not target_atom in dos_obj: dos_obj[target_atom] = dos
            else:
                if len(dos) != len(dos_obj[target_atom]): raise RuntimeError("Unexpected data format in dos.xml!")
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
        while elem.getprevious() is not None:
            del elem.getparent()[0] # delete previous siblings; make sure there are no references to Element objects outside the loop!
            
    return dos_obj
    
def parse_bandsxml(fp):
    band_obj = {'ticks': [], 'abscissa': [], 'stripes': [[],]}
    first_cyc = True
    
    context = etree.iterparse(fp, events=('end',))
    
    for action, elem in context:
        if elem.tag=='band':
            band_obj['stripes'].append([])          
            first_cyc = False
            
        elif elem.tag=='point':
            if first_cyc: band_obj['abscissa'].append( float(elem.attrib['distance']) )
            band_obj['stripes'][-1].append(float(elem.attrib['eval']) * Hartree)
            
        elif elem.tag=='vertex':
            band_obj['ticks'].append( [ float(elem.attrib['distance']), elem.attrib['label'] ] ) # NB : elem.attrib['coord']
                        
        elem.clear()
        while elem.getprevious() is not None:
            try: del elem.getparent()[0] # delete previous siblings; make sure there are no references to Element objects outside the loop!
            except TypeError: break
    
    if band_obj['ticks'][0][0] != band_obj['abscissa'][0] or band_obj['ticks'][-1][0] != band_obj['abscissa'][-1]: raise RuntimeError("Unexpected data format in bandstructure.xml!")
    band_obj['stripes'].pop() # last []
        
    return band_obj
