import os, sys
import psycopg2

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
from core.settings import DB_SCHEMA

'''conn = psycopg2.connect("dbname=postgres user=eb")
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()
cursor.execute("CREATE DATABASE tilde;")
conn.commit()
cursor.close()
conn.close()'''

conn = psycopg2.connect("dbname=tilde user=eb")
cursor = conn.cursor()
for i in DB_SCHEMA.splitlines():
    cursor.execute( i )  
conn.commit()
cursor.close()
conn.close()
