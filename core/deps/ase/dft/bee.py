import numpy as np
import os
from ase.atoms import Atoms
from ase.parallel import rank

class BEEF_Ensemble:
    """BEEF type ensemble error estimation"""
    def __init__(self, atoms=None, e=None, contribs=None, xc=None):
        if (atoms is not None or contribs is not None or xc is not None):
            if atoms is None:
                assert e is not None
                assert contribs is not None
                assert xc is not None
            else:
                if isinstance(atoms, Atoms):
                    calc = atoms.get_calculator()
                    self.atoms = atoms
                else:
                    calc = atoms
                    self.atoms = calc.atoms
                xc = calc.get_xc_functional()
            self.calc = calc
            self.e = e
            self.contribs = contribs
            self.xc = xc
            self.done = False
            if self.xc in ['BEEF-vdW', 'BEEF', 'BEEF-1', 'PBE']:
                self.beef_type = 'beefvdw'
            elif self.xc == 'mBEEF':
                self.beef_type = 'mbeef'
            else:
                raise NotImplementedError('No ensemble for xc = %s' % self.xc)

    def get_ensemble_energies(self, size=2000, seed=0):
        """Returns an array of ensemble total energies"""
        self.seed = seed
        if rank == 0:
            print '\n'
            print '%s ensemble started' % self.beef_type

        if self.contribs is None:
            self.contribs = self.calc.get_nonselfconsistent_energies(self.beef_type)
            self.e = self.calc.get_potential_energy(self.atoms)
        if self.beef_type == 'beefvdw':
            assert len(self.contribs) == 32
            coefs = self.get_beefvdw_ensemble_coefs(size, seed)
        elif self.beef_type == 'mbeef':
            assert len(self.contribs) == 64
            coefs = self.get_mbeef_ensemble_coefs(size, seed)
        self.de = np.dot(coefs, self.contribs)
        self.done = True

        if rank == 0:
            print '%s ensemble finished' % self.beef_type
            print '\n'

        return self.de

    def get_beefvdw_ensemble_coefs(self, size=2000, seed=0):
        """Pertubation coefficients of the BEEF-vdW ensemble"""
        from pars_beefvdw import uiOmega as omega
        assert np.shape(omega) == (31, 31)

        W, V, generator = self.eigendecomposition(omega, seed)
        RandV = generator.randn(31, size)

        for j in range(size):
            v = RandV[:,j]
            coefs_i = (np.dot(np.dot(V, np.diag(np.sqrt(W))), v)[:])
            if j == 0:
                ensemble_coefs = coefs_i
            else:
                ensemble_coefs = np.vstack((ensemble_coefs, coefs_i))
        PBEc_ens = -ensemble_coefs[:, 30]
        return (np.vstack((ensemble_coefs.T, PBEc_ens))).T

    def get_mbeef_ensemble_coefs(self, size=2000, seed=0):
        """Pertubation coefficients of the mBEEF ensemble"""
        from pars_mbeef import uiOmega as omega
        assert np.shape(omega) == (64, 64)

        W, V, generator = self.eigendecomposition(omega, seed)
        mu, sigma = 0.0, 1.0
        rand = np.array(generator.normal(mu, sigma, (len(W), size)))
        return (np.sqrt(2.)*np.dot(np.dot(V, np.diag(np.sqrt(W))), rand)[:]).T

    def eigendecomposition(self, omega, seed=0):
        u, s, v = np.linalg.svd(omega) # unsafe: W, V = np.linalg.eig(omega)
        generator = np.random.RandomState(seed)
        return s, v.T, generator

    def write(self, fname):
        """Write ensemble data file"""
        import cPickle as pickle
        isinstance(fname, str)
        if fname[-4:] != '.bee':
            fname += '.bee'
        assert self.done
        if rank is 0:
            if os.path.isfile(fname):
                os.rename(fname, fname + '.old')
            f = open(fname, 'w')
            obj = [self.e, self.de, self.contribs, self.seed, self.xc]
            pickle.dump(obj, f)
            f.close()

    def read(self, fname, all=False):
        import cPickle as pickle
        isinstance(fname, str)
        if fname[-4:] != '.bee':
            fname += '.bee'
        assert os.path.isfile(fname)
        f = open(fname, 'r')
        e, de, contribs, seed, xc = pickle.load(f)
        f.close()
        if all:
            return e, de, contribs, seed, xc
        else:
            return e, de
