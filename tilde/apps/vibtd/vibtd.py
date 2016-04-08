
# Vibrational thermodynamics module
# this is to assure if we are able to avoid thermodynamics extraction
# from CRYSTAL outputs and calculate thermodynamics from phonons directly
# UPD: an answer is not really, since the vibrational thermodynamics is
# updated in CRYSTAL from version to version drastically.
# Author: Evgeny Blokhin
# partly uses Phonopy code written by Atsushi Togo

from tilde.core.common import ModuleError

class Vibtd():
    def __init__(self, tilde_calc):
        self.vibtd = {
        'ezpe': None,
        'zpe': None
        }

        # actual for CRYSTAL code only
        if tilde_calc.phonons['zpe'] and tilde_calc.phonons['td']:

            # per cell or supercell? depends on CRYSTAL version
            self.vibtd['zpe'] = tilde_calc.phonons['zpe']
            self.vibtd['td'] = tilde_calc.phonons['td']
