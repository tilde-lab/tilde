
# Phonon and electron DOS plotter
# Author: Evgeny Blokhin
#
# Based mainly on DOS implementation by A.Togo in Phonopy 0.7 code (dos.py)
# http://phonopy.sf.net/

import os, sys
import numpy as np


class NormalDistribution:
    def __init__(self, sigma):
        self.sigma = sigma

    def calc(self, x):
        return 1.0 / np.sqrt(2 * np.pi) / self.sigma * np.exp(-x**2 / 2.0 / self.sigma**2)

class CauchyDistribution:
    def __init__(self, gamma):
        self.gamma = gamma

    def calc(self, x):
        return self.gamma / np.pi / ( x**2 + self.gamma**2 )

class Dos:
    def __init__(self, eigenvalues, sigma=None):
        self.eigenvalues = np.array(eigenvalues)
        if sigma == None: self.sigma = 0.2
        else: self.sigma = sigma
        self.set_draw_area()

        # Default smearing
        self.set_smearing_function('Normal')

    def set_smearing_function(self, function_name):
        if function_name == 'Cauchy': self.smearing_function = CauchyDistribution(self.sigma)
        else: self.smearing_function = NormalDistribution(self.sigma)

    def set_draw_area(self, omega_min=None, omega_max=None, omega_pitch=None):
        if omega_pitch == None: self.omega_pitch = float(self.eigenvalues.max() - self.eigenvalues.min()) / 200
        else: self.omega_pitch = omega_pitch

        if omega_min == None: self.omega_min = self.eigenvalues.min() - self.sigma * 10
        else: self.omega_min = omega_min

        if omega_max == None: self.omega_max = self.eigenvalues.max() + self.sigma * 10
        else: self.omega_max = omega_max

class TotalDos(Dos):
    def __init__(self, eigenvalues, sigma=None):
        Dos.__init__(self, eigenvalues, sigma)

    def get_density_of_states_at_omega(self, omega):
        return np.sum( self.smearing_function.calc(self.eigenvalues - omega))

    def calculate(self):
        omega = self.omega_min
        dos = []

        if self.omega_pitch == 0: self.omega_pitch = 1 # beware of endless loop if omega_pitch=0
        while omega < self.omega_max + self.omega_pitch/10 :
            p = self.get_density_of_states_at_omega(omega)
            dos.append( [round(omega, 3), round(p, 3)] ) # round to reduce output
            omega += self.omega_pitch
        return dos

class PartialDos(Dos):
    # eigenvalues and impacts must be unique and one-to-one correspondent
    def __init__(self, eigenvalues, impacts, sigma=None):
        Dos.__init__(self, eigenvalues, sigma)
        self.impacts = np.array(impacts)

    def get_partial_dos_impact_at_omega(self, omega):
        # function for obtaining scaled partial impacts in any omega point using a linear equation interpolation
        if omega in self.eigenvalues:
            return self.impacts[ np.where(self.eigenvalues == omega)[0][0] ]
        if omega < self.eigenvalues[0]:
            return np.zeros( len(self.impacts[0]) )
        elif omega > self.eigenvalues[-1]:
            return self.impacts[-1]
        else:
            for n, i in enumerate(self.eigenvalues):
                if self.eigenvalues[n] < omega < self.eigenvalues[n+1]:
                    result = (omega - self.eigenvalues[n])*(self.impacts[n+1] - self.impacts[n])/(self.eigenvalues[n+1] - self.eigenvalues[n]) + self.impacts[n]
                    return result

    def calculate(self, types, labels):
        omega = self.omega_min
        pdos = []
        omegas = []

        plots = []

        if self.omega_pitch == 0: self.omega_pitch = 1 # beware of endless loop if omega_pitch=0
        while omega < self.omega_max + self.omega_pitch/10:
            partial = self.get_partial_dos_impact_at_omega(omega) * np.sum( self.smearing_function.calc(self.eigenvalues - omega) )
            omegas.append( omega )
            pdos.append( partial )
            omega += self.omega_pitch
        partial_dos = np.array(pdos).transpose()
        omegas = np.array(omegas)

        for n, set_for_sum in enumerate(types):
            atom = [k for k, v in labels.iteritems() if v == n][0] # find k by v
            
            multdos = 1
            #if atom != 'Fe': continue
            #else: multdos = 3

            pdos_sum = np.zeros(omegas.shape, dtype=float)
            for i in set_for_sum:
                pdos_sum += multdos * partial_dos[(i-1):i].sum(axis=0)
            plots.append( {'label': atom, 'data': [ [ round(omegas[n], 3), round(i, 3) ] for n, i in enumerate(pdos_sum.tolist()) ]} ) # round to reduce output
        return plots
