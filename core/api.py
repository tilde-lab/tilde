
# Tilde project: core
# v140714

__version__ = "0.3.0"   # numeric-only, should be the same as at GitHub repo, otherwise a warning is raised

import os
import sys
import math, random
import re
import fractions
import inspect
import traceback
import json

from numpy import dot, array
from numpy.linalg import det

from common import u, is_binary_string, dict2ase, generate_cif, html_formula
from symmetry import SymmetryHandler
from settings import DEFAULT_SETUP, read_hierarchy
from electron_structure import ElectronStructureError
import model

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps'))
from ase.data import chemical_symbols
from ase.lattice.spacegroup.cell import cell_to_cellpar
from sqlalchemy import exists, func

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from parsers import Output


class API:
    version = __version__
    __shared_state = {} # singleton
        
    def __init__(self, session=None, settings=DEFAULT_SETUP):
        self.__dict__ = self.__shared_state
        self.session = session
        self.settings = settings        
        self.hierarchy, self.supercategories = read_hierarchy()
        self.deferred_storage = {}

        # *parser API*
        # Subfolder "parsers" contains directories with parsers.
        # Parser will be active if:
        # (1) its class defines a fingerprints method
        # (2) it is enabled in its manifest file
        # (3) its file name repeats the name of parser folder
        All_parsers, self.Parsers = {}, {}
        for parsername in os.listdir( os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + '/../parsers' ):
            if self.settings['demo_regime']: continue
            
            if not os.path.isfile( os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../parsers/' + parsername + '/manifest.json') ): continue
            if not os.path.isfile( os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../parsers/' + parsername + '/' + parsername + '.py') ):
                raise RuntimeError('Parser API Error: Parser code for ' + parsername + ' is missing!')
            try: parsermanifest = json.loads( open( os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../parsers/' + parsername + '/manifest.json') ).read() )
            except: raise RuntimeError('Parser API Error: Parser manifest for ' + parsername + ' has corrupted format!')
            
            if (not 'enabled' in parsermanifest or not parsermanifest['enabled']) and not self.settings['debug_regime']: continue
            
            All_parsers[parsername] = getattr(getattr(__import__('parsers.' + parsername + '.' + parsername), parsername), parsername) # all imported modules will be stored here
        
        # replace modules by classes and check *fingerprints* method
        for parser, module in All_parsers.iteritems():
            for name, cls in inspect.getmembers(module):
                if inspect.isclass(cls):
                    if inspect.isclass(cls) and hasattr(cls, 'fingerprints'):
                        self.Parsers[cls.__name__] = cls

        # *module API*
        # Tilde module (app) is a subfolder (%appfolder%) of apps folder
        # contains manifest.json and %appfolder%.py files
        # the following tags in manifest.json matter:
        # ((*onprocess* - invoking during processing: therefore %appfolder%.py must provide the class %Appfolder%))
        # *appcaption* - module caption (used as column caption in GUI data table & as atomic structure rendering pane overlay caption)
        # *appdata* - a new property defined by app
        # *apptarget* - conditions on whether an app should be executed, based on hierarchy values
        # *on3d* - app provides the data which may be shown in GUI on atomic structure rendering pane (used only by make3d of daemon.py)
        # *plottable* - column provided may be plotted in GUI
        # NB. GUI (has_column) is supported only if the class %Appfolder% defines cell_wrapper
        self.Apps = {}
        n = 1
        for appname in os.listdir( os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + '/../apps' ):
            if os.path.isfile( os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../apps/' + appname + '/manifest.json') ):
                try: appmanifest = json.loads( open( os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../apps/' + appname + '/manifest.json') ).read() )
                except: raise RuntimeError('Module API Error: Module manifest for ' + appname + ' has corrupted format!')

                # tags processing
                if not 'appdata' in appmanifest: raise RuntimeError('Module API Error: no appdata tag for ' + appname + '!')
                if 'onprocess' in appmanifest:
                    try: app = __import__('apps.' + appname + '.' + appname, fromlist=[appname.capitalize()]) # this means: from foo import Foo
                    except ImportError: raise RuntimeError('Module API Error: module ' + appname + ' is invalid or not found!')
                    self.Apps[appname] = {'appmodule': getattr(app, appname.capitalize()), 'appdata': appmanifest['appdata'], 'apptarget': appmanifest.get('apptarget', None), 'appcaption': appmanifest['appcaption'], 'on3d': appmanifest.get('on3d', 0)}
                    
                    # compiling table columns:
                    if hasattr(self.Apps[appname]['appmodule'], 'cell_wrapper'):
                        self.hierarchy.append( {'cid': (2000+n), 'category': appmanifest['appcaption'], 'sort': (2000+n), 'has_column': True, 'cell_wrapper': getattr(self.Apps[appname]['appmodule'], 'cell_wrapper')}  )
                        if appmanifest.get('plottable', False): self.hierarchy[-1].update({'plottable': 1})
                        n += 1
        
        self.hierarchy = sorted( self.hierarchy, key=lambda x: x['sort'] )

        # *connector API*
        # Every connector implements reading methods:
        # *list* (if applicable) and *report* (obligatory)
        self.Conns = {}
        for connectname in os.listdir( os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + '/../connectors' ):
            if connectname.endswith('.py') and connectname != '__init__.py':
                connectname = connectname[0:-3]
                conn = __import__('connectors.' + connectname) # this means: from foo import Foo
                self.Conns[connectname] = {'list': getattr(getattr(conn, connectname), 'list'), 'report': getattr(getattr(conn, connectname), 'report')}
        
        # *hierarchy API*
        # This is used for classification
        # (also displayed in GUI at the splashscreen and tagcloud)
        self.Classifiers = []
        for classifier in os.listdir( os.path.realpath(os.path.dirname(os.path.abspath(__file__))) + '/../classifiers' ):
            if classifier.endswith('.py') and classifier != '__init__.py':
                classifier = classifier[0:-3]
                obj = __import__('classifiers.' + classifier) # this means: from foo import Foo
                if getattr(getattr(obj, classifier), '__order__') is None: raise RuntimeError('Classifier '+classifier+' has not defined an order to apply!')

                self.Classifiers.append({ \
                    'classify': getattr(getattr(obj, classifier), 'classify'),\
                    'order': getattr(getattr(obj, classifier), '__order__'),\
                    'class': classifier})
                self.Classifiers = sorted(self.Classifiers, key = lambda x: x['order'])   

    def wrap_cell(self, categ, obj, table_view=None):
        '''
        Cell wrappers
        for customizing the GUI data table
        TODO : must coincide with hierarchy.xml!
        '''
        html_class = '' # for GUI javascript
        out = ''
        
        if 'cell_wrapper' in categ: # this bound type is currently defined by apps only
            out = categ['cell_wrapper'](obj)
        else:
            if categ['source'] in ['standard', 'adsorbent', 'termination']:
                out = html_formula(obj['info'][ categ['source'] ]) if categ['source'] in obj['info'] else '&mdash;'
                
            elif categ['source'] == 'etype':
                out = '?' if not 'etype' in obj['info'] else obj['info']['etype']
                
            elif categ['source'] == 'bandgap':
                html_class = ' class=_g'
                out = '?' if not 'bandgap' in obj['info'] else obj['info']['bandgap']
            
            # pseudo-source (derivative determination)    
            elif categ['source'] == 'natom':
                out = "%3d" % len( obj['structures'][-1]['symbols'] )
                
            elif categ['source'] == 'e':
                html_class = ' class=_e'
                out = "%6.5f" % obj['energy'] if obj['energy'] else '&mdash;'
                
            elif categ['source'] == 'dims':
                out = "%4.2f" % obj['structures'][-1]['dims'] if obj['structures'][-1]['periodicity'] in [2, 3] else '&mdash;'
                               
            elif categ['source'] == 'finished':
                f = int(obj['info']['finished'])
                if f > 0: out = 'yes'
                elif f == 0: out = 'n/a'
                elif f < 0: out = 'no'
            
            else:
                out = '&mdash;' if not categ['source'] in obj['info'] or not obj['info'][ categ['source'] ] else obj['info'][ categ['source'] ]
        
        if table_view:
            return '<td rel=' + str(categ['cid']) + html_class + '>' + str(out) + '</td>'
        elif html_class:
            return '<span' + html_class + '>' + str(out) + '</span>'
        else:
            return str(out)

    def reload(self, session=None, settings=None):
        '''
        Switch Tilde API object to another context, if provided
        NB: this is the PUBLIC method
        @procedure
        '''
        if session: self.session = session
        if settings: self.settings = settings

    def assign_parser(self, name):
        '''
        Restricts parsing
        **name** is a name of the parser class
        NB: this is the PUBLIC method
        @procedure
        '''
        for n, p in self.Parsers.items():
            if n != name:
                del self.Parsers[n]
        if len(self.Parsers) != 1: raise RuntimeError('Parser cannot be assigned!')

    def formula(self, atom_sequence):
        '''
        Constructs standardized chemical formula
        NB: this is the PUBLIC method
        @returns formula_str
        '''
        formula_sequence = ['Li','Na','K','Rb','Cs',  'Be','Mg','Ca','Sr','Ba','Ra',  'Sc','Y','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb',  'Ac','Th','Pa','U','Np','Pu',  'Ti','Zr','Hf',  'V','Nb','Ta',  'Cr','Mo','W',  'Fe','Ru','Os',  'Co','Rh','Ir',  'Mn','Tc','Re',  'Ni','Pd','Pt',  'Cu','Ag','Au',  'Zn','Cd','Hg',  'B','Al','Ga','In','Tl',  'Pb','Sn','Ge','Si','C',   'N','P','As','Sb','Bi',   'H',   'Po','Te','Se','S','O',  'At','I','Br','Cl','F',  'He','Ne','Ar','Kr','Xe','Rn']
        labels = {}
        types = []
        y = 0
        for k, atomi in enumerate(atom_sequence):
            lbl = re.sub("[0-9]+", "", atomi).capitalize()
            if lbl not in labels:
                labels[lbl] = y
                types.append([k+1])
                y += 1
            else:
                types[ labels[lbl] ].append(k+1)
        atoms = labels.keys()
        atoms = [x for x in formula_sequence if x in atoms] + [x for x in atoms if x not in formula_sequence] # O(N^2) sorting
        formula = ''
        for atom in atoms:
            n = len(types[labels[atom]])
            if n==1: n = ''
            else: n = str(n)
            formula += atom + n
        return formula
        
    def count(self):
        if not self.session: return None
        return self.session.query(func.count(model.Simulation.id)).one()[0]
        
    def savvyize(self, input_string, recursive=False, stemma=False):
        '''
        Determines which files should be processed
        NB: this is the PUBLIC method
        @returns filenames_list
        '''
        input_string = os.path.abspath(input_string)
        tasks = []
        
        restricted = [ symbol for symbol in self.settings['skip_if_path'] ] if self.settings['skip_if_path'] else []

        # given folder
        if os.path.isdir(input_string):
            if recursive:
                for root, dirs, files in os.walk(input_string): # beware of broken links on unix! (NB find ~ -type l -exec rm -f {} \;)
                    # skip_if_path directive
                    to_filter = []
                    for dir in dirs:
                        dir = u(dir)
                        for rs in restricted:
                            if dir.startswith(rs) or dir.endswith(rs):
                                to_filter.append(dir)
                                break
                    dirs[:] = [x for x in dirs if x not in to_filter] # keep reference
                    for filename in files:
                        # skip_if_path directive
                        filename = u(filename)
                        if restricted:
                            for rs in restricted:
                                if filename.startswith(rs) or filename.endswith(rs): break
                            else: tasks.append(root + os.sep + filename)
                        else: tasks.append(root + os.sep + filename)
            else:
                for filename in os.listdir(input_string):
                    filename = u(filename)
                    if os.path.isfile(input_string + os.sep + filename):
                        # skip_if_path directive
                        if restricted:
                            for rs in restricted:
                                if filename.startswith(rs) or filename.endswith(rs): break
                            else: tasks.append(input_string + os.sep + filename)
                        else: tasks.append(input_string + os.sep + filename)

        # given full filename
        elif os.path.isfile(input_string):
            tasks.append(input_string) # skip_if_path directive is not invoked here

        # given filename stemma
        else:
            if stemma:
                parent = os.path.dirname(input_string)
                for filename in os.listdir(parent):
                    filename = u(filename)
                    if input_string in parent + os.sep + filename and not os.path.isdir(parent + os.sep + filename):
                        # skip_if_path directive
                        if restricted:
                            for rs in restricted:
                                if filename.startswith(rs) or filename.endswith(rs): break
                            else: tasks.append(parent + os.sep + filename)
                        else: tasks.append(parent + os.sep + filename)
        return tasks

    def _parse(self, parsable, parser_name, **missing_props):
        '''
        Low-level parsing
        @returns (Tilde_obj, error)
        '''
        calc, error = None, None
        try: calc = self.Parsers[parser_name](parsable, **missing_props)
        except RuntimeError as e: error = "routine %s parser error in %s: %s" % ( parser_name, parsable, e )
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            error = "unexpected %s parser error in %s:\n %s" % ( parser_name, parsable, "".join(traceback.format_exception( exc_type, exc_value, exc_tb )) )
        return (calc, error)

    def parse(self, file):
        ''' High-level parsing:
        determines the data format
        and combines parent-children outputs
        NB: this is the PUBLIC method
        @returns (Tilde_obj, error)
        '''
        calc, error = None, None        
        try: f = open(file, 'r')
        except IOError: return (None, 'read error!')        
        if is_binary_string(f.read(2048)): return (None, 'nothing found (binary data)...')
        f.seek(0)
        i = 0
        stop_read = False
        while 1:
            if i>700 or stop_read: break # criterion: parser must detect its working format in first N lines of output
            str = f.readline()
            if not str: break
            str = str.replace('\r\n', '\n').replace('\r', '\n')
            for name, Parser in self.Parsers.iteritems():
                if Parser.fingerprints(str):
                    calc, error = self._parse(file, name)
                    stop_read = True
                    break
            i += 1
        f.close()

        # (1) unsupported data occured
        if not calc and not error: return (None, 'nothing found...')

        # (3) check if we parsed something reasonable <- should be merged?
        if not error and calc:

            if not len(calc.structures) or not len(calc.structures[-1]): error = 'Valid structure is not present!'            

            if calc.info['finished'] < 0: calc.warning( 'This calculation is not correctly finished!' )

        return (calc, error)

    def classify(self, calc, symprec=None):
        '''
        Reasons on normalization, invokes hierarchy API and prepares to saving
        NB: this is the PUBLIC method
        @returns (Tilde_obj, error)
        '''
        error = None
        
        calc.info['formula'] = self.formula( calc.structures[-1].get_chemical_symbols() )
        calc.info['cellpar'] = cell_to_cellpar(calc.structures[-1].cell).tolist()
        if calc.info['input']:
            try: calc.info['input'] = unicode(calc.info['input'], errors='ignore')
            except: pass
        
        # applying filter: todo
        if calc.info['finished'] < 0 and self.settings['skip_unfinished']:
            return (None, 'data do not satisfy the filter')
            
        # TODO (?)
        fragments = re.findall(r'([A-Z][a-z]?)(\d*[?:.\d+]*)?', calc.info['formula'])
        for i in fragments:
            if i[0] == 'X': continue
            calc.info['elements'].append(i[0])
            calc.info['contents'].append(int(i[1])) if i[1] else calc.info['contents'].append(1)

        # extend Tilde hierarchy with modules
        for C_obj in self.Classifiers:
            try: calc = C_obj['classify'](calc)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                error = "Fatal error during classification:\n %s" % "".join(traceback.format_exception( exc_type, exc_value, exc_tb ))
                return (None, error)
        
        # chemical ratios
        if not len(calc.info['standard']):
            if len(calc.info['elements']) == 1: calc.info['expanded'] = 1
            if not calc.info['expanded']: calc.info['expanded'] = reduce(fractions.gcd, calc.info['contents'])
            for n, i in enumerate(map(lambda x: x/calc.info['expanded'], calc.info['contents'])):
                if i==1: calc.info['standard'] += calc.info['elements'][n]
                else: calc.info['standard'] += calc.info['elements'][n] + str(i)
        if not calc.info['expanded']: del calc.info['expanded']
        calc.info['nelem'] = len(calc.info['elements'])
        
        # general calculation type reasoning
        if (calc.structures[-1].get_initial_charges() != 0).sum(): calc.info['calctypes'].append('charges') # numpy count_nonzero implementation
        if calc.phonons['modes']: calc.info['calctypes'].append('phonons')
        if calc.phonons['ph_k_degeneracy']: calc.info['calctypes'].append('phonon dispersion')
        if calc.phonons['dielectric_tensor']: calc.info['calctypes'].append('static dielectric const') # CRYSTAL-only!
        if calc.info['tresholds'] or len( getattr(calc, 'ionic_steps', []) ) > 1: calc.info['calctypes'].append('geometry optimization')
        if calc.electrons['dos'] or calc.electrons['bands']: calc.info['calctypes'].append('electron structure')
        if calc.info['energy']: calc.info['calctypes'].append('total energy')

        # TODO: standardize computational materials science methods
        if 'vac' in calc.info['properties']:
            if 'X' in calc.structures[-1].get_chemical_symbols(): calc.info['techs'].append('vacancy defect: ghost')
            else: calc.info['techs'].append('vacancy defect: void space')
       
        if calc.structures[-1].periodicity == 3: calc.info['periodicity'] = '3-periodic'
        elif calc.structures[-1].periodicity == 2: calc.info['periodicity'] = '2-periodic'
        elif calc.structures[-1].periodicity == 1: calc.info['periodicity'] = '1-periodic'
        elif calc.structures[-1].periodicity == 0: calc.info['periodicity'] = 'non-periodic'                

        # invoke symmetry finder
        found = SymmetryHandler(calc, symprec)
        if found.error:
            return (None, found.error)
        calc.info['sg'] = found.i
        calc.info['ng'] = found.n
        calc.info['symmetry'] = found.symmetry
        calc.info['pg'] = found.pg
        calc.info['dg'] = found.dg
        
        # phonons
        if calc.phonons['dfp_magnitude']: calc.info['dfp_magnitude'] = round(calc.phonons['dfp_magnitude'], 3)
        if calc.phonons['dfp_disps']: calc.info['dfp_disps'] = len(calc.phonons['dfp_disps'])
        if calc.phonons['modes']:
            calc.info['n_ph_k'] = len(calc.phonons['ph_k_degeneracy']) if calc.phonons['ph_k_degeneracy'] else 1
        
        # electronic properties reasoning
        # by bands
        if calc.electrons['bands']:
            if calc.electrons['bands'].is_conductor():
                calc.info['etype'] = 'conductor'
                calc.info['bandgap'] = 0.0
            else:
                try: gap, is_direct = calc.electrons['bands'].get_bandgap()
                except ElectronStructureError as e:
                    calc.electrons['bands'] = None
                    calc.warning(e.value)
                else:    
                    calc.info['etype'] = 'insulator' # semiconductor?
                    calc.info['bandgap'] = round(gap, 2)
                    calc.info['bandgaptype'] = 'direct' if is_direct else 'indirect'
        
        # by DOS  
        if calc.electrons['dos']:            
            try: gap = round(calc.electrons['dos'].get_bandgap(), 2)
            except ElectronStructureError as e:
                calc.electrons['dos'] = None
                calc.warning(e.value)
            else:
                if calc.electrons['bands']: # check coincidence
                    if abs(calc.info['bandgap'] - gap) > 0.2: calc.warning('Gaps in DOS and bands differ considerably! The latter is considered.')
                else:
                    calc.info['bandgap'] = gap
                    if gap: calc.info['etype'] = 'insulator' # semiconductor?
                    else: calc.info['etype'] = 'conductor'
        
        for n, i in enumerate(calc.info['techs']):
            calc.info['tech' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        for n, i in enumerate(calc.info['calctypes']):
            calc.info['calctype' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        for n, i in enumerate(calc.info['elements']):
            calc.info['element' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        for n, i in enumerate(calc.info['tags']):
            calc.info['tag' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        
        # properties determined by classifiers
        for k, v in calc.info['properties'].iteritems():
            calc.info[k] = v
        del calc.info['properties']
        
        calc.benchmark() # this call must be at the very end of parsing

        return (calc, error)

    def postprocess(self, calc, with_module=None, dry_run=None):
        '''
        Invokes module(s) API
        NB: this is the PUBLIC method
        @returns apps_dict
        '''
        for appname, appclass in self.Apps.iteritems():
            if with_module and with_module != appname: continue

            run_permitted = False

            # scope-conditions
            if appclass['apptarget']:
                for key in appclass['apptarget']:
                    negative = False
                    if appclass['apptarget'][key].startswith('!'):
                        negative = True
                        scope_prop = appclass['apptarget'][key][1:]
                    else:
                        scope_prop = appclass['apptarget'][key]

                    if key in calc.info: # note sharp-signed multiple tag containers in Tilde hierarchy : todo simplify
                        # operator *in* permits non-strict comparison, e.g. "CRYSTAL" matches CRYSTAL09 v2.0
                        if (scope_prop in calc.info[key] or scope_prop == calc.info[key]) != negative: # true if only one, but not both
                            run_permitted = True
                        else:
                            run_permitted = False
                            break

            else: run_permitted = True

            # module code running
            if run_permitted:
                calc.apps[appname] = {'error': None, 'data': None}
                if dry_run: continue
                try: AppInstance = appclass['appmodule'](calc)
                except:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    errmsg = "Fatal error in %s module:\n %s" % ( appname, " ".join(traceback.format_exception( exc_type, exc_value, exc_tb )) )
                    calc.apps[appname]['error'] = errmsg
                    calc.warning( errmsg )
                else:
                    try: calc.apps[appname]['data'] = getattr(AppInstance, appclass['appdata'])
                    except AttributeError:
                        errmsg = 'No appdata-defined property found for %s module!' % appname
                        calc.apps[appname]['error'] = errmsg
                        calc.warning( errmsg )
        return calc

    def save(self, calc, db_transfer_mode=False):
        '''
        Saves Tilde_obj into the database
        NB: this is the PUBLIC method
        @returns (id, error)
        '''
        if not self.session: return (None, 'Database is not connected!')
        
        checksum = calc.get_checksum()

        # check unique
        (already, ) = self.session.query(exists().where(model.Simulation.checksum==checksum)).one()
        if already:
            del calc
            return (checksum, None)       
        
        if not db_transfer_mode:

            # prepare phonon data
            # this is actually a dict to list conversion: TODO
            if calc.phonons['modes']:
                phonons_json = []

                for bzpoint, frqset in calc.phonons['modes'].iteritems():
                    # re-orientate eigenvectors
                    for i in range(0, len(calc.phonons['ph_eigvecs'][bzpoint])):
                        for j in range(0, len(calc.phonons['ph_eigvecs'][bzpoint][i])/3):
                            eigv = array([calc.phonons['ph_eigvecs'][bzpoint][i][j*3], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+1], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+2]])
                            R = dot( eigv, calc.structures[-1].cell ).tolist()
                            calc.phonons['ph_eigvecs'][bzpoint][i][j*3], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+1], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+2] = map(lambda x: round(x, 3), R)

                    try: irreps = calc.phonons['irreps'][bzpoint]
                    except KeyError:
                        empty = []
                        for i in range(len(frqset)): empty.append('')
                        irreps = empty
                    phonons_json.append({  'bzpoint':bzpoint, 'freqs':frqset, 'irreps':irreps, 'ph_eigvecs':calc.phonons['ph_eigvecs'][bzpoint]  })
                    if bzpoint == '0 0 0':
                        phonons_json[-1]['ir_active'] = calc.phonons['ir_active']
                        phonons_json[-1]['raman_active'] = calc.phonons['raman_active']
                    if calc.phonons['ph_k_degeneracy']:
                        phonons_json[-1]['ph_k_degeneracy'] = calc.phonons['ph_k_degeneracy'][bzpoint]

                calc.phonons = phonons_json
            else: calc.phonons = False
                        
            # prepare electron data
            for i in ['dos', 'bands']: # projected?
                if calc.electrons[i]: calc.electrons[i] = calc.electrons[i].todict()
            
            calc.info['rgkmax'] = calc.electrons['rgkmax']
        
        sim = model.Simulation(checksum=checksum)
        
        pot = model.Pottype.as_unique(self.session, name = calc.info['H'])
        pot.instances.append(sim)
        
        sim.recipinteg = model.Recipinteg(kgrid = calc.info['k'], kshift = calc.info['kshift'], smearing = calc.info['smear'], smeartype = calc.info['smeartype'])
        sim.basis = model.Basis(type = calc.electrons['type'], rgkmax = calc.electrons['rgkmax'],
            repr = json.dumps(calc.electrons['basis_set']) if calc.electrons['basis_set'] else None)
        sim.energy = model.Energy(convergence = json.dumps(calc.info['convergence']), total = calc.info['energy'])
        sim.auxiliary = model.Auxiliary(location = calc.info['location'], finished = calc.info['finished'], raw_input = calc.info['input'])
        
        codefamily = model.Codefamily.as_unique(self.session, content = calc.info['framework'])
        codeversion = model.Codeversion.as_unique(self.session, content = calc.info['prog'])
        codeversion.instances.append( sim.auxiliary )
        codefamily.versions.append( codeversion )
        
        # electrons
        if calc.electrons['dos'] or calc.electrons['bands']:
            sim.electrons = model.Electrons(gap = calc.info['bandgap'])
            if 'bandgaptype' in calc.info: sim.electrons.is_direct = 1 if calc.info['bandgaptype'] == 'direct' else -1
            sim.electrons.eigenvalues = model.Eigenvalues(
                dos = json.dumps(calc.electrons['dos']),
                bands = json.dumps(calc.electrons['bands']),
                projected = json.dumps(calc.electrons['projected']),
                eigenvalues = json.dumps(calc.electrons['eigvals']))
        
        # phonons
        if calc.phonons:
            sim.phonons = model.Phonons()
            sim.phonons.eigenvalues = model.Eigenvalues(eigenvalues = json.dumps(calc.phonons))
        
        for n, ase_repr in enumerate(calc.structures):
            
            struct = model.Structure()
            
            if n == len(calc.structures)-1:
                struct.spacegroup = model.Spacegroup(n=calc.info['ng'])

            s = cell_to_cellpar(ase_repr.cell)
            struct.lattice_basis = model.Lattice_basis(a=s[0], b=s[1], 
            c=s[2], alpha=s[3], beta=s[4], gamma=s[5], 
            a11=ase_repr.cell[0][0], a12=ase_repr.cell[0][1], 
            a13=ase_repr.cell[0][2], a21=ase_repr.cell[1][0], 
            a22=ase_repr.cell[1][1], a23=ase_repr.cell[1][2], 
            a31=ase_repr.cell[2][0], a32=ase_repr.cell[2][1], 
            a33=ase_repr.cell[2][2])
            struct.struct_ratios = model.Struct_ratios(chemical_formula=calc.info['standard'], formula_units=calc.info['expanded'])

            for i in ase_repr:
                struct.atoms.append( model.Atom( number=chemical_symbols.index(i.symbol), x=i.x, y=i.y, z=i.z ) )
            
            sim.structures.append(struct)
        
        # save tags: only those marked with *has_label* and having *source* values are considered        
        sim.uigrid = model.uiGrid(info=json.dumps(calc.info))
        
        for entity in self.hierarchy:
            
            if not 'has_label' in entity: continue
            
            if 'multiple' in entity:
                n=0
                while 1:
                    try:
                        sim.uitopics.append( model.uiTopic.as_unique(self.session, cid=entity['cid'], topic=calc.info[ entity['source'].replace('#', str(n)) ]) )
                    except KeyError:
                        if 'negative_tagging' in entity: sim.uitopics.append( model.uiTopic.as_unique(self.session, cid=entity['cid'], topic='none') ) # beware to add something new to an existing item!
                        break
                    else: n+=1
            else:
                try:
                    sim.uitopics.append( model.uiTopic.as_unique(self.session, cid=entity['cid'], topic=calc.info[ entity['source'] ]) )
                except KeyError:
                    if 'negative_tagging' in entity: sim.uitopics.append( model.uiTopic.as_unique(self.session, cid=entity['cid'], topic='none') ) # beware to add something new to an existing item!

        # save apps        
        for appname, appcontent in calc.apps.iteritems():
            sim.apps.append(model.Apps(name = appname, data = json.dumps(appcontent)))
        
        self.session.add(sim)
        self.session.commit()

        del calc, sim
        return (checksum, None)

    def restore(self, db_row, db_transfer_mode=False):
        '''
        Restores Tilde_obj from the database
        NB: this is the PUBLIC method
        @returns Tilde_obj
        '''
        calc = Output()

        calc._checksum = db_row['checksum']
        
        try: calc.energy = float( db_row['energy'] )
        except TypeError: pass
        
        calc.info = json.loads(db_row['info'])

        # unpacking of the
        # Tilde ORM objects
        # NB: here they are except *info*
        # Why this is so?
        # We store the redundant copy
        # of tags marked with *has_column*
        # in results table (info field)
        # to speed up DB queries
        for i in ['structures', 'phonons', 'electrons', 'apps']:
            if not db_transfer_mode:
                calc[i] = json.loads(db_row[i])
                if i=='structures': calc.structures = [dict2ase(ase_dict) for ase_dict in calc.structures]              
            else: calc[i] = db_row[i]

        return calc
