import os
import operator
from time import time
from random import randint
from math import log, ceil

try:
    from functools import wraps
except ImportError:
    wraps = lambda f: lambda g: g  # PY24

from ase.utils import Lock
from ase.atoms import Atoms
from ase.data import atomic_numbers
from ase.constraints import FixAtoms
from ase.parallel import world, broadcast, DummyMPI
from ase.calculators.calculator import get_calculator
from ase.calculators.singlepoint import SinglePointCalculator


T0 = 946681200.0  # January 1. 2000

YEAR = 31557600.0  # 365.25 days

seconds = {'s': 1,
           'm': 60,
           'h': 3600,
           'd': 86400,
           'w': 604800,
           'M': 2629800,
           'y': YEAR}

ops = {'<': operator.lt,
       '<=': operator.le,
       '=': operator.eq,
       '>=': operator.ge,
       '>': operator.gt,
       '!=': operator.ne}


def connect(name, type='extract_from_name', create_indices=True,
            use_lock_file=False):
    if type == 'extract_from_name':
        if name is None:
            type = None
        elif name.startswith('postgres://'):
            type = 'postgres'
        else:
            type = os.path.splitext(name)[1][1:]

    if type is None:
        return NoDatabase()

    if type == 'json':
        from ase.db.json import JSONDatabase
        return JSONDatabase(name, use_lock_file=use_lock_file)
    if type == 'db':
        from ase.db.sqlite import SQLite3Database
        return SQLite3Database(name, create_indices, use_lock_file)
    if type == 'postgres':
        from ase.db.postgresql import PostgreSQLDatabase as DB
        return PostgreSQLDatabase(name, create_indices)
    raise ValueError('Unknown database type: ' + type)


class FancyDict(dict):
    def __getattr__(self, key):
        if key not in self:
            return dict.__getattribute__(self, key)#raise KeyError
        value = self[key]
        if isinstance(value, dict):
            return FancyDict(value)
        return value


def lock(method):
    @wraps(method)
    def new_method(self, *args, **kwargs):
        if self.lock is None:
            return method(self, *args, **kwargs)
        else:
            #with self.lock: PY24
            #    return method(self, *args, **kwargs)
            self.lock.acquire()
            try:
                return method(self, *args, **kwargs)
            finally:
                self.lock.release()
    return new_method


def parallel(method):
    if world.size == 1:
        return method
    @wraps(method)
    def new_method(*args, **kwargs):
        if world.rank == 0:
            result = method(*args, **kwargs)
        else:
            result = None
        result = broadcast(result)
        return result
    return new_method


def parallel_generator(generator):
    if world.size == 1:
        return generator
    @wraps(generator)
    def new_generator(*args, **kwargs):
        if world.rank == 0:
            for result in generator(*args, **kwargs):
                result = broadcast(result)
                yield result
            broadcast(None)
        else:
            result = broadcast(None)
            while result is not None:
                yield result
    return new_generator


class NoDatabase:
    def __init__(self, filename=None, create_indices=True,
                 use_lock_file=False):
        self.filename = filename
        self.create_indices = create_indices
        if use_lock_file:
            self.lock = Lock(filename + '.lock', world=DummyMPI())
        else:
            self.lock = None

        self.timestamp = None  # timestamp form last write

    @parallel
    @lock
    def write(self, id, atoms, keywords=[], key_value_pairs={}, data={},
              timestamp=None, replace=True):
        if timestamp is None:
            timestamp = (time() - T0) / YEAR
        self.timestamp = timestamp
        if atoms is None:
            atoms = Atoms()
        self._write(id, atoms, keywords, key_value_pairs, data, replace)

    def _write(self, id, atoms, keywords, key_value_pairs, data, replace):
        pass

    def create_random_id(self, n):
        hexdigits = int(ceil(log((n + 1) * 100) / log(2) / 4))
        id = '%x' % randint(16**(hexdigits - 1), 16**hexdigits - 1)
        return id

    def collect_data(self, atoms):
        dct = atoms2dict(atoms)
        dct['timestamp'] = self.timestamp
        dct['username'] = os.getenv('USER')
        if atoms.calc is not None:
            dct['calculator_name'] = atoms.calc.name.lower()
            dct['calculator_parameters'] = atoms.calc.todict()
            if len(atoms.calc.check_state(atoms)) == 0:
                dct['results'] = atoms.calc.results
            else:
                dct['results'] = {}
        return dct

    @parallel
    def get_dict(self, id, fancy=True):
        dct = self._get_dict(id)
        if fancy:
            dct = FancyDict(dct)
        return dct

    def get_atoms(self, id=0, attach_calculator=False,
                  add_additional_information=False):
        dct = self.get_dict(id, fancy=False)
        atoms = dict2atoms(dct, attach_calculator)
        if add_additional_information:
            atoms.info = {}
            for key in ['id', 'unique_id', 'keywords', 'key_value_pairs',
                        'data']:
                if key in dct:
                    atoms.info[key] = dct[key]
        return atoms

    def __getitem__(self, index):
        if index == slice(None, None, None):
            return [self[0]]
        return self.get_atoms(index)

    @lock
    @parallel
    def update(self, ids, add_keywords, add_key_value_pairs):
        m = 0
        n = 0
        for id in ids:
            dct = self._get_dict(id)
            keywords = dct.get('keywords', [])
            for keyword in add_keywords:
                if keyword not in keywords:
                    keywords.append(keyword)
                    m += 1
            key_value_pairs = dct.get('key_value_pairs', {})
            n -= len(key_value_pairs)
            key_value_pairs.update(add_key_value_pairs)
            n += len(key_value_pairs)
            self.timestamp = dct['timestamp']
            self._write(id, dct, keywords, key_value_pairs,
                        data=dct.get('data', {}), replace=True)
        return m, n

    @parallel_generator
    def select(self, expressions=None, **kwargs):
        username = kwargs.pop('username', None)  # PY24
        charge = kwargs.pop('charge', None)
        calculator = kwargs.pop('calculator', None)
        filter = kwargs.pop('filter', None)
        fancy = kwargs.pop('fancy', True)
        explain = kwargs.pop('explain', False)
        count = kwargs.pop('count', False)
        verbosity = kwargs.pop('verbosity', 1)

        if expressions is None:
            expressions = []
        elif not isinstance(expressions, list):
            expressions = expressions.split(',')
        keywords = []
        comparisons = []
        for expression in expressions:
            if not isinstance(expression, str):
                comparisons.append(expression)
                continue
            if expression.count('<') == 2:
                value, expression = expression.split('<', 1)
                if expression[0] == '=':
                    op = '>='
                    expression = expression[1:]
                else:
                    op = '>'
                key = expression.split('<', 1)[0]
                comparisons.append((key, op, value))
            for op in ['!=', '<=', '>=', '<', '>', '=']:
                if op in expression:
                    break
            else:
                keywords.append(expression)
                continue
            key, value = expression.split(op)
            comparisons.append((key, op, value))
        cmps = []
        for key, op, value in comparisons:
            if key == 'age':
                key = 'timestamp'
                op = {'<': '>', '<=': '>=', '>=': '<=', '>': '<'}.get(op, op)
                value = (time() - T0) / YEAR - time_string_to_float(value)
            elif key == 'calculator':
                key = 'calculator_name'
            elif key in atomic_numbers:
                key = atomic_numbers[key]
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    assert op == '='
            cmps.append((key, op, value))
        if username is not None:
            cmps.append(('username', '=', username))
        if charge is not None:
            cmps.append(('charge', '=', charge))
        if calculator is not None:
            cmps.append(('claculator_name', '=', calculator))
        for symbol, n in kwargs.items():
            assert isinstance(n, int)
            Z = atomic_numbers[symbol]
            cmps.append((Z, op, n))
        for dct in self._select(keywords, cmps, explain=explain,
                                verbosity=verbosity):
            if filter is None or filter(dct):
                if fancy:
                    dct = FancyDict(dct)
                yield dct
                

def atoms2dict(atoms):
    data = {
        'numbers': atoms.numbers,
        'pbc': atoms.pbc,
        'cell': atoms.cell,
        'positions': atoms.positions,
        'unique_id': '%x' % randint(16**31, 16**32 - 1)}
    if atoms.has('magmoms'):
        data['magmoms'] = atoms.get_initial_magnetic_moments()
    if atoms.has('charges'):
        data['charges'] = atoms.get_initial_charges()
    if atoms.has('masses'):
        data['masses'] = atoms.get_masses()
    if atoms.has('tags'):
        data['tags'] = atoms.get_tags()
    if atoms.has('momenta'):
        data['momenta'] = atoms.get_momenta()
    if atoms.constraints:
        data['constraints'] = [c.todict() for c in atoms.constraints]
    return data


def dict2atoms(dct, attach_calculator=False):
    constraint_dicts = dct.get('constraints')
    if constraint_dicts:
        constraints = []
        for c in constraint_dicts:
            assert c.pop('__name__') == 'ase.constraints.FixAtoms'
            constraints.append(FixAtoms(**c))
    else:
        constraints = None

    atoms = Atoms(dct['numbers'],
                  dct['positions'],
                  cell=dct['cell'],
                  pbc=dct['pbc'],
                  magmoms=dct.get('magmoms'),
                  charges=dct.get('charges'),
                  tags=dct.get('tags'),
                  masses=dct.get('masses'),
                  momenta=dct.get('momenta'),
                  constraint=constraints)

    results = dct.get('results')
    if attach_calculator:
        atoms.calc = get_calculator(dct['calculator_name'])(
            **dct['calculator_parameters'])
    elif results:
        atoms.calc = SinglePointCalculator(atoms, **results)

    return atoms


def time_string_to_float(s):
    if isinstance(s, (float, int)):
        return s
    s = s.replace(' ', '')
    if '+' in s:
        return sum(time_string_to_float(x) for x in s.split('+'))
    if s[-2].isalpha() and s[-1] == 's':
        s = s[:-1]
    i = 1
    while s[i].isdigit():
        i += 1
    return seconds[s[i:]] * int(s[:i]) / YEAR


def float_to_time_string(t):
    t *= YEAR
    for s in 'yMwdhms':
        if t / seconds[s] > 5:
            break
    return '%d%s' % (round(t / seconds[s]), s)
