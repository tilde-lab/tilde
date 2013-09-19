
# Vibrational thermodynamics module
# obtains thermodynamic functions basing on phonons
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
        
        if tilde_calc.phonons['zpe'] and tilde_calc['energy']:
            self.vibtd['zpe'] = tilde_calc.phonons['zpe'] # a.u. (per cell or supercell???)
            self.vibtd['ezpe'] = tilde_calc.phonons['zpe'] + tilde_calc['energy']