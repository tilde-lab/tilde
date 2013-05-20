from ase.asec.command import Command
from ase.visualize import view


class ViewCommand(Command):
    @classmethod
    def add_parser(cls, subparser):
        parser = subparser.add_parser('view', help='ag ...')
        
    def run(self, atoms, name):
        view(atoms)
