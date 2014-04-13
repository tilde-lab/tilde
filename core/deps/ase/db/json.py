from __future__ import absolute_import
import os
import copy
import datetime
import warnings
from json import JSONEncoder, JSONDecoder

import numpy as np

from ase.parallel import world
from ase.db import IdCollisionError
from ase.db.core import NoDatabase, ops, parallel, lock


class MyEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime.datetime):
            return {'__datetime__': obj.isoformat()}
        if hasattr(obj, 'todict'):
            return obj.todict()
        return JSONEncoder.default(self, obj)


encode = MyEncoder().encode


def object_hook(dct):
    if '__datetime__' in dct:
        return datetime.datetime.strptime(dct['__datetime__'],
                                          "%Y-%m-%dT%H:%M:%S.%f")
    return dct


mydecode = JSONDecoder(object_hook=object_hook).decode


def numpyfy(obj):
    if isinstance(obj, dict):
        return dict((key, numpyfy(value)) for key, value in obj.items())
    if isinstance(obj, list) and len(obj) > 0:
        try:
            a = np.array(obj)
        except ValueError:
            obj = [numpyfy(value) for value in obj]
        else:
            if a.dtype in [bool, int, float]:
                obj = a
    return obj


def decode(txt):
    return numpyfy(mydecode(txt))


def write_json(name, results):
    if world.rank == 0:
        if isinstance(name, str):
            fd = open(name, 'w')
        else:
            fd = name
        fd.write(encode(results))
        fd.close()


def read_json(name):
    if isinstance(name, str):
        fd = open(name, 'r')
    else:
        fd = name
    results = decode(fd.read())
    fd.close()
    return results


class JSONDatabase(NoDatabase):
    def _write(self, id, atoms, keywords, key_value_pairs, data, replace):
        bigdct = {}
        if isinstance(self.filename, str) and os.path.isfile(self.filename):
            try:
                bigdct = read_json(self.filename)
            except SyntaxError:
                pass
            else:
                if not replace and id in bigdct:
                    raise IdCollisionError

        if isinstance(atoms, dict):
            dct = copy.deepcopy(atoms)
            unique_id = dct['unique_id']
            for d in bigdct.values():
                if d['unique_id'] == unique_id:
                    id = d['id']
                    break
        else:
            dct = self.collect_data(atoms)

        if id is None:
            nrows = len(bigdct)
            while id is None:
                id = self.create_random_id(nrows)
                if id in bigdct:
                    id = None

        dct['id'] = id

        if keywords:
            dct['keywords'] = keywords
        if key_value_pairs:
            dct['key_value_pairs'] = key_value_pairs
        if data:
            dct['data'] = data

        bigdct[id] = dct
        write_json(self.filename, bigdct)

    @lock
    @parallel
    def delete(self, ids):
        bigdct = read_json(self.filename)
        for id in ids:
            del bigdct[id]
        write_json(self.filename, bigdct)

    def _get_dict(self, id):
        bigdct = read_json(self.filename)
        if id in [-1, 0]:
            assert len(bigdct) == 1
            id = bigdct.keys()[0]
        return bigdct[id]

    def _select(self, keywords, cmps, explain=False, verbosity=1):
        if explain:
            return
        bigdct = read_json(self.filename)
        cmps = [(key, ops[op], val) for key, op, val in cmps]
        for dct in bigdct.values():
            for keyword in keywords:
                if 'keywords' not in dct or keyword not in dct['keywords']:
                    break
            else:
                for key, op, val in cmps:
                    value = get_value(dct, key)
                    if not op(value, val):
                        break
                else:
                    yield dct

    @lock
    @parallel
    def update(self, ids, add_keywords, add_key_value_pairs):
        bigdct = read_json(self.filename)
        m = 0
        n = 0
        for id in ids:
            dct = bigdct[id]
            if add_keywords:
                keywords = dct.setdefault('keywords', [])
                for keyword in add_keywords:
                    if keyword not in keywords:
                        keywords.append(keyword)
                        m += 1
            if add_key_value_pairs:
                key_value_pairs = dct.setdefault('key_value_pairs', {})
                n -= len(key_value_pairs)
                key_value_pairs.update(add_key_value_pairs)
                n += len(key_value_pairs)
        write_json(self.filename, bigdct)
        return m, n


def get_value(dct, key):
    pairs = dct.get('key_value_pairs')
    if pairs is None:
        value = None
    else:
        value = pairs.get(key)
    if value is not None:
        return value
    if key in ['energy', 'magmom']:
        return dct.get('results', {}).get(key)
    if key in ['id', 'timestamp', 'username', 'calculator_name']:
        return dct.get(key)
    if isinstance(key, int):
        return np.equal(dct['numbers'], key).sum()
    if key == 'natoms':
        return len(dct['numbers'])
