import os
import time
import argparse
import traceback

from ase.asec.command import Command
from ase.calculators.calculator import get_calculator
from ase.utils import Lock, OpenLock
from ase.tasks.io import read_json, write_json


def str2dict(s, namespace={}, sep='='):
    """Convert comma-separated key=value string to dictionary.

    Examples:

    >>> str2dict('xc=PBE,nbands=200,parallel={band:4}')
    {'xc': 'PBE', 'nbands': 200, 'parallel': {'band': 4}}
    >>> str2dict('a=1.2,b=True,c=ab,d=1,2,3,e={f:42,g:cd}')
    {'a': 1.2, 'c': 'ab', 'b': True, 'e': {'g': 'cd', 'f': 42}, 'd': (1, 2, 3)}
    """
    
    dct = {}
    s = (s + ',').split(sep)
    for i in range(len(s) - 1):
        key = s[i]
        m = s[i + 1].rfind(',')
        value = s[i + 1][:m]
        if value[0] == '{':
            assert value[-1] == '}'
            value = str2dict(value[1:-1], namespace, ':')
        else:
            try:
                value = eval(value, namespace)
            except (NameError, SyntaxError):
                pass
        dct[key] = value
        s[i + 1] = s[i + 1][m + 1:]
    return dct


class RunCommand(Command):
    @classmethod
    def add_parser(cls, subparser):
        parser = subparser.add_parser('run', help='run ...')
        cls.add_arguments(parser)

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--after')
        calculator = getattr(cls, '_calculator', None)
        if calculator is None:
            parser.add_argument(
                '-c', '--calculator', default='emt',
                help='...')
        else:
            parser.add_argument(
                '-c', '--calculator', default=calculator.name,
                help=argparse.SUPPRESS)
            
        parser.add_argument('-p', '--parameters', default='',
                            metavar='key=value,...',
                        help='Comma-separated key=value pairs of ' +
                        'calculator specific parameters.')
        parser.add_argument('-l', '--use-lock-file', action='store_true',
                            help='Skip calculations where the json ' +
                           'lock-file or result file already exists.')
        parser.add_argument(
            '--properties', default='efsdMm',
            help='Default value is "efsdMm" meaning calculate energy, ' +
            'forces, stress, dipole moment, total magnetic moment and ' +
            'atomic magnetic moments.')
    
    lock = None
        
    def run(self, atoms, name):
        args = self.args

        if self.lock is None:
            # Create lock object:
            if args.use_lock_file:
                self.lock = Lock(self.get_filename(ext='lock'))
            else:
                self.lock = OpenLock()

        skip = False
        if args.use_lock_file:
            try:
                filename = self.get_filename(ext='json')
                self.lock.acquire()
                if os.path.isfile(filename):
                    data = read_json(filename)
                    if name in data:
                        skip = True
                    else:
                        data[name] = {}
                        write_json(filename, data)
                else:
                    write_json(filename, {name: {}})
            finally:
                self.lock.release()
        
        if not skip:
            self.set_calculator(atoms, name)

            tstart = time.time()
            try:
                data = self.calculate(atoms, name)
            except KeyboardInterrupt:
                raise
            except Exception:
                self.log(name, 'FAILED')
                traceback.print_exc(file=self.logfile)
            else:
                tstop = time.time()
                data['time'] = tstop - tstart
                self.write(name, data)

    def set_calculator(self, atoms, name):
        args = self.args
        cls = get_calculator(args.calculator)
        if self._calculator is None:
            namespace = {}
        else:
            namespace = self._calculator.namespace
        parameters = str2dict(args.parameters, namespace)
        if getattr(cls, 'nolabel', False):
            atoms.calc = cls(**parameters)
        else:
            atoms.calc = cls(label=self.get_filename(name), **parameters)

    def calculate(self, atoms, name):
        args = self.args

        data = {}
        for p in args.properties:
            property, method = {'e': ('energy', 'get_potential_energy'),
                                'f': ('forces', 'get_forces'),
                                's': ('stress', 'get_stress'),
                                'd': ('dipole', 'get_dipole_moment'),
                                'M': ('magmom', 'get_magnetic_moment'),
                                'm': ('magmoms', 'get_magnetic_moments')}[p]
            try:
                x = getattr(atoms, method)()
            except NotImplementedError:
                pass
            else:
                data[property] = x

        if args.after:
            exec args.after in {'atoms': atoms, 'data': data}
        
        return data

    def write(self, name, data):
        filename = self.get_filename(ext='json')
        try:
            self.lock.acquire()
            if os.path.isfile(filename):
                alldata = read_json(filename)
            else:
                alldata = {}
            alldata[name] = data
            write_json(filename, alldata)
        finally:
            self.lock.release()
