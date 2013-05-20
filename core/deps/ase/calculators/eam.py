"""Calculator for the Embedded Atom Method Potential"""

# eam.py
# Embedded Atom Method Potential
# These routines integrate with the ASE simulation environment
# Paul White (Oct 2012)
# UNCLASSIFIED
# License: See accompanying license files for details

import os

import numpy as np

from ase.test import NotAvailable

from ase.calculators.neighborlist import NeighborList
from ase.calculators.general import Calculator

from scipy.interpolate import InterpolatedUnivariateSpline as spline


class EAM(Calculator):
    r"""

    EAM Interface Documentation

Introduction
============

The Embedded Atom Method (EAM) [1]_ is a classical potential which is
good for modelling metals, particularly fcc materials. Because it is
an equiaxial potential the EAM does not model directional bonds
well. However, the Angular Dependent Potential (ADP) [2]_ which is an
extended version of EAM is able to model directional bonds and is also
included in the EAM calculator.

A single element EAM potential is defined by three functions: the
embedded energy, electron density and the pair potential.  A two
element alloy contains the individual three functions for each element
plus cross pair interactions.  The ADP potential has two additional
sets of data to define the dipole and quadrupole directional terms for
each alloy and their cross interactions.

The total energy `E_{\rm tot}` of an arbitrary arrangement of atoms is
given by the EAM potential as

.. math::
   E_{\rm tot} = \sum_i F(\bar\rho_i) + \frac{1}{2}\sum_{i\ne j} \phi(r_{ij})

and

.. math:: 
   \bar\rho_i = \sum_j \rho(r_{ij})

where `F` is an embedding function, namely the energy to embed an atom `i` in
the combined electron density `\bar\rho_i` which is contributed from
each of its neighbouring atoms `j` by an amount `\rho(r_{ij})`,
`\phi(r_{ij})` is the pair potential function representing the energy
in bond `ij` which is due to the short-range electro-static
interaction between atoms, and `r_{ij}` is the distance between an
atom and its neighbour for that bond.

The ADP potential is defined as

.. math:: 
   E_{\rm tot} = \sum_i F(\bar\rho_i) + \frac{1}{2}\sum_{i\ne j} \phi(r_{ij})
   + {1\over 2} \sum_{i,\alpha} (\mu_i^\alpha)^2
   + {1\over 2} \sum_{i,\alpha,\beta} (\lambda_i^{\alpha\beta})^2
   - {1 \over 6} \sum_i \nu_i^2

where `\mu_i^\alpha` is the dipole vector, `\lambda_i^{\alpha\beta}`
is the quadrupole tensor and `\nu_i` is the trace of
`\lambda_i^{\alpha\beta}`.

The files containing the potentials for this calculator are not
included but many suitable potentials can be downloaded from The
Interatomic Potentials Repository Project at
http://www.ctcms.nist.gov/potentials/

Running the Calculator
======================

EAM calculates the cohesive atom energy and forces. Internally the
potential functions are defined by splines which may be directly
supplied or created by reading the spline points from a data file from
which a slpline function is created.  The LAMMPS compatible ``.alloy``
and ``.adp`` formats are supported. The LAMMPS ``.eam`` format is
slightly different from the ``.alloy`` format and is currently not
supported.

For example::

    from eam import EAM

    mishin = EAM('Al99.eam.alloy')
    mishin.write_file('new.eam.alloy')
    mishin.plot()

    slab.set_calculator(mishin)
    slab.get_potential_energy()
    slab.get_forces()


Arguments
=========

=========================  ====================================================
Keyword                    Description
=========================  ====================================================
``fileobj``                file of potential in ``.alloy`` or ``.adp`` format
                           (This is generally all you need to supply)

``elements[N]``            array of N element abreviations

``embedded_energy[N]``     arrays of embedded energy functions

``electron_density[N]``    arrays of electron density functions

``phi[N,N]``               arrays of pair potential functions

``d_embedded_energy[N]``   arrays of derivative embedded energy functions

``d_electron_density[N]``  arrays of derivative electron density functions

``d_phi[N,N]``             arrays of derivative pair potentials functions

``d[N], q[N,N]``           ADP dipole and quadrupole function

``d_d[N,N], d_q[N,N]``     ADP dipole and quadrupole derivative functions

``skin``                   skin distance passed to NeighborList(). If no atom 
                           has moved more than the skin-distance since the last
                           call to the ``update()`` method then the neighbor 
                           list can be reused. Defaults to 1.0. 

``form``                   the form of the potential ``alloy`` or ``adp``. This
                           will be determined from the file suffix or must be 
                           set if using equations

=========================  ====================================================


Additional parameters for writing potential files
=================================================

The following parameters are only required for writing a potential in
``.alloy`` or ``.adp`` format file.

=========================  ====================================================
Keyword                    Description
=========================  ====================================================
``header``                 Three line text header. Default is standard message.

``Z[N]``                   Array of atomic number of each element

``mass[N]``                Atomic mass of each element

``a[N]``                   Array of lattice parameters for each element

``lattice[N]``             Lattice type

``nrho``                   No. of rho samples along embedded energy curve

``drho``                   Increment for sampling density

``nr``                     No. of radial points along density and pair 
                           potential curves

``dr``                     Increment for sampling radius

=========================  ====================================================

Special features
================

``.plot()``
  Plots the individual functions. This may be called from multiple EAM
  potentials to compare the shape of the individual curves. This
  function requires the installation of the Matplotlib libraries.

Notes/Issues
=============

* Although currently not fast, this calculator can be good for trying
  small calculations or for creating new potentials by matching baseline
  data such as from DFT results. The format for these potentials is
  compatable with LAMMPS_ and so can be used either directly by LAMMPS or
  with the ASE LAMMPS calculator interface.

* Supported formats are the LAMMPS_ ``.alloy`` and ``.adp``. The
  ``.eam`` format is currently not supported. The form of the
  potential will be determined from the file suffix.

* Any supplied values will overide values read from the file.

* The derivative functions, if supplied, are only used to calculate
  forces.


.. _LAMMPS: http://lammps.sandia.gov/

.. [1] M.S. Daw and M.I. Baskes, Phys. Rev. Letters 50 (1983)
       1285.

.. [2] Y. Mishin, M.J. Mehl, and D.A. Papaconstantopoulos,
       Acta Materialia 53 2005 4029--4041.


End EAM Interface Documentation
    """

    def __init__(self, fileobj=None, **kwargs):

        if fileobj != None:
            self.read_file(fileobj)

        valid_args = ('elements', 'header', 'drho', 'dr', 'cutoff',
                      'atomic_number', 'mass', 'a', 'lattice',
                      'embedded_energy', 'electron_density', 'phi',
                      # adp terms
                      'd', 'q', 'd_d', 'd_q',
                      # derivatives
                      'd_embedded_energy', 'd_electron_density', 'd_phi',
                      'skin', 'form', 'Z', 'nr', 'nrho', 'mass')

        # these variables need to be set, but are not read in
        if 'skin' not in kwargs:
            self.skin = 1.0

        # set any additional keyword arguments
        for arg, val in kwargs.iteritems():
            if arg in valid_args:
                setattr(self, arg, val)
            else:
                raise RuntimeError('unknown keyword arg "%s" : not in %s'
                                   % (arg, valid_args))

        # initialise the state of the calculation
        self.Nelements = len(self.elements)
        self.energy = 0.0
        self.positions = None
        self.cell = None
        self.pbc = None
        
    def set_form(self, fileobj):
        """set the form variable based on the file name suffix"""
        extension = os.path.splitext(fileobj)[1]

        if extension == '.eam':
            self.form = 'eam'
            raise NotImplementedError
        
        elif extension == '.alloy':
            self.form = 'alloy'
                
        elif extension == '.adp':
            self.form = 'adp'

        else:
            raise RuntimeError('unknown file extension type: %s' % extension)

    def read_file(self, fileobj):
        """Reads a LAMMPS EAM file in alloy format
        and creates the interpolation functions from the data
        """

        if isinstance(fileobj, str):
            f = open(fileobj)
            self.set_form(fileobj)
        else:
            f = fileobj
         
        lines = f.readlines()
        self.header = lines[:3]
        i = 3

        # make the data one long line so as not to care how its formatted
        data = []
        for line in lines[i:]:
            data.extend(line.split())
            
        self.Nelements = int(data[0])
        d = 1
        self.elements = data[d:(d + self.Nelements)]
        d += self.Nelements

        self.nrho = int(data[d])
        self.drho = float(data[d + 1])
        self.nr = int(data[d + 2])
        self.dr = float(data[d + 3])
        self.cutoff = float(data[d + 4])
        
        self.embedded_data = np.zeros([self.Nelements, self.nrho])
        self.density_data = np.zeros([self.Nelements, self.nr])
        self.Z = np.zeros([self.Nelements], dtype=int)
        self.mass = np.zeros([self.Nelements])
        self.a = np.zeros([self.Nelements])
        self.lattice = []
        d += 5

        # reads in the part of the eam file for each element
        for elem in range(self.Nelements):
            self.Z[elem] = int(data[d])
            self.mass[elem] = float(data[d + 1])
            self.a[elem] = float(data[d + 2])
            self.lattice.append(data[d + 3])
            d += 4
            
            self.embedded_data[elem] = np.float_(data[d:(d + self.nrho)])
            d += self.nrho
            self.density_data[elem] = np.float_(data[d:(d + self.nr)])
            d += self.nr

        # reads in the r*phi data for each interaction between elements
        self.rphi_data = np.zeros([self.Nelements, self.Nelements, self.nr])

        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                self.rphi_data[i, j] = np.float_(data[d:(d + self.nr)])
                d += self.nr

        self.r = np.arange(0, self.nr) * self.dr
        self.rho = np.arange(0, self.nrho) * self.drho

        # this section turns the file data into three functions (and
        # derivative functions) that define the potential
        self.embedded_energy = np.zeros(self.Nelements, object)
        self.electron_density = np.zeros(self.Nelements, object)
        self.d_embedded_energy = np.zeros(self.Nelements, object)
        self.d_electron_density = np.zeros(self.Nelements, object)

        for i in range(self.Nelements):
            self.embedded_energy[i] = spline(self.rho,
                                             self.embedded_data[i], k=3)
            self.electron_density[i] = spline(self.r,
                                              self.density_data[i], k=3)
            self.d_embedded_energy[i] = self.deriv(self.embedded_energy[i])
            self.d_electron_density[i] = self.deriv(self.electron_density[i])

        self.phi = np.zeros([self.Nelements, self.Nelements], object)
        self.d_phi = np.zeros([self.Nelements, self.Nelements], object)

        # ignore the first point of the phi data because it is forced
        # to go through zero due to the r*phi format in alloy and adp
        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                if self.form == 'eam':  # not stored as rphi
                    # should we igore the first point for eam ?
                    raise RuntimeError('.eam format not yet supported')

                    self.phi[i, j] = spline(
                        self.r[1:], self.rphi_data[i, j][1:], k=3)
                else:
                    self.phi[i, j] = spline(
                        self.r[1:],
                        self.rphi_data[i, j][1:] / self.r[1:], k=3)

                self.d_phi[i, j] = self.deriv(self.phi[i, j])

                if j != i:
                    self.phi[j, i] = self.phi[i, j]
                    self.d_phi[j, i] = self.d_phi[i, j]

        if (self.form == 'adp'):
            self.read_adp_data(data, d)

    def read_adp_data(self, data, d):
        """reads in the extra data fro the adp format"""

        self.d_data = np.zeros([self.Nelements, self.Nelements, self.nr])
        # should be non symetrical combinations of 2
        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                self.d_data[i, j] = data[d:d + self.nr]
                d += self.nr
                
        self.q_data = np.zeros([self.Nelements, self.Nelements, self.nr])
        # should be non symetrical combinations of 2
        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                self.q_data[i, j] = data[d:d + self.nr]
                d += self.nr
    
        self.d = np.zeros([self.Nelements, self.Nelements], object)
        self.d_d = np.zeros([self.Nelements, self.Nelements], object)
        self.q = np.zeros([self.Nelements, self.Nelements], object)
        self.d_q = np.zeros([self.Nelements, self.Nelements], object)
    
        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                self.d[i, j] = spline(self.r[1:], self.d_data[i, j][1:], k=3)
                self.d_d[i, j] = self.deriv(self.d[i, j])
                self.q[i, j] = spline(self.r[1:], self.q_data[i, j][1:], k=3)
                self.d_q[i, j] = self.deriv(self.q[i, j])

                # make symmetrical
                if j != i:
                    self.d[j, i] = self.d[i, j]
                    self.d_d[j, i] = self.d_d[i, j]
                    self.q[j, i] = self.q[i, j]
                    self.d_q[j, i] = self.d_q[i, j]

    def write_file(self, filename, nc=1, form='%.8e'):
        """Writes out the model of the eam_alloy in lammps alloy
        format to file with name = 'filename' with a data format that
        is nc columns wide.  Note: array lengths need to be an exact
        multiple of nc
"""

        f = open(filename, 'w')

        assert self.nr % nc == 0
        assert self.nrho % nc == 0

        if not hasattr(self, 'header'):
            self.header = """Unknown EAM potential file
Generated from eam.py
blank
"""
        for line in self.header:
            f.write(line)

        f.write('%d ' % self.Nelements)
        for i in range(self.Nelements):
            f.write('%s ' % str(self.elements[i]))
        f.write('\n')

        f.write('%d %f %d %f %f \n' %
                (self.nrho, self.drho, self.nr, self.dr, self.cutoff))
    
        # start of each section for each element
#        rs = np.linspace(0, self.nr * self.dr, self.nr)
#        rhos = np.linspace(0, self.nrho * self.drho, self.nrho)

        rs = np.arange(0, self.nr) * self.dr
        rhos = np.arange(0, self.nrho) * self.drho

        for i in range(self.Nelements):
            f.write('%d %f %f %s\n' % (self.Z[i], self.mass[i],
                                       self.a[i], str(self.lattice[i])))
            np.savetxt(f,
                       self.embedded_energy[i](rhos).reshape(self.nrho / nc,
                                                             nc),
                       fmt=nc * [form])
            np.savetxt(f,
                       self.electron_density[i](rs).reshape(self.nr / nc,
                                                            nc),
                       fmt=nc * [form])

        # write out the pair potentials in Lammps DYNAMO setfl format
        # as r*phi for alloy format
        for i in range(self.Nelements):
            for j in range(i, self.Nelements):
                np.savetxt(f,
                           (rs * self.phi[i, j](rs)).reshape(self.nr / nc,
                                                             nc),
                           fmt=nc * [form])

        if self.form == 'adp':
            # these are the u(r) values
            for i in range(self.Nelements):
                for j in range(i + 1):
                    np.savetxt(f, self.d_data[i, j])
            
            # these are the w(r) values
            for i in range(self.Nelements):
                for j in range(i + 1):
                    np.savetxt(f, self.q_data[i, j])
                
        f.close()

    def update(self, atoms):
        # check all the elements are available in the potential
        elements = np.unique(atoms.get_chemical_symbols())
        unavailable = np.logical_not(
            np.array([item in self.elements for item in elements]))
        if np.any(unavailable):
            raise RuntimeError('These elements are not in the potential: %s' %
                               elements[unavailable])
                    
        # check if anything has changed to require re-calculation
        if (self.positions is None or
            len(self.positions) != len(atoms.get_positions()) or
            (self.positions != atoms.get_positions()).any() or
            (self.cell != atoms.get_cell()).any() or
            (self.pbc != atoms.get_pbc()).any()):

            # cutoffs need to be a vector for NeighborList
            cutoffs = self.cutoff * np.ones(len(atoms))

            # convert the elements to an index of the position
            # in the eam format
            self.index = np.array([atoms.calc.elements.index(el)
                                   for el in atoms.get_chemical_symbols()])
            self.pbc = atoms.get_pbc()

            # since we need the contribution of all neighbors to the
            # local electron density we cannot just calculate and use
            # one way neighbors
            self.neighbors = NeighborList(cutoffs, skin=self.skin,
                                          self_interaction=False,
                                          bothways=True)
            self.neighbors.update(atoms)
            self.calculate(atoms)
            
    def get_forces(self, atoms):
        # calculate the forces based on derivatives of the three EAM functions
        self.update(atoms)
        self.forces = np.zeros((len(atoms), 3))

        for i in range(len(atoms)):  # this is the atom to be embedded
            neighbors, offsets = self.neighbors.get_neighbors(i)
            offset = np.dot(offsets, atoms.get_cell())
            # create a vector of relative positions of neighbors
            rvec = atoms.positions[neighbors] + offset - atoms.positions[i]
            r = np.sqrt(np.sum(np.square(rvec), axis=1))
            nearest = np.arange(len(r))[r < self.cutoff]

            d_embedded_energy_i = self.d_embedded_energy[
                self.index[i]](self.total_density[i])
            urvec = rvec.copy()  # unit directional vector

            for j in np.arange(len(neighbors)):
                urvec[j] = urvec[j] / r[j]
    
            for j_index in range(self.Nelements):
                use = self.index[neighbors[nearest]] == j_index
                if not use.any():
                    continue
                rnuse = r[nearest][use]
                density_j = self.total_density[neighbors[nearest][use]]
                scale = (self.d_phi[self.index[i], j_index](rnuse) +
                         (d_embedded_energy_i *
                          self.d_electron_density[j_index](rnuse)) +
                         (self.d_embedded_energy[j_index](density_j) *
                          self.d_electron_density[self.index[i]](rnuse)))
            
                self.forces[i] += np.dot(scale, urvec[nearest][use])
                
                if (self.form == 'adp'):
                    adp_forces = self.angular_forces(
                        self.mu[i],
                        self.mu[neighbors[nearest][use]],
                        self.lam[i],
                        self.lam[neighbors[nearest][use]],
                        rnuse,
                        rvec[nearest][use],
                        self.index[i],
                        j_index)

                    self.forces[i] += adp_forces
                    
        return self.forces.copy()
            
    def get_stress(self, atoms):
        ## currently not implemented
        raise NotImplementedError
    
    def calculate(self, atoms):
        # calculate the energy
        # the energy is made up of the ionic or pair interaction and
        # the embedding energy of each atom into the electron cloud
        # generated by its neighbors

        energy = 0.0
        adp_energy = 0.0
        self.total_density = np.zeros(len(atoms))
        if (self.form == 'adp'):
            self.mu = np.zeros([len(atoms), 3])
            self.lam = np.zeros([len(atoms), 3, 3])

        for i in range(len(atoms)):  # this is the atom to be embedded
            neighbors, offsets = self.neighbors.get_neighbors(i)
            offset = np.dot(offsets, atoms.get_cell())
            
            rvec = (atoms.positions[neighbors] + offset -
                    atoms.positions[i])

            ## calculate the distance to the nearest neighbors
            r = np.sqrt(np.sum(np.square(rvec), axis=1))  # fast
#            r = np.apply_along_axis(np.linalg.norm, 1, rvec)  # sloow

            nearest = np.arange(len(r))[r <= self.cutoff]
            for j_index in range(self.Nelements):
                use = self.index[neighbors[nearest]] == j_index
                if not use.any():
                    continue
                pair_energy = np.sum(self.phi[self.index[i], j_index](
                        r[nearest][use])) / 2.
                energy += pair_energy

                density = np.sum(
                    self.electron_density[j_index](r[nearest][use]))
                self.total_density[i] += density

                if self.form == 'adp':
                    self.mu[i] += self.eam_dipole(
                        r[nearest][use],
                        rvec[nearest][use],
                        self.d[self.index[i], j_index])
                    
                    self.lam[i] += self.eam_quadrupole(
                        r[nearest][use],
                        rvec[nearest][use],
                        self.q[self.index[i], j_index])

            # add in the electron embedding energy
            embedding_energy = self.embedded_energy[self.index[i]](
                self.total_density[i])
#            print 'pair energy',energy
#            print 'embed energy',embedding_energy
            
            energy += embedding_energy

        if self.form == 'adp':
            mu_energy = np.sum(self.mu**2) / 2.
            adp_energy += mu_energy
#            print 'adp mu', mu_energy
            lam_energy = np.sum(self.lam**2) / 2.
            adp_energy += lam_energy
#            print 'adp lam', lam_energy

            for i in range(len(atoms)):  # this is the atom to be embedded
                adp_energy -= np.sum(self.lam[i].trace()**2) / 6.

#            print 'energy no adp', energy
            energy += adp_energy

        self.positions = atoms.positions.copy()
        self.cell = atoms.get_cell().copy()
        
        self.energy_free = energy
        self.energy_zero = energy

    def plot(self, name=''):
        """Plot the individual curves"""

        try:
            import matplotlib.pyplot as plt
        
        except ImportError:
            raise NotAvailable('This needs matplotlib module.')

        if self.form == 'eam' or self.form == 'alloy':
            nrow = 2
        elif self.form == 'adp':
            nrow = 3
        else:
            raise RuntimeError('Unknown form of potential: %s' % self.form)

        if hasattr(self, 'r'):
            r = self.r
        else:
            r = np.linspace(0, self.cutoff, 50)

        if hasattr(self, 'rho'):
            rho = self.rho
        else:
            rho = np.linspace(0, 10.0, 50)
        
        plt.subplot(nrow, 2, 1)
        self.elem_subplot(rho, self.embedded_energy,
                          r'$\rho$', r'Embedding Energy $F(\bar\rho)$',
                          name, plt)
        
        plt.subplot(nrow, 2, 2)
        self.elem_subplot(r, self.electron_density,
                          r'$r$', r'Electron Density $\rho(r)$', name, plt)

        plt.subplot(nrow, 2, 3)
        self.multielem_subplot(r, self.phi,
                               r'$r$', r'Pair Potential $\phi(r)$', name, plt)
        plt.ylim(-1.0, 1.0)  # need reasonable values

        if self.form == 'adp':
            plt.subplot(nrow, 2, 5)
            self.multielem_subplot(r, self.d,
                                   r'$r$', r'Dipole Energy', name, plt)
            
            plt.subplot(nrow, 2, 6)
            self.multielem_subplot(r, self.q,
                                   r'$r$', r'Quadrupole Energy', name, plt)

        plt.plot()

    def elem_subplot(self, curvex, curvey, xlabel, ylabel, name, plt):
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        for i in np.arange(self.Nelements):
            label = name + ' ' + self.elements[i]
            plt.plot(curvex, curvey[i](curvex), label=label)
        plt.legend()

    def multielem_subplot(self, curvex, curvey, xlabel, ylabel, name, plt):
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        for i in np.arange(self.Nelements):
            for j in np.arange(i + 1):
                label = name + ' ' + self.elements[i] + '-' + self.elements[j]
                plt.plot(curvex, curvey[i, j](curvex), label=label)
        plt.legend()

    def angular_forces(self, mu_i, mu, lam_i, lam, r, rvec, form1, form2):
        # calculate the extra components for the adp forces
        # rvec are the relative positions to atom i
        psi = np.zeros(mu.shape)
        for gamma in range(3):
            term1 = (mu_i[gamma] - mu[:, gamma]) * self.d[form1][form2](r)

            term2 = np.sum((mu_i - mu) * self.d_d[form1][form2](r)[:, np.newaxis]
                           * (rvec * rvec[:, gamma][:, np.newaxis]
                              / r[:, np.newaxis]), axis=1)
            
            term3 = 2 * np.sum((lam_i[:, gamma] + lam[:, :, gamma])
                               * rvec * self.q[form1][form2](r)[:, np.newaxis],
                               axis=1)
            term4 = 0.0
            for alpha in range(3):
                for beta in range(3):
                    rs = rvec[:, alpha] * rvec[:, beta] * rvec[:, gamma]
                    term4 += ((lam_i[alpha, beta] + lam[:, alpha, beta]) *
                              self.d_q[form1][form2](r) * rs) / r
                    
            term5 = ((lam_i.trace() + lam.trace(axis1=1, axis2=2)) *
                     (self.d_q[form1][form2](r) * r
                      + 2 * self.q[form1][form2](r)) * rvec[:, gamma]) / 3.

            # the minus for term5 is a correction on the adp
            # formulation given in the 2005 Mishin Paper and is posted
            # on the NIST website with the AlH potential
            psi[:, gamma] = term1 + term2 + term3 + term4 - term5

        return np.sum(psi, axis=0)

    def eam_dipole(self, r, rvec, d):
        # calculate the dipole contribution
        mu = np.sum((rvec * d(r)[:, np.newaxis]), axis=0)

        return mu  # sign to agree with lammps

    def eam_quadrupole(self, r, rvec, q):
        # slow way of calculating the quadrupole contribution
        r = np.sqrt(np.sum(rvec**2, axis=1))
    
        lam = np.zeros([rvec.shape[0], 3, 3])
        qr = q(r)
        for alpha in range(3):
            for beta in range(3):
                lam[:, alpha, beta] += qr * rvec[:, alpha] * rvec[:, beta]
            
        return np.sum(lam, axis=0)

    def deriv(self, spline):
        """Wrapper for extracting the derivative from a spline"""
        def d_spline(aspline):
            return spline(aspline, 1)

        return d_spline

#print 'done'
