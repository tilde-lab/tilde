
import sys
import os
import json

try: import sqlite3
except: from pysqlite2 import dbapi2 as sqlite3

SETTINGS_FILE = 'settings.~'
DEFAULT_DB = 'default.db'
DATA_DIR = os.path.realpath(os.path.dirname(__file__) + '/../data')
EXAMPLE_DIR = os.path.realpath(os.path.dirname(__file__) + '/../examples')
DEFAULT_SETUP = {
                'webport': 7777,
                'default_db': DEFAULT_DB,
                'local_dir': None,
                'demo_regime': 0,
                'debug_regime': 0,
                'quick_regime': 0,
                'filter': 1,
                'skip_if_path': "-_~",
                'title': None
                }
DB_SCHEMA = '''
DROP TABLE IF EXISTS "results";
CREATE TABLE "results" ("id" INTEGER PRIMARY KEY NOT NULL, "uid" INTEGER NOT NULL, "shared" INTEGER DEFAULT 0, "checksum" TEXT, "structure" TEXT, "energy" REAL, "phonons" TEXT, "electrons" TEXT, "info" TEXT, "apps" TEXT);

DROP TABLE IF EXISTS "topics";
CREATE TABLE "topics" ("tid" INTEGER PRIMARY KEY NOT NULL, "categ" INTEGER NOT NULL, "topic" TEXT);

DROP TABLE IF EXISTS "tags";
CREATE TABLE "tags" ("checksum" TEXT, "tid" INTEGER NOT NULL, FOREIGN KEY(tid) REFERENCES topics(tid));
'''


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


# INSTALL MODE
if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + SETTINGS_FILE  ) ):
    settings = DEFAULT_SETUP
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    if not write_settings(settings): raise RuntimeError('Fatal error: failed to save settings in ' + DATA_DIR)
try: settings
except NameError:
    try: settings = json.loads( open( DATA_DIR + os.sep + SETTINGS_FILE ).read() )
    except ValueError: raise RuntimeError('Your settings JSON seems to be bad-formatted, please, pay attention to commas and quotes!')
    DEFAULT_SETUP.update(settings)
    settings = DEFAULT_SETUP

    
# CREATE DB IF NOT FOUND
if not os.path.exists( os.path.abspath(  DATA_DIR + os.sep + settings['default_db']  ) ):
    if settings['default_db'] == DEFAULT_DB:
        conn = sqlite3.connect( os.path.abspath(  DATA_DIR + os.sep + settings['default_db']  ) )
        cursor = conn.cursor()
        for i in DB_SCHEMA.splitlines():
            cursor.execute( i )
        conn.commit()
        conn.close()
        os.chmod(os.path.abspath(  DATA_DIR + os.sep + settings['default_db']  ), 0777)
    else:
        raise RuntimeError('The user-defined database does not exist!')

        
# DB POOL
repositories = []
for file in os.listdir( os.path.realpath(DATA_DIR) ):
    if file[-3:] == '.db':
        if len(file) > 21: raise RuntimeError('Please, do not use long names for the databases!')
        repositories.append(file)
if len(repositories) > 6:
    raise RuntimeError('Due to memory limits cannot manage more than 6 databases!')

    
# SETTINGS COMBINATIONS
if settings['demo_regime'] and settings['debug_regime']: settings['debug_regime'] = 0


# SETTINGS RESTRICTIONS
if settings['skip_if_path'] and len(settings['skip_if_path']) > 3: raise RuntimeError('Path skipping directive must not contain more than 3 symbols due to memory limits!')
