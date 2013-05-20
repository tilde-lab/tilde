import numpy as np

from ase.asec.command import Command


class ResultsCommand(Command):
    @classmethod
    def add_parser(cls, subparser):
        parser = subparser.add_parser('results', help='results ...')

    def __init__(self, logfile, args):
        Command.__init__(self, logfile, args)
        self.data = self.read()

    def finalize(self):
        for name in self.args.names:
            if name in self.data:
                e = self.data[name].get('energy', 42)
            else:
                e = 117
            print '%2s %10.3f' % (name, e)
