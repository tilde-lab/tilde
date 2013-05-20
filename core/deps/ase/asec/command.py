from ase.utils import prnt
from ase.tasks.io import read_json


class Command:
    def __init__(self, logfile, args):
        self.logfile = logfile
        self.args = args

    def log(self, *args, **kwargs):
        prnt(file=self.logfile, *args, **kwargs)

    @classmethod
    def add_parser(cls, subparser):
        pass

    def get_filename(self, name=None, ext=None):
        if name is None:
            if self.args.tag is None:
                filename = 'asec'
            else:
                filename = self.args.tag
        else:
            if '.' in name:
                name = name.rsplit('.', 1)[0]
            if self.args.tag is None:
                filename = name
            else:
                filename = name + '-' + self.args.tag

        if ext:
            filename += '.' + ext

        return filename

    def run(self, atoms, name):
        pass

    def finalize(self):
        pass
    
    def read(self):
        filename = self.get_filename(ext='json')
        return read_json(filename)
