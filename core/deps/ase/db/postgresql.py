import psycopg2

from ase.db.sqlite import init_statements, tables, SQLite3Database


class Connection:
    def __init__(self, con):
        self.con = con

    def cursor(self):
        return Cursor(self.con.cursor())
    
    def commit(self):
        self.con.commit()

    def close(self):
        self.con.close()


class Cursor:
    def __init__(self, cur):
        self.cur = cur

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    def execute(self, statement, *args):
        self.cur.execute(statement.replace('?', '%s'), *args)

    def executemany(self, statement, *args):
        self.cur.executemany(statement.replace('?', '%s'), *args)

    
class PostgreSQLDatabase(SQLite3Database):
    def _connect(self):
        con = psycopg2.connect(database='postgres', user='ase', password='ase',
                               host='localhost')
        return Connection(con)

    def _initialize(self, con):
        pass


def reset():
    con = psycopg2.connect(database='postgres', user='postgres')
    cur = con.cursor()

    cur.execute("select count(*) from pg_tables where tablename='systems'")
    if cur.fetchone()[0] == 1:
        cur.execute('drop table %s cascade' % ', '.join(tables))
        cur.execute('drop role ase')
        cur.execute("create role ase login password 'ase'")
        con.commit()

    sql = init_statements.replace('blob', 'bytea')
    sql = sql.replace('real', 'double precision')
    cur.execute(sql)
    cur.execute('grant all privileges on %s to ase' % ', '.join(tables))
    con.commit()


if __name__ == '__main__':
    reset()
