
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


DB_SCHEMA_VERSION = '5.11'
SETTINGS_FILE = 'settings.json'
DEFAULT_SQLITE_DB = 'default.db'
BASE_DIR = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
ROOT_DIR = os.path.normpath(BASE_DIR + '/../')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
EXAMPLE_DIR = os.path.join(ROOT_DIR, '../tests/data')
INIT_DATA = os.path.join(DATA_DIR, 'sql/init-data.sql')
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
    'gui_url': "http://tilde-lab.github.io/berlinium/?https://db.tilde.pro"
}
repositories = []

def virtualize_path(item):
    return item

def connect_url(settings, named=None):
    if settings['db']['engine'] == 'sqlite':
        if not named:       named = settings['db']['default_sqlite_db']
        if os.sep in named: named = os.path.realpath(os.path.abspath(named))
        else:               named = os.path.join(DATA_DIR, named)
        return settings['db']['engine'] + ':///' + named

    elif settings['db']['engine'] == 'postgresql':
        return settings['db']['engine'] + '+pg8000://' + settings['db']['user'] + ':' + settings['db']['password'] + '@' + settings['db']['host'] + ':' + str(settings['db']['port']) + '/' + settings['db']['dbname']

    else: sys.exit('Unsupported DB type: %s!\n' % settings['db']['engine'])

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
        # 1.
        model.Base.metadata.create_all(engine)

        session = Session()
        # 2.
        try: pragma = session.query(model.Pragma.content).one()
        except NoResultFound:
            pragma = model.Pragma(content = DB_SCHEMA_VERSION)
            session.add(pragma)
        else:
            if pragma.content != DB_SCHEMA_VERSION:
                sys.exit('Database %s is incompatible: expected schema version %s, found %s' % (connstring.split('/')[-1], DB_SCHEMA_VERSION, pragma.content))
        # 3.
        chk = session.query(model.Hierarchy_value).first()
        if not chk:
            if not os.path.exists(INIT_DATA): sys.exit(INIT_DATA + ' not found!')
            with open(INIT_DATA) as f:
                while True:
                    sql = f.readline().strip()
                    if not sql: break
                    engine.execute(sql)

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
        os.chmod(os.path.abspath(DATA_DIR + os.sep + SETTINGS_FILE), 0o777) # to avoid (or create?) IO problems with multiple users
    except IOError:
        return False
    else:
        return True

def get_hierarchy(settings):
    '''
    Gets main mapping source according to what a data classification is made
    Gets the hierarchy groups (only for GUI)
    Gets the hierarchy values
    '''
    hierarchy, hierarchy_groups, hierarchy_values = [], [], {}
    hgroup_ids, enumerated_vals = {}, set()
    session = connect_database(settings)
    for item in session.query(model.Hierarchy_value).all():
        try:
            hierarchy_values[item.cid].update({item.num: item.name})
        except KeyError:
            hierarchy_values[item.cid] = {item.num: item.name}
        enumerated_vals.add(item.cid)
    try:
        for item in session.query(model.Hierarchy).all():
            if item.has_facet and not item.has_topic: raise RuntimeError('Fatal error: "has_facet" implies "has_topic"')
            if item.slider and not '.' in item.slider: raise RuntimeError('Fatal error: "has_slider" must have a reference to some table field')
            hierarchy.append({
                'cid':item.cid,
                'category':item.name,
                'source':item.source,
                'html':item.html,
                'has_slider':item.slider,
                'sort':item.sort,
                'multiple':item.multiple,
                'optional':item.optional,
                'has_summary_contrb':item.has_summary_contrb,
                'has_column':item.has_column,
                'has_facet':item.has_facet,
                'creates_topic':item.has_topic,
                'is_chem_formula':item.chem_formula,
                'plottable':item.plottable,
                'enumerated':True if item.cid in enumerated_vals else False
            })
            try: hgroup_ids[item.hgroup_id].append(item.cid)
            except KeyError: hgroup_ids[item.hgroup_id] = [item.cid]
    except RuntimeError as e:
        session.close()
        sys.exit(e)
    for item in session.query(model.Hierarchy_group).all():
        hierarchy_groups.append({
            'id': item.hgroup_id,
            'category': item.name,
            'html_pocket': '', # specially for JavaScript client
            'landing_group': item.landing_group,
            'settings_group': item.settings_group,
            'includes': hgroup_ids[item.hgroup_id]
        })
    session.close()
    return hierarchy, hierarchy_groups, hierarchy_values

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
if settings['skip_if_path'] and len(settings['skip_if_path']) > 3:
    sys.exit('Path skipping directive must not contain more than 3 symbols due to memory limits!')

if not 'engine' in settings['db'] or settings['db']['engine'] not in ['sqlite', 'postgresql']:
    sys.exit('This DB backend is not supported!')

if not 'default_sqlite_db' in settings['db']:
    sys.exit('Note that the settings.json format has been changed with the respect to the default sqlite DB.')
