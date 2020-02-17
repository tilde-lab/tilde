"""
An updated CRYSTAL logs parser
wrapping a standalone parser called pycrystal
Authors: Evgeny Blokhin and Andrey Sobolev
"""
import os

from pycrystal import CRYSTOUT as _CRYSTOUT, CRYSTOUT_Error
from tilde.parsers import Output


class CRYSTOUT(Output):
    def __init__(self, filename):
        Output.__init__(self, filename)

        try:
            result = _CRYSTOUT(filename)
        except CRYSTOUT_Error as ex:
            raise RuntimeError(ex)

        for key in self.info:
            if result.info.get(key):
                self.info[key] = result.info[key]

        self.structures = result.info['structures']
        self.convergence = result.info['convergence']
        self.tresholds = result.info['optgeom']
        self.ncycles = result.info['ncycles']
        self.phonons = result.info['phonons']
        self.electrons = result.info['electrons']
        self.electrons['basis_set']['ps'] = self.electrons['basis_set']['ecp']
        self.elastic = result.info['elastic']

        self.info['framework'] = 0x3
        self.info['ansatz'] = 0x3

        self.related_files.append(filename)
        cur_folder = os.path.dirname(filename)
        check_files = []
        if filename.endswith('.cryst.out'):
            check_files = [filename.replace('.cryst.out', '') + '.d12', filename.replace('.cryst.out', '') + '.gui']
        elif filename.endswith('.out'):
            check_files = [filename.replace('.out', '') + '.d12', filename.replace('.out', '') + '.gui']
        for check in check_files:
            if os.path.exists(os.path.join(cur_folder, check)):
                self.related_files.append(os.path.join(cur_folder, check))

    @staticmethod
    def fingerprints(test_string):
        return _CRYSTOUT.detect(test_string)
