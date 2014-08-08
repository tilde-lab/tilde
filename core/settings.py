
# Installation and actions to be always done
# v160714

import sys
import os
import re
import json

import installation # DEFAULT ACTIONS: EXTENSIONS COMPILATION & INSTALLATION
import model

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps')) # this is done to have all 3rd party code in core/deps
from sqlalchemy import create_engine, MetaData, desc, exists
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

from xml.etree import ElementTree as ET


SETTINGS_FILE = 'settings.json'
HIERARCHY_FILE = os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/gui_entities.xml')
DEFAULT_SQLITE_DB = 'default.db'
DEFAULT_POSTGRES_DB = 'tilde'
DATA_DIR = os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../data')
EXAMPLE_DIR = os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../tests/examples')
MAX_CONCURRENT_DBS = 1
DEFAULT_SETUP = {
                # DB scope:
                'default_sqlite_db': DEFAULT_SQLITE_DB,
                'db':{
                    'engine': 'sqlite', # may be postgresql, NB if sqlite is chosen: further info is not used
                    'host': 'localhost',
                    'port': 5432, # may be 5433
                    'user': 'postgres',
                    'password': '',
                    'dbname': 'nomad',
                    },

                # API (parsing) scope:
                'demo_regime': False,
                'debug_regime': False,
                'skip_unfinished': False,
                'skip_if_path': "-_~",
                
                # GUI scope:
                'webport': 7777, # is it robust to use?                
                'local_dir': EXAMPLE_DIR,
                'exportability': False,              
                'title': None,
                'update_server': "http://tilde.pro/VERSION",
                'custom_about_link': False, # only in demo mode: if set to URL, the URL is used
}
repositories = []

# begin obligatory routines

def connect_database(settings, uc):
    '''
    Tries to connect to a DB
    @returns handler on success
    @returns False on failure
    '''    
    if settings['db']['engine'] == 'sqlite':
        if uc is None: sys.exit('Sqlite DB name was not given!')
        
        try:
            import sqlite3
        except ImportError:
            print '\nSQLite driver is not available!'
            return False  
        
        connstring = settings['db']['engine'] + ':///' + os.path.abspath(DATA_DIR + os.sep + os.path.basename(uc))
        
    elif settings['db']['engine'] == 'postgresql':
        try:            
            import psycopg2
            postgres_driver = 'psycopg2'
        except ImportError:
            print '\nNative Postgres driver not available, falling back to a slower Python version!\n'
            import pg8000
            postgres_driver = 'pg8000'
            
        connstring = settings['db']['engine'] + '+' + postgres_driver + '://' + settings['db']['user'] + ':' + settings['db']['password'] + '@' + settings['db']['host'] + ':' + str(settings['db']['port']) + '/' + settings['db']['dbname']
    
    else:
        print '\nUnsupported DB type: %s!\n' % settings['db']['engine']
        return False    
    
    engine = create_engine(connstring, echo=settings['debug_regime'])
    Session = sessionmaker(bind=engine)
    model.Base.metadata.create_all(engine)
    session = Session()
    
    try: p = session.query(model.Pragma.content).one()
    except NoResultFound:
        p = model.Pragma(content=model.DB_SCHEMA_VERSION)
        session.add(p)
    else:
        if p.content != model.DB_SCHEMA_VERSION:
            uc = uc if uc else 'at server'
            sys.exit('Sorry, database '+uc+' is incompatible.')

    return session

def write_settings(settings):
    '''
    Saves user's settings
    @returns True on success
    @returns False on failure    
    ''' 
    if not os.access(DATA_DIR, os.W_OK): return False
    try:
        f = open(DATA_DIR + os.sep + SETTINGS_FILE, 'w')
        f.writelines(json.dumps(settings, indent=0))
        f.close()
        os.chmod(os.path.abspath(  DATA_DIR + os.sep + SETTINGS_FILE  ), 0777) # to avoid (or create?) IO problems with multiple users
    except IOError:
        return False
    else:
        return True

def read_hierarchy():
    '''
    Reads main mapping source according to what a data classification is made
    Also reads the supercategories (only for GUI)
    '''
    try: tree = ET.parse(HIERARCHY_FILE)
    except: sys.exit('Fatal error: invalid file ' + HIERARCHY_FILE)
    
    hierarchy, supercategories = [], []
    
    doc = tree.getroot()
    
    for elem in doc.findall('entity'):
        hierarchy.append( elem.attrib )        
        # type corrections
        hierarchy[-1]['cid'] = int(hierarchy[-1]['cid'])
        hierarchy[-1]['sort'] = int(hierarchy[-1]['sort'])
        
    for elem in doc.findall('superentity'):
        supercategories.append(  {  'category': elem.attrib['category'], 'includes': map(int, elem.attrib['includes'].split(',')), 'contains': []  }  )
        
    return hierarchy, supercategories
    
# end obligatory routines

# DEFAULT ACTIONS: MAIN INSTALLATION

if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + SETTINGS_FILE  ) ):
    settings = DEFAULT_SETUP
    if not os.path.exists(DATA_DIR):
        try: os.makedirs(DATA_DIR)
        except IOError: sys.exit('I/O error: failed write ' + DATA_DIR)
    if not write_settings(settings): sys.exit('I/O error: failed to save settings in ' + DATA_DIR)
try: settings
except NameError:
    try: settings = json.loads( open( DATA_DIR + os.sep + SETTINGS_FILE ).read() )
    except ValueError: sys.exit('Your '+DATA_DIR + os.sep + SETTINGS_FILE+' seems to be bad-formatted, please, pay attention to commas and quotes!')
    except IOError: sys.exit('Your '+DATA_DIR + os.sep + SETTINGS_FILE+' is not accessible!')
    DEFAULT_SETUP.update(settings)
    settings = DEFAULT_SETUP

# DEFAULT ACTIONS: CHECK SETTINGS COMBINATIONS & RESTRICTIONS

if not settings['local_dir'].endswith(os.sep):
    settings['local_dir'] += os.sep

if settings['demo_regime'] and settings['debug_regime']:
    settings['debug_regime'] = False
    
if (not settings['local_dir']) or ('win' in sys.platform and settings['local_dir'].startswith('/')) or ('linux' in sys.platform and not settings['local_dir'].startswith('/')):
    settings['local_dir'] = EXAMPLE_DIR
    
if settings['skip_if_path'] and len(settings['skip_if_path']) > 3:
    sys.exit('Path skipping directive must not contain more than 3 symbols due to memory limits!')

if not 'engine' in settings['db'] or settings['db']['engine'] not in ['sqlite', 'postgresql']:
    sys.exit('Wrong / outdated DB definition!')

if not 'http://' in settings['update_server']:
    sys.exit('Directive update_server must be a valid url!')
    
if settings['custom_about_link'] and not 'http://' in settings['custom_about_link']:
    sys.exit('Directive custom_about_link must be a valid url!')
