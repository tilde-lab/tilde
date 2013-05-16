#!/usr/bin/env python
# tilda project: GAUSSIAN log parser
# based on cclib (author Noel O'Boyle, http://dx.doi.org/10.1002/jcc.20823)
# TODO: this code needs to be rewritten in accordance to other tilde parsers
# v050113

import os
import sys
import re
import math
from parsers import Output

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/../core/deps'))
from ase.data import chemical_symbols
from ase.lattice.spacegroup.cell import cell_to_cellpar
from numpy import array
from numpy import matrix
from numpy import ndarray
from numpy import zeros
from numpy import dot
from numpy import cross

Hartree = 27.211398

class GAUSSIAN(Output):
    # this is an interface to cclib Gaussian parser
    def __init__(self, file, **kwargs):
        Output.__init__(self)
        self.prog = 'GAUSSIAN'
        self.data = open(file).read().replace('\r\n', '\n').replace('\r', '\n')

        parts = self.data.split('\n Cite this work as:')
        if len(parts) > 2:
            self.warning('File contains several merged outputs - only the last one is taken!')

        self.location = file
        
        if '\n Normal termination ' in parts[-1]: self.finished = 1
        else: self.finished = -1
        
        logfile = GaussianParser(parts[-1])
        parsed = logfile.parse()

        self.warns.extend(list(set(parsed.warns)))

        if not hasattr(parsed, 'atomcoords'): raise RuntimeError('Valid geometry not found!')
        atoms, cell = [], []
        coords = parsed.atomcoords.tolist()[-1]

        for n, i in enumerate(parsed.atomnos):
            if i == -2: cell.append( [ coords[n][0], coords[n][1], coords[n][2] ] ) # PBC
            elif i == -1: atoms.append( [ 'Xx', coords[n][0], coords[n][1], coords[n][2] ] ) # X-atom
            else: atoms.append( [ chemical_symbols[i], coords[n][0], coords[n][1], coords[n][2] ] )
        periodicity = len(cell)

        # construct missing vectors and fractionize atomic coords
        if periodicity == 0:
            cell = [ [self.periodic_limit, 0, 0],  [0, self.periodic_limit, 0],  [0, 0, self.periodic_limit] ]
        elif periodicity == 1:
            cell.append( cross(cell[0], [ 1, 1, 1 ]) )
            cell[1] = cell[1] * self.periodic_limit / math.sqrt( cell[1][0]**2+cell[1][1]**2+cell[1][2]**2 )
            cell.append( cross(cell[0], cell[1]) )
            cell[2] = cell[2] * self.periodic_limit / math.sqrt( cell[2][0]**2+cell[2][1]**2+cell[2][2]**2 )
        elif periodicity == 2:
            cell.append( cross(cell[0], cell[1]) )
            cell[2] = cell[2] * self.periodic_limit / math.sqrt( cell[2][0]**2+cell[2][1]**2+cell[2][2]**2 )

        cell = map(lambda x: round(x, 4), cell_to_cellpar(array( cell )).tolist())
        self.structures = [{'cell': cell, 'atoms': atoms, 'periodicity': periodicity}]

        # Get basis set
        self.bs = { 'bs': {}, 'ps': {} }

        #if hasattr(parsed, 'coreelectrons'):
        #    if sum( parsed.coreelectrons.tolist() ):
        #        self.bs['ps'] = parsed.coreelectrons.tolist()
        
        if hasattr(parsed, 'gbasis'):
            for n, i in enumerate(parsed.gbasis):
                if not self.structures[-1]['atoms'][n][0] in self.bs['bs'].keys():
                    self.bs['bs'][ self.structures[-1]['atoms'][n][0] ] = i
                else:
                    if self.bs['bs'][ self.structures[-1]['atoms'][n][0] ] != i:
                        try: self.bs['bs'][ self.structures[-1]['atoms'][n][0] + '1' ]
                        except KeyError: self.bs['bs'][ self.structures[-1]['atoms'][n][0] + '1' ] = i
                        else: raise RuntimeError('More than two different basis sets for one element - not supported case!')
        else:
            if ' Standard basis:' in self.data:
                diff_atoms = []
                for i in self.structures[-1]['atoms']:
                    if not i[0] in diff_atoms:
                        diff_atoms.append(i[0])
                        self.bs['bs'][i[0]] = self.data.split(' Standard basis:', 1)[-1].split("\n", 1)[0].strip()
            elif ' General basis read from cards:' in self.data:
                sections = self.data.split(' General basis read from cards:', 1)[-1].split(" ****\n")
                bstype, sections[0] = sections[0].split("\n", 1)
                for s in sections:
                    if not s.startswith(" Centers:"): break
                    for line in s.splitlines():

                        if " Centers:" in line:
                            bs_concurrency = False
                            atomn = int( line.replace("Centers:", "").split()[0] ) - 1
                            try: self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] ]
                            except KeyError: self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] ] = []
                            else:
                                bs_concurrency = True
                                try: self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] + '1' ]
                                except KeyError: self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] + '1' ] = []
                                else: raise RuntimeError('More than two different basis sets for one element - not supported case!')

                        elif len(line) < 30:
                            marker = line.split()[0]
                            if len(marker) > 2:
                                # bs follows in short standard form
                                if bs_concurrency:
                                    self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] + '1' ] = marker
                                else:
                                    self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] ] = marker
                            else:
                                # bs follows as exponent list
                                try:
                                    if bs_concurrency:
                                        self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] + '1' ].append( [marker.upper()] )
                                    else:
                                        self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] ].append( [marker.upper()] )
                                except AttributeError: # bs is mixed from short standard form and exponent list, not supported
                                    pass

                        else:
                            try:
                                e = map(  logfile.float, line.replace('Exponent=', '').replace('Coefficients=', '').split()  )
                                if bs_concurrency:
                                    self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] + '1' ][-1].append( tuple(e) )
                                else:
                                    self.bs['bs'][ self.structures[-1]['atoms'][atomn][0] ][-1].append( tuple(e) )
                            except AttributeError: # bs is mixed from short standard form and exponent list, not supported
                                pass

        if not self.bs['bs']: raise RuntimeError( 'No basis set found!')

        # Get energy and method (theory level) TODO!
        self.method = {'H': None, 'tol': None, 'k': None, 'spin': None, 'technique': {}, 'lockstate': None}

        E, E_mp, E_cc = None, None, None
        try: E_mp = parsed.mpenergies[-1] # Hartree
        except: pass
        else: self.method['H'] = 'MP2'

        try: E_cc = parsed.ccenergies[-1] # Hartree
        except: pass
        else: self.method['H'] = 'coupled clusters'

        try: E = parsed.scfenergies[-1] # Hartree
        except: pass

        ene = filter(None, [E, E_mp, E_cc])
        if ene: self.energy = min(ene)

        # Get phonons
        if (hasattr(parsed, 'vibfreqs') and hasattr(parsed, 'vibdisps')) and (len(parsed.vibfreqs) and len(parsed.vibdisps)):
            if len(parsed.vibfreqs)/3 != len(filter(lambda x: x != -1, parsed.atomnos)): # we cannot guarantee that X-atoms are not present here (NB eigenvectors are already adjusted!)
                raise RuntimeError('Number of frequencies is not equal to 3 * number of atoms!')
            self.phonons, self.ph_eigvecs = {'0 0 0': parsed.vibfreqs}, {'0 0 0': parsed.vibdisps}

    @staticmethod
    def fingerprints(test_string):
        if " Gaussian, Inc.\n" in test_string: return True
        else: return False

def convertor(value, fromunits, tounits):
    '''Convert from one set of units to another: "%.1f" % convertor(8, "eV", "cm-1")'''
    _convertor = {"eV_to_cm-1": lambda x: x*8065.6,
                  "hartree_to_eV": lambda x: x*27.2113845,
                  "bohr_to_Angstrom": lambda x: x*0.529177,
                  "Angstrom_to_bohr": lambda x: x*1.889716,
                  "nm_to_cm-1": lambda x: 1e7/x,
                  "cm-1_to_nm": lambda x: 1e7/x,
                  "hartree_to_cm-1": lambda x: x*219474.6,
                  # Taken from GAMESS docs, "Further information",
                  # "Molecular Properties and Conversion Factors"
                  "Debye^2/amu-Angstrom^2_to_km/mol": lambda x: x*42.255}

    return _convertor["%s_to_%s" % (fromunits, tounits)] (value)

class ccData(object):
    """Class for objects containing data from cclib parsers and methods.

    Description of cclib attributes:
        aonames -- atomic orbital names (list)
        aooverlaps -- atomic orbital overlap matrix (array[2])
        atombasis -- indices of atomic orbitals on each atom (list of lists)
        atomcoords -- atom coordinates (array[3], angstroms)
        atommasses -- atom masses (array[1], daltons)
        atomnos -- atomic numbers (array[1])
        charge -- net charge of the system (integer)
        ccenergies -- molecular energies with Coupled-Cluster corrections (array[2], eV)
        coreelectrons -- number of core electrons in atom pseudopotentials (array[1])
        etenergies -- energies of electronic transitions (array[1], 1/cm)
        etoscs -- oscillator strengths of electronic transitions (array[1])
        etrotats -- rotatory strengths of electronic transitions (array[1], ??)
        etsecs -- singly-excited configurations for electronic transitions (list of lists)
        etsyms -- symmetries of electronic transitions (list)
        fonames -- fragment orbital names (list)
        fooverlaps -- fragment orbital overlap matrix (array[2])
        fragnames -- names of fragments (list)
        frags -- indices of atoms in a fragment (list of lists)
        gbasis -- coefficients and exponents of Gaussian basis functions (PyQuante format)
        geotargets -- targets for convergence of geometry optimization (array[1])
        geovalues -- current values for convergence of geometry optmization (array[1])
        hessian -- elements of the force constant matrix (array[1])
        homos -- molecular orbital indices of HOMO(s) (array[1])
        mocoeffs -- molecular orbital coefficients (list of arrays[2])
        moenergies -- molecular orbital energies (list of arrays[1], eV)
        mosyms -- orbital symmetries (list of lists)
        mpenergies -- molecular electronic energies with Moller-Plesset corrections (array[2], eV)
        mult -- multiplicity of the system (integer)
        natom -- number of atoms (integer)
        nbasis -- number of basis functions (integer)
        nmo -- number of molecular orbitals (integer)
        nocoeffs -- natural orbital coefficients (array[2])
        scfenergies -- molecular electronic energies after SCF (Hartree-Fock, DFT) (array[1], eV)
        scftargets -- targets for convergence of the SCF (array[2])
        scfvalues -- current values for convergence of the SCF (list of arrays[2])
        vibdisps -- cartesian displacement vectors (array[3], delta angstrom)
        vibfreqs -- vibrational frequencies (array[1], 1/cm)
        vibirs -- IR intensities (array[1], km/mol)
        vibramans -- Raman intensities (array[1], A^4/Da)
        vibsyms -- symmetries of vibrations (list)
    (1) The term 'array' refers to a numpy array
    (2) The number of dimensions of an array is given in square brackets
    (3) Python indexes arrays/lists starting at zero, so if homos==[10], then
            the 11th molecular orbital is the HOMO
    """

    def __init__(self, attributes=None):
        #"""Initialize the cclibData object.
        #
        #Normally called in the parse() method of a Logfile subclass.
        #
        #Inputs:
        #    attributes - dictionary of attributes to load
        #"""

        # Names of all supported attributes.
        self._attrlist = ['aonames', 'aooverlaps', 'atombasis',
                          'atomcoords', 'atommasses', 'atomnos',
                          'ccenergies', 'charge', 'coreelectrons',
                          'etenergies', 'etoscs', 'etrotats', 'etsecs', 'etsyms',
                          'fonames', 'fooverlaps', 'fragnames', 'frags',
                          'gbasis', 'geotargets', 'geovalues', 'grads',
                          'hessian', 'homos',
                          'mocoeffs', 'moenergies', 'mosyms', 'mpenergies', 'mult',
                          'natom', 'nbasis', 'nmo', 'nocoeffs',
                          'scfenergies', 'scftargets', 'scfvalues',
                          'vibdisps', 'vibfreqs', 'vibirs', 'vibramans', 'vibsyms',

                          'warns']

        # The expected types for all supported attributes.
        self._attrtypes = { "aonames":        list,
                            "aooverlaps":     ndarray,
                            "atombasis":      list,
                            "atomcoords":     ndarray,
                            "atommasses":     ndarray,
                            "atomnos":        ndarray,
                            "charge":         int,
                            "coreelectrons":  ndarray,
                            "etenergies":     ndarray,
                            "etoscs":         ndarray,
                            "etrotats":       ndarray,
                            "etsecs":         list,
                            "etsyms":         list,
                            'gbasis':         list,
                            "geotargets":     ndarray,
                            "geovalues":      ndarray,
                            "grads":          ndarray,
                            "hessian":        ndarray,
                            "homos":          ndarray,
                            "mocoeffs":       list,
                            "moenergies":     list,
                            "mosyms":         list,
                            "mpenergies":     ndarray,
                            "mult":           int,
                            "natom":          int,
                            "nbasis":         int,
                            "nmo":            int,
                            "nocoeffs":       ndarray,
                            "scfenergies":    ndarray,
                            "scftargets":     ndarray,
                            "scfvalues":      list,
                            "vibdisps":       list,
                            "vibfreqs":       list,
                            "vibirs":         ndarray,
                            "vibramans":      ndarray,
                            "vibsyms":        list,

                            "warns":          list,
                          }

        # Arrays are double precision by default, but these will be integer arrays.
        self._intarrays = ['atomnos', 'coreelectrons', 'homos']

        # Attributes that should be lists of arrays (double precision).
        self._listsofarrays = ['mocoeffs', 'moenergies', 'scfvalues']

        if attributes:
            self.setattributes(attributes)

    def listify(self):
        """Converts all attributes that are arrays or lists of arrays to lists."""

        for k, v in self._attrtypes.iteritems():
            if hasattr(self, k):
                if v == ndarray:
                    setattr(self, k, getattr(self, k).tolist())
                elif v == list and k in self._listsofarrays:
                    setattr(self, k, [x.tolist() for x in getattr(self, k)])

    def arrayify(self):
        """Converts appropriate attributes to arrays or lists of arrays."""

        for k, v in self._attrtypes.iteritems():
            if hasattr(self, k):
                precision = 'd'
                if k in self._intarrays:
                    precision = 'i'
                if v == ndarray:
                    try: setattr(self, k, array(getattr(self, k), precision))
                    except ValueError, e: raise RuntimeError('Uncorrespondence in extracted %s!' % k) # by jam31
                elif v == list and k in self._listsofarrays:
                    setattr(self, k, [array(x, precision) for x in getattr(self, k)])

    def getattributes(self, tolists=False):
        """Returns a dictionary of existing data attributes.

        Inputs:
            tolists - flag to convert attributes to lists where applicable
        """

        if tolists:
            self.listify()
        attributes = {}
        for attr in self._attrlist:
            if hasattr(self, attr):
                attributes[attr] = getattr(self,attr)
        if tolists:
            self.arrayify()
        return attributes

    def setattributes(self, attributes):
        """Sets data attributes given in a dictionary.

        Inputs:
            attributes - dictionary of attributes to set
        Outputs:
            invalid - list of attributes names that were not set, which
                      means they are not specified in self._attrlist
        """

        if type(attributes) is not dict:
            raise TypeError, "attributes must be in a dictionary"

        valid = [a for a in attributes if a in self._attrlist]
        invalid = [a for a in attributes if a not in self._attrlist]

        for attr in valid:
            setattr(self, attr, attributes[attr])
        self.arrayify()
        return invalid

class Logfile(object):
    """Abstract class for logfile objects.

    Subclasses defined by cclib:
        ADF, GAMESS, GAMESSUK, Gaussian, Jaguar, Molpro, ORCA
    """

    def __init__(self, source, datatype = ccData):

        self.inputfile = iter(source.splitlines())

        # Set up the logger.
        # Note that calling logging.getLogger() with one name always returns the same instance.
        # Presently in cclib, all parser instances of the same class use the same logger,
        #   which means that care needs to be taken not to duplicate handlers.
        #self.loglevel = loglevel
        #self.logname  = logname
        #self.logger = logging.getLogger('%s %s' % (self.logname,self.filename))
        #self.logger.setLevel(self.loglevel)
        #if len(self.logger.handlers) == 0:
        #        handler = logging.StreamHandler(logstream)
        #        handler.setFormatter(logging.Formatter("[%(name)s %(levelname)s] %(message)s"))
        #        self.logger.addHandler(handler)

        # Periodic table of elements.
        # self.table = utils.PeriodicTable() # by jam31, not needed

        # This is the class that will be used in the data object returned by parse(),
        #   and should normally be ccData or a subclass.

        self.datatype = datatype

    def __setattr__(self, name, value):

        # Send info to logger if the attribute is in the list self._attrlist.
        #if name in getattr(self, "_attrlist", {}) and hasattr(self, "logger"):
        #
        #    # Call logger.info() only if the attribute is new.
        #    if not hasattr(self, name):
        #        if type(value) in [ndarray, list]:
        #            self.logger.info("Creating attribute %s[]" %name)
        #        else:
        #            self.logger.info("Creating attribute %s: %s" %(name, str(value)))

        object.__setattr__(self, name, value)

    def parse(self, fupdate=None, cupdate=None):
        """Parse the logfile, using the assumed extract method of the child."""

        # Check that the sub-class has an extract attribute,
        #  that is callable with the proper number of arguemnts.
        #if not hasattr(self, "extract"):
        #    raise AttributeError, "Class %s has no extract() method." %self.__class__.__name__
        #    return -1
        #if not callable(self.extract):
        #    raise AttributeError, "Method %s._extract not callable." %self.__class__.__name__
        #    return -1
        #if len(inspect.getargspec(self.extract)[0]) != 3:
        #    raise AttributeError, "Method %s._extract takes wrong number of arguments." %self.__class__.__name__
        #    return -1

        # Save the current list of attributes to keep after parsing.
        # The dict of self should be the same after parsing.
        _nodelete = list(set(self.__dict__.keys()))

        # Initialize the ccData object that will be returned.
        # This is normally ccData, but can be changed by passing
        #   the datatype argument to __init__().

        data = self.datatype()

        # Copy the attribute list, so that the parser knows what to expect,
        #   specifically in __setattr__().
        # The class self.datatype (normally ccData) must have this attribute.

        self._attrlist = data._attrlist

        # Maybe the sub-class has something to do before parsing.
        if hasattr(self, "before_parsing"):
            self.before_parsing()

        # Loop over lines in the file object and call extract().
        # This is where the actual parsing is done.
        for line in self.inputfile:

            # This call should check if the line begins a section of extracted data.
            # If it does, it parses some lines and sets the relevant attributes (to self).
            # Any attributes can be freely set and used across calls, however only those
            #   in data._attrlist will be moved to final data object that is returned.

            self.extract(self.inputfile, line)

        # Maybe the sub-class has something to do after parsing.
        #if hasattr(self, "after_parsing"):
        #    self.after_parsing()

        # If atomcoords were not parsed, but some input coordinates were ("inputcoords").
        # This is originally from the Gaussian parser, a regression fix.

        if not hasattr(self, "atomcoords") and hasattr(self, "inputcoords"):
            self.warning('Standard geometry not found, input has been taken!')
            #if len(self.inputcoords) > 1: self.inputcoords = [ self.inputcoords[-1] ] # by jam31
            self.atomcoords = array(self.inputcoords, 'd')

        # Set nmo if not set already - to nbasis.
        #if not hasattr(self, "nmo") and hasattr(self, "nbasis"):
        #    self.nmo = self.nbasis

        # Creating deafult coreelectrons array.
        #if not hasattr(self, "coreelectrons") and hasattr(self, "natom"):
        #    self.coreelectrons = zeros(self.natom, "i")

        # Move all cclib attributes to the ccData object.
        # To be moved, an attribute must be in data._attrlist.
        for attr in data._attrlist:
            if hasattr(self, attr):
                setattr(data, attr, getattr(self, attr))

        # Now make sure that the cclib attributes in the data object
        #   are all the correct type (including arrays and lists of arrays).
        data.arrayify()

        # Delete all temporary attributes (including cclib attributes).
        # All attributes should have been moved to a data object,
        #   which will be returned.
        for attr in self.__dict__.keys():
            if not attr in _nodelete:
                self.__delattr__(attr)

        # Update self.progress as done.
        #if self.progress:
        #    self.progress.update(nstep, "Done")

        # Return the ccData object that was generated.
        return data

    #def normalisesym(self,symlabel):
    #    """Standardise the symmetry labels between parsers.
    #
    #    This method should be overwritten by individual parsers, and should
    #    contain appropriate doctests. If is not overwritten, this is detected
    #    as an error by unit tests.
    #    """
    #    return "ERROR: This should be overwritten by this subclass"

    def float(self, number):
        """Convert a string to a float avoiding the problem with Ds.

        >>> t = Logfile("dummyfile")
        >>> t.float("123.2323E+02")
        12323.23
        >>> t.float("123.2323D+02")
        12323.23
        """
        if '***' in number: number = 'nan' # by jam31
        number = number.replace("D","E")
        return float(number)

class GaussianParser(Logfile):
    """A Gaussian 98/03 log file."""

    def __init__(self, *args, **kwargs):
        # Call the __init__ method of the superclass
        Logfile.__init__(self, *args, **kwargs)
        self.warns = []

    def warning(self, msg):
        ''' store diagnostic messages '''
        self.warns.append(msg)

    #def normalisesym(self, label):
    #    """Use standard symmetry labels instead of Gaussian labels.
    #
    #    To normalise:
    #    (1) If label is one of [SG, PI, PHI, DLTA], replace by [sigma, pi, phi, delta]
    #    (2) replace any G or U by their lowercase equivalent
    #
    #    >>> sym = Gaussian("dummyfile").normalisesym
    #    >>> labels = ['A1', 'AG', 'A1G', "SG", "PI", "PHI", "DLTA", 'DLTU', 'SGG']
    #    >>> map(sym, labels)
    #    ['A1', 'Ag', 'A1g', 'sigma', 'pi', 'phi', 'delta', 'delta.u', 'sigma.g']
    #    """
    #    # note: DLT must come after DLTA
    #    greek = [('SG', 'sigma'), ('PI', 'pi'), ('PHI', 'phi'),
    #             ('DLTA', 'delta'), ('DLT', 'delta')]
    #    for k,v in greek:
    #        if label.startswith(k):
    #            tmp = label[len(k):]
    #            label = v
    #            if tmp:
    #                label = v + "." + tmp
    #
    #    ans = label.replace("U", "u").replace("G", "g")
    #    return ans

    def before_parsing(self):

        # Used to index self.scftargets[].
        SCFRMS, SCFMAX, SCFENERGY = range(3)

        # Flag that indicates whether it has reached the end of a geoopt.
        self.optfinished = False

        # Flag for identifying Coupled Cluster runs.
        self.coupledcluster = False

        # Fragment number for counterpoise calculations (normally zero).
        self.counterpoise = 0

        # Flag for identifying ONIOM calculations.
        self.oniom = False

    #def after_parsing(self):

    # Correct the percent values in the etsecs in the case of
    # a restricted calculation. The following has the
    # effect of including each transition twice.
    #if hasattr(self, "etsecs") and len(self.homos) == 1:
    #    new_etsecs = [[(x[0], x[1], x[2] * sqrt(2)) for x in etsec]
    #                  for etsec in self.etsecs]
    #    self.etsecs = new_etsecs

    def extract(self, inputfile, line):
        """Extract information from the file object"""

        # Number of atoms.
        if line[1:8] == "NAtoms=":
            natom = int(line.split()[1])
            if not hasattr(self, "natom"):
                self.natom = natom

        # Catch message about completed optimization.
        #if line[1:23] == "Optimization completed":
        #    self.optfinished = True

        # Extract the atomic numbers and coordinates from the input orientation,
        #   in the event the standard orientation isn't available.
        #if not self.optfinished and line.find("Input orientation") > -1 or line.find("Z-Matrix orientation") > -1:
        if "Input orientation" in line or "Z-Matrix orientation" in line:
        
            # If this is a counterpoise calculation, this output means that
            #   the supermolecule is now being considered, so we can set:
            self.counterpoise = 0
        
            #if not hasattr(self, "inputcoords"):
            #    self.inputcoords = []
            
            self.inputcoords = []
            self.inputatoms = []
        
            hyphens = inputfile.next()
            colmNames = inputfile.next()
            colmNames = inputfile.next()
            hyphens = inputfile.next()
        
            atomcoords = []
            line = inputfile.next()
            while line != hyphens:
                broken = line.split()
                if len(broken) < 6: raise RuntimeError('Unknown atomic structure format!')
                try: broken[1] = int(broken[1]) # unexpected end of the section
                except ValueError: break
                else:
                    self.inputatoms.append(broken[1])
                    atomcoords.append(map(float, broken[3:6]))
                    line = inputfile.next()
        
            self.inputcoords.append(atomcoords)
        
            if not hasattr(self, "atomnos"):
                self.atomnos = array(self.inputatoms, 'i')
                self.natom = len(self.atomnos)

        # Extract the atomic masses.
        # Typical section:
        #                    Isotopes and Nuclear Properties:
        #(Nuclear quadrupole moments (NQMom) in fm**2, nuclear magnetic moments (NMagM)
        # in nuclear magnetons)
        #
        #  Atom         1           2           3           4           5           6           7           8           9          10
        # IAtWgt=          12          12          12          12          12           1           1           1          12          12
        # AtmWgt=  12.0000000  12.0000000  12.0000000  12.0000000  12.0000000   1.0078250   1.0078250   1.0078250  12.0000000  12.0000000
        # NucSpn=           0           0           0           0           0           1           1           1           0           0
        # AtZEff=  -3.6000000  -3.6000000  -3.6000000  -3.6000000  -3.6000000  -1.0000000  -1.0000000  -1.0000000  -3.6000000  -3.6000000
        # NQMom=    0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   0.0000000
        # NMagM=    0.0000000   0.0000000   0.0000000   0.0000000   0.0000000   2.7928460   2.7928460   2.7928460   0.0000000   0.0000000
        # ... with blank lines dividing blocks of ten, and Leave Link 101 at the end.
        # This is generally parsed before coordinates, so atomnos is not defined.
        # Note that in Gaussian03 the comments are not there yet and the labels are different.

        #if line.strip() == "Isotopes and Nuclear Properties:":
        #
        #    if not hasattr(self, "atommasses"):
        #        self.atommasses = []
        #
        #    line = inputfile.next()
        #    while line[1:16] != "Leave Link  101":
        #        if line[1:8] == "AtmWgt=":
        #            self.atommasses.extend(map(float,line.split()[1:]))
        #        line = inputfile.next()

        # Extract the atomic numbers and coordinates of the atoms.
        #if not self.optfinished and line.strip() == "Standard orientation:":
        if line.strip() == "Standard orientation:":

            # If this is a counterpoise calculation, this output means that
            #   the supermolecule is now being considered, so we can set:
            self.counterpoise = 0

            #if not hasattr(self, "atomcoords"):
            #    self.atomcoords = []
            self.atomcoords = []
            
            hyphens = inputfile.next()
            colmNames = inputfile.next()
            colmNames = inputfile.next()
            hyphens = inputfile.next()

            atomnos = []
            atomcoords = []
            line = inputfile.next()
            while line != hyphens:
                broken = line.split()
                if len(broken) < 6: raise RuntimeError('Unknown atomic structure format!')
                try: broken[1] = int(broken[1]) # unexpected end of the section
                except ValueError: break
                else:
                    atomnos.append(broken[1])
                    atomcoords.append(map(float, broken[-3:]))
                    line = inputfile.next()
            self.atomcoords.append(atomcoords)

            #if not hasattr(self, "natom"):
            #    self.atomnos = array(atomnos, 'i')
            #    self.natom = len(self.atomnos)

            # make sure atomnos is added for the case where natom has already been set
            #elif not hasattr(self, "atomnos"):
            #    self.atomnos = array(atomnos, 'i')

            self.atomnos = array(atomnos, 'i')
            self.natom = len(self.atomnos)   
                
        # Find the targets for SCF convergence (QM calcs).
        #if line[1:44] == 'Requested convergence on RMS density matrix':
        #
        #    if not hasattr(self, "scftargets"):
        #        self.scftargets = []
        #
        #    scftargets = []
        #    # The RMS density matrix.
        #    scftargets.append(self.float(line.split('=')[1].split()[0]))
        #    line = inputfile.next()
        #    # The MAX density matrix.
        #    scftargets.append(self.float(line.strip().split('=')[1][:-1]))
        #    line = inputfile.next()
        #    # For G03, there's also the energy (not for G98).
        #    if line[1:10] == "Requested":
        #        scftargets.append(self.float(line.strip().split('=')[1][:-1]))
        #
        #    self.scftargets.append(scftargets)

        # Extract SCF convergence information (QM calcs).
        #if line[1:10] == 'Cycle   1':
        #
        #    if not hasattr(self, "scfvalues"):
        #        self.scfvalues = []
        #
        #    scfvalues = []
        #    line = inputfile.next()
        #    while line.find("SCF Done") == -1:
        #
        #        #if line.find(' E=') == 0:
        #        #    self.logger.debug(line)
        #        #  RMSDP=3.74D-06 MaxDP=7.27D-05 DE=-1.73D-07 OVMax= 3.67D-05
        #        # or
        #        #  RMSDP=1.13D-05 MaxDP=1.08D-04              OVMax= 1.66D-04
        #        if line.find(" RMSDP") == 0:
        #
        #            parts = line.split()
        #            newlist = [self.float(x.split('=')[1]) for x in parts[0:2]]
        #            energy = 1.0
        #            if len(parts) > 4:
        #                energy = parts[2].split('=')[1]
        #                if energy == "":
        #                    energy = self.float(parts[3])
        #                else:
        #                    energy = self.float(energy)
        #            if len(self.scftargets[0]) == 3: # Only add the energy if it's a target criteria
        #                newlist.append(energy)
        #            scfvalues.append(newlist)
        #
        #        try:
        #            line = inputfile.next()
        #        # May be interupted by EOF.
        #        except StopIteration:
        #            break
        #
        #    self.scfvalues.append(scfvalues)

        # Extract SCF convergence information (AM1 calcs).
        #if line[1:4] == 'It=':
        #
        #    #self.scftargets = array([1E-7], "d") # This is the target value for the rms
        #    self.scftargets = [[1E-7, 1E-7, 1E-7]] # by jam31
        #    self.scfvalues = [[]]
        #
        #    line = inputfile.next()
        #    while line.find(" Energy") == -1:
        #
        #        #if self.progress:
        #        #    step = inputfile.tell()
        #        #    if step != oldstep:
        #        #        self.progress.update(step, "AM1 Convergence")
        #        #        oldstep = step
        #
        #        if line[1:4] == "It=":
        #            parts = line.strip().split()
        #            if 'ST=' in line: v = parts[-1].replace('ST=', '')
        #            else: v = parts[-1][:-1]
        #            self.scfvalues[0].append(self.float( v ))
        #        line = inputfile.next()
        
        # Note: this needs to follow the section where 'SCF Done' is used
        #   to terminate a loop when extracting SCF convergence information.
        if line[1:9] == 'SCF Done':
        
            if not hasattr(self, "scfenergies"):
                self.scfenergies = []
        
            self.scfenergies.append(convertor(self.float(line.split()[4]), "hartree", "eV"))
            
        # gmagoon 5/27/09: added scfenergies reading for PM3 case
        # Example line: " Energy=   -0.077520562724 NIter=  14."
        # See regression Gaussian03/QVGXLLKOCUKJST-UHFFFAOYAJmult3Fixed.out
        
        if line[1:8] == 'Energy=':
            if not hasattr(self, "scfenergies"):
                self.scfenergies = []
            self.scfenergies.append(convertor(self.float(line.split()[1]), "hartree", "eV"))

        # Total energies after Moller-Plesset corrections.
        # Second order correction is always first, so its first occurance
        #   triggers creation of mpenergies (list of lists of energies).
        # Further MP2 corrections are appended as found.
        #
        # Example MP2 output line:
        #  E2 =    -0.9505918144D+00 EUMP2 =    -0.28670924198852D+03
        # Warning! this output line is subtly different for MP3/4/5 runs
        
        if "EUMP2" in line[27:34]:

            if not hasattr(self, "mpenergies"):
                self.mpenergies = []
            #self.mpenergies.append([])
            mp2energy = self.float(line.split("=")[2])
            self.mpenergies.append(mp2energy)

        # Example MP3 output line:
        #  E3=       -0.10518801D-01     EUMP3=      -0.75012800924D+02
        #if line[34:39] == "EUMP3":
        #
        #    if not hasattr(self, "mpenergies"):
        #        self.mpenergies = []
        #
        #    mp3energy = self.float(line.split("=")[2])
        #    self.mpenergies.append(convertor(mp3energy, "hartree", "eV"))

        # Example MP4 output lines:
        #  E4(DQ)=   -0.31002157D-02        UMP4(DQ)=   -0.75015901139D+02
        #  E4(SDQ)=  -0.32127241D-02        UMP4(SDQ)=  -0.75016013648D+02
        #  E4(SDTQ)= -0.32671209D-02        UMP4(SDTQ)= -0.75016068045D+02
        # Energy for most substitutions is used only (SDTQ by default)
        #if line[34:42] == "UMP4(DQ)":
        #
        #    mp4energy = self.float(line.split("=")[2])
        #    line = inputfile.next()
        #    if line[34:43] == "UMP4(SDQ)":
        #      mp4energy = self.float(line.split("=")[2])
        #      line = inputfile.next()
        #      if line[34:44] == "UMP4(SDTQ)":
        #        mp4energy = self.float(line.split("=")[2])
        #    self.mpenergies.append(convertor(mp4energy, "hartree", "eV"))
        #
        # Example MP5 output line:
        #  DEMP5 =  -0.11048812312D-02 MP5 =  -0.75017172926D+02
        # if line[29:32] == "MP5":
        #    mp5energy = self.float(line.split("=")[2])
        #    self.mpenergies.append(convertor(mp5energy, "hartree", "eV"))

        # Total energies after Coupled Cluster corrections.
        # Second order MBPT energies (MP2) are also calculated for these runs,
        #  but the output is the same as when parsing for mpenergies.
        # First turn on flag for Coupled Cluster runs.
        
        if line[1:23] == "Coupled Cluster theory" or line[1:8] == "CCSD(T)":

            self.coupledcluster = True
            if not hasattr(self, "ccenergies"):
                self.ccenergies = []

        # Now read the consecutive correlated energies when ,
        #  but append only the last one to ccenergies.
        # Only the highest level energy is appended - ex. CCSD(T), not CCSD.
        
        if self.coupledcluster and line[27:35] == "E(CORR)=":
            self.ccenergy = self.float(line.split()[3])
        if self.coupledcluster and line[1:9] == "CCSD(T)=":
            self.ccenergy = self.float(line.split()[1])
        # Append when leaving link 913
        if self.coupledcluster and line[1:16] == "Leave Link  913":
            self.ccenergies.append(self.ccenergy)

        # Geometry convergence information.
        #if line[49:59] == 'Converged?':
        #
        #    if not hasattr(self, "geotargets"):
        #        self.geovalues = []
        #        self.geotargets = array([0.0, 0.0, 0.0, 0.0], "d")
        #
        #    newlist = [0]*4
        #    for i in range(4):
        #        line = inputfile.next()
        #        #self.logger.debug(line)
        #        parts = line.split()
        #        try:
        #            value = self.float(parts[2])
        #        except ValueError:
        #            pass
        #            #self.logger.error("Problem parsing the value for geometry optimisation: %s is not a number." % parts[2])
        #        else:
        #            newlist[i] = value
        #        self.geotargets[i] = self.float(parts[3])
        #
        #    self.geovalues.append(newlist)

        # Gradients.
        # Read in the cartesian energy gradients (forces) from a block like this:
        # -------------------------------------------------------------------
        # Center     Atomic                   Forces (Hartrees/Bohr)
        # Number     Number              X              Y              Z
        # -------------------------------------------------------------------
        # 1          1          -0.012534744   -0.021754635   -0.008346094
        # 2          6           0.018984731    0.032948887   -0.038003451
        # 3          1          -0.002133484   -0.006226040    0.023174772
        # 4          1          -0.004316502   -0.004968213    0.023174772
        #           -2          -0.001830728   -0.000743108   -0.000196625
        # ------------------------------------------------------------------
        #
        # The "-2" line is for a dummy atom
        #
        # Then optimization is done in internal coordinates, Gaussian also
        # print the forces in internal coordinates, which can be produced from
        # the above. This block looks like this:
        # Variable       Old X    -DE/DX   Delta X   Delta X   Delta X     New X
        #                                 (Linear)    (Quad)   (Total)
        #   ch        2.05980   0.01260   0.00000   0.01134   0.01134   2.07114
        #   hch        1.75406   0.09547   0.00000   0.24861   0.24861   2.00267
        #   hchh       2.09614   0.01261   0.00000   0.16875   0.16875   2.26489
        #         Item               Value     Threshold  Converged?
        #if line[37:43] == "Forces":
        #
        #    if not hasattr(self, "grads"):
        #        self.grads = []
        #
        #    header = inputfile.next()
        #    dashes = inputfile.next()
        #    line = inputfile.next()
        #    forces = []
        #    while line != dashes:
        #        broken = line.split()
        #        Fx, Fy, Fz = broken[-3:]
        #        forces.append([float(Fx),float(Fy),float(Fz)])
        #        line = inputfile.next()
        #    self.grads.append(forces)
        #
        # Charge and multiplicity.
        # If counterpoise correction is used, multiple lines match.
        # The first one contains charge/multiplicity of the whole molecule.:
        #   Charge =  0 Multiplicity = 1 in supermolecule
        #   Charge =  0 Multiplicity = 1 in fragment  1.
        #   Charge =  0 Multiplicity = 1 in fragment  2.
        #if line[1:7] == 'Charge' and line.find("Multiplicity")>=0:
        #
        #    regex = ".*=(.*)Mul.*=\s*(\d+).*"
        #    match = re.match(regex, line)
        #    if not match: raise RuntimeError("Something unusual about the line: '%s'" % line) # modified by jam31
        #
        #    self.charge = int(match.groups()[0])
        #    self.mult = int(match.groups()[1])
        # Orbital symmetries.
        #if line[1:20] == 'Orbital symmetries:' and not hasattr(self, "mosyms"):
        #
        #    # For counterpoise fragments, skip these lines.
        #    if self.counterpoise != 0: return
        #
        #    self.mosyms = [[]]
        #    line = inputfile.next()
        #    unres = False
        #    if line.find("Alpha Orbitals") == 1:
        #        unres = True
        #        line = inputfile.next()
        #    i = 0
        #    while len(line) > 18 and line[17] == '(':
        #        if line.find('Virtual') >= 0:
        #            self.homos = array([i-1], "i") # 'HOMO' indexes the HOMO in the arrays
        #        parts = line[17:].split()
        #        for x in parts:
        #            self.mosyms[0].append(self.normalisesym(x.strip('()')))
        #            i += 1
        #        line = inputfile.next()
        #    if unres:
        #        line = inputfile.next()
        #        # Repeat with beta orbital information
        #        i = 0
        #        self.mosyms.append([])
        #        while len(line) > 18 and line[17] == '(':
        #            if line.find('Virtual')>=0:
        #                # Here we consider beta
        #                # If there was also an alpha virtual orbital,
        #                #  we will store two indices in the array
        #                # Otherwise there is no alpha virtual orbital,
        #                #  only beta virtual orbitals, and we initialize
        #                #  the array with one element. See the regression
        #                #  QVGXLLKOCUKJST-UHFFFAOYAJmult3Fixed.out
        #                #  donated by Gregory Magoon (gmagoon).
        #                if (hasattr(self, "homos")):
        #                    # Extend the array to two elements
        #                    # 'HOMO' indexes the HOMO in the arrays
        #                    self.homos.resize([2])
        #                    self.homos[1] = i-1
        #                else:
        #                    # 'HOMO' indexes the HOMO in the arrays
        #                    self.homos = array([i-1], "i")
        #            parts = line[17:].split()
        #            for x in parts:
        #                self.mosyms[1].append(self.normalisesym(x.strip('()')))
        #                i += 1
        #            line = inputfile.next()
        #
        # Alpha/Beta electron eigenvalues.
        # if line[1:6] == "Alpha" and line.find("eigenvalues") >= 0:
        #
        #    # For counterpoise fragments, skip these lines.
        #    if self.counterpoise != 0: return
        #
        #    # For ONIOM calcs, ignore this section in order to bypass assertion failure.
        #    if self.oniom: return

        #    self.moenergies = [[]]
        #    HOMO = -2
        #
        #    while line.find('Alpha') == 1:
        #        if line.split()[1] == "virt." and HOMO == -2:
        #
        #            # If there aren't any symmetries, this is a good way to find the HOMO.
        #            # Also, check for consistency if homos was already parsed.
        #            HOMO = len(self.moenergies[0])-1
        #            if hasattr(self, "homos"):
        #                if HOMO != self.homos[0]: raise RuntimeError("HOMO values not match: %s and %s" % (HOMO, self.homos[0])) # modified by jam31
        #            else:
        #                self.homos = array([HOMO], "i")
        #
        #        part = line[28:]
        #        i = 0
        #        while i*10+4 < len(part):
        #            x = part[i*10:(i+1)*10]
        #            self.moenergies[0].append(convertor(self.float(x), "hartree", "eV"))
        #            i += 1
        #        line = inputfile.next()
        #    # If, at this point, self.homos is unset, then there were not
        #    # any alpha virtual orbitals
        #    if not hasattr(self, "homos"):
        #        HOMO = len(self.moenergies[0])-1
        #        self.homos = array([HOMO], "i")
        #
        #
        #    if line.find('Beta') == 2:
        #        self.moenergies.append([])
        #
        #    HOMO = -2
        #    while line.find('Beta') == 2:
        #        if line.split()[1] == "virt." and HOMO == -2:
        #
        #            # If there aren't any symmetries, this is a good way to find the HOMO.
        #            # Also, check for consistency if homos was already parsed.
        #            HOMO = len(self.moenergies[1])-1
        #            if len(self.homos) == 2:
        #                if HOMO != self.homos[1]: raise RuntimeError("HOMO values not match: %s and %s" % (HOMO, self.homos[1])) # modified by jam31
        #            else:
        #                self.homos.resize([2])
        #                self.homos[1] = HOMO
        #
        #        part = line[28:]
        #        i = 0
        #        while i*10+4 < len(part):
        #            x = part[i*10:(i+1)*10]
        #            self.moenergies[1].append(convertor(self.float(x), "hartree", "eV"))
        #            i += 1
        #        line = inputfile.next()
        #
        #    self.moenergies = [array(x, "d") for x in self.moenergies]

        # Gaussian Rev <= B.0.3 (?)
        # AO basis set in the form of general basis input:
        #  1 0
        # S   3 1.00       0.000000000000
        #      0.7161683735D+02  0.1543289673D+00
        #      0.1304509632D+02  0.5353281423D+00
        #      0.3530512160D+01  0.4446345422D+00
        # SP   3 1.00       0.000000000000
        #      0.2941249355D+01 -0.9996722919D-01  0.1559162750D+00
        #      0.6834830964D+00  0.3995128261D+00  0.6076837186D+00
        #      0.2222899159D+00  0.7001154689D+00  0.3919573931D+00
        
        if line[1:16] == "AO basis set in":

            # For counterpoise fragment calcualtions, skip these lines.
            if self.counterpoise != 0: return

            self.gbasis = []
            line = inputfile.next()
            while line.strip():
                gbasis = []
                line = inputfile.next()
                while line.find("*")<0:
                    temp = line.split()
                    symtype = temp[0]
                    numgau = int(temp[1])
                    gau = []
                    for i in range(numgau):
                        temp = map(self.float, inputfile.next().split())
                        gau.append(temp)
                    #for i,x in enumerate(symtype):
                    #    newgau = [(z[0],z[i+1]) for z in gau]
                    #    gbasis.append( (x,newgau) )

                    newgau = [tuple(z) for z in gau]
                    gbasis.append( (symtype, tuple( newgau )) ) # by jam31

                    line = inputfile.next() # i.e. "****" or "SP ...."
                self.gbasis.append( tuple(gbasis) ) # by jam31
                line = inputfile.next() # i.e. "20 0" or blank line

        # Start of the IR/Raman frequency section.
        # Caution is advised here, as additional frequency blocks
        #   can be printed by Gaussian (with slightly different formats),
        #   often doubling the information printed.
        # See, for a non-standard exmaple, regression Gaussian98/test_H2.log

        if "Full mass-weighted force constant matrix" in line:
            if not hasattr(self, 'atomnos'): raise RuntimeError('Atoms are not found!')

            if hasattr(self, 'lovibfreqs') or hasattr(self, 'vibfreqs') or hasattr(self, 'vibdisps'):
                self.warning('Several phonon sets are found - only the last one is taken!')

            self.lovibfreqs, self.vibfreqs, self.vibdisps = [], [], []
            while not (line.strip() == "" and self.vibfreqs):

                if '- Thermochemistry -' in line: break # if no harmonic section (self.vibfreqs)

                # Lines with symmetries and symm. indices begin with whitespace.
                #if line[1:15].strip() == "" and not line[15:22].strip().isdigit():
                #
                #    if not hasattr(self, 'vibsyms'):
                #        self.vibsyms = []
                #    syms = line.split()
                #    self.vibsyms.extend(syms)

                if " Low frequencies ---" in line:
                    freqs, v = [], ''
                    for n, f in enumerate(line[ 20 : ]):
                        if not n % 10 and len(v):
                            freqs.append(float(v))
                            v = ''
                        v += f
                    if len(v): freqs.append(float(v))
                    self.lovibfreqs.extend(freqs)

                elif " Frequencies -- " in line:
                    freqs = [self.float(f) for f in line[ 15 : ].split()]
                    self.vibfreqs.extend(freqs)

                #if line[1:15] == "IR Inten    --":
                #
                #    if not hasattr(self, 'vibirs'):
                #        self.vibirs = []
                #    irs = [self.float(f) for f in line[15:].split()]
                #    self.vibirs.extend(irs)
                #

                #if line[1:15] == "Raman Activ --":
                #
                #    if not hasattr(self, 'vibramans'):
                #        self.vibramans = []
                #    ramans = [self.float(f) for f in line[15:].split()]
                #    self.vibramans.extend(ramans)
                #

                # Block with displacement should start with this.
                # Remember, it is possible to have less than three columns!
                # There should be as many lines as there are atoms.
                p = line.split()
                if p[0:5] == ['Atom', 'AN', 'X', 'Y', 'Z']:
                    disps = []
                    for n in range(self.natom):
                        line = inputfile.next()
                        splt = line[10:].split()
                        numbers = [float(s) for s in splt]
                        N = len(numbers) / 3
                        if not disps:
                            for n in range(N):
                                disps.append([])
                        for n in range(N):
                            disps[n].extend(numbers[3*n:3*n+3])
                    self.vibdisps.extend(disps)

                line = inputfile.next()

            #print self.atomnos, self.lovibfreqs, self.vibfreqs

            # sometimes imaginary frequencies occur in a harmonic area, is it a GAUSSIAN bug?
            neweigenv_pos = 0
            for f in self.lovibfreqs:
                if not len(self.vibfreqs): break
                if f<0 and f == self.vibfreqs[0]:
                    self.vibfreqs.pop(0)
                    neweigenv_pos += 1
                else: break

            if neweigenv_pos: self.warning('Attention: an imaginary frequency was found in a harmonic section!')

            n_vib_atoms = len(filter(lambda x: x != -1, self.atomnos))

            lodiff = len(self.lovibfreqs + self.vibfreqs) - n_vib_atoms*3

            if lodiff < 0: raise RuntimeError('Fatal error! Number of frequencies < 3 * N_atoms!')
            elif lodiff > 0:
                self.lovibfreqs = self.lovibfreqs[0:-lodiff]
                self.warning('Attention: the last %s low frequencies are replaced with matching ones from harmonic section, because it must be %s frequencies for %s atoms.' % (lodiff, n_vib_atoms*3, n_vib_atoms))

            if len(self.lovibfreqs):
                self.warning('Attention: phonon eigenvectors are missing for %s low frequencies, zero values have been inserted!' % len(self.lovibfreqs))
                for i in range(len(self.lovibfreqs)):
                    self.vibdisps.insert(neweigenv_pos, [0.0, 0.0, 0.0] * n_vib_atoms) # fake zeros for missing eigenvectors --- where you think should we get them?

            for g in [n for n in range(len(self.atomnos)) if self.atomnos[n] == -1]: # fake zeros for X atoms
                for m in range(len(self.vibdisps)):
                    for j in range(3): self.vibdisps[m].insert(g*3, 0)

            self.vibfreqs = self.lovibfreqs + self.vibfreqs

            #print self.vibdisps

        # Pseudopotential charges.
        #if line.find("Pseudopotential Parameters") > -1:
        #
        #    dashes = inputfile.next()
        #    label1 = inputfile.next()
        #    label2 = inputfile.next()
        #    dashes = inputfile.next()
        #
        #    line = inputfile.next()
        #    if line.find("Centers:") < 0:
        #        return
        #    centers = []
        #    while line.find("Centers:") >= 0:
        #        centers.extend(map(int, line.split()[1:]))
        #        line = inputfile.next()
        #    centers.sort() # Not always in increasing order
        #
        #    self.coreelectrons = zeros(self.natom, "i")
        #
        #    for center in centers:
        #        front = line[:10].strip()
        #        while not (front and int(front) == center):
        #            line = inputfile.next()
        #            front = line[:10].strip()
        #        info = line.split()
        #        self.coreelectrons[center-1] = int(info[1]) - int(info[2])
        #        line = inputfile.next()

        # This will be printed for counterpoise calcualtions only.
        # To prevent crashing, we need to know which fragment is being considered.
        # Other information is also printed in lines that start like this.
        #if line[1:14] == 'Counterpoise:':
        #
        #    if line[42:50] == "fragment":
        #        self.counterpoise = int(line[51:54])

        # This will be printed only during ONIOM calcs; use it to set a flag
        # that will allow assertion failures to be bypassed in the code.
        #if line[1:7] == "ONIOM:":
        #    self.oniom = True
