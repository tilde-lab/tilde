import numpy as np
from ase.calculators.calculator import Calculator


class LennardJones(Calculator):
    implemented_properties = ['energy', 'forces']
    default_parameters = {'epsilon': 1.0,
                          'sigma': 1.0}
    nolabel = True

    def __init__(self, **kwargs):
        Calculator.__init__(self, **kwargs)

    def calculate(self, atoms, properties, changes):
        epsilon = self.parameters.epsilon
        sigma = self.parameters.sigma
        positions = atoms.get_positions()
        energy = 0.0
        forces = np.zeros((len(atoms), 3))
        for i1, p1 in enumerate(positions):
            for i2, p2 in enumerate(positions[:i1]):
                diff = p2 - p1
                d2 = np.dot(diff, diff)
                c6 = (sigma**2 / d2)**3
                c12 = c6**2
                energy += 4 * epsilon * (c12 - c6)
                F = 24 * epsilon * (2 * c12 - c6) / d2 * diff
                forces[i1] -= F
                forces[i2] += F
        self.results['energy'] = energy
        self.results['forces'] = forces
