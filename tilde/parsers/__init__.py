
# Generic parser schema
# with the default values
# Author: Evgeny Blokhin

import os, sys
import re
import time
import math
import random

from numpy import array

import hashlib
import base64
from tilde.core.settings import settings
from ase.data import chemical_symbols


HASH_LENGTH = 47

class Output:
    def __init__(self, filename='', calcset=False):

        self._filename = filename # for quick and cheap checksums (NB never generate checksum from entire calc file, which may be huge!)
        self.data = ''            # file contents holder; may be empty for some parsers!
        self._checksum = None     # NB do not use directly
        self._calcset = calcset
        self._nested_depth = 0

        self.download_size = 0
        self.related_files = []

        if self._calcset:
            self.info = {}
            return

        self._starttime = time.time()

        self.structures =  [] # list of ASE objects with additional properties
        self.convergence = [] # zero-point energy convergence (I)
        self.tresholds =   [] # optimization convergence, list of 5 lists (II)
        self.ncycles =     [] # number of cycles at each optimisation step

        self.electrons = {
            #'rgkmax':          None,
            'basis_set':       None, # format depends on ansatz:
                                     # LCAO Gaussians: {'bs': {}, 'ps': {}}
                                     # PWs and LAPW: [atom1, ...]
            'eigvals':         {}, # raw eigenvalues {k:{alpha:[], beta:[]},}
            'projected':       [], # raw eigenvalues [..., ...] for total DOS smearing
            'dos':             {}, # in advance pre-computed DOS
            'bands':           {}  # in advance pre-computed band structure
        }
        # NB own properties for CRYSTAL: impacts, proj_eigv_impacts, e_proj_eigvals (TODO)

        self.phonons = {
            'modes':            {},
            'irreps':           {},
            'ir_active':        {},
            'raman_active':     {},
            'ph_eigvecs':       {},
            'ph_k_degeneracy':  {},
            'dfp_disps':        [],
            'dfp_magnitude':    None,
            'dielectric_tensor':False,
            'zpe':              None,
            'td':               None
        }

        # modules output object
        self.apps = {}

        # classification and technical info object
        # NB API call *classify* extends it with the new items
        self.info = {
            'warns':      [],
            'framework':  0x0, # code name
            'prog':       'unknown version', # code version
            'perf':       None, # benchmarking
            'location':   filename,
            'finished':   0x0,
            'duration':   None,
            'input':      None,

            'energy':     None, # in eV

            'standard':   '',
            'formula':    '',
            'dims':       False,
            'natom':      0,
            'elements':   [],
            'contents':   [],
            'lack':       False,
            'expanded':   False,
            'tags':       [],

            'etype':      0x0,
            'bandgap':    None, # in eV
            'bandgaptype':0x0,

            'optgeom':    False,
            'calctypes':  [],
            'H':          None,
            'H_types':    [],
            'tol':        None,
            'k':          None,
            'kshift':     None,
            'smear':      None, # in a.u.
            'smeartype':  None,
            'spin':       False,
            'lockstate':  None,

            'ansatz':     0x0,
            'techs':      [],
        }

    @classmethod
    def iparse(cls, filename):
        return [cls(filename)]

    def __getitem__(self, key):
        ''' get either by dict key or by attribute '''
        return getattr(self, key)

    def __setitem__(self, key, value):
        ''' in-place modifying '''
        return setattr(self, key, value)

    def __repr__(self):
        out = ''
        for repr in dir(self):
            if not hasattr(getattr(self, repr), '__call__') and repr != '__doc__':
                if repr == 'structures' and len(getattr(self, repr)):
                    if len(getattr(self, repr)) > 1:
                        out += repr + " ->\nINITIAL:\n" + str( getattr(self, repr)[0] ) + "\nFINAL:\n" + str( getattr(self, repr)[-1] ) + "\n\n"
                    else:
                        out += repr + " -> " + str( getattr(self, repr)[-1] ) + "\n\n"
                else:
                    str_repr = str( getattr(self, repr) )
                    if len(str_repr) < 2000: out += repr + ' -> ' + str_repr + "\n\n"
                    else: out += repr + ' -> ' + str_repr[:1000] + '...\n\n'
        return out

    def warning(self, msg):
        ''' store diagnostic messages '''
        self.info['warns'].append(msg)

    def get_checksum(self):
        ''' retrieve unique hash in a cross-platform manner:
        this is how unique identity is determined '''
        if self._checksum: return self._checksum

        if not self._filename: raise RuntimeError('Source calc file is required in order to properly save the data!')

        calc_checksum = hashlib.sha224()
        struc_repr = ""
        for ase_repr in self.structures:
            struc_repr += "%3.6f %3.6f %3.6f %3.6f %3.6f %3.6f %3.6f %3.6f %3.6f " % tuple(map(abs, [ase_repr.cell[0][0], ase_repr.cell[0][1], ase_repr.cell[0][2], ase_repr.cell[1][0], ase_repr.cell[1][1], ase_repr.cell[1][2], ase_repr.cell[2][0], ase_repr.cell[2][1], ase_repr.cell[2][2]])) # NB beware of length & minus zeros
            for atom in ase_repr:
                struc_repr += "%s %3.6f %3.6f %3.6f " % tuple(map(abs, [chemical_symbols.index(atom.symbol), atom.x, atom.y, atom.z])) # NB beware of length & minus zeros

        if self.info["energy"] is None:
            energy = str(None)
        else:
            energy = str(round(self.info['energy'], 11 - int(math.log10(math.fabs(self.info['energy'])))))

        calc_checksum.update(
            (struc_repr +
            energy + " " +
            self.info['prog'] + " " +
            str(self.info['input']) + " " +
            str(sum([2**x for x in self.info['calctypes']]))).encode('ascii')
        ) # this is fixed in DB schema 5.11 and should not be changed

        result = base64.b32encode(calc_checksum.digest()).decode('ascii')
        result = result[:result.index('=')] + 'CI'
        return result

    def benchmark(self):
        ''' benchmarking '''
        self.info['perf'] = "%1.2f" % (time.time() - self._starttime)
