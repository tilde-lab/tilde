
# Tilde project: basic routines
# v170513
# See http://wwwtilda.googlecode.com

__version__ = "0.2.1"

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

from numpy import dot
from numpy import array
from numpy.linalg import det

from common import generate_cif
from common import ModuleError
from symmetry import SymmetryFinder

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../'))
sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/deps'))
from ase.lattice.spacegroup.cell import cellpar_to_cell

class API:
    version = __version__
    __shared_state = {} # singleton

    def __init__(self, db_conn=None, filter=None, skip_if_path=None):

        self.__dict__ = self.__shared_state

        self.db_conn = db_conn
        self.filter = filter
        self.skip_if_path = skip_if_path

        self.deferred_storage = {}

        # *parser API*
        # Any python file in parsers subfolder will be treated as parser if its classes define a fingerprints method
        self.Parsers = {}
        for parserfile in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../parsers' ):
            if parserfile.endswith('.py') and parserfile != '__init__.py':
                parser_modules = __import__('parsers.' + parserfile[0:-3]) # all imported parsers will be included in this scope
        for i in dir(parser_modules):
            obj = getattr(parser_modules, i)
            if inspect.ismodule(obj):
                for j in dir(obj):
                    cls = getattr(obj, j)
                    if inspect.isclass(cls) and hasattr(cls, 'fingerprints'):
                        self.Parsers[j] = cls # all Tilde parsers will be here

        # *module API*
        # Tilde module (app) is simply a subfolder (%appfolder%) of apps folder containing manifest.json and %appfolder%.py files
        # The following tags in manifest matter:
        # *onprocess* - invoking during processing (therefore %appfolder%.py must provide the class called %Appfolder%)
        # *provides* - column caption in data table
        # *appdata* - a new property defined by app
        # *apptarget* - whether an app should be executed (based on hierarchy API)
        self.Apps = {}
        for appname in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../apps' ):
            if os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ):
                try: appmanifest = json.loads( open( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ).read() )
                except: raise RuntimeError('Module API Error: Module manifest for ' + appname + ' has corrupted format!')

                # tags processing
                if not 'appdata' in appmanifest: raise RuntimeError('Module API Error: no appdata tag for ' + appname + '!')
                if not 'apptarget' in appmanifest: appmanifest['apptarget'] = None
                if 'onprocess' in appmanifest:
                    try: app = __import__('apps.' + appname + '.' + appname, fromlist=[appname.capitalize()]) # this means: from foo import Foo
                    except ImportError: raise RuntimeError('Module API Error: module ' + appname + ' code is invalid or not found!')
                    self.Apps[appname] = {'appmodule': getattr(app, appname.capitalize()), 'appdata': appmanifest['appdata'], 'apptarget': appmanifest['apptarget'], 'provides': appmanifest['provides']}

        # *connector API*
        # Every connector implements reading methods *list* (if applicable) and *report* (obligatory)
        self.Conns = {}
        for connectname in os.listdir( os.path.realpath(os.path.dirname(__file__)) + '/../connectors' ):
            if connectname.endswith('.py') and connectname != '__init__.py':
                connectname = connectname[0:-3]
                conn = __import__('connectors.' + connectname) # this means: from foo import Foo
                self.Conns[connectname] = {'list': getattr(getattr(conn, connectname), 'list'), 'report': getattr(getattr(conn, connectname), 'report')}

        # *hierarchy API*
        # This is used while building topics (displayed at the splashscreen and tagcloud)
        self.hierarchy = [ \
            {"cid": 1, "category": "formula", "source": "standard", "chem_notation": True, "order": 1, "has_column": True}, \
            {"cid": 2, "category": "host elements number", "source": "nelem", "order": 13}, \
            {"cid": 3, "category": "supercell", "source": "expanded", "order": 29, "has_column": True}, \
            {"cid": 4, "category": "periodicity", "source": "periodicity", "order": 12, "has_column": True}, \
            {"cid": 5, "category": "calculation type", "source": "calctype#", "order": 10, "has_column": True}, \
            {"cid": 6, "category": "hamiltonian", "source": "H", "order": 30, "has_column": True}, \
            {"cid": 7, "category": "label", "source": "tag#", "order": 11, "has_column": True}, \
            {"cid": 8, "category": "result symmetry", "source": "symmetry", "negative_tagging": True, "order": 80, "has_column": True}, \
            {"cid": 9, "category": "result space group", "source": "sg", "negative_tagging": True, "order": 81, "has_column": True}, \
            {"cid": 10, "category": "result point group", "source": "pg", "negative_tagging": True, "order": 82, "has_column": True}, \
            {"cid": 90, "category": "main tolerances", "source": "tol", "order": 83, "has_column": True}, \
            {"cid": 91, "category": "spin-polarized", "source": "spin", "negative_tagging": True, "order": 22, "has_column": True}, \
            {"cid": 94, "category": "locked magn.state", "source": "lockstate", "order": 23, "has_column": True}, \
            {"cid": 92, "category": "k-points set", "source": "k", "order": 85, "has_column": True}, \
            {"cid": 93, "category": "used techniques", "source": "tech#", "order": 84, "has_column": True}, \
            #{"category": "code", "source": "code"}, \ <- this can be changed while merging!
            #{"category": "containing element", "source": "element#"}, \
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
                    if not 'order' in local_props[n]: local_props[n]['order'] = local_props[n]['cid']
                if local_props: self.hierarchy.extend( local_props )

                self.Classifiers.append({ \
                    'classify': getattr(getattr(obj, classifier), 'classify'),\
                    'order': getattr(getattr(obj, classifier), '__order__'),\
                    'class': classifier})
                self.Classifiers = sorted(self.Classifiers, key = lambda x: x['order'])

    def reload(self, db_conn=None, filter=None, skip_if_path=None):
        ''' __init__() in another context '''
        if db_conn: self.db_conn = db_conn
        if filter: self.filter = filter
        if skip_if_path: self.skip_if_path = skip_if_path

    def assign_parser(self, name):
        ''' Restricts parsing '''
        for n, p in self.Parsers.items():
            if n != name:
                del self.Parsers[n]
        if len(self.Parsers) != 1: raise RuntimeError('Parser cannot be assigned!')

    def formula(self, atom_sequence):
        ''' Constructs standardized chemical formula '''
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
        ''' Determines which files should be processed '''
        input_string = os.path.abspath(input_string)
        tasks = []
        restricted = [ symbol for symbol in self.skip_if_path ]

        # given folder
        if os.path.isdir(input_string):
            if recursive:
                for root, dirs, files in os.walk(input_string): # beware of broken links on unix! (NB find ~ -type l -exec rm -f {} \;)
                    # skip_if_path directive
                    to_filter = []
                    for dir in dirs:
                        for rs in restricted:
                            if dir.startswith(rs) or dir.endswith(rs):
                                to_filter.append(dir)
                                break
                    dirs[:] = [x for x in dirs if x not in to_filter] # keep reference
                    for filename in files:
                        # skip_if_path directive
                        for rs in restricted:
                            if filename.startswith(rs) or filename.endswith(rs): break
                        else: tasks.append(root + os.sep + filename)
            else:
                for filename in os.listdir(input_string):
                    if os.path.isfile(input_string + os.sep + filename):
                        # skip_if_path directive
                        for rs in restricted:
                            if filename.startswith(rs) or filename.endswith(rs): break
                        else: tasks.append(input_string + os.sep + filename)

        # given full filename
        elif os.path.isfile(input_string):
            tasks.append(input_string) # skip_if_path directive is not invoked here

        # given filename stemma
        else:
            if stemma:
                parent = os.path.dirname(input_string)
                for filename in os.listdir(parent):
                    if input_string in parent + os.sep + filename and not os.path.isdir(parent + os.sep + filename):
                        # skip_if_path directive
                        for rs in restricted:
                            if filename.startswith(rs) or filename.endswith(rs): break
                        else: tasks.append(parent + os.sep + filename)
        return tasks

    def _parse(self, parsable, parser_name, **missing_props):
        ''' Low-level parsing '''
        error = None
        calc = None
        try: calc = self.Parsers[parser_name](parsable, **missing_props)
        except RuntimeError, ex: error = "routine %s parser error: %s" % ( parser_name, ex )
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            error = "unexpected %s parser error in %s:\n %s" % ( parser_name, parsable, "".join(traceback.format_exception( exc_type, exc_value, exc_tb )) )
        return (calc, error)

    def parse(self, file):
        ''' High-level parsing: determines the data format and combines parent-children outputs '''
        error = None
        calc = None
        f = open(file, 'r')
        i = 0
        stop_read = False
        while 1:
            if i>1000 or stop_read: break # criterion: parser must detect its working format in first 1000 lines of output
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

        # (1) unsupported
        if calc is None and error is None: error = 'nothing found...'

        # (2) some CRYSTAL outputs contain not enough data -> they should be merged with other outputs
        if not error and calc._coupler_:
            calc._coupler_ = round(calc._coupler_, 5)
            if self.db_conn:
                cursor = self.db_conn.cursor()
                try: cursor.execute( 'SELECT id, checksum, structure, electrons, info FROM results WHERE ROUND(energy, 5) = ?', (calc._coupler_,) )
                except:
                    error = 'SQLite error: %s' % sys.exc_info()[1]
                    return (None, error)
                row = cursor.fetchone()
                if row is not None:
                    # in-place merging
                    strucs = json.loads(row['structure'])
                    e_props = json.loads(row['electrons'])
                    info = json.loads(row['info'])

                    props, error = self._parse(  file, 'CRYSTOUT', basisset=e_props['basisset'], atomtypes=[i[0] for i in strucs[-1]['atoms']]  )
                    if error: error = 'Merging of two outputs failed: ' + error
                    else:
                        # does merging make sense?

                        if not 'e_eigvals' in e_props: e_props['e_eigvals'] = props.e_eigvals
                        if 'e_eigvals' in e_props and len(e_props['e_eigvals'].keys()) < len(props.e_eigvals.keys()): e_props['e_eigvals'] = props.e_eigvals

                        if not 'e_proj_eigvals' in e_props:
                            e_proj_eigvals, impacts = [], []
                            for i in props.e_proj_eigv_impacts:
                                e_proj_eigvals.append(i['val'])
                                impacts.append(i['impacts'])
                            e_props['e_proj_eigvals'] = e_proj_eigvals
                            e_props['impacts'] = impacts

                            # update tags:
                            res = self.save_tags(row['checksum'], {'calctype0':'el.structure'}, update=True)
                            if res: return (None, 'Tags saving failed: '+res)

                        del props
                        electrons_json = json.dumps(e_props)
                        info['prog'] = 'CRYSTAL+PROPERTIES'
                        info_json = json.dumps(info)
                        try: cursor.execute( 'UPDATE results SET electrons = ?, info = ? WHERE id = ?', (electrons_json, info_json, row['id']) )
                        except:
                            error = 'SQLite error: %s' % sys.exc_info()[1]
                        else:
                            error = 'Merging of two outputs successful!' # TODO: this should not be error, but special type of msg

                else:
                    # deferred merging
                    self.deferred_storage[file] = calc._coupler_
                    error = 'OK, but merging with other output is required!'

            else: error = 'This file type is not supported in this usage regime!'

        # (3) check if we parsed something reasonable
        if not error and calc is not None:
            # corrections
            if not calc.structures[-1]['periodicity']: calc.structures[-1]['cell'] = [10, 10, 10, 90, 90, 90]

            if not len(calc.structures) or not calc.structures[-1]['atoms']: error = 'Valid structure is not present!'
            elif 0 in calc.structures[-1]['cell']: error = 'Cell data are corrupted!' # prevent cell collapses known in CRYSTAL outputs

            if calc.finished < 0: calc.warns.append( 'This calculation is not correctly finished!' )

            # (3.1) check whether a merging with some existing deferred item is required
            elif len(self.deferred_storage) and calc.energy:
                if round(calc.energy, 5) in self.deferred_storage.values():
                    deferred = [k for k, v in self.deferred_storage.iteritems() if v == round(calc.energy, 5)][0]
                    props, error = self._parse(  deferred, 'CRYSTOUT', basisset=calc.bs['bs'], atomtypes=[i[0] for i in calc.structures[-1]['atoms']]  )
                    if error: error = 'OK, but merging of two outputs failed: ' + error
                    else:
                        # does merging make sense?

                        if not calc.e_eigvals: calc.e_eigvals = props.e_eigvals
                        if calc.e_eigvals and len(calc.e_eigvals.keys()) < len(props.e_eigvals.keys()): calc.e_eigvals = props.e_eigvals
                        if not calc.e_proj_eigv_impacts: calc.e_proj_eigv_impacts = props.e_proj_eigv_impacts
                        calc.prog = 'CRYSTAL+PROPERTIES'
                    del props
                    del self.deferred_storage[deferred]

        return (calc, error)

    def postprocess(self, calc):
        ''' Invokes modules (apps) API '''
        apps = {}
        for appname, appclass in self.Apps.iteritems():
            run_permitted = False

            # scope-conditions
            if appclass['apptarget']:
                for key in appclass['apptarget']:
                    #if type(appclass['apptarget'][key]) is unicode: scope_prop = [ appclass['apptarget'][key] ]
                    #elif type(appclass['apptarget'][key]) is list: scope_prop = appclass['apptarget'][key]
                    #else: raise RuntimeError('Module API Error: apptarget for ' + appname + ' is of unknown type!')

                    negative = False
                    if appclass['apptarget'][key].startswith('!'):
                        negative = True
                        scope_prop = appclass['apptarget'][key][1:]
                    else: scope_prop = appclass['apptarget'][key]
                    if key in calc.classified:
                        if (scope_prop in calc.classified[key] or scope_prop == calc.classified[key]) != negative: # true if only one, but not both
                            run_permitted = True
                        else:
                            run_permitted = False
                            break

            else: run_permitted = True

            # running
            if run_permitted:
                apps[appname] = {'error': None, 'data': None}
                try: AppInstance = appclass['appmodule'](calc)
                except ModuleError, ex: apps[appname]['error'] = "%s module error: %s" % (appname, ex)
                except:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    apps[appname]['error'] = "%s module error:\n %s" % (appname, " / ".join(traceback.format_exception( exc_type, exc_value, exc_tb )))
                else:
                    try: apps[appname]['data'] = getattr(AppInstance, appclass['appdata'])
                    except AttributeError: apps[appname]['error'] = 'No appdata-defined property found!'
        return apps

    def classify(self, calc):
        ''' Invokes hierarchy API '''
        error = None
        dataitem = {'standard': '', 'formula': '', 'dims': 0, 'elements': [], 'contents': [], 'lack': False, 'expanded': False, 'properties': {}, 'tags': []}

        # applying filter: todo
        if calc.finished == -1 and self.filter:
            return (None, 'data do not satisfy the filter')
        
        xyz_matrix = cellpar_to_cell(calc.structures[-1]['cell'])
        
        dataitem['formula'] = self.formula( [i[0] for i in calc.structures[-1]['atoms']] )
        if calc.structures[-1]['periodicity'] == 3: dataitem['dims'] = abs(det(xyz_matrix))
        elif calc.structures[-1]['periodicity'] == 2: dataitem['dims'] = reduce(lambda x, y:x*y, sorted(calc.structures[-1]['cell'])[0:2])        
        
        fragments = re.findall(r'([A-Z][a-z]?)(\d*[?:.\d+]*)?', dataitem['formula'])
        for i in fragments:
            if i[0] == 'Xx': continue
            dataitem['elements'].append(i[0])
            dataitem['contents'].append(int(i[1])) if i[1] else dataitem['contents'].append(1)
        for C_obj in self.Classifiers:
            try: dataitem = C_obj['classify'](dataitem, calc)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                error = "Fatal error during classification:\n %s" % "".join(traceback.format_exception( exc_type, exc_value, exc_tb ))
                return (None, error)

        # post-processing tags
        if not len(dataitem['standard']):
            if len(dataitem['elements']) == 1: dataitem['expanded'] = 1
            if not dataitem['expanded']: dataitem['expanded'] = reduce(fractions.gcd, dataitem['contents'])
            for n, i in enumerate(map(lambda x: x/dataitem['expanded'], dataitem['contents'])):
                if i==1: dataitem['standard'] += dataitem['elements'][n]
                else: dataitem['standard'] += dataitem['elements'][n] + str(i)

        # calculated properties
        calctype = []
        if calc.phonons: calctype.append('phonons')
        if calc.ph_k_degeneracy: calctype.append('phon.dispersion')
        if calc.tresholds or len( getattr(calc, 'ionic_steps', []) ) > 1: calctype.append('optimization')
        if (calc.e_proj_eigv_impacts and calc.e_eigvals) or getattr(calc, 'complete_dos', None): calctype.append('el.structure')
        if calc.energy: calctype.append('total energy')
        for n, i in enumerate(calctype): dataitem['calctype' + str(n)] = i

        # getting and standardizing methods
        if calc.method:
            if calc.method['H']: dataitem['H'] = calc.method['H']
            if calc.method['tol']: dataitem['tol'] = calc.method['tol']
            if calc.method['k']: dataitem['k'] = calc.method['k']
            if calc.method['spin']: dataitem['spin'] = 'yes'
            if calc.method['lockstate'] is not None: dataitem['lockstate'] = calc.method['lockstate']
            tech = []
            if calc.method['technique'].keys():
                for i in calc.method['technique'].keys():
                    if i=='anderson': tech.append(i)
                    elif i=='fmixing':
                        if 0<calc.method['technique'][i]<=25:    tech.append(i + '<25%')
                        elif 25<calc.method['technique'][i]<=50: tech.append(i + ' 25-50%')
                        elif 50<calc.method['technique'][i]<=75: tech.append(i + ' 50-75%')
                        elif 75<calc.method['technique'][i]<=90: tech.append(i + ' 75-90%')
                        elif 90<calc.method['technique'][i]:     tech.append(i + '>90%')
                    elif i=='shifter':
                        if 0<calc.method['technique'][i]<=0.5:   tech.append(i + '<0.5au')
                        elif 0.5<calc.method['technique'][i]<=1: tech.append(i + ' 0.5-1au')
                        elif 1<calc.method['technique'][i]<=2.5: tech.append(i + ' 1-2.5au')
                        elif 2.5<calc.method['technique'][i]:    tech.append(i + '>2.5au')
                    elif i=='smear':
                        if 0<calc.method['technique'][i]<=0.005:      tech.append(i + '<0.005au')
                        elif 0.005<calc.method['technique'][i]<=0.01: tech.append(i + ' 0.005-0.01au')
                        elif 0.01<calc.method['technique'][i]:        tech.append(i + '>0.01au')
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
                        tech.append(i + type)
            if 'vac' in dataitem['properties']:
                if 'Xx' in [i[0] for i in calc.structures[-1]['atoms']]: tech.append('defect as ghost')
                else: tech.append('defect as void space')
            for n, i in enumerate(tech): dataitem['tech' + str(n)] = i

        for n, i in enumerate(dataitem['elements']): dataitem['element' + str(n)] = i
        for n, i in enumerate(dataitem['tags']): dataitem['tag' + str(n)] = i
        dataitem['nelem'] = len(dataitem['elements'])
        dataitem['code'] = calc.prog
        if dataitem['expanded']: dataitem['expanded'] = str(dataitem['expanded']) + 'x'
        else: del dataitem['expanded']
        if calc.structures[-1]['periodicity'] == 3: dataitem['periodicity'] = '3-periodic'
        elif calc.structures[-1]['periodicity'] == 2: dataitem['periodicity'] = '2-periodic'
        elif calc.structures[-1]['periodicity'] == 1: dataitem['periodicity'] = '1-periodic'
        elif calc.structures[-1]['periodicity'] == 0: dataitem['periodicity'] = 'non-periodic'
        for k, v in dataitem['properties'].iteritems(): dataitem[k] = v

        # invoke symmetry finder
        found = SymmetryFinder(calc)
        if found.error: return (None, found.error)

        dataitem['sg'] = found.i

        # data from Bandura-Evarestov book "Non-emp calculations of crystals", 2004, ISBN 5-288-03401-X
        if   195 <= found.n <= 230: dataitem['symmetry'] = 'cubic'
        elif 168 <= found.n <= 194: dataitem['symmetry'] = 'hexagonal'
        elif 143 <= found.n <= 167: dataitem['symmetry'] = 'rhombohedral'
        elif 75  <= found.n <= 142: dataitem['symmetry'] = 'tetragonal'
        elif 16  <= found.n <= 74:  dataitem['symmetry'] = 'orthorhombic'
        elif 3   <= found.n <= 15:  dataitem['symmetry'] = 'monoclinic'
        elif 1   <= found.n <= 2:   dataitem['symmetry'] = 'triclinic'
        # data from Bandura-Evarestov book "Non-emp calculations of crystals", 2004, ISBN 5-288-03401-X
        if   221 <= found.n <= 230: dataitem['pg'] = 'O<sub>h</sub>'
        elif 215 <= found.n <= 220: dataitem['pg'] = 'T<sub>d</sub>'
        elif 207 <= found.n <= 214: dataitem['pg'] = 'O'
        elif 200 <= found.n <= 206: dataitem['pg'] = 'T<sub>h</sub>'
        elif 195 <= found.n <= 199: dataitem['pg'] = 'T'
        elif 191 <= found.n <= 194: dataitem['pg'] = 'D<sub>6h</sub>'
        elif 187 <= found.n <= 190: dataitem['pg'] = 'D<sub>3h</sub>'
        elif 183 <= found.n <= 186: dataitem['pg'] = 'C<sub>6v</sub>'
        elif 177 <= found.n <= 182: dataitem['pg'] = 'D<sub>6</sub>'
        elif 175 <= found.n <= 176: dataitem['pg'] = 'C<sub>6h</sub>'
        elif found.n == 174:        dataitem['pg'] = 'C<sub>3h</sub>'
        elif 168 <= found.n <= 173: dataitem['pg'] = 'C<sub>6</sub>'
        elif 162 <= found.n <= 167: dataitem['pg'] = 'D<sub>3d</sub>'
        elif 156 <= found.n <= 161: dataitem['pg'] = 'C<sub>3v</sub>'
        elif 149 <= found.n <= 155: dataitem['pg'] = 'D<sub>3</sub>'
        elif 147 <= found.n <= 148: dataitem['pg'] = 'C<sub>3i</sub>'
        elif 143 <= found.n <= 146: dataitem['pg'] = 'C<sub>3</sub>'
        elif 123 <= found.n <= 142: dataitem['pg'] = 'D<sub>4h</sub>'
        elif 111 <= found.n <= 122: dataitem['pg'] = 'D<sub>2d</sub>'
        elif 99 <= found.n <= 110:  dataitem['pg'] = 'C<sub>4v</sub>'
        elif 89 <= found.n <= 98:   dataitem['pg'] = 'D<sub>4</sub>'
        elif 83 <= found.n <= 88:   dataitem['pg'] = 'C<sub>4h</sub>'
        elif 81 <= found.n <= 82:   dataitem['pg'] = 'S<sub>4</sub>'
        elif 75 <= found.n <= 80:   dataitem['pg'] = 'C<sub>4</sub>'
        elif 47 <= found.n <= 74:   dataitem['pg'] = 'D<sub>2h</sub>'
        elif 25 <= found.n <= 46:   dataitem['pg'] = 'C<sub>2v</sub>'
        elif 16 <= found.n <= 24:   dataitem['pg'] = 'D<sub>2</sub>'
        elif 10 <= found.n <= 15:   dataitem['pg'] = 'C<sub>2h</sub>'
        elif 6 <= found.n <= 9:     dataitem['pg'] = 'C<sub>s</sub>'
        elif 3 <= found.n <= 5:     dataitem['pg'] = 'C<sub>2</sub>'
        elif found.n == 2:          dataitem['pg'] = 'C<sub>i</sub>'
        elif found.n == 1:          dataitem['pg'] = 'C<sub>1</sub>'

        calc.classified = dataitem

        return (calc, error)

    def save_tags(self, for_checksum, classified, update=False):
        ''' Saves tags with checking '''
        #result, error = [], None
        tags = []
        cursor = self.db_conn.cursor()
        for n, i in enumerate(self.hierarchy):
            found_topics = []
            if '#' in i['source']:
                n=0
                while 1:
                    try: topic = classified[ i['source'].replace('#', str(n)) ]
                    except KeyError:
                        if 'negative_tagging' in i and n==0 and not update: found_topics.append('none') # beware to add something new to an existing item!
                        break
                    else:
                        found_topics.append(topic)
                        n+=1
            else:
                try: found_topics.append( classified[ i['source'] ] )
                except KeyError:
                    if 'negative_tagging' in i and not update: found_topics.append('none') # beware to add something new to an existing item!

            #if 'has_column' in i and len(found_topics):
            #    result.append()

            for topic in found_topics:
                try: cursor.execute( 'SELECT tid FROM topics WHERE categ = ? AND topic = ?', (i['cid'], topic) )
                except: return 'SQLite error: %s' % sys.exc_info()[1]
                tid = cursor.fetchone()
                if tid: tid = tid[0]
                else:
                    try: cursor.execute( 'INSERT INTO topics (categ, topic) VALUES (?, ?)', (i['cid'], topic) )
                    except: return 'SQLite error: %s' % sys.exc_info()[1]
                    tid = cursor.lastrowid
                tags.append( (for_checksum, tid) )

        try: cursor.executemany( 'INSERT INTO tags (checksum, tid) VALUES (?, ?)', tags )
        except: return 'SQLite error: %s' % sys.exc_info()[1]

        return False

    def save(self, calc, for_user=0):
        ''' Prepares and saves tags and data '''
        checksum = calc.checksum()

        # check unique
        try:
            cursor = self.db_conn.cursor()
            cursor.execute( 'SELECT uid FROM results WHERE checksum = ?', (checksum,) )
            row = cursor.fetchone()
            if row: return (checksum, None)
        except:
            error = 'SQLite error: %s' % sys.exc_info()[1]
            return (None, error)

        # run apps and pack their output
        apps_json = {}
        for appname, output in self.postprocess(calc).iteritems():
            if output['error']:
                calc.warns.append( output['error'] )
            else:
                apps_json[appname] = output['data']
        apps_json = json.dumps(apps_json)

        # save tags
        res = self.save_tags(checksum, calc.classified)
        if res: return (None, 'Tags saving failed: '+res)

        xyz_matrix = cellpar_to_cell(calc.structures[-1]['cell'])

        # pack phonon data
        phonons_json = None
        if calc.phonons:
            phonons_json = []

            '''# check if fake (ghost) atoms are involved into a vibration
            for k, atomi in enumerate(calc.structures[-1]['atoms']):
                if atomi[0] == 'Xx' and len(calc.ph_eigvecs['0 0 0'])/3 != len(calc.structures[-1]['atoms']):
                    # insert fake zero vectors
                    for bz, item in calc.ph_eigvecs.iteritems():
                        for n in range(len(item)):
                            for i in range(3):
                                calc.ph_eigvecs[bz][n].insert(k*3, 0)'''

            for bzpoint, frqset in calc.phonons.iteritems():
                # re-orientate eigenvectors
                for i in range(0, len(calc.ph_eigvecs[bzpoint])):
                    for j in range(0, len(calc.ph_eigvecs[bzpoint][i])/3):
                        eigv = array([calc.ph_eigvecs[bzpoint][i][j*3], calc.ph_eigvecs[bzpoint][i][j*3+1], calc.ph_eigvecs[bzpoint][i][j*3+2]])
                        R = dot( eigv, xyz_matrix ).tolist()
                        calc.ph_eigvecs[bzpoint][i][j*3], calc.ph_eigvecs[bzpoint][i][j*3+1], calc.ph_eigvecs[bzpoint][i][j*3+2] = map(lambda x: round(x, 3), R)
                try: irreps = calc.irreps[bzpoint]
                except (KeyError, TypeError):
                    empty = []
                    for i in range(len(frqset)): empty.append('')
                    irreps = empty
                phonons_json.append({  'bzpoint':bzpoint, 'freqs':frqset, 'irreps':irreps, 'ph_eigvecs':calc.ph_eigvecs[bzpoint]  })
                if bzpoint == '0 0 0':
                    phonons_json[-1]['ir_active'] = calc['ir_active']
                    phonons_json[-1]['raman_active'] = calc['raman_active']
                if calc['ph_k_degeneracy']:
                    phonons_json[-1]['ph_k_degeneracy'] = calc['ph_k_degeneracy'][bzpoint]
            phonons_json = json.dumps(phonons_json)

        # pack structural data
        structure_json = []
        #if calc['ph_k_degeneracy']: current_N_atoms = len(calc.ph_eigvecs['0 0 0'])/3 # accounted atoms are on top of the supercell
        #structure_json['end']['xyz'] = generate_xyz( calc['end_frac_structure']['cell'], calc['end_frac_structure']['atoms'][0:current_N_atoms] )
        structure_json.extend( calc.structures )
        structure_json[-1]['orig_cif'] = generate_cif( calc.structures[-1]['cell'], calc.structures[-1]['atoms'], calc['symops'] )
        structure_json[-1]['dims'] = calc.classified['dims']
        structure_json = json.dumps(structure_json)

        # pack metadata
        info_json = {'perf': "%1.2f" % calc.perf(), 'warns': calc.warns, 'prog': calc.prog, 'location': calc.location, 'finished': calc.finished}
        for item in self.hierarchy:
            if 'has_column' in item:
                if '#' in item['source']: continue # todo
                if item['source'] in calc.classified: info_json[ item['source'] ] = calc.classified[ item['source'] ]
        info_json = json.dumps(info_json)

        # pack electronic structure data
        electrons_json = {}
        if calc.bs and 'bs' in calc.bs:
            # this is for CRYSTAL merging
            electrons_json.update(  {'basisset': calc.bs['bs']}  )
        if calc.e_eigvals:
            # this is for band structure plotting
            electrons_json.update(  {'e_eigvals': calc.e_eigvals}  )
        if calc.e_proj_eigv_impacts:
            # this is for CRYSTAL DOS calculation and plotting
            e_proj_eigvals, impacts = [], []
            for i in calc.e_proj_eigv_impacts:
                e_proj_eigvals.append(i['val'])
                impacts.append(i['impacts'])
            electrons_json.update(  {'e_proj_eigvals': e_proj_eigvals, 'impacts': impacts}  )
        if getattr(calc, 'complete_dos', None):
            # this is for VASP DOS plotting
            electrons_json.update(  {'dos': calc.complete_dos}  )
        electrons_json = json.dumps(electrons_json)

        # save extracted data
        try:
            cursor.execute( 'INSERT INTO results (uid, checksum, structure, energy, phonons, electrons, info, apps) VALUES ( ?, ?, ?, ?, ?, ?, ?, ? )', (for_user, checksum, structure_json, calc['energy'], phonons_json, electrons_json, info_json, apps_json) )
        except:
            error = 'SQLite error: %s' % sys.exc_info()[1]
            return (None, error)
        self.db_conn.commit()
        del calc
        del phonons_json
        del structure_json
        del electrons_json
        return (checksum, None)
