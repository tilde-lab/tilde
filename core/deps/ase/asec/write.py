from ase.asec.command import Command
from ase.io import write


class WriteCommand(Command):
    @classmethod
    def add_parser(cls, subparser):
        parser = subparser.add_parser('write', help='write ...')
        cls.add_arguments(parser)

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('filename', nargs='?')
        
    def run(self, atoms, name):
        filename = self.args.filename or '.traj'
        if filename[0] == '.':
            filename = name + self.args.tag + filename
        write(filename, atoms)
