
# Vibrational thermodynamics module
# this is a check module,
# to assure if we are able to avoid TD extraction
# and obtain TD from phonons only;

# partly uses Phonopy code
# written by Atsushi Togo

import os
import sys

from core.common import ModuleError

class Vibtd():
    def __init__(self, tilde_calc):
        self.vibtd = {
        'ezpe': None,
        'zpe': None
        }
        
        # actual for CRYSTAL code only
        if tilde_calc.phonons['zpe'] and tilde_calc.phonons['td']:
            
            # per cell or supercell? depends on CRYSTAL version!            
            self.vibtd['zpe'] = tilde_calc.phonons['zpe']
            self.vibtd['td'] = tilde_calc.phonons['td']
