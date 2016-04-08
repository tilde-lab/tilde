# Copyright (C) 2011 Atsushi Togo
#
# This file is part of phonopy.
#
# Phonopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Phonopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with phonopy.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np

from core.constants import Constants # patched by eb

class ThermalPropertiesBase:
    def __init__(self, eigenvalues, weights=None):
        self.temperature = 0
        self.eigenvalues = eigenvalues
        if weights is not None:
            self.weights = weights
        else:
            self.weights = np.ones(eigenvalues.shape[0], dtype=int)
        self.nqpoint = eigenvalues.shape[0]

    def set_temperature(self, temperature):
        self.temperature = temperature

    def get_free_energy(self):

        def func(temp, omega):
            return Constants.Kb * temp * np.log(1.0 - np.exp((- omega) / (Constants.Kb * temp)))

        free_energy = self.get_thermal_property(func)
        return free_energy / np.sum(self.weights) * Constants.EvTokJmol + self.zero_point_energy

    def get_free_energy2(self):

        if self.temperature > 0:
            def func(temp, omega):
                return  Constants.Kb * temp * np.log(2.0 * np.sinh(omega / (2 * Constants.Kb * temp)))

            free_energy = self.get_thermal_property(func)
            return free_energy / np.sum(self.weights) * Constants.EvTokJmol
        else:
            return self.zero_point_energy

    def get_heat_capacity_v(self):

        def func(temp, omega):
            expVal = np.exp(omega / (Constants.Kb * temp))
            return Constants.Kb * (omega / (Constants.Kb * temp)) ** 2 * expVal / (expVal - 1.0) ** 2

        cv = self.get_thermal_property(func)
        return cv / np.sum(self.weights) * Constants.EvTokJmol

    def get_entropy(self):
        
        def func(temp, omega):
            val = omega / (2 * Constants.Kb * temp)
            return 1. / (2 * temp) * omega * np.cosh(val) / np.sinh(val) - Constants.Kb * np.log(2 * np.sinh(val))

        entropy = self.get_thermal_property(func)
        return entropy / np.sum(self.weights) * Constants.EvTokJmol

    def get_entropy2(self):

        def func(temp, omega):
            val = omega / (Constants.Kb * temp)
            return -Constants.Kb * np.log(1 - np.exp( -val )) + 1.0 / temp * omega / (np.exp( val ) - 1)

        entropy = self.get_thermal_property(func)
        return entropy / np.sum(self.weights) * Constants.EvTokJmol


class ThermalProperties(ThermalPropertiesBase):
    def __init__(self, eigenvalues, weights=None, factor=Constants.VaspToTHz, cutoff_eigenvalue=None):
        ThermalPropertiesBase.__init__(self, eigenvalues, weights)
        self.factor = factor
        if cutoff_eigenvalue:
            self.cutoff_eigenvalue = cutoff_eigenvalue
        else:
            self.cutoff_eigenvalue = 0.0
        self.__frequencies()
        self.__zero_point_energy()
        self.__high_T_entropy()
        
    def __frequencies(self):
        frequencies = []
        for eigs in self.eigenvalues:
            frequencies.append(
                np.sqrt( np.extract( eigs>self.cutoff_eigenvalue, eigs)
                         ) * self.factor * Constants.THzToEv )
        self.frequencies = frequencies

    def __zero_point_energy(self):
        z_energy = 0.
        for i, freqs in enumerate(self.frequencies):
            z_energy += np.sum(1.0 / 2 * freqs) * self.weights[i]
        self.zero_point_energy = z_energy / np.sum(self.weights) * Constants.EvTokJmol

    def get_zero_point_energy(self):
        return self.zero_point_energy

    def __high_T_entropy(self):
        entropy = 0.0
        for i, freqs in enumerate(self.frequencies):
            entropy -= np.sum(np.log(freqs)) * self.weights[i]
        self.high_T_entropy = entropy * Constants.Kb / np.sum(self.weights) * Constants.EvTokJmol

    def get_high_T_entropy(self):
        return self.high_T_entropy

    def get_thermal_property(self, func):
        property = 0.0

        if self.temperature > 0:
            temp = self.temperature
            for i, freqs in enumerate(self.frequencies):
                property += np.sum(func(temp, freqs)) * self.weights[i]

        return property

    def get_c_thermal_properties(self):
        import phonopy._phonopy as phonoc

        if self.temperature > 0:
            return phonoc.thermal_properties( self.temperature,
                                              self.eigenvalues,
                                              self.weights,
                                              self.factor * Constants.THzToEv,
                                              self.cutoff_eigenvalue )
        else:
            return (0.0, 0.0, 0.0)

    def plot_thermal_properties(self):
        import matplotlib.pyplot as plt
        
        temps, fe, entropy, cv = self.thermal_properties

        plt.plot(temps, fe, 'r-')
        plt.plot(temps, entropy, 'b-')
        plt.plot(temps, cv, 'g-')
        plt.legend(('Free energy [kJ/mol]', 'Entropy [J/K/mol]',
                    r'C$_\mathrm{V}$ [J/K/mol]'),
                   'best', shadow=True)
        plt.grid(True)
        plt.xlabel('Temperature [K]')

        return plt

    def set_thermal_properties(self, t_step=10, t_max=1000, t_min=0):
        t = t_min
        temps = []
        fe = []
        entropy = []
        cv = []
        energy = []
        while t < t_max + t_step / 2.0:
            self.set_temperature(t)
            temps.append(t)

            # try:
                # import phonopy._phonopy as phonoc
                # C implementation, but not so faster than Numpy
                # props = self.get_c_thermal_properties()
                # fe.append(props[0] * Constants.EvTokJmol + self.zero_point_energy)
                # entropy.append(props[1] * Constants.EvTokJmol * 1000)
                # cv.append(props[2] * Constants.EvTokJmol * 1000)
            # except ImportError:
                # Numpy implementation, but not so bad
                
            fe.append(self.get_free_energy())
            entropy.append(self.get_entropy()*1000)
            cv.append(self.get_heat_capacity_v()*1000)

            t += t_step

        thermal_properties = [temps, fe, entropy, cv]
        self.thermal_properties = np.array(thermal_properties)

    def get_thermal_properties( self ):
        return self.thermal_properties

    def write_yaml(self):
        file = open('thermal_properties.yaml', 'w')
        file.write("# Thermal properties / unit cell (natom)\n")
        file.write("\n")
        file.write("unit:\n")
        file.write("  temperature:   K\n")
        file.write("  free_energy:   kJ/mol\n")
        file.write("  entropy:       J/K/mol\n")
        file.write("  heat_capacity: J/K/mol\n")
        file.write("\n")
        file.write("natom: %5d\n" % ((self.eigenvalues[0].shape)[0]/3))
        file.write("zero_point_energy: %15.7f\n" % self.zero_point_energy)
        file.write("high_T_entropy:    %15.7f\n" % (self.high_T_entropy * 1000))
        file.write("\n")
        file.write("thermal_properties:\n")
        temperatures, fe, entropy, cv = self.thermal_properties
        for i, t in enumerate(temperatures):
            file.write("- temperature:   %15.7f\n" % t)
            file.write("  free_energy:   %15.7f\n" % fe[i])
            file.write("  entropy:       %15.7f\n" % entropy[i])
            # Sometimes 'nan' of C_V is returned at low temperature.
            if np.isnan( cv[i] ):
                file.write("  heat_capacity: %15.7f\n" % 0 )
            else:
                file.write("  heat_capacity: %15.7f\n" % cv[i])
            file.write("  energy:        %15.7f\n" % (fe[i]+entropy[i]*t/1000))
            file.write("\n")
        

class PartialThermalProperties(ThermalProperties):
    def __init__(self, eigenvalues, eigenvectors, weights=None, factor=Constants.VaspToTHz):
        ThermalPropertiesBase.__init__(self, eigenvalues, weights=weights)
        # eigenvalues[q-point][mode] = eigenvalue
        # eigenvectors2[q-point][natom*3][mode] = 
        #           amplitude of each atom and corrdinates
        # Be careful of this dimension order
        self.factor = factor
        self.eigenvectors2 = (np.abs(eigenvectors))**2
        
    def set_indices(self, set_of_indices):
        if set_of_indices == None:
            set_of_indices = []
            for i in range(self.eigenvalues.shape[1]/3):
                set_of_indices.append([i+1])
        self.set_of_indices = set_of_indices
        self.__zero_point_energy()
        self.write_yaml()

    def __zero_point_energy(self):
        zero_point_energy = np.zeros(len(self.set_of_indices), dtype=float)
        for i, indices in enumerate(self.set_of_indices):
            z_energy = 0.
            for j, eigenvals in enumerate(self.eigenvalues): # q-point
                for k, eig in enumerate(eigenvals): # mode
                    if eig < 0:
                        continue
                    for index in indices:
                        z_energy += 1.0 / 2 * np.sqrt(eig) * \
                            self.eigenvectors2[j,(index-1)*3:index*3,k].sum() * \
                            self.weights[j]

            zero_point_energy[i] = \
                z_energy / np.sum(self.weights) * self.factor * Constants.THzToEv * Constants.EvTokJmol

        self.zero_point_energy = zero_point_energy

    def get_zero_point_energy(self):
        return self.zero_point_energy

    def write_yaml(self, mode='a'):
        file = open('thermal_properties.yaml', mode)
        file.write("partial_thermal_properties:\n")
        for i, indices in enumerate(self.set_of_indices):
            file.write(("- atoms: [" + "%4d," * (len(indices)-1) + "%4d ]\n") % tuple(indices))
            file.write("  zero_point_energy: %15.7f\n" % self.zero_point_energy[i])
        

