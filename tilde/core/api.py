
# Functionality exposed as an API
# Author: Evgeny Blokhin

__version__ = "0.8.0"

import os, sys
import re
from fractions import gcd
import inspect
import traceback
import datetime
import importlib

from numpy import dot, array

from tilde.core.common import u, is_binary_string, generate_cif, html_formula, hrsize
from tilde.core.symmetry import SymmetryHandler
from tilde.core.settings import BASE_DIR, settings, virtualize_path, get_hierarchy
from tilde.core.electron_structure import ElectronStructureError
from tilde.parsers import Output
import tilde.core.model as model

from ase.data import chemical_symbols
from ase.geometry import cell_to_cellpar
from sqlalchemy import exists, func
from sqlalchemy.orm.exc import NoResultFound

import ujson as json
from functools import reduce


class API:
    version = __version__
    __shared_state = {}
    formula_sequence = ['Fr','Cs','Rb','K','Na','Li',  'Be','Mg','Ca','Sr','Ba','Ra',  'Sc','Y','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb',  'Ac','Th','Pa','U','Np','Pu',  'Ti','Zr','Hf',  'V','Nb','Ta',  'Cr','Mo','W',  'Fe','Ru','Os',  'Co','Rh','Ir',  'Mn','Tc','Re',  'Ni','Pd','Pt',  'Cu','Ag','Au',  'Zn','Cd','Hg',  'B','Al','Ga','In','Tl',  'Pb','Sn','Ge','Si','C',   'N','P','As','Sb','Bi',   'H',   'Po','Te','Se','S','O',  'At','I','Br','Cl','F',  'He','Ne','Ar','Kr','Xe','Rn']

    def __init__(self, settings=settings):
        self.settings = settings

        # Default hierarchy is set in the file init-data.sql
        # Conventionally, the hierarchy values are set by hexadecimal numbers (with leading 0x)
        self.hierarchy, self.hierarchy_groups, self.hierarchy_values = get_hierarchy(settings)

        # *parser API*
        # Subfolder "parsers" contains directories with parsers.
        # Parser will be active if:
        # (1) its class defines a fingerprints method
        # (2) it is enabled by its manifest file
        # (3) its filename repeats the name of parser folder
        All_parsers, self.Parsers = {}, {}
        for parsername in os.listdir( os.path.realpath(BASE_DIR + '/../parsers') ):
            if self.settings.get('no_parse'): continue
            if not os.path.isfile( os.path.realpath(BASE_DIR + '/../parsers') + '/' + parsername + '/manifest.json' ): continue
            if not os.path.isfile( os.path.realpath(BASE_DIR + '/../parsers') + '/' + parsername + '/' + parsername + '.py' ):
                raise RuntimeError('Parser API Error: Parser code for ' + parsername + ' is missing!')
            try: parsermanifest = json.loads( open( os.path.realpath(BASE_DIR + '/../parsers') + '/' + parsername + '/manifest.json' ).read() )
            except: raise RuntimeError('Parser API Error: Parser manifest for ' + parsername + ' has corrupted format!')

            if (not 'enabled' in parsermanifest or not parsermanifest['enabled']) and not self.settings['debug_regime']: continue

            All_parsers[parsername] = importlib.import_module('tilde.parsers.' + parsername + '.' + parsername) # all imported modules will be stored here

        # replace modules by classes and check *fingerprints* method
        for parser, module in All_parsers.items():
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
        for appname in os.listdir( os.path.realpath(BASE_DIR + '/../apps') ):
            if self.settings.get('no_parse'): continue
            if os.path.isfile( os.path.realpath(BASE_DIR + '/../apps') + '/' + appname + '/manifest.json' ):
                try: appmanifest = json.loads( open( os.path.realpath(BASE_DIR + '/../apps') + '/' + appname + '/manifest.json' ).read() )
                except: raise RuntimeError('Module API Error: Module manifest for ' + appname + ' has corrupted format!')

                # tags processing
                if not 'appdata' in appmanifest: raise RuntimeError('Module API Error: no appdata tag for ' + appname + '!')
                if 'onprocess' in appmanifest:
                    try: app = __import__('tilde.apps.' + appname + '.' + appname, fromlist=[appname.capitalize()]) # this means: from foo import Foo
                    except ImportError:
                        raise RuntimeError('Module API Error: module ' + appname + ' is invalid or not found!')
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
        for connectname in os.listdir( os.path.realpath(BASE_DIR + '/../connectors') ):
            if connectname.endswith('.py') and connectname != '__init__.py':
                connectname = connectname[0:-3]
                conn = importlib.import_module('tilde.connectors.' + connectname) # this means: from foo import Foo
                self.Conns[connectname] = {'list': getattr(conn, 'list'), 'report': getattr(conn, 'report')}

        # *hierarchy API*
        # This is used for classification
        self.Classifiers = []
        for classifier in os.listdir( os.path.realpath(BASE_DIR + '/../classifiers') ):
            if self.settings.get('no_parse'): continue
            if classifier.endswith('.py') and classifier != '__init__.py':
                classifier = classifier[0:-3]
                obj = importlib.import_module('tilde.classifiers.' + classifier) # this means: from foo import Foo
                if getattr(obj, '__order__') is None: raise RuntimeError('Classifier %s has not defined an order to apply!' % classifier)

                self.Classifiers.append({
                    'classify': getattr(obj, 'classify'),\
                    'order': getattr(obj, '__order__'),\
                    'class': classifier})
                self.Classifiers = sorted(self.Classifiers, key = lambda x: x['order'])

    def assign_parser(self, name):
        '''
        Restricts parsing
        **name** is a name of the parser class
        NB: this is the PUBLIC method
        @procedure
        '''
        for n, p in list(self.Parsers.items()):
            if n != name:
                del self.Parsers[n]
        if len(self.Parsers) != 1: raise RuntimeError('Parser cannot be assigned!')

    def formula(self, atom_sequence):
        '''
        Constructs standardized chemical formula
        NB: this is the PUBLIC method
        @returns formula_str
        '''
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
        atoms = list(labels.keys())
        atoms = [x for x in self.formula_sequence if x in atoms] + [x for x in atoms if x not in self.formula_sequence] # accordingly
        formula = ''
        for atom in atoms:
            n = len(types[labels[atom]])
            if n==1: n = ''
            else: n = str(n)
            formula += atom + n
        return formula

    def count(self, session):
        return session.query(func.count(model.Calculation.checksum)).one()[0]

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
                    dirs[:] = [x for x in dirs if x not in to_filter]
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
            tasks.append(input_string) # skip_if_path directive is not applicable here

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

    def _parse(self, parsable, parser_name):
        '''
        Low-level parsing
        NB: this is the PRIVATE method
        @returns tilde_obj, error
        '''
        calc, error = None, None
        try:
            for calc in self.Parsers[parser_name].iparse(parsable):
                yield calc, None
            return
        except RuntimeError as e: error = "routine %s parser error in %s: %s" % ( parser_name, parsable, e )
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            error = "unexpected %s parser error in %s:\n %s" % ( parser_name, parsable, "".join(traceback.format_exception( exc_type, exc_value, exc_tb )) )
        yield None, error

    def parse(self, parsable):
        '''
        High-level parsing:
        determines the data format
        and combines parent-children outputs
        NB: this is the PUBLIC method
        @returns tilde_obj, error
        '''
        calc, error = None, None
        try:
            f = open(parsable, 'rb')
            if is_binary_string(f.read(2048)):
                yield None, 'was read (binary data)...'
                return
            f.close()
        except IOError:
            yield None, 'read error!'
            return
        f = open(parsable, 'r')  # open the file once again with right mode
        f.seek(0)
        i, detected = 0, False
        while not detected:
            if i>700: break # criterion: parser must detect its working format in first N lines of output
            fingerprint = f.readline()
            if not fingerprint: break
            for name, Parser in self.Parsers.items():
                if Parser.fingerprints(fingerprint):
                    for calc, error in self._parse(parsable, name):
                        detected = True
                        # check if we parsed something reasonable
                        if not error and calc:

                            if not len(calc.structures) or not len(calc.structures[-1]): error = 'Valid structure is not present!'

                            if calc.info['finished'] == 0x1: calc.warning( 'This calculation is not correctly finished!' )

                            if not calc.info['H']: error = 'XC potential is not present!'

                        yield calc, error

                    if detected: break
            i += 1
        f.close()

        # unsupported data occured
        if not detected: yield None, 'was read...'

    def classify(self, calc, symprec=None):
        '''
        Reasons on normalization, invokes hierarchy API and prepares calc for saving
        NB: this is the PUBLIC method
        @returns tilde_obj, error
        '''
        error = None
        symbols = calc.structures[-1].get_chemical_symbols()
        calc.info['formula'] = self.formula(symbols)
        calc.info['cellpar'] = cell_to_cellpar(calc.structures[-1].cell).tolist()
        if calc.info['input']:
            try: calc.info['input'] = str(calc.info['input'], errors='ignore')
            except: pass

        # applying filter: todo
        if (calc.info['finished'] == 0x1 and self.settings['skip_unfinished']) or \
           (not calc.info['energy'] and self.settings['skip_notenergy']):
            return None, 'data do not satisfy the active filter'

        # naive elements extraction
        fragments = re.findall(r'([A-Z][a-z]?)(\d*[?:.\d+]*)?', calc.info['formula'])
        for i in fragments:
            if i[0] == 'X': continue
            calc.info['elements'].append(i[0])
            calc.info['contents'].append(int(i[1])) if i[1] else calc.info['contents'].append(1)

        # extend hierarchy with modules
        for C_obj in self.Classifiers:
            try: calc = C_obj['classify'](calc)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                error = "Fatal error during classification:\n %s" % "".join(traceback.format_exception( exc_type, exc_value, exc_tb ))
                return None, error

        # chemical ratios
        if not len(calc.info['standard']):
            if len(calc.info['elements']) == 1: calc.info['expanded'] = 1
            if not calc.info['expanded']: calc.info['expanded'] = reduce(gcd, calc.info['contents'])
            for n, i in enumerate([x//calc.info['expanded'] for x in calc.info['contents']]):
                if i==1: calc.info['standard'] += calc.info['elements'][n]
                else: calc.info['standard'] += calc.info['elements'][n] + str(i)
        if not calc.info['expanded']: del calc.info['expanded']
        calc.info['nelem'] = len(calc.info['elements'])
        if calc.info['nelem'] > 13: calc.info['nelem'] = 13
        calc.info['natom'] = len(symbols)

        # periodicity
        if calc.info['periodicity'] == 0: calc.info['periodicity'] = 0x4
        elif calc.info['periodicity'] == -1: calc.info['periodicity'] = 0x5

        # general calculation type reasoning
        if (calc.structures[-1].get_initial_charges() != 0).sum(): calc.info['calctypes'].append(0x4) # numpy count_nonzero implementation
        if (calc.structures[-1].get_initial_magnetic_moments() != 0).sum(): calc.info['calctypes'].append(0x5)
        if calc.phonons['modes']: calc.info['calctypes'].append(0x6)
        if calc.phonons['ph_k_degeneracy']: calc.info['calctypes'].append(0x7)
        if calc.phonons['dielectric_tensor']: calc.info['calctypes'].append(0x8) # CRYSTAL-only!
        if len(calc.tresholds) > 1:
            calc.info['calctypes'].append(0x3)
            calc.info['optgeom'] = True
        if calc.electrons['dos'] or calc.electrons['bands']: calc.info['calctypes'].append(0x2)
        if calc.info['energy']: calc.info['calctypes'].append(0x1)
        calc.info['spin'] = 0x2 if calc.info['spin'] else 0x1

        # TODO: standardize
        if 'vac' in calc.info:
            if 'X' in symbols: calc.info['techs'].append('vacancy defect: ghost')
            else: calc.info['techs'].append('vacancy defect: void space')

        calc.info['lata'] = round(calc.info['cellpar'][0], 3)
        calc.info['latb'] = round(calc.info['cellpar'][1], 3)
        calc.info['latc'] = round(calc.info['cellpar'][2], 3)
        calc.info['latalpha'] = round(calc.info['cellpar'][3], 2)
        calc.info['latbeta'] = round(calc.info['cellpar'][4], 2)
        calc.info['latgamma'] = round(calc.info['cellpar'][5], 2)

        # invoke symmetry finder
        found = SymmetryHandler(calc, symprec)
        if found.error:
            return None, found.error
        calc.info['sg'] = found.i
        calc.info['ng'] = found.n
        calc.info['symmetry'] = found.symmetry
        calc.info['spg'] = "%s &mdash; %s" % (found.n, found.i)
        calc.info['pg'] = found.pg
        calc.info['dg'] = found.dg

        # phonons
        if calc.phonons['dfp_magnitude']: calc.info['dfp_magnitude'] = round(calc.phonons['dfp_magnitude'], 3)
        if calc.phonons['dfp_disps']: calc.info['dfp_disps'] = len(calc.phonons['dfp_disps'])
        if calc.phonons['modes']:
            calc.info['n_ph_k'] = len(calc.phonons['ph_k_degeneracy']) if calc.phonons['ph_k_degeneracy'] else 1

        #calc.info['rgkmax'] = calc.electrons['rgkmax'] # LAPW

        # electronic properties reasoning by bands
        if calc.electrons['bands']:
            if calc.electrons['bands'].is_conductor():
                calc.info['etype'] = 0x2
                calc.info['bandgap'] = 0.0
                calc.info['bandgaptype'] = 0x1
            else:
                try: gap, is_direct = calc.electrons['bands'].get_bandgap()
                except ElectronStructureError as e:
                    calc.electrons['bands'] = None
                    calc.warning(e.value)
                else:
                    calc.info['etype'] = 0x1
                    calc.info['bandgap'] = round(gap, 2)
                    calc.info['bandgaptype'] = 0x2 if is_direct else 0x3

        # electronic properties reasoning by DOS
        if calc.electrons['dos']:
            try: gap = round(calc.electrons['dos'].get_bandgap(), 2)
            except ElectronStructureError as e:
                calc.electrons['dos'] = None
                calc.warning(e.value)
            else:
                if calc.electrons['bands']: # check coincidence
                    if abs(calc.info['bandgap'] - gap) > 0.2: calc.warning('Bans gaps in DOS and bands data differ considerably! The latter will be considered.')
                else:
                    calc.info['bandgap'] = gap
                    if gap: calc.info['etype'] = 0x1
                    else:
                        calc.info['etype'] = 0x2
                        calc.info['bandgaptype'] = 0x1

        # TODO: beware to add something new to an existing item!
        # TODO2: unknown or absent?
        for entity in self.hierarchy:
            if entity['creates_topic'] and not entity['optional'] and not calc.info.get(entity['source']):
                if entity['enumerated']:
                    calc.info[ entity['source'] ] = [0x0] if entity['multiple'] else 0x0
                else:
                    calc.info[ entity['source'] ] = ['none'] if entity['multiple'] else 'none'

        calc.benchmark() # this call must be at the very end of parsing

        return calc, error

    def postprocess(self, calc, with_module=None, dry_run=None):
        '''
        Invokes module(s) API
        NB: this is the PUBLIC method
        @returns apps_dict
        '''
        for appname, appclass in self.Apps.items():
            if with_module and with_module != appname: continue

            run_permitted = False

            # scope-conditions
            if appclass['apptarget']:
                for key in appclass['apptarget']:
                    negative = False
                    if str(appclass['apptarget'][key]).startswith('!'):
                        negative = True
                        scope_prop = appclass['apptarget'][key][1:]
                    else:
                        scope_prop = appclass['apptarget'][key]

                    if key in calc.info:
                        # non-strict comparison ("CRYSTAL" matches "CRYSTAL09 v2.0")
                        if (str(scope_prop) in str(calc.info[key]) or scope_prop == calc.info[key]) != negative: # true if only one, but not both
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

    def save(self, calc, session):
        '''
        Saves tilde_obj into the database
        NB: this is the PUBLIC method
        @returns checksum, error
        '''
        checksum = calc.get_checksum()

        try: existing_calc = session.query(model.Calculation).filter(model.Calculation.checksum == checksum).one()
        except NoResultFound: pass
        else:
            del calc
            return None, "This calculation already exists!"

        if not calc.download_size:
            for f in calc.related_files:
                calc.download_size += os.stat(f).st_size

        ormcalc = model.Calculation(checksum = checksum)

        if calc._calcset:
            ormcalc.meta_data = model.Metadata(chemical_formula = calc.info['standard'], download_size = calc.download_size)

            for child in session.query(model.Calculation).filter(model.Calculation.checksum.in_(calc._calcset)).all():
                ormcalc.children.append(child)
            ormcalc.siblings_count = len(ormcalc.children)
            ormcalc.nested_depth = calc._nested_depth

        else:
            # prepare phonon data for saving
            # this is actually a dict to list conversion TODO re-structure this
            if calc.phonons['modes']:
                phonons_json = []

                for bzpoint, frqset in calc.phonons['modes'].items():
                    # re-orientate eigenvectors
                    for i in range(0, len(calc.phonons['ph_eigvecs'][bzpoint])):
                        for j in range(0, len(calc.phonons['ph_eigvecs'][bzpoint][i])//3):
                            eigv = array([calc.phonons['ph_eigvecs'][bzpoint][i][j*3], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+1], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+2]])
                            R = dot( eigv, calc.structures[-1].cell ).tolist()
                            calc.phonons['ph_eigvecs'][bzpoint][i][j*3], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+1], calc.phonons['ph_eigvecs'][bzpoint][i][j*3+2] = [round(x, 3) for x in R]

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

                ormcalc.phonons = model.Phonons()
                ormcalc.spectra.append( model.Spectra(kind = model.Spectra.PHONON, eigenvalues = json.dumps(phonons_json)) )

            # prepare electron data for saving TODO re-structure this
            for i in ['dos', 'bands']: # projected?
                if calc.electrons[i]: calc.electrons[i] = calc.electrons[i].todict()

            if calc.electrons['dos'] or calc.electrons['bands']:
                ormcalc.electrons = model.Electrons(gap = calc.info['bandgap'])
                if 'bandgaptype' in calc.info: ormcalc.electrons.is_direct = 1 if calc.info['bandgaptype'] == 'direct' else -1
                ormcalc.spectra.append(model.Spectra(
                    kind = model.Spectra.ELECTRON,
                    dos = json.dumps(calc.electrons['dos']),
                    bands = json.dumps(calc.electrons['bands']),
                    projected = json.dumps(calc.electrons['projected']),
                    eigenvalues = json.dumps(calc.electrons['eigvals']))
                )

            # construct ORM for other props
            calc.related_files = list(map(virtualize_path, calc.related_files))
            ormcalc.meta_data = model.Metadata(location = calc.info['location'], finished = calc.info['finished'], raw_input = calc.info['input'], modeling_time = calc.info['duration'], chemical_formula = html_formula(calc.info['standard']), download_size = calc.download_size, filenames = json.dumps(calc.related_files))

            codefamily = model.Codefamily.as_unique(session, content = calc.info['framework'])
            codeversion = model.Codeversion.as_unique(session, content = calc.info['prog'])

            codeversion.instances.append( ormcalc.meta_data )
            codefamily.versions.append( codeversion )

            pot = model.Pottype.as_unique(session, name = calc.info['H'])
            pot.instances.append(ormcalc)
            ormcalc.recipinteg = model.Recipinteg(kgrid = calc.info['k'], kshift = calc.info['kshift'], smearing = calc.info['smear'], smeartype = calc.info['smeartype'])
            ormcalc.basis = model.Basis(kind = calc.info['ansatz'], content = json.dumps(calc.electrons['basis_set']) if calc.electrons['basis_set'] else None)
            ormcalc.energy = model.Energy(convergence = json.dumps(calc.convergence), total = calc.info['energy'])

            ormcalc.spacegroup = model.Spacegroup(n=calc.info['ng'])
            ormcalc.struct_ratios = model.Struct_ratios(chemical_formula=calc.info['standard'], formula_units=calc.info['expanded'], nelem=calc.info['nelem'], dimensions=calc.info['dims'])
            if len(calc.tresholds) > 1: ormcalc.struct_optimisation = model.Struct_optimisation(tresholds=json.dumps(calc.tresholds), ncycles=json.dumps(calc.ncycles))

            for n, ase_repr in enumerate(calc.structures):
                is_final = True if n == len(calc.structures)-1 else False
                struct = model.Structure(step = n, final = is_final)

                s = cell_to_cellpar(ase_repr.cell)
                struct.lattice = model.Lattice(a=s[0], b=s[1], c=s[2], alpha=s[3], beta=s[4], gamma=s[5], a11=ase_repr.cell[0][0], a12=ase_repr.cell[0][1], a13=ase_repr.cell[0][2], a21=ase_repr.cell[1][0], a22=ase_repr.cell[1][1], a23=ase_repr.cell[1][2], a31=ase_repr.cell[2][0], a32=ase_repr.cell[2][1], a33=ase_repr.cell[2][2])

                #rmts =      ase_repr.get_array('rmts') if 'rmts' in ase_repr.arrays else [None for j in range(len(ase_repr))]
                charges =   ase_repr.get_array('charges') if 'charges' in ase_repr.arrays else [None for j in range(len(ase_repr))]
                magmoms =   ase_repr.get_array('magmoms') if 'magmoms' in ase_repr.arrays else [None for j in range(len(ase_repr))]
                for n, i in enumerate(ase_repr):
                    struct.atoms.append( model.Atom( number=chemical_symbols.index(i.symbol), x=i.x, y=i.y, z=i.z, charge=charges[n], magmom=magmoms[n] ) )

                ormcalc.structures.append(struct)
            # TODO Forces

        ormcalc.uigrid = model.Grid(info=json.dumps(calc.info))

        # tags ORM
        uitopics = []
        for entity in self.hierarchy:

            if not entity['creates_topic']: continue

            if entity['multiple'] or calc._calcset:
                for item in calc.info.get( entity['source'], [] ):
                    uitopics.append( model.topic(cid=entity['cid'], topic=item) )
            else:
                topic = calc.info.get(entity['source'])
                if topic or not entity['optional']: uitopics.append( model.topic(cid=entity['cid'], topic=topic) )

        uitopics = [model.Topic.as_unique(session, cid=x.cid, topic="%s" % x.topic) for x in uitopics]

        ormcalc.uitopics.extend(uitopics)

        if calc._calcset: session.add(ormcalc)
        else: session.add_all([codefamily, codeversion, pot, ormcalc])

        session.commit()
        del calc, ormcalc
        return checksum, None

    def purge(self, session, checksum):
        '''
        Deletes calc entry by checksum entirely from the database
        NB source files on disk are not deleted
        NB: this is the PUBLIC method
        @returns error
        '''
        C = session.query(model.Calculation).get(checksum)

        if not C: return 'Calculation does not exist!'

        # dataset deletion includes editing the whole dataset hierarchical tree (if any)
        if C.siblings_count:
            C_meta = session.query(model.Metadata).get(checksum)
            higher_lookup = {}
            more = C.parent
            distance = 0
            while True:
                distance += 1
                higher, more = more, []
                if not higher: break
                for i in higher:
                    try: higher_lookup[distance].add(i)
                    except KeyError: higher_lookup[distance] = set([i])
                    if i.parent:
                        more += i.parent
            for distance, members in higher_lookup.items():
                for i in members:
                    if distance == 1:
                        i.siblings_count -= 1
                    if not i.siblings_count:
                        return 'The parent dataset contains only one (current) item, please, delete parent dataset first!'

                    i.meta_data.download_size -= C_meta.download_size
                    session.add(i)
        # low-level entry deletion deals with additional tables
        else:
            session.execute( model.delete( model.Spectra ).where( model.Spectra.checksum == checksum) )
            session.execute( model.delete( model.Electrons ).where( model.Electrons.checksum == checksum ) )
            session.execute( model.delete( model.Phonons ).where( model.Phonons.checksum == checksum ) )
            session.execute( model.delete( model.Recipinteg ).where( model.Recipinteg.checksum == checksum ) )
            session.execute( model.delete( model.Basis ).where( model.Basis.checksum == checksum ) )
            session.execute( model.delete( model.Energy ).where( model.Energy.checksum == checksum ) )
            session.execute( model.delete( model.Spacegroup ).where( model.Spacegroup.checksum == checksum ) )
            session.execute( model.delete( model.Struct_ratios ).where( model.Struct_ratios.checksum == checksum ) )
            session.execute( model.delete( model.Struct_optimisation ).where( model.Struct_optimisation.checksum == checksum ) )

            struct_ids = [ int(i[0]) for i in session.query(model.Structure.struct_id).filter(model.Structure.checksum == checksum).all() ]
            for struct_id in struct_ids:
                session.execute( model.delete( model.Atom ).where( model.Atom.struct_id == struct_id ) )
                session.execute( model.delete( model.Lattice ).where( model.Lattice.struct_id == struct_id ) )
            session.execute( model.delete( model.Structure ).where( model.Structure.checksum == checksum ) )

        # for all types of entries
        if len(C.references):
            left_references = [ int(i[0]) for i in session.query(model.Reference.reference_id).join(model.metadata_references, model.Reference.reference_id == model.metadata_references.c.reference_id).filter(model.metadata_references.c.checksum == checksum).all() ]
            session.execute( model.delete( model.metadata_references ).where( model.metadata_references.c.checksum == checksum ) )

            # remove the whole citation?
            for lc in left_references:
                if not (session.query(model.metadata_references.c.checksum).filter(model.metadata_references.c.reference_id == lc).count()):
                    session.execute( model.delete( model.Reference ).where(model.Reference.reference_id == lc) )

        # TODO rewrite with cascading
        session.execute( model.delete( model.Metadata ).where( model.Metadata.checksum == checksum ) )

        session.execute( model.delete( model.Grid ).where( model.Grid.checksum == checksum ) )
        session.execute( model.delete( model.tags ).where( model.tags.c.checksum == checksum ) )

        session.execute( model.delete( model.calcsets ).where( model.calcsets.c.children_checksum == checksum ) )
        session.execute( model.delete( model.calcsets ).where( model.calcsets.c.parent_checksum == checksum ) )
        session.execute( model.delete( model.Calculation ).where( model.Calculation.checksum == checksum ) )
        session.commit()
        # NB tables topics, codefamily, codeversion, pottype are mostly irrelevant and, if needed, should be cleaned manually
        return False

    def merge(self, session, checksums, title):
        '''
        Merges calcs into a new calc called DATASET
        NB: this is the PUBLIC method
        @returns DATASET, error
        '''
        calc = Output(calcset=checksums)

        cur_depth = 0

        for nested_depth, grid_item, download_size in session.query(model.Calculation.nested_depth, model.Grid.info, model.Metadata.download_size).filter(model.Calculation.checksum == model.Grid.checksum, model.Grid.checksum == model.Metadata.checksum, model.Calculation.checksum.in_(checksums)).all():

            if nested_depth > cur_depth: cur_depth = nested_depth

            grid_item = json.loads(grid_item)

            for entity in self.hierarchy:

                topic = grid_item.get(entity['source'])
                if not topic: continue

                if not isinstance(topic, list): topic = [ topic ]
                calc.info[ entity['source'] ] = list(set( calc.info.get(entity['source'], []) + topic ))

            calc.download_size += download_size

        if not calc.download_size: return None, 'Wrong parameters provided!'

        calc._nested_depth = cur_depth + 1

        calc.info['standard'] = title

        # generate fake checksum
        calc._checksum = calc.get_collective_checksum()

        return calc, None

    def augment(self, session, parent, addendum):
        '''
        Augments a DATASET with some calcs
        NB: this is the PUBLIC method
        @returns error
        '''
        parent_calc = session.query(model.Calculation).get(parent)
        if not parent_calc or not parent_calc.siblings_count: return 'Dataset is erroneously selected!'

        existing_children, filtered_addendum = [child.checksum for child in parent_calc.children], []

        for child in addendum:
            if not child in existing_children: filtered_addendum.append(child)

        if not filtered_addendum: return 'All these data are already present in this dataset.'
        if parent_calc.checksum in filtered_addendum: return 'A dataset cannot be added into itself.'

        higher_lookup = {}
        more = parent_calc.parent
        distance = 0
        while True:
            distance += 1
            higher, more = more, []
            if not higher: break
            for i in higher:
                try: higher_lookup[distance].add(i)
                except KeyError: higher_lookup[distance] = set([i])
                if i.parent:
                    more += i.parent
        for members in list(higher_lookup.values()):
            for i in members:
                if i.checksum in filtered_addendum: return 'A parent dataset cannot be added to its children dataset.'

        parent_meta = session.query(model.Metadata).get(parent)
        parent_grid = session.query(model.Grid).get(parent)
        info_obj = json.loads(parent_grid.info)

        for nested_depth, grid_item, download_size in session.query(model.Calculation.nested_depth, model.Grid.info, model.Metadata.download_size).filter(model.Calculation.checksum == model.Grid.checksum, model.Grid.checksum == model.Metadata.checksum, model.Calculation.checksum.in_(filtered_addendum)).all():

            if nested_depth >= parent_calc.nested_depth: parent_calc.nested_depth = nested_depth + 1

            grid_item = json.loads(grid_item)

            for entity in self.hierarchy:

                topic = grid_item.get(entity['source'])
                if not topic: continue

                if entity['source'] == 'standard': topic = []

                if not isinstance(topic, list): topic = [ topic ]

                existing_term = info_obj.get(entity['source'], [])
                if not isinstance(existing_term, list): existing_term = [ existing_term ] # TODO

                info_obj[ entity['source'] ] = list(set( existing_term + topic ))

            parent_meta.download_size += download_size

        info_obj['standard'] = info_obj['standard'][0] # TODO
        parent_grid.info = json.dumps(info_obj)

        # tags ORM
        for entity in self.hierarchy:

            if not entity['creates_topic']: continue

            for item in info_obj.get( entity['source'], [] ):
                parent_calc.uitopics.append( model.Topic.as_unique(session, cid=entity['cid'], topic="%s" % item) )

        for child in session.query(model.Calculation).filter(model.Calculation.checksum.in_(filtered_addendum)).all():
            parent_calc.children.append(child)
        parent_calc.siblings_count = len(parent_calc.children)

        for distance, members in higher_lookup.items():
            for i in members:
                d = parent_calc.nested_depth - i.nested_depth + distance
                if d > 0:
                    i.nested_depth += d
                i.meta_data.download_size += parent_meta.download_size # fixme
                session.add(i)

        session.add_all([parent_calc, parent_meta, parent_grid])
        session.commit()
        return False
