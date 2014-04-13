from __future__ import absolute_import, print_function
import sqlite3

import numpy as np

from ase.db import IdCollisionError
from ase.db.core import NoDatabase, ops
from ase.db.json import encode, decode


init_statements = """\
create table systems (
    id text primary key,
    unique_id text unique,
    timestamp real,
    username text,
    numbers blob,
    positions blob,
    cell blob,
    pbc integer,
    initial_magmoms blob,
    initial_charges blob,
    masses blob,
    tags blob,
    moments blob,
    constraints text,
    calculator_name text,
    calculator_parameters text,
    energy real,
    free_energy real,
    forces blob,
    stress blob,
    magmoms blob,
    magmom blob,
    charges blob,
    data text); -- contains keywords and key_value_pairs also
create table species (
    Z integer,
    n integer,
    id text,
    foreign key (id) references systems(id));
create table keywords (
    keyword text,
    id text,
    foreign key (id) references systems(id));
create table text_key_values (
    key text,
    value text,
    id text,
    foreign key (id) references systems(id));
create table number_key_values (
    key text,
    value real,
    id text,
    foreign key (id) references systems (id))
"""

index_statements = """\
create index unique_id_index on systems(unique_id);
create index species_index on species(Z)
"""

tables = ['systems', 'species', 'keywords',
          'text_key_values', 'number_key_values']


class SQLite3Database(NoDatabase):
    def _connect(self):
        return sqlite3.connect(self.filename)

    def _initialize(self, con):
        cur = con.execute(
            'select count(*) from sqlite_master where name="systems"')
        if cur.fetchone()[0] == 0:
            for statement in init_statements.split(';'):
                con.execute(statement)
            if self.create_indices:
                for statement in index_statements.split(';'):
                    con.execute(statement)
            con.commit()

    def _write(self, id, atoms, keywords, key_value_pairs, data, replace):
        con = self._connect()
        self._initialize(con)
        cur = con.cursor()
                
        if isinstance(atoms, dict):
            dct = atoms
            unique_id = dct['unique_id']
            cur.execute('select id from systems where unique_id=?',
                        (unique_id,))
            rows = cur.fetchall()
            if rows:
                id = rows[0][0]
        else:
            dct = self.collect_data(atoms)

        if id is None:
            cur.execute('select count(*) from systems')
            nrows = cur.fetchone()[0]
            while id is None:
                id = self.create_random_id(nrows)
                cur.execute('select count(*) from systems where id=?', (id,))
                if cur.fetchone()[0] == 1:
                    id = None
            
        row = (id,
               dct['unique_id'],
               self.timestamp,
               dct['username'],
               blob(dct.get('numbers')),
               blob(dct.get('positions')),
               blob(dct.get('cell')),
               int(np.dot(dct.get('pbc'), [1, 2, 4])),
               blob(dct.get('magmoms')),
               blob(dct.get('charges')),
               blob(dct.get('masses')),
               blob(dct.get('tags')),
               blob(dct.get('moments')),
               dct.get('constraints'))

        if 'calculator_name' in dct:
            row += (dct['calculator_name'],
                    encode(dct['calculator_parameters']))
        else:
            row += (None, None)

        if 'results' in dct:
            r = dct['results']
            magmom = r.get('magmom')
            if magmom is not None:
                # magmom can be one or three numbers (non-collinear case)
                magmom = np.array(magmom)
            row += (r.get('energy'),
                    r.get('free_energy'),
                    blob(r.get('forces')),
                    blob(r.get('stress')),
                    blob(r.get('magmoms')),
                    blob(magmom),
                    blob(r.get('charges')))
        else:
            row += (None, None, None, None, None, None, None)

        row += (encode({'data': data,
                        'keywords': keywords,
                        'key_value_pairs': key_value_pairs}),)

        cur.execute('select count(*) from systems where id=?', (id,))
        new = (cur.fetchone()[0] == 0)

        if not (replace or new):
            raise IdCollisionError

        if not new:
            self._delete(cur, [id])

        q = ', '.join('?' * len(row))
        cur.execute('insert into systems values (%s)' % q, row)

        count = np.bincount(dct['numbers'])
        unique_numbers = count.nonzero()[0]
        species = [(int(Z), int(count[Z]), id) for Z in unique_numbers]
        cur.executemany('insert into species values (?, ?, ?)', species)

        text_key_values = []
        number_key_values = []
        for key, value in key_value_pairs.items():
            if isinstance(value, str):
                text_key_values.append([key, value, id])
            elif isinstance(value, (float, int)):
                number_key_values.append([key, float(value), id])
            else:
                assert 0, value
 
        if text_key_values:
            cur.executemany('insert into text_key_values values (?, ?, ?)',
                            text_key_values)
        if number_key_values:
            cur.executemany('insert into number_key_values values (?, ?, ?)',
                            number_key_values)
        if keywords:
            cur.executemany('insert into keywords values (?, ?)',
                            [(keyword, id) for keyword in keywords])

        con.commit()
        con.close()
       
    def _get_dict(self, id):
        con = self._connect()
        c = con.cursor()
        if id in [-1, 0]:
            c.execute('select count(*) from systems')
            assert c.fetchone()[0] == 1
            c.execute('select * from systems')
        else:
            c.execute('select * from systems where id=?', (id,))
        row = c.fetchone()
        return self.row_to_dict(row)

    def row_to_dict(self, row):
        dct = {'id': row[0],
               'unique_id': row[1],
               'timestamp': row[2],
               'username': row[3],
               'numbers': deblob(row[4], np.int32),
               'positions': deblob(row[5], shape=(-1, 3)),
               'cell': deblob(row[6], shape=(3, 3)),
               'pbc': (row[7] & np.array([1, 2, 4])).astype(bool)}
        if row[8] is not None:
            dct['magmoms'] = deblob(row[8])
        if row[9] is not None:
            dct['charges'] = deblob(row[9])
        if row[10] is not None:
            dct['masses'] = deblob(row[10])
        if row[11] is not None:
            dct['tags'] = deblob(row[11], np.int32)
        if row[12] is not None:
            dct['moments'] = deblob(row[12], shape=(-1, 3))
        if row[13] is not None:
            dct['constraints'] = decode(row[13])
        if row[14] is not None:
            dct['calculator_name'] = row[14]
            dct['calculator_parameters'] = decode(row[15])
            results = {}
            if row[16] is not None:
                results['energy'] = row[16]
            if row[17] is not None:
                results['free_energy'] = row[17]
            if row[18] is not None:
                results['forces'] = deblob(row[18], shape=(-1, 3))
            if row[19] is not None:
                results['stress'] = deblob(row[19])
            if row[20] is not None:
                results['magmoms'] = deblob(row[20])
            if row[21] is not None:
                results['magmom'] = deblob(row[21])[0]
            if row[22] is not None:
                results['charges'] = deblob(row[22])
            if results:
                dct['results'] = results

        extra = decode(row[23])
        for key in ['keywords', 'key_value_pairs', 'data']:
            if extra[key]:
                dct[key] = extra[key]
        return dct

    def _select(self, keywords, cmps, explain, verbosity):
        tables = ['systems']
        where = []
        args = []
        for n, keyword in enumerate(keywords):
            tables.append('keywords as keyword{0}'.format(n))
            where.append(
                'systems.id=keyword{0}.id and keyword{0}.keyword=?'.format(n))
            args.append(keyword)
        bad = {}
        for key, op, value in cmps:
            if isinstance(key, int):
                bad[key] = bad.get(key, True) and ops[op](0, value)
        cmps2 = []
        nspecies = 0
        ntext = 0
        nnumber = 0
        for key, op, value in cmps:
            if key in ['id', 'energy', 'magmom', 'timestamp', 'username',
                       'calculator_name']:
                where.append('systems.{0}{1}?'.format(key, op))
                args.append(value)
            elif key == 'natoms':
                cmps2.append((key, ops[op], value))
            elif isinstance(key, int):
                if bad[key]:
                    cmps2.append((key, ops[op], value))
                else:
                    tables.append('species as specie{0}'.format(nspecies))
                    where.append(('systems.id=specie{0}.id and ' +
                                  'specie{0}.Z=? and ' +
                                  'specie{0}.n{1}?').format(nspecies, op))
                    args += [key, value]
                    nspecies += 1
            elif isinstance(value, str):
                tables.append('text_key_values as text{0}'.format(ntext))
                where.append(('systems.id=text{0}.id and ' +
                              'text{0}.key=? and ' +
                              'text{0}.value{1}?').format(ntext, op))
                args += [key, value]
                ntext += 1
            else:
                tables.append('number_key_values as number{0}'.format(nnumber))
                where.append(('systems.id=number{0}.id and ' +
                              'number{0}.key=? and ' +
                              'number{0}.value{1}?').format(nnumber, op))
                args += [key, value]
                nnumber += 1
                
        sql = 'select systems.* from\n  ' + ', '.join(tables)
        if where:
            sql += '\n  where\n  ' + ' and\n  '.join(where)
        if explain:
            sql = 'explain query plan ' + sql
        if verbosity == 2:
            print(sql, args)
        con = self._connect()
        cur = con.cursor()
        cur.execute(sql, args)
        if explain:
            for row in cur.fetchall():
                yield {'explain': row}
        else:
            for row in cur.fetchall():
                if cmps2:
                    numbers = deblob(row[4], np.int32)
                    for key, op, value in cmps2:
                        if key == 'natoms':
                            if not op(len(numbers), value):
                                break
                        elif not op((numbers == key).sum(), value):
                            break
                    else:
                        yield self.row_to_dict(row)
                else:
                    yield self.row_to_dict(row)
        
    def delete(self, ids):
        con = self._connect()
        self._delete(con.cursor(), ids)
        con.commit()
        con.close()

    def _delete(self, cur, ids):
        for table in tables[::-1]:
            cur.executemany('delete from {0} where id=?'.format(table),
                            ((id,) for id in ids))


def blob(array):
    """Convert array to blob/buffer object."""

    if array is None:
        return None
    if array.dtype == np.int64:
        array = array.astype(np.int32)
    return buffer(array)


def deblob(buf, dtype=float, shape=None):
    """Convert blob/buffer object to ndarray of correct dtype and shape.

    (without creating an extra view)."""

    if buf is None:
        return None
    array = np.frombuffer(buf, dtype)
    if shape is not None:
        array.shape = shape
    return array
