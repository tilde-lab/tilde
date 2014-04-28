# script for initial Postgres setup
# creates Postgres DB with the schema

import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
import psycopg2

from core.settings import settings, write_settings, connect_database, DEFAULT_POSTGRES_DB, POSTGRES_DB_SCHEMA, DATA_DIR


conn_setup = {'db': {}}
conn_setup['db'].update(settings['db'])
if conn_setup['db']['type'] != 'postgres':
    sys.exit("\nBe sure to enable postgres support in Tilde settings!\n")

# We can only be sure this DB exists!
conn_setup['db']['dbname'] = 'postgres'
db = connect_database(conn_setup, None)
if not db:
    sys.exit('Cannot connect with these creds: ' + str(conn_setup['db']))

db.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = db.cursor()
cursor.execute("CREATE DATABASE %s;" % DEFAULT_POSTGRES_DB)
db.commit()
cursor.close()
db.close()

print 'DB %s created.' % DEFAULT_POSTGRES_DB

# Update settings!
settings['db']['dbname'] = DEFAULT_POSTGRES_DB
if not write_settings(settings):
    sys.exit('I/O error: failed to save settings in ' + DATA_DIR)

db = connect_database(settings, None)
if not db:
    sys.exit('Cannot connect with these creds: ' + str(settings['db']))

cursor = db.cursor()
for i in POSTGRES_DB_SCHEMA.splitlines():
    cursor.execute( i )  
db.commit()
cursor.close()
db.close()

print 'DB %s is ready-to-use.' % DEFAULT_POSTGRES_DB
