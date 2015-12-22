
# Installation and actions to be always done
# Author: Evgeny Blokhin

import os, sys
import json # using native driver due to indent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.pool import QueuePool, NullPool

import pg8000

import tilde.core.model as model

from xml.etree import ElementTree as ET


DB_SCHEMA_VERSION = '5.02'
SETTINGS_FILE = 'settings.json'
DEFAULT_SQLITE_DB = 'default.db'

BASE_DIR = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
HIERARCHY_FILE = os.path.join(BASE_DIR, 'hierarchy.xml')
ROOT_DIR = os.path.normpath(BASE_DIR + '/../../')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
EXAMPLE_DIR = os.path.join(ROOT_DIR, 'tests/examples')
TEST_DBS_FILE = os.path.join(DATA_DIR, 'test_dbs.txt')
TEST_DBS_REF_FILE = os.path.join(DATA_DIR, 'test_dbs_ref.txt')

DEFAULT_SETUP = {

    # General part
    'debug_regime': False, # TODO
    'log_dir': os.path.join(DATA_DIR, "logs"), # TODO
    'skip_unfinished': False,
    'skip_notenergy': False,
    'skip_if_path': "",

    # DB part
    'db': {
        'default_sqlite_db': DEFAULT_SQLITE_DB,
        'engine': 'sqlite', # if sqlite is chosen: further info is not used
        'host': 'localhost',
        'port': 5432, # may be 5433
        'user': 'postgres',
        'password': '',
        'dbname': 'tilde'
    },

    # Server part
    'webport': 8070,
    'title': "Tilde GUI",
    'gui_url': "http://tilde-lab.github.io/berlinium"
}
repositories = []

def get_virtual_path(item):
    return item

def connect_url(settings, named=None):
    if settings['db']['engine'] == 'sqlite':
        if not named:       named = settings['db']['default_sqlite_db']
        if os.sep in named: named = os.path.realpath(os.path.abspath(named))
        else:               named = os.path.join(DATA_DIR, named)
        return settings['db']['engine'] + ':///' + named

    elif settings['db']['engine'] == 'postgresql':
        return settings['db']['engine'] + '+pg8000://' + settings['db']['user'] + ':' + settings['db']['password'] + '@' + settings['db']['host'] + ':' + str(settings['db']['port']) + '/' + settings['db']['dbname']

    else: raise Exception('Unsupported DB type: %s!\n' % settings['db']['engine'])

def connect_database(settings, named=None, no_pooling=False, default_actions=True, scoped=False):
    '''
    @returns session factory on success
    @returns False on failure
    '''
    connstring = connect_url(settings, named)
    poolclass = NullPool if no_pooling else QueuePool
    engine = create_engine(connstring, echo=settings['debug_regime'], poolclass=poolclass)
    Session = sessionmaker(bind=engine, autoflush=False)

    if default_actions:
        model.Base.metadata.create_all(engine)

        session = Session()

        try: p = session.query(model.Pragma.content).one()
        except NoResultFound:
            p = model.Pragma(content = DB_SCHEMA_VERSION)
            session.add(p)
        else:
            if p.content != DB_SCHEMA_VERSION:
                sys.exit('Database %s is incompatible: expected schema version %s, found %s' % (connstring.split('/')[-1], DB_SCHEMA_VERSION, p.content))

        session.commit()
        session.close()

    if scoped: return scoped_session(Session)
    else:      return Session()

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
        os.chmod(os.path.abspath(DATA_DIR + os.sep + SETTINGS_FILE), 0777) # to avoid (or create?) IO problems with multiple users
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
        if 'has_facet' in elem.attrib and not 'creates_topic' in elem.attrib: sys.exit('Fatal error: "has_facet" implies "creates_topic" in ' + HIERARCHY_FILE)
        if 'has_slider' in elem.attrib and not '.' in elem.attrib['has_slider']: sys.exit('Fatal error: "has_slider" implies table fields set in ' + HIERARCHY_FILE)

        hierarchy.append( elem.attrib )
        # type corrections
        hierarchy[-1]['cid'] = int(hierarchy[-1]['cid'])
        hierarchy[-1]['sort'] = int(hierarchy[-1]['sort'])

    for elem in doc.findall('superentity'):
        supercategories.append({
            'id': elem.attrib['id'],
            'category': elem.attrib['category'],
            'includes': map(int, elem.attrib['includes'].split(',')),
            'html_pocket': '',
            'landing_group': elem.attrib.get('landing_group'),
            'settings_group': elem.attrib.get('settings_group'),
            'toggling': elem.attrib.get('toggling')
        })

    return hierarchy, supercategories


# DEFAULT ACTIONS: LOAD/SAVE SETTINGS

if not os.path.exists( os.path.abspath( DATA_DIR + os.sep + SETTINGS_FILE ) ):
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

'''if not settings['local_dir'].endswith(os.sep):
    settings['local_dir'] += os.sep'''

'''if (not settings['local_dir']) or ('win' in sys.platform and settings['local_dir'].startswith('/')) or ('linux' in sys.platform and not settings['local_dir'].startswith('/')):
    settings['local_dir'] = EXAMPLE_DIR'''

if settings['skip_if_path'] and len(settings['skip_if_path']) > 3:
    sys.exit('Path skipping directive must not contain more than 3 symbols due to memory limits!')

if not 'engine' in settings['db'] or settings['db']['engine'] not in ['sqlite', 'postgresql']:
    sys.exit('This DB backend is not supported!')

if not 'default_sqlite_db' in settings['db']:
    sys.exit('Note that the settings.json format has been changed with the respect to the default sqlite DB.')
