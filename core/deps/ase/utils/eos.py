# -*- coding: utf-8 -*-

import numpy as np

from ase.utils.eosip3 import EquationOfStateIP3

try:
    # ase.utils.eosase2 requires scipy
    import scipy
    from ase.utils.eosase2 import EquationOfStateASE2

    class EquationOfState(EquationOfStateIP3, EquationOfStateASE2):

        """Fit equation of state for bulk systems.

        The following equation is used::

           ip3 (default)
               A third order inverse polynomial fit

                               2      3        -1/3
           E(V) = c + c t + c t  + c t ,  t = V
                   0   1     2      3

           taylor
               A third order Taylor series expansion about the minimum volume

           murnaghan
               PRB 28, 5480 (1983)

           birch
               Intermetallic compounds: Principles and Practice,
               Vol I: Principles. pages 195-210

           birchmurnaghan
               PRB 70, 224107

           pouriertarantola
               PRB 70, 224107

           vinet
               PRB 70, 224107

           antonschmidt
               Intermetallics 11, 23-32 (2003)

           p3
               A third order polynomial fit

        Use::

           eos = EquationOfState(volumes, energies, eos='ip3')
           v0, e0, B = eos.fit()
           eos.plot()

        """
        def __init__(self, volumes, energies, eos='ip3'):
            if eos == 'ip3':
                EquationOfStateIP3.__init__(self, volumes, energies, eos)
            else:
                # old ASE2 implementation
                EquationOfStateASE2.__init__(self, volumes, energies, eos)

        def fit(self):
            if self.eos_string == 'ip3':
                return EquationOfStateIP3.fit(self)
            else:
                return EquationOfStateASE2.fit(self)

        def plot(self, filename=None, show=None):
            if self.eos_string == 'ip3':
                return EquationOfStateIP3.plot(self, filename, show)
            else:
                return EquationOfStateASE2.plot(self, filename, show)

except ImportError:
    # ase.utils.eosip3 requires only numpy
    EquationOfState = EquationOfStateIP3
