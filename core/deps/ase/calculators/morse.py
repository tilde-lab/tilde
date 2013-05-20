import numpy as np

from math import exp, sqrt

from ase.calculators.lj import LennardJones


class MorsePotential(LennardJones):
    """Morse potential.

    Default values chosen to be similar as Lennard-Jones.
    """

    default_parameters = {'epsilon': 1.0,
                          'rho0': 6.0,
                          'r0': 1.0}

    def calculate(self, atoms, properties, changes):
        epsilon = self.parameters.epsilon
        rho0 = self.parameters.rho0
        r0 = self.parameters.r0
        positions = atoms.get_positions()
        energy = 0.0
        forces = np.zeros((len(atoms), 3))
        preF = 2 * epsilon * rho0 / r0
        for i1, p1 in enumerate(positions):
            for i2, p2 in enumerate(positions[:i1]):
                diff = p2 - p1
                r = sqrt(np.dot(diff, diff))
                expf = exp(rho0 * (1.0 - r / r0))
                energy += epsilon * expf * (expf - 2)
                F = preF * expf * (expf - 1) * diff / r
                forces[i1] -= F
                forces[i2] += F
        self.results['energy'] = energy
        self.results['forces'] = forces
