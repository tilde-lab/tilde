
# Tilde project: basic routines
# v030913
# See http://wwwtilda.googlecode.com

__version__ = "0.2.2"

import os
import sys
import math, random
import re
import fractions
import inspect
import traceback
import subprocess
import json
from string import letters

from numpy import dot, array, cross
from numpy.linalg import det, norm

from common import u, is_binary_string
from common import ase2dict, dict2ase
from common import generate_cif
from symmetry import SymmetryHandler

# this is done to simplify adding modules to Tilde according its API
# TODO: dealing with sys.path is malpractice
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.common import ModuleError
from parsers import Output
from settings import DEFAULT_SETUP
from core.deps.ase import Atoms

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps/ase/lattice'))
from spacegroup.cell import cell_to_cellpar


class API:
    version = __version__
    __shared_state = {} # singleton

    def __init__(self, db_conn=None, settings=DEFAULT_SETUP):
        self.__dict__ = self.__shared_state

        self.db_conn = db_conn
        self.settings = settings

        self.deferred_storage = {}

        # *parser API*
        # Subfolder "parsers" contains directories with parsers.
        # Parser will be active if:
        # (1) its class defines a fingerprints method
        # (2) it is enabled in its manifest file
        # (3) its file name repeats the name of parser folder
        All_parsers, self.Parsers = {}, {}
        for parsername in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../parsers' ):
            if not os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../parsers/' + parsername + '/manifest.json') ): continue
            if not os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../parsers/' + parsername + '/' + parsername + '.py') ):
                raise RuntimeError('Parser API Error: Parser code for ' + parsername + ' is missing!')
            try: parsermanifest = json.loads( open( os.path.realpath(os.path.dirname(__file__) + '/../parsers/' + parsername + '/manifest.json') ).read() )
            except: raise RuntimeError('Parser API Error: Parser manifest for ' + parsername + ' has corrupted format!')
            
            if not 'enabled' in parsermanifest or not parsermanifest['enabled'] and not settings['debug_regime']: continue  
            
            All_parsers[parsername] = getattr(getattr(__import__('parsers.' + parsername + '.' + parsername), parsername), parsername) # all imported modules will be stored here
        
        # replace modules by classes and check *fingerprints* method
        for parser, module in All_parsers.iteritems():
            for name, cls in inspect.getmembers(module):
                if inspect.isclass(cls):
                    if inspect.isclass(cls) and hasattr(cls, 'fingerprints'):
                        self.Parsers[cls.__name__] = cls

        # *module API*
        # Tilde module (app) is simply a subfolder (%appfolder%) of apps folder
        # contains manifest.json and %appfolder%.py files
        # the following tags in manifest matter:
        # *onprocess* - invoking during processing (therefore %appfolder%.py must provide the class %Appfolder%)
        # *appcaption* - module caption (used as column caption in data table & as atomic structure rendering pane overlay caption)
        # *appdata* - a new property defined by app
        # *apptarget* - whether an app should be executed (based on hierarchy API)
        # *on3d* - app provides the data which may be shown on atomic structure rendering pane (used only by make3d of daemon.py)
        self.Apps = {}
        for appname in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../apps' ):
            if os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ):
                try: appmanifest = json.loads( open( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ).read() )
                except: raise RuntimeError('Module API Error: Module manifest for ' + appname + ' has corrupted format!')

                # tags processing
                if not 'appdata' in appmanifest: raise RuntimeError('Module API Error: no appdata tag for ' + appname + '!')
                if 'onprocess' in appmanifest:
                    try: app = __import__('apps.' + appname + '.' + appname, fromlist=[appname.capitalize()]) # this means: from foo import Foo
                    except ImportError: raise RuntimeError('Module API Error: module ' + appname + ' is invalid or not found!')
                    self.Apps[appname] = {'appmodule': getattr(app, appname.capitalize()), 'appdata': appmanifest['appdata'], 'apptarget': appmanifest.get('apptarget', None), 'appcaption': appmanifest['appcaption'], 'on3d': appmanifest.get('on3d', 0)}

        # *connector API*
        # Every connector implements reading methods:
        # *list* (if applicable) and *report* (obligatory)
        self.Conns = {}
        for connectname in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../connectors' ):
            if connectname.endswith('.py') and connectname != '__init__.py':
                connectname = connectname[0:-3]
                conn = __import__('connectors.' + connectname) # this means: from foo import Foo
                self.Conns[connectname] = {'list': getattr(getattr(conn, connectname), 'list'), 'report': getattr(getattr(conn, connectname), 'report')}

        # *hierarchy API*
        # This is used while building topics
        # (displayed at the splashscreen and tagcloud)
        self.hierarchy = [ \
            {"cid": 1, "category": "formula",               "source": "standard", "chem_notation": True, "sort": 1, "has_column": True, "has_label": True, "descr": ""}, \
            
            {"cid": 2, "category": "containing element",    "source": "element#", "sort": 14, "descr": ""}, \
            {"cid": 3, "category": "host elements number",  "source": "nelem", "sort": 13, "descr": ""}, \
            {"cid": 4, "category": "supercell",             "source": "expanded", "sort": 29, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 5, "category": "periodicity",           "source": "periodicity", "sort": 12, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 6, "category": "calculation type",      "source": "calctype#", "sort": 10, "has_label": True, "descr": ""}, \
            {"cid": 7, "category": "hamiltonian",           "source": "H", "sort": 30, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 8, "category": "system",                "source": "tag#", "sort": 11, "has_label": True, "descr": ""}, \
            
            {"cid": 9, "category": "symmetry",              "source": "symmetry", "sort": 80, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 10,"category": "space group (Schon.)",  "source": "sg", "sort": 81, "has_column": True, "descr": "Result space group (Schoenflis notation)"}, \
            {"cid": 11,"category": "point group",           "source": "pg", "sort": 82, "has_column": True, "has_label": True, "descr": "Result point group"}, \
            {"cid": 12,"category": "space group (intl.)",   "source": "ng", "sort": 90, "has_column": True, "descr": "Result space group (international notation)"}, \
            {"cid": 13,"category": "layer group (intl.)",   "source": "dg", "sort": 91, "has_column": True, "descr": "Result layer group (international notation)"}, \
            
            {"cid": 14,"category": "main tolerance",        "source": "tol", "sort": 84, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 15,"category": "spin-polarized",        "source": "spin", "sort": 22, "negative_tagging": True, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 16,"category": "locked magn.state",     "source": "lockstate", "sort": 23, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 17,"category": "k-point set",           "source": "k", "sort": 85, "has_column": True, "has_label": True, "descr": ""}, \
            {"cid": 18,"category": "used techniques",       "source": "tech#", "sort": 84, "has_label": True, "descr": ""}, \
            {"cid": 19,"category": "phon.magnitude",        "source": "dfp_magnitude", "sort": 86, "has_column": True, "descr": ""}, \
            {"cid": 20,"category": "phon.disp.number",      "source": "dfp_disps", "sort": 87, "has_column": True, "descr": ""}, \
            {"cid": 21,"category": "phon.k-points",         "source": "n_ph_k", "sort": 88, "has_column": True, "descr": ""}, \
            {"cid": 22,"category": "code",                  "source": 'prog', "sort": 89, "has_column": True, "has_label": True, "descr": ""},
            
            {"cid": 23,"category": "modeling time, hr",     "source": 'duration', "sort": 90, "has_column": True, "has_label": False, "descr": ""},
            
            {"cid": 24,"category": "conductivity",          "source": 'etype', "sort": 5, "unknown_tagging": True, "has_column": True, "has_label": True, "descr": ""},
            {"cid": 25,"category": "Min. band gap, eV",     "source": 'bandgap', "sort": 6, "unknown_tagging": True, "has_column": True, "has_label": False, "descr": "", "nocap": True},
            {"cid": 26,"category": "band gap type",         "source": 'bandgaptype', "sort": 31, "unknown_tagging": True, "has_column": True, "has_label": True, "descr": ""},
        ]
        
        self.Classifiers = []
        for classifier in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../classifiers' ):
            if classifier.endswith('.py') and classifier != '__init__.py':
                classifier = classifier[0:-3]
                obj = __import__('classifiers.' + classifier) # this means: from foo import Foo
                if getattr(getattr(obj, classifier), '__order__') is None: raise RuntimeError('Classifier '+classifier+' has not defined an order to apply!')

                local_props = getattr(getattr(obj, classifier), '__properties__')
                for n, prop in enumerate(local_props):
                    local_props[n]['cid'] = int(10000*len(classifier)*math.log(int("".join([str(letters.index(l)+1) for l in classifier if l in letters]))))+n # we need to build a uniqie cid to use in tag system
                    if not 'sort' in local_props[n]: local_props[n]['sort'] = local_props[n]['cid']
                if local_props: self.hierarchy.extend( local_props )

                self.Classifiers.append({ \
                    'classify': getattr(getattr(obj, classifier), 'classify'),\
                    'order': getattr(getattr(obj, classifier), '__order__'),\
                    'class': classifier})
                self.Classifiers = sorted(self.Classifiers, key = lambda x: x['order'])

    def reload(self, db_conn=None, settings=None):
        '''
        Switch Tilde API object to another context, if provided
        NB: this may be run from outside
        @procedure
        '''
        if db_conn: self.db_conn = db_conn
        if settings: self.settings = settings

    def assign_parser(self, name):
        '''
        Restricts parsing
        **name** is a name of the parser class
        NB: this may be run from outside
        @procedure
        '''
        for n, p in self.Parsers.items():
            if n != name:
                del self.Parsers[n]
        if len(self.Parsers) != 1: raise RuntimeError('Parser cannot be assigned!')

    def formula(self, atom_sequence):
        '''
        Constructs standardized chemical formula
        NB: this may be run from outside
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
        
    def savvyize(self, input_string, recursive=False, stemma=False):
        '''
        Determines which files should be processed
        NB: this may be run from outside
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
        NB: this may be run from outside
        @returns (Tilde_obj, error)
        '''
        calc, error = None, None
        try: f = open(file, 'r')
        except IOError: return (None, 'read error!')
        i = 0
        stop_read, binary_check = False, True
        while 1:
            if i>700 or stop_read: break # criterion: parser must detect its working format in first N lines of output
            str = f.readline()
            if not str: break
            if binary_check:
                if is_binary_string(str): break
                else: binary_check = False
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

    def postprocess(self, calc, with_module=None):
        '''
        Invokes module(s) API
        NB: this may be run from outside
        @returns apps_dict
        '''
        apps = {}
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
                apps[appname] = {'error': None, 'data': None}
                try: AppInstance = appclass['appmodule'](calc)
                except ModuleError as e:
                    apps[appname]['error'] = e.value
                except:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    apps[appname]['error'] = "Fatal error in %s module:\n %s" % ( appname, " ".join(traceback.format_exception( exc_type, exc_value, exc_tb )) )
                else:
                    try: apps[appname]['data'] = getattr(AppInstance, appclass['appdata'])
                    except AttributeError: apps[appname]['error'] = 'No appdata-defined property found!'
        return apps

    def classify(self, calc, symprec=None):
        '''
        Invokes hierarchy API
        NB: this may be run from outside
        @returns (Tilde_obj, error)
        '''
        error = None
        
        calc.info['formula'] = self.formula( calc.structures[-1].get_chemical_symbols() )
        calc.info['cellpar'] = cell_to_cellpar(calc.structures[-1].cell).tolist()
        
        # applying filter: todo
        if calc.info['finished'] < 0 and self.settings['skip_unfinished']:
            return (None, 'data do not satisfy the filter')
        
        # extend ASE object with useful properties
        for i in range(len(calc.structures)):
            calc.structures[i].periodicity = sum(calc.structures[i].get_pbc())
            calc.structures[i].dims = abs(det(calc.structures[i].cell))
        calc.info['dims'] = calc.structures[-1].dims        

        # this is stupid (?), TODO
        fragments = re.findall(r'([A-Z][a-z]?)(\d*[?:.\d+]*)?', calc.info['formula'])
        for i in fragments:
            if i[0] == 'X': continue
            calc.info['elements'].append(i[0])
            calc.info['contents'].append(int(i[1])) if i[1] else calc.info['contents'].append(1)

        # extend Tilde hierarchy
        # with modules (idea of *hierarchy API*)
        for C_obj in self.Classifiers:
            try: calc = C_obj['classify'](calc)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                error = "Fatal error during classification:\n %s" % "".join(traceback.format_exception( exc_type, exc_value, exc_tb ))
                return (None, error)

        # post-processing tags
        if not len(calc.info['standard']):
            #if len(calc.info['elements']) == 1: calc.info['expanded'] = 1
            if not calc.info['expanded']: calc.info['expanded'] = reduce(fractions.gcd, calc.info['contents'])
            for n, i in enumerate(map(lambda x: x/calc.info['expanded'], calc.info['contents'])):
                if i==1: calc.info['standard'] += calc.info['elements'][n]
                else: calc.info['standard'] += calc.info['elements'][n] + str(i)

        # general calculation type reasoning
        if (calc.structures[-1].get_initial_charges() != 0).sum(): calc.info['calctypes'].append('charges') # numpy count_nonzero implementation
        if calc.phonons['modes']: calc.info['calctypes'].append('phonons')
        if calc.phonons['ph_k_degeneracy']: calc.info['calctypes'].append('phonon dispersion')
        if calc.phonons['dielectric_tensor']: calc.info['calctypes'].append('static dielectric const') # CRYSTAL-only - TODO: extend
        if calc.method['perturbation']: calc.info['calctypes'].append('electric field response') # CRYSTAL-only - TODO: extend
        if calc.tresholds or len( getattr(calc, 'ionic_steps', []) ) > 1: calc.info['calctypes'].append('optimization')
        if calc.electrons['dos']: calc.info['calctypes'].append('electron DOS')
        if calc.electrons['bands'] or calc.electrons['eigvals']: calc.info['calctypes'].append('electron bands')
        if calc.energy: calc.info['calctypes'].append('total energy')

        for n, i in enumerate(calc.info['calctypes']):
            calc.info['calctype' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify

        # standardizing materials science methods
        # TODO add modularity
        if calc.method:
            if calc.method['H']: calc.info['H'] = calc.method['H']
            if calc.method['tol']: calc.info['tol'] = calc.method['tol']
            if calc.method['k']: calc.info['k'] = calc.method['k']
            if calc.method['spin']: calc.info['spin'] = 'yes'
            if calc.method['lockstate']: calc.info['lockstate'] = calc.method['lockstate']
            if calc.method['technique'].keys():
                for i in calc.method['technique'].keys():
                    
                    # CRYSTAL
                    if i=='anderson': calc.info['techs'].append(i)
                    elif i=='fmixing':
                        if 0<calc.method['technique'][i]<=25:    calc.info['techs'].append(i + '<25%')
                        elif 25<calc.method['technique'][i]<=50: calc.info['techs'].append(i + ' 25-50%')
                        elif 50<calc.method['technique'][i]<=75: calc.info['techs'].append(i + ' 50-75%')
                        elif 75<calc.method['technique'][i]<=90: calc.info['techs'].append(i + ' 75-90%')
                        elif 90<calc.method['technique'][i]:     calc.info['techs'].append(i + '>90%')
                    elif i=='shifter':
                        if 0<calc.method['technique'][i]<=0.5:   calc.info['techs'].append(i + '<0.5au')
                        elif 0.5<calc.method['technique'][i]<=1: calc.info['techs'].append(i + ' 0.5-1au')
                        elif 1<calc.method['technique'][i]<=2.5: calc.info['techs'].append(i + ' 1-2.5au')
                        elif 2.5<calc.method['technique'][i]:    calc.info['techs'].append(i + '>2.5au')
                    elif i=='smear':
                        if 0<calc.method['technique'][i]<=0.005:      calc.info['techs'].append(i + '<0.005au')
                        elif 0.005<calc.method['technique'][i]<=0.01: calc.info['techs'].append(i + ' 0.005-0.01au')
                        elif 0.01<calc.method['technique'][i]:        calc.info['techs'].append(i + '>0.01au')
                    elif i=='broyden':
                        if 0<calc.method['technique'][i][0]<=25:    type='<25%'
                        elif 25<calc.method['technique'][i][0]<=50: type=' 25-50%'
                        elif 50<calc.method['technique'][i][0]<=75: type=' 50-75%'
                        elif 75<calc.method['technique'][i][0]<=90: type=' 75-90%'
                        elif 90<calc.method['technique'][i][0]:     type='>90%'
                        if round(calc.method['technique'][i][1], 4) == 0.0001: type += ' (std.)' # broyden parameter
                        else: type += ' ('+str(round(calc.method['technique'][i][1], 5))+')'
                        if calc.method['technique'][i][2] < 5: type += ' start'
                        else: type += ' defer.'
                        calc.info['techs'].append(i + type)
                    
                    # EXCITING
                    elif i=='vacuum2d':
                        calc.info['techs'].append('vacuum %sA' % calc.method['technique'][i])
                    elif i=='spin-orbit':
                        calc.info['techs'].append('spin-orbit coupling')
                    elif i=='empty_states':
                        calc.info['techs'].append('%s empty states' % calc.method['technique'][i])

            if 'vac' in calc.info['properties']:
                if 'X' in [i[0] for i in calc.structures[-1].atoms]: calc.info['techs'].append('vacancy defect: ghost')
                else: calc.info['techs'].append('vacancy defect: void space')

            if calc.method['perturbation']:
                calc.info['techs'].append('perturbation: ' + calc.method['perturbation'])

            for n, i in enumerate(calc.info['techs']):
                calc.info['tech' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify

        for n, i in enumerate(calc.info['elements']):
            calc.info['element' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        for n, i in enumerate(calc.info['tags']):
            calc.info['tag' + str(n)] = i # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
        calc.info['nelem'] = len(calc.info['elements'])

        if calc.info['expanded']: calc.info['expanded'] = str(calc.info['expanded']) + 'x'
        else: del calc.info['expanded']

        if calc.structures[-1].periodicity == 3: calc.info['periodicity'] = '3-periodic'
        elif calc.structures[-1].periodicity == 2: calc.info['periodicity'] = '2-periodic'
        elif calc.structures[-1].periodicity == 1: calc.info['periodicity'] = '1-periodic'
        elif calc.structures[-1].periodicity == 0: calc.info['periodicity'] = 'non-periodic'
        for k, v in calc.info['properties'].iteritems():
            calc.info[k] = v

        # invoke symmetry finder
        found = SymmetryHandler(calc, symprec)
        if found.error:
            return (None, found.error)
        calc.info['sg'] = found.i
        calc.info['ng'] = found.n
        calc.info['symmetry'] = found.symmetry
        calc.info['pg'] = found.pg
        calc.info['dg'] = found.dg        

        if calc.phonons['dfp_magnitude']: calc.info['dfp_magnitude'] = round(calc.phonons['dfp_magnitude'], 3)
        if calc.phonons['dfp_disps']: calc.info['dfp_disps'] = len(calc.phonons['dfp_disps'])
        if calc.phonons['modes']:
            calc.info['n_ph_k'] = len(calc.phonons['ph_k_degeneracy']) if calc.phonons['ph_k_degeneracy'] else 1
        
        # electronic properties reasoning
        # by bands
        if calc.electrons['bands']:
            if calc.electrons['bands'].is_metal():
                calc.info['etype'] = 'metal'
                calc.info['bandgap'] = 0.0
            else:
                gap, is_direct = calc.electrons['bands'].get_bandgap()                
                calc.info['bandgap'] = round(gap, 2)
                calc.info['bandgaptype'] = 'direct' if is_direct else 'indirect'
                if gap<=1.0: calc.info['etype'] = 'semiconductor'
                else: calc.info['etype'] = 'insulator'
        
        # by DOS  
        if calc.electrons['dos']:
            
            gap = round(calc.electrons['dos'].get_bandgap(), 2)
            
            if calc.electrons['bands']: # check coincidence
                if abs(calc.info['bandgap'] - gap) > 0.2: calc.warning('Gaps in DOS and bands differ considerably! The latter is taken.')
            else:
                calc.info['bandgap'] = gap
                if gap:
                    if gap<=1.0: calc.info['etype'] = 'semiconductor'
                    else: calc.info['etype'] = 'insulator'
                else: calc.info['etype'] = 'metal'
        
        calc.benchmark() # this call must be at the very end of parsing

        return (calc, error)

    def _save_tags(self, for_checksum, tags_obj, update=False):
        '''
        Saves tags with checking
        @returns error
        '''
        tags = []
        cursor = self.db_conn.cursor()
        for n, i in enumerate(self.hierarchy):
            found_topics = []
            if '#' in i['source']:
                n=0
                while 1:
                    try: topic = tags_obj[ i['source'].replace('#', str(n)) ]
                    except KeyError:
                        if 'negative_tagging' in i and n==0 and not update: found_topics.append('none') # beware to add something new to an existing item!
                        elif 'unknown_tagging' in i and n==0 and not update: found_topics.append('unknown')
                        break
                    else:
                        found_topics.append(topic)
                        n+=1
            else:
                try: found_topics.append( tags_obj[ i['source'] ] )
                except KeyError:
                    if 'negative_tagging' in i and not update: found_topics.append('none') # beware to add something new to an existing item!
                    elif 'unknown_tagging' in i and not update: found_topics.append('unknown')

            for topic in found_topics:
                try: cursor.execute( 'SELECT tid FROM topics WHERE categ = ? AND topic = ?', (i['cid'], topic) )
                except: return 'Fatal error: %s' % sys.exc_info()[1]
                tid = cursor.fetchone()
                if tid: tid = tid[0]
                else:
                    try: cursor.execute( 'INSERT INTO topics (categ, topic) VALUES (?, ?)', (i['cid'], topic) )
                    except: return 'Fatal error: %s' % sys.exc_info()[1]
                    tid = cursor.lastrowid
                tags.append( (for_checksum, tid) )

        try: cursor.executemany( 'INSERT INTO tags (checksum, tid) VALUES (?, ?)', tags )
        except: return 'Fatal error: %s' % sys.exc_info()[1]

        return False

    def _save_preacts(self, calc):
        '''
        Prepares all for saving: converts Output instance *calc* into json strings
        @returns Tilde_obj
        '''
        # run apps and prepare their output
        for appname, output in self.postprocess(calc).iteritems():
            if output['error']:
                calc.warning( output['error'] )
            else:
                calc.apps[appname] = output['data']

        # prepare phonon data
        # this is actually
        # a dict to list conversion: TODO
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

        # prepare structural data
        #calc.structures[-1].orig_cif = generate_cif( calc.structures[-1], symops=calc['symops'] )
        calc.structures = [ase2dict(ase_obj) for ase_obj in calc.structures]
        
        # prepare electron data
        for i in ['dos', 'bands']:
            if calc.electrons[i]: calc.electrons[i] = calc.electrons[i].todict()
        
        # packing of the
        # Tilde ORM objects
        # NB: here they are except *info*
        # Why this is so?
        # We store the redundant copy
        # of tags marked with *has_column*
        # in results table (info field)
        # to speed up DB queries
        for i in ['structures', 'phonons', 'electrons', 'apps']:
            calc[i] = json.dumps(calc[i])

        return calc

    def save(self, calc, db_transfer_mode=False):
        '''
        Saves Tilde_obj into the database
        NB: this may be run from outside
        @returns (id, error)
        '''
        if not self.db_conn: return (None, 'Database is not connected!')
        
        checksum = calc.get_checksum()

        # check unique
        try:
            cursor = self.db_conn.cursor()
            cursor.execute( 'SELECT id FROM results WHERE checksum = ?', (checksum,) )
            row = cursor.fetchone()
            if row: return (checksum, None)
        except:
            error = 'Fatal error: %s' % sys.exc_info()[1]
            return (None, error)

        # save tags
        res = self._save_tags(checksum, calc.info)
        if res: return (None, 'Tags saving failed: '+res)
        
        if not db_transfer_mode: calc = self._save_preacts(calc)
        calc.info = json.dumps(calc.info)

        # save extracted data
        try:
            cursor.execute( 'INSERT INTO results (checksum, structures, energy, phonons, electrons, info, apps) VALUES ( ?, ?, ?, ?, ?, ?, ? )', \
            (checksum, calc.structures, calc.energy, calc.phonons, calc.electrons, calc.info, calc.apps) )
        except:
            error = 'Fatal error: %s' % sys.exc_info()[1]
            return (None, error)
        self.db_conn.commit()

        del calc

        return (checksum, None)

    def restore(self, db_row, db_transfer_mode=False):
        '''
        Restores Tilde_obj from the database
        NB: this may be run from outside
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
