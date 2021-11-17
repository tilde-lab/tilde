
# Installation and actions to be always done
# Author: Evgeny Blokhin

import os, sys
import json
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.pool import QueuePool, NullPool

import tilde.core.model as model


DB_SCHEMA_VERSION = '5.20'
SETTINGS_FILE = 'settings.json'
DEFAULT_SQLITE_DB = 'default.db'
BASE_DIR = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))
ROOT_DIR = os.path.normpath(BASE_DIR + '/../')
DATA_DIR = os.path.join(ROOT_DIR, 'data')
EXAMPLE_DIR = os.path.join(ROOT_DIR, '../tests/data')
INIT_DATA = os.path.join(DATA_DIR, 'sql/init-data.sql')
TEST_DBS_FILE = os.path.join(DATA_DIR, 'test_dbs.txt')
TEST_DBS_REF_FILE = os.path.join(DATA_DIR, 'test_dbs_ref.txt')
SETTINGS_PATH = DATA_DIR + os.sep + SETTINGS_FILE
GUI_URL_TPL = 'http://tilde-lab.github.io/berlinium/?http://127.0.0.1:%s' # ?https://db.tilde.pro

DEFAULT_SETUP = {

    # General part
    'debug_regime': False, # TODO
    'log_dir': os.path.join(DATA_DIR, "logs"), # TODO
    'skip_unfinished': False,
    'skip_notenergy': False,
    'skip_if_path': [],

    # DB part
    'db': {
        'default_sqlite_db': DEFAULT_SQLITE_DB,
        'engine': 'sqlite', # if sqlite is chosen: further info is not used
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': '',
        'dbname': 'tilde'
    },

    # Server part
    'webport': 8070,
    'title': "Tilde GUI"
}


def virtualize_path(item):
    return item


def connect_url(settings, named=None):
    if settings['db']['engine'] == 'sqlite':
        if not named:
            named = settings['db']['default_sqlite_db']
        if os.sep in named:
            named = os.path.realpath(os.path.abspath(named))
        else:
            named = os.path.join(DATA_DIR, named)

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
            if not os.path.exists(INIT_DATA):
                sys.exit(INIT_DATA + ' not found!')

            f = open(INIT_DATA)
            statements = list(filter(None, f.read().splitlines()))
            f.close()

            nlines = 0
            pocket = []
            for n in range(len(statements)):
                if statements[n].startswith('--'):
                    continue
                elif not statements[n].endswith(';'):
                    pocket.append(statements[n])
                    continue
                else:
                    if pocket:
                        engine.execute( "".join(pocket) + statements[n] )
                        pocket = []
                    else:
                        engine.execute(statements[n])
                nlines += 1

            logging.warning("Applied DB model from file %s" % INIT_DATA)
            logging.warning("SQL statements executed: %s" % nlines)

        session.commit()
        session.close()

    if scoped:
        return scoped_session(Session)

    return Session()


def write_settings(settings):
    '''
    Saves user's settings
    @returns True on success
    @returns False on failure
    '''
    if not os.access(DATA_DIR, os.W_OK): return False
    try:
        f = open(SETTINGS_PATH, 'w')
        f.writelines(json.dumps(settings, indent=4))
        f.close()
        os.chmod(os.path.abspath(SETTINGS_PATH), 0o777) # to avoid (or create?) IO problems with multiple users
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
            if item.has_facet and not item.has_topic:
                raise RuntimeError('Fatal error: "has_facet" implies "has_topic"')
            if item.slider and not '.' in item.slider:
                raise RuntimeError('Fatal error: "has_slider" must have a reference to some table field')

            hierarchy.append({
                'cid': item.cid,
                'category': item.name,
                'source': item.source,
                'html': item.html,
                'has_slider': item.slider,
                'sort': item.sort,
                'multiple': item.multiple,
                'optional': item.optional,
                'has_summary_contrb': item.has_summary_contrb,
                'has_column': item.has_column,
                'has_facet': item.has_facet,
                'creates_topic': item.has_topic,
                'is_chem_formula': item.chem_formula,
                'plottable': item.plottable,
                'enumerated': True if item.cid in enumerated_vals else False
            })
            try:
                hgroup_ids[item.hgroup_id].append(item.cid)
            except KeyError:
                hgroup_ids[item.hgroup_id] = [item.cid]
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


# DEFAULT ACTIONS ALWAYS TO DO: LOAD/SAVE SETTINGS
if not os.path.exists(os.path.abspath(SETTINGS_PATH)):
    settings = DEFAULT_SETUP
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR)
        except IOError:
            sys.exit('I/O error: failed write to %s' % DATA_DIR)
    if not write_settings(settings):
        sys.exit('I/O error: failed to save settings in %s' % DATA_DIR)

try: settings
except NameError:
    try:
        settings = json.loads(open(SETTINGS_PATH).read())
    except ValueError:
        sys.exit('Your %s seems to be bad-formatted, please, pay attention to commas and quotes' % SETTINGS_PATH)
    except IOError:
        sys.exit('Your %s is not accessible' % SETTINGS_PATH)

    DEFAULT_SETUP.update(settings)
    settings = DEFAULT_SETUP


# DEFAULT ACTIONS ALWAYS TO DO: CHECK SETTINGS COMBINATIONS & RESTRICTIONS
if settings['skip_if_path'] and len(settings['skip_if_path']) > 3:
    sys.exit('Path skipping directive must not contain more than 3 symbols due to memory limits')

if not 'engine' in settings['db'] or settings['db']['engine'] not in ['sqlite', 'postgresql']:
    sys.exit('This DB backend is not supported')

if not 'default_sqlite_db' in settings['db']:
    sys.exit('Note that the settings.json format has been changed with the respect to the default sqlite DB')
