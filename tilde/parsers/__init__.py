
# Abstract JSON schema of a generic parser
# v140714

import os
import sys
import re
import time
from hashlib import sha224

from numpy import array


class Output:
    def __init__(self, filename=None):
        
        # private objects
        
        self._starttime = time.time()        
        self._checksum = None   # 56-symbol hash NB: do not call directly
        self.data = ''          # file contents holder; may be empty for some parsers!

        # public objects
               
        self.structures = [] # list of ASE objects with additional properties

        self.electrons = {
            'type':            None,
            'rgkmax':          None,
            'basis_set':       None, # format depends on type:
                                     # LCAO: {'bs': {}, 'ps': {}}
                                     # PP_PW: {'ps': {}}
                                     # FP_LAPW: [atom1, ...]
            
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
        # API call *classify* extends it with the new items
        
        self.info = {
            'warns':      [],
            'framework':  'unknown', # code name
            'prog':       'unknown', # code version
            'perf':       None,
            'location':   filename,
            'finished':   0,  # -1 for not, 0 for n/a, +1 for yes
            'duration':   None,
            'input':      None,
            
            'energy':     None, # in eV
            
            'standard':   '',
            'formula':    '',
            'dims':       False,
            'natom':      0,
            'elements':   [], # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
            'contents':   [],
            'lack':       False,
            'expanded':   False,
            'tags':       [], # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
            
            'calctypes':  [], # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
            'H':          None,
            'tol':        None,
            'k':          None,
            'kshift':     None,
            'smear':      None, # in a.u.
            'smeartype':  None,
            'spin':       False,
            'lockstate':  None,
            
            'techs':      [], # corresponds to sharp-signed multiple tag container in Tilde hierarchy : todo simplify
                     
            'convergence':[], # zero-point energy convergence (I)
            'tresholds':  [], # optimization convergence, list of 5 lists (II)
            'ncycles':    [], # number of cycles at each optimisation pass step
        }

    def __getitem__(self, key):
        ''' get either by dict key or by attribute '''
        return getattr(self, key)
        
    def __setitem__(self, key, value):
        ''' in-place modifying '''
        return setattr(self, key, value)

    def __str__(self):
        ''' debug dumping '''
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
        ''' retrieve unique hash '''
        if not self._checksum:
            file_sha224_checksum = sha224()
            file_sha224_checksum.update(str(self.structures) + str(self.info['energy']) + str(self.info['location'])) # this is how unique identity is determined
            return file_sha224_checksum.hexdigest()
        else:
            return self._checksum

    def benchmark(self):
        ''' benchmarking '''
        self.info['perf'] = "%1.2f" % (time.time() - self._starttime)
