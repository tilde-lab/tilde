#!/usr/bin/env python
# tilda project: abstract class of a generic parser
# v241012

import os
import sys
import re
import time
from hashlib import sha224

class Output:
    def __init__(self):
        ''' PARSER API obligatory attributes '''
        self.prog = 'unknown'
        self._coupler_ = False # special attribute for an output which should be merged with other by coinciding E_tot
        self.classified = {}
        self.location = '' # path to the original file
        
        self.method = {}
        self.structures = [] # x, y, z are in cartesian system
        self.charges = None
        self.input = None
        self.energy = None
        self.bs = None
        
        self.phonons = None
        self.irreps = None
        self.ir_active = None
        self.raman_active = None
        self.ph_eigvecs = None        
        self.ph_k_degeneracy = None
        
        self.e_eigvals = None
        self.e_proj_eigv_impacts = None
        self.e_last = None
        
        self.convergence = None
        self.ncycles = None
        self.tresholds = None
        self.finished = 0 # -1 for not, 0 for n/a, +1 for yes
        self.symops = ['+x,+y,+z']
        self.periodic_limit = 50 # note: non-periodic component(s) are assigned 500 in CRYSTAL
        
        self.warns = []
        self.starttime = time.time()
        
    def __getitem__(self, item):
        ''' get either by dict key or by attribute '''
        return getattr(self, item)
        
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
        self.warns.append(msg)

    def checksum(self):
        ''' calculate unique ID '''
        if not self.data: return None
        file_sha224_checksum = sha224()
        file_sha224_checksum.update(self.data)
        return file_sha224_checksum.hexdigest()
        
    def perf(self):
        return time.time() - self.starttime
    