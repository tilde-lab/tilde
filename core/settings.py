
# Tilde project: installation and actions to be always done
# v260414

import sys
import os
import re
import json

import installation # EXTENSIONS COMPILATION

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps')) # this is done to have all 3rd party code in core/deps

from xml.etree import ElementTree as ET


DB_SCHEMA_VERSION = '1.08'
SETTINGS_FILE = 'settings.json'
HIERARCHY_FILE = os.path.realpath(os.path.dirname(__file__) + '/hierarchy.xml')
DEFAULT_SQLITE_DB = 'default.db'
DEFAULT_POSTGRES_DB = 'tilde'
DATA_DIR = os.path.realpath(os.path.dirname(__file__) + '/../data')
EXAMPLE_DIR = os.path.realpath(os.path.dirname(__file__) + '/../tests/examples')
MAX_CONCURRENT_DBS = 10
DEFAULT_SETUP = {
                'webport': 7777, # is it robust to use?
                'default_sqlite_db': DEFAULT_SQLITE_DB,
                'local_dir': EXAMPLE_DIR,
                'exportability': False,
                'demo_regime': False,
                'debug_regime': False,
                'skip_unfinished': False,
                'skip_if_path': "-_~",
                'title': None,
                'update_server': "http://tilde.pro/VERSION",
                'db':{
                    'type': 'sqlite',   # may be postgres
                                        # if sqlite is chosen: further info is not used
                    'host': 'localhost',
                    'port': 5432, # may be 5433
                    'user': 'postgres',
                    'password': '',
                    'dbname': 'postgres', # for initial first-time connection
                    },
                }
SQLITE_DB_SCHEMA = '''CREATE TABLE "results" ("id" INTEGER PRIMARY KEY NOT NULL, "checksum" TEXT, "structures" TEXT, "energy" REAL, "phonons" TEXT, "electrons" TEXT, "info" TEXT, "apps" TEXT);
CREATE TABLE "topics" ("tid" INTEGER PRIMARY KEY NOT NULL, "categ" INTEGER NOT NULL, "topic" TEXT);
CREATE TABLE "tags" ("checksum" TEXT, "tid" INTEGER NOT NULL, FOREIGN KEY(tid) REFERENCES topics(tid));
CREATE TABLE "pragma" ("content" TEXT);'''
SQLITE_DB_SCHEMA += '\nINSERT INTO "pragma" ("content") VALUES (' + DB_SCHEMA_VERSION + ');'

POSTGRES_DB_SCHEMA = '''CREATE TABLE "results" ("id" SERIAL PRIMARY KEY, "checksum" TEXT, "structures" TEXT, "energy" FLOAT8, "phonons" TEXT, "electrons" TEXT, "info" TEXT, "apps" TEXT);
CREATE TABLE "topics" ("tid" SERIAL PRIMARY KEY, "categ" INTEGER NOT NULL, "topic" TEXT);
CREATE TABLE "tags" ("checksum" TEXT, "tid" INTEGER NOT NULL REFERENCES topics(tid));
CREATE TABLE "pragma" ("content" TEXT);'''
POSTGRES_DB_SCHEMA += '\nINSERT INTO "pragma" ("content") VALUES (' + DB_SCHEMA_VERSION + ');'

repositories = []

#
# BOF routines, which involve Tilde API and schema : TODO
#
def connect_database(settings, uc):
    '''
    Tries to connect to a DB
    @returns handler on success
    @returns False on failure
    '''
    if settings['db']['type'] == 'sqlite':
        if uc is None: sys.exit('Sqlite DB name was not given!')
        
        try: import sqlite3
        except ImportError: from pysqlite2 import dbapi2 as sqlite3
        
        try: db = sqlite3.connect(os.path.abspath(DATA_DIR + os.sep + uc))
        except: return False
        else:
            db.row_factory = sqlite3.Row
            db.text_factory = str
            return db
        
    elif settings['db']['type'] == 'postgres':
        try: import psycopg2 as postgres_driver
        except ImportError: import pg8000 as postgres_driver
            
        try: db = postgres_driver.connect(host = settings['db']['host'], port = int(settings['db']['port']), user = settings['db']['user'], password = settings['db']['password'], database = settings['db']['dbname'])
        except: return False
        else: return db
        
    return False

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
        
def write_db(name):
    '''
    Write SQLite DB file
    @returns False on success
    @returns error on failure
    '''        
    if not len(name) or not re.match('^[\w-]+$', name):
        return 'Invalid database name: ' + name

    name = name.replace('../', '') + '.db'
    
    if len(name) > 21:
        return 'Please, do not use long names for the databases, as such: ' + name
    
    if os.path.exists(DATA_DIR + os.sep + name) or not os.access(DATA_DIR, os.W_OK):
        return 'Cannot write database file, please, check the path ' + DATA_DIR + os.sep + name
    
    conn = connect_database(settings, name)
    if not conn:
        return 'SQLite extension cannot write DB!'
    
    cursor = conn.cursor()
    for i in SQLITE_DB_SCHEMA.splitlines():
        cursor.execute( i )
    conn.commit()
    conn.close()
    os.chmod(os.path.abspath(  DATA_DIR + os.sep + name  ), 0777) # to avoid (or create?) IO problems with multiple users
    
    return False

def check_db_version(db_conn):
    '''
    Checks, whether DB is known
    @returns False on success
    @returns True on failure
    '''  
    cursor = db_conn.cursor()
    try: cursor.execute( "SELECT content FROM pragma;" )
    except: return True
    row = cursor.fetchone()
    if row[0] != DB_SCHEMA_VERSION:
        return True
    else:
        return False

def user_db_choice(options, choice=None, add_msg="", create_allowed=True):
    '''
    Auxiliary procedure to simplify CLI
    '''
    if choice is None:
        suggest = " (0) create new" if create_allowed else ""
        for n, i in enumerate(options):
            suggest += " (" + str(n+1) + ") " + i
        choice = raw_input(add_msg + "Which database to use?\nPlease, input one of the options:" + suggest + "\n")
        add_msg = ""
    
    try: choice = int(choice)
    
    # Not numeric
    except ValueError:
        if choice not in options:
            return user_db_choice(options, add_msg="Invalid choice!\n")
        else:
            return choice
    
    # Numeric    
    # invoke creation subroutine
    if choice == 0:
        if not create_allowed: return user_db_choice(options, add_msg="Invalid choice!\n")
            
        choice = raw_input(add_msg + "Please, input name without \".db\" extension:\n")
        add_msg = ""
        
        error = write_db(choice)
        if error:
            return user_db_choice(options, choice=0, add_msg=error + "\n")                
        else:
            return choice + '.db'
    
    # choice by index       
    try: choice = options[choice-1]
    except IndexError:
        return user_db_choice(options, add_msg="Invalid choice!\n")
    else:
        return choice

def read_hierarchy():
    '''
    Reads main mapping source according to what a data classification is made
    Also reads the supercategories (only for GUI)
    '''
    try: tree = ET.parse(HIERARCHY_FILE)
    except: sys.exit('Fatal error: invalid file ' + HIERARCHY_FILE)
    
    hierarchy, supercategories = [], {}
    
    doc = tree.getroot()
    
    for elem in doc.findall('entity'):
        hierarchy.append( elem.attrib )        
        # type corrections
        hierarchy[-1]['cid'] = int(hierarchy[-1]['cid'])
        hierarchy[-1]['sort'] = int(hierarchy[-1]['sort'])
        
    for elem in doc.findall('superentity'):
        supercategories[ elem.attrib['category'] ] = map(int, elem.attrib['includes'].split(','))
        
    return hierarchy, supercategories
#
# EOF routines, which involve Tilde API and schema
#

# INSTALLATION / SETTINGS

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

# DB / CREATE IF NOT FOUND

if settings['db']['type'] == 'sqlite':
    try: import sqlite3
    except ImportError:
        try: from pysqlite2 import dbapi2 as sqlite3
        except ImportError: sys.exit('\n\nI cannot proceed. Please, install python sqlite3 module!\n\n')
    
    if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + settings['default_sqlite_db']  ) ):
        error = write_db(settings['default_sqlite_db'][:-3])
        if error: 
            sys.exit(error)
        
    # DB POOL
    for file in os.listdir( os.path.realpath(DATA_DIR) ):
        if file[-3:] == '.db':
            if len(file) > 21: sys.exit('Please, do not use long names for the databases!')
            repositories.append(file)
    if len(repositories) > MAX_CONCURRENT_DBS:
        sys.exit('Due to memory limits cannot manage more than %s databases!' % MAX_CONCURRENT_DBS)

elif settings['db']['type'] == 'postgres':
    try: import psycopg2
    except ImportError:
        print '\nNative Postgres driver not available, falling back to a slower Python version!\n'
        try: import pg8000
        except ImportError: sys.exit('\nI cannot proceed: your Python needs Postgres support!\n')
    
    if not connect_database(settings, None):
        sys.exit('Cannot connect to %s DB with the current settings!' % settings['db']['dbname'])

else: sys.exit('DB type misconfigured!')
    
# SETTINGS COMBINATIONS & RESTRICTIONS

if not settings['local_dir'].endswith(os.sep):
    settings['local_dir'] += os.sep

if settings['demo_regime'] and settings['debug_regime']:
    settings['debug_regime'] = 0
    
if (not settings['local_dir']) or ('win' in sys.platform and settings['local_dir'].startswith('/')) or ('linux' in sys.platform and not settings['local_dir'].startswith('/')):
    settings['local_dir'] = EXAMPLE_DIR
    
if settings['db']['type'] == 'sqlite':
    settings['ph'] = '?'
elif settings['db']['type'] == 'postgres':
    settings['ph'] = '%s'
    
if settings['skip_if_path'] and len(settings['skip_if_path']) > 3:
    sys.exit('Path skipping directive must not contain more than 3 symbols due to memory limits!')
        
if not 'http://' in settings['update_server']:
    sys.exit('Directive update_server must be a valid url!')
