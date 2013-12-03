
# Tilde project: installation and actions to be always done
# v271113

import sys
import os
import re
import json

try: import sqlite3
except: from pysqlite2 import dbapi2 as sqlite3

# EXTENSIONS COMPILATION
import installation

from xml.etree import ElementTree as ET


DB_SCHEMA_VERSION = '1.0'
SETTINGS_FILE = 'settings.json'
HIERARCHY_FILE = os.path.realpath(os.path.dirname(__file__) + '/hierarchy.xml')
DEFAULT_DB = 'default.db'
DATA_DIR = os.path.realpath(os.path.dirname(__file__) + '/../data')
EXAMPLE_DIR = os.path.realpath(os.path.dirname(__file__) + '/../tests/examples')
MAX_CONCURRENT_DBS = 10
DEFAULT_SETUP = {
                'webport': 7777, # is it robust to use?
                'default_db': DEFAULT_DB,
                'local_dir': EXAMPLE_DIR,
                'exportability': True,
                'demo_regime': False,
                'debug_regime': False,
                'skip_unfinished': False,
                'skip_if_path': "-_~",
                'title': None,
                'update_server': "http://tilde.pro/VERSION"
                }
DB_SCHEMA = '''
CREATE TABLE "results" ("id" INTEGER PRIMARY KEY NOT NULL, "checksum" TEXT, "structures" TEXT, "energy" REAL, "phonons" TEXT, "electrons" TEXT, "info" TEXT, "apps" TEXT);
CREATE TABLE "topics" ("tid" INTEGER PRIMARY KEY NOT NULL, "categ" INTEGER NOT NULL, "topic" TEXT);
CREATE TABLE "tags" ("checksum" TEXT, "tid" INTEGER NOT NULL, FOREIGN KEY(tid) REFERENCES topics(tid));
CREATE TABLE "pragma" ("content" TEXT);
'''
DB_SCHEMA += 'INSERT INTO "pragma" ("content") VALUES (' + DB_SCHEMA_VERSION + ');'
repositories = []


#
# routines, which involve Tilde API and schema : TODO
#

def write_settings(settings):
    if not os.access(DATA_DIR, os.W_OK): return False
    try:
        f = open(DATA_DIR + os.sep + SETTINGS_FILE, 'w')
        f.writelines(json.dumps(settings, indent=0))
        f.close()
    except IOError:
        return False
    else:
        return True
        
def write_db(name):
    if not len(name) or not re.match('^[\w-]+$', name):
        return 'Invalid database name: ' + name

    name = name.replace('../', '') + '.db'
    
    if len(name) > 21:
        return 'Please, do not use long names for the databases, as such: ' + name
    
    if os.path.exists(DATA_DIR + os.sep + name) or not os.access(DATA_DIR, os.W_OK):
        return 'Cannot write database file, please, check the path ' + DATA_DIR + os.sep + name

    conn = sqlite3.connect( os.path.abspath(  DATA_DIR + os.sep + name  ) )
    conn.row_factory = sqlite3.Row
    conn.text_factory = str
    
    cursor = conn.cursor()
    for i in DB_SCHEMA.splitlines():
        cursor.execute( i )
    conn.commit()
    conn.close()
    os.chmod(os.path.abspath(  DATA_DIR + os.sep + name  ), 0777) # to avoid (or create?) IO problems with multiple users
    
    return False

def userdbchoice(options, choice=None, add_msg="", create_allowed=True):
    ''' Auxiliary procedure to simplify UI '''
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
            return userdbchoice(options, add_msg="Invalid choice!\n")
        else:
            return choice
    
    # Numeric    
    # invoke creation subroutine
    if choice == 0:
        if not create_allowed: return userdbchoice(options, add_msg="Invalid choice!\n")
            
        choice = raw_input(add_msg + "Please, input name without \".db\" extension:\n")
        add_msg = ""
        
        error = write_db(choice)
        if error:
            return userdbchoice(options, choice=0, add_msg=error + "\n")                
        else:
            return choice + '.db'
    
    # choice by index       
    try: choice = options[choice-1]
    except IndexError:
        return userdbchoice(options, add_msg="Invalid choice!\n")
    else:
        return choice

def read_hierarchy():
    try: tree = ET.parse(HIERARCHY_FILE)
    except: raise RuntimeError('Fatal error: invalid file ' + HIERARCHY_FILE)
    hierarchy = []
    doc = tree.getroot()
    for elem in doc.findall('entity'):
        hierarchy.append( elem.attrib )
        
        # type corrections
        hierarchy[-1]['cid'] = int(hierarchy[-1]['cid'])
        hierarchy[-1]['sort'] = int(hierarchy[-1]['sort'])
    return hierarchy
    
def check_db_version(db_conn):
    cursor = db_conn.cursor()
    try: cursor.execute( "SELECT name FROM sqlite_master WHERE type='table' AND name='pragma'" ) # is there such a table?
    except: raise RuntimeError('Fatal error: ' + "%s" % sys.exc_info()[1])
    row = cursor.fetchone()
    if row is None:
        return True
    try: cursor.execute( "SELECT content FROM pragma" )
    except: raise RuntimeError('Fatal error: ' + "%s" % sys.exc_info()[1])
    row = cursor.fetchone()
    if row['content'] != DB_SCHEMA_VERSION:
        return True
    else:
        return False


# INSTALLATION

if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + SETTINGS_FILE  ) ):
    settings = DEFAULT_SETUP
    if not os.path.exists(DATA_DIR):
        try: os.makedirs(DATA_DIR)
        except IOError: raise RuntimeError('Fatal error: failed write ' + DATA_DIR)
    if not write_settings(settings): raise RuntimeError('Fatal error: failed to save settings in ' + DATA_DIR)
try: settings
except NameError:
    try: settings = json.loads( open( DATA_DIR + os.sep + SETTINGS_FILE ).read() )
    except ValueError: raise RuntimeError('Your settings JSON seems to be bad-formatted, please, pay attention to commas and quotes!')
    DEFAULT_SETUP.update(settings)
    settings = DEFAULT_SETUP
    
# CREATE DB IF NOT FOUND

if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + settings['default_db']  ) ):
    error = write_db(settings['default_db'][:-3])
    if error: raise RuntimeError(error)
        
# DB POOL

for file in os.listdir( os.path.realpath(DATA_DIR) ):
    if file[-3:] == '.db':
        if len(file) > 21: raise RuntimeError('Please, do not use long names for the databases!')
        repositories.append(file)
if len(repositories) > MAX_CONCURRENT_DBS:
    raise RuntimeError('Due to memory limits cannot manage more than %s databases!' % MAX_CONCURRENT_DBS)
    
# SETTINGS COMBINATIONS

if settings['demo_regime'] and settings['debug_regime']: settings['debug_regime'] = 0

# SETTINGS RESTRICTIONS

if settings['skip_if_path'] and len(settings['skip_if_path']) > 3: raise RuntimeError('Path skipping directive must not contain more than 3 symbols due to memory limits!')
if (not settings['local_dir']) or ('win' in sys.platform and settings['local_dir'].startswith('/')) or ('linux' in sys.platform and not settings['local_dir'].startswith('/')): settings['local_dir'] = EXAMPLE_DIR
if not settings['local_dir'].endswith(os.sep): settings['local_dir'] += os.sep
