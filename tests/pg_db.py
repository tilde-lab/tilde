import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
import psycopg2

from core.settings import POSTGRES_DB_SCHEMA

conn = psycopg2.connect("dbname=tilde_master user=nobody")
cursor = conn.cursor()
for i in POSTGRES_DB_SCHEMA.splitlines():
    cursor.execute( i )  
conn.commit()
cursor.close()
conn.close()
