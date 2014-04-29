# script for initial Postgres setup
# creates Postgres DB with the schema
#
# Usage:
# ./pg_db.py [creates only schema in the existing DB]
# ./pg_db.py doall [creates DB and schema]

import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.settings import settings, write_settings, connect_database, DEFAULT_POSTGRES_DB, POSTGRES_DB_SCHEMA, DATA_DIR

try: sys.argv[1]
except IndexError: skip_db_creation = True
else: skip_db_creation = False

# 1) CREATE DB

if not skip_db_creation:
    import psycopg2

    conn_setup = {'db': {}}
    conn_setup['db'].update(settings['db'])
    if conn_setup['db']['type'] != 'postgres':
        sys.exit("\nBe sure to enable postgres support in Tilde settings!\n")

    # We can only be sure this DB exists!
    conn_setup['db']['dbname'] = 'postgres'
    try: db = psycopg2.connect(host = conn_setup['db']['host'], port = int(conn_setup['db']['port']), user = conn_setup['db']['user'], password = conn_setup['db']['password'], database = conn_setup['db']['dbname'])
    except: sys.exit('Cannot connect for DB creation with these creds: ' + str(conn_setup['db']))

    db.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = db.cursor()
    cursor.execute("CREATE DATABASE %s;" % DEFAULT_POSTGRES_DB)
    db.commit()
    cursor.close()
    db.close()
    print 'DB %s created.' % DEFAULT_POSTGRES_DB

# 2) LOAD SCHEMA

settings['db']['dbname'] = DEFAULT_POSTGRES_DB # Update settings!
if not write_settings(settings):
    sys.exit('I/O error: failed to save settings in ' + DATA_DIR)

db = connect_database(settings, None)
if not db:
    sys.exit('Cannot connect for schema creation with these creds: ' + str(settings['db']))

cursor = db.cursor()
for i in POSTGRES_DB_SCHEMA.splitlines():
    cursor.execute( i )  
db.commit()
cursor.close()
db.close()

print 'DB %s is ready-to-use.' % DEFAULT_POSTGRES_DB
