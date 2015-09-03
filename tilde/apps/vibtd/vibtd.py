
# Vibrational thermodynamics module
# this is to assure if we are able to avoid TD extraction
# and obtain TD from phonons only
# Author: Evgeny Blokhin
# partly uses Phonopy code written by Atsushi Togo

import os, sys

from tilde.core.common import ModuleError

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
