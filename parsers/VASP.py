#!/usr/bin/env python
# Tilde project: VASP XML parser
# contains modified pymatgen iovasp module (author: Shyue Ping Ong)
# v011212

import os
import sys
import re
import math

import itertools
import xml.sax.handler
import StringIO
from collections import defaultdict
import logging

from numpy import dot
from numpy import array
from numpy import zeros

from parsers import Output
sys.path.append(os.path.realpath(os.path.dirname(__file__)) + '/../core/deps')
from ase.lattice.spacegroup.cell import cell_to_cellpar
from ase.data import atomic_numbers, chemical_symbols
from ase.atoms import Atoms

Hartree = 27.211398
VaspToCm = 521.47083

logger = logging.getLogger(__name__)

def reverse_readline(m_file, blk_size=4096):
    """Generator method to read a file line-by-line, but backwards. This allows
    one to efficiently get data at the end of a file.

    Based on code by Peter Astrand <astrand@cendio.se>, using modifications by
    Raymond Hettinger and Kevin German.
    http://code.activestate.com/recipes/439045-read-a-text-file-backwards-yet-another-implementat/

    Args:
        m_file:
            File stream to read (backwards)
        blk_size:
            The buffer size. Defaults to 4096.

    Returns:
        Generator that returns lines from the file. Similar behavior to the
        file.readline() method, except the lines are returned from the back
        of the file."""

    buf = ""
    m_file.seek(0, 2)
    lastchar = m_file.read(1)
    trailing_newline = (lastchar == "\n")

    while 1:
        newline_pos = buf.rfind("\n")
        pos = m_file.tell()
        if newline_pos != -1:
            # Found a newline
            line = buf[newline_pos+1:]
            buf = buf[:newline_pos]
            if pos or newline_pos or trailing_newline:
                line += "\n"
            yield line
        elif pos:
            # Need to fill buffer
            toread = min(blk_size, pos)
            m_file.seek(pos-toread, 0)
            buf = m_file.read(toread) + buf
            m_file.seek(pos-toread, 0)
            if pos == toread:
                buf = "\n" + buf
        else:
            # Start-of-file
            return

def str_delimited(results, header=None, delimiter="\t"):
    """
    Given a tuple of tuples, generate a delimited string form.
    >>> results = [["a","b","c"],["d","e","f"],[1,2,3]]
    >>> print str_delimited(results,delimiter=",")
    a,b,c
    d,e,f
    1,2,3
    Args:
        result: 2d sequence of arbitrary types.
        header: optional header

    Returns:
        Aligned string output in a table-like format.
    """
    returnstr = ""
    if header is not None:
        returnstr += delimiter.join(header) + "\n"
    return returnstr + "\n".join([delimiter.join([str(m) for m in result])
                                  for result in results])


def str_aligned(results, header=None):
    """
    Given a tuple, generate a nicely aligned string form.
    >>> results = [["a","b","cz"],["d","ez","f"],[1,2,3]]
    >>> print str_aligned(results)
    a    b   cz
    d   ez    f
    1    2    3
    Args:
        result: 2d sequence of arbitrary types.
        header: optional header

    Returns:
        Aligned string output in a table-like format.
    """
    k = list(zip(*results))
    stringlengths = list()
    count = 0
    for i in k:
        col_max_len = max([len(str(m)) for m in i])
        if header is not None:
            col_max_len = max([len(str(header[count])), col_max_len])
        stringlengths.append(col_max_len)
        count += 1
    format_string = "   ".join(["%" + str(d) + "s" for d in stringlengths])
    returnstr = ""
    if header is not None:
        header_str = format_string % tuple(header)
        returnstr += header_str + "\n"
        returnstr += "-" * len(header_str) + "\n"
    return returnstr + "\n".join([format_string % tuple(result) for result in results])
      
class Enum(set):
    """ Creates an enum out of a set """
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError
        
class Kpoints():
    supported_modes = Enum(("Gamma", "Monkhorst", "Automatic", "Line_mode", "Cartesian", "Reciprocal"))

    def __init__(self, comment="Default gamma", num_kpts=0,
                 style=supported_modes.Gamma,
                 kpts=[[1, 1, 1]], kpts_shift=(0, 0, 0),
                 kpts_weights=None, coord_type=None, labels=None,
                 tet_number=0, tet_weight=0, tet_connections=None):
                 
        """Highly flexible constructor for Kpoints object.  The flexibility comes
        at the cost of usability and in general, it is recommended that you use
        the default constructor only if you know exactly what you are doing and
        requires the flexibility.  For most usage cases, the three automatic
        schemes can be constructed far more easily using the convenience static
        constructors (automatic, gamma_automatic, monkhorst_automatic) and it
        is recommended that you use those.

        Args:
            comment:
                String comment for Kpoints
            num_kpts:
                Following VASP method of defining the KPOINTS file, this
                parameter is the number of kpoints specified. If set to 0
                (or negative), VASP automatically generates the KPOINTS.
            style:
                Style for generating KPOINTS.  Use one of the
                Kpoints.supported_modes enum types.
            kpts:
                2D array of kpoints.  Even when only a single specification is
                required, e.g. in the automatic scheme, the kpts should still
                be specified as a 2D array. e.g., [[20]] or [[2,2,2]].
            kpts_shift:
                Shift for Kpoints.
            kpts_weights:
                Optional weights for kpoints.  For explicit kpoints.
            coord_type:
                In line-mode, this variable specifies whether the Kpoints were
                given in Cartesian or Reciprocal coordinates.
            labels:
                In line-mode, this should provide a list of labels for each
                kpt.
            tet_number:
                For explicit kpoints, specifies the number of tetrahedrons for
                the tetrahedron method.
            tet_weight:
                For explicit kpoints, specifies the weight for each tetrahedron
                for the tetrahedron method.
            tet_connections:
                For explicit kpoints, specifies the connections of the
                tetrahedrons for the tetrahedron method.
                Format is a list of tuples, [ (sym_weight, [tet_vertices]), ...]

        The default behavior of the constructor is for a Gamma centered,
        1x1x1 KPOINTS with no shift."""
        
        if num_kpts > 0 and (not labels) and (not kpts_weights):
            raise ValueError("For explicit or line-mode kpoints, either the labels or kpts_weights must be specified.")
        if style in (Kpoints.supported_modes.Automatic,
                     Kpoints.supported_modes.Gamma,
                     Kpoints.supported_modes.Monkhorst) and len(kpts) > 1:
            raise ValueError("For fully automatic or automatic gamma or monk kpoints, only a single line for the number of divisions is allowed.")

        self.comment = comment
        self.num_kpts = num_kpts
        self.style = style
        self.coord_type = coord_type
        self.kpts = kpts
        self.kpts_weights = kpts_weights
        self.kpts_shift = kpts_shift
        self.labels = labels
        self.tet_number = tet_number
        self.tet_weight = tet_weight
        self.tet_connections = tet_connections

    @staticmethod
    def automatic(subdivisions):
        """
        Convenient static constructor for a fully automatic Kpoint grid, with
        gamma centered Monkhorst-Pack grids and the number of subdivisions
        along each reciprocal lattice vector determined by the scheme in the
        VASP manual.

        Args:
            subdivisions:
                 Parameter determining number of subdivisions along each
                 reciprocal lattice vector.

        Returns:
            Kpoints object
        """
        return Kpoints("Fully automatic kpoint scheme", 0,
                       style=Kpoints.supported_modes.Automatic,
                       kpts=[[subdivisions]])

    @staticmethod
    def gamma_automatic(kpts=(1, 1, 1), shift=(0, 0, 0)):
        """
        Convenient static constructor for an automatic Gamma centered Kpoint
        grid.

        Args:
            kpts:
                Subdivisions N_1, N_2 and N_3 along reciprocal lattice vectors.
                Defaults to (1,1,1)
            shift:
                Shift to be applied to the kpoints. Defaults to (0,0,0).

        Returns:
            Kpoints object
        """
        return Kpoints("Automatic kpoint scheme", 0,
                       Kpoints.supported_modes.Gamma, kpts=[kpts],
                       kpts_shift=shift)

    @staticmethod
    def monkhorst_automatic(kpts=(2, 2, 2), shift=(0, 0, 0)):
        """
        Convenient static constructor for an automatic Monkhorst pack Kpoint
        grid.

        Args:
            kpts:
                Subdivisions N_1, N_2 and N_3 along reciprocal lattice vectors.
                Defaults to (2,2,2)
            shift:
                Shift to be applied to the kpoints. Defaults to (0,0,0).

        Returns:
            Kpoints object
        """
        return Kpoints("Automatic kpoint scheme", 0,
                       Kpoints.supported_modes.Monkhorst, kpts=[kpts],
                       kpts_shift=shift)

    @staticmethod
    def automatic_density(structure, kppa):
        """
        Returns an automatic Kpoint object based on a structure and a kpoint
        density. Uses Gamma centered meshes for hexagonal cells and
        Monkhorst-Pack grids otherwise.

        Algorithm:
            Uses a simple approach scaling the number of divisions along each
            reciprocal lattice vector proportional to its length.

        Args:
            structure:
                Input structure
            kppa:
                Grid density
        """

        latt = structure.lattice
        lengths = latt.abc
        ngrid = kppa / structure.num_sites

        mult = (ngrid * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)

        num_div = [int(round(1 / lengths[i] * mult)) for i in xrange(3)]
        #ensure that numDiv[i] > 0
        num_div = [i if i > 0 else 1 for i in num_div]

        angles = latt.angles
        hex_angle_tol = 5  # in degrees
        hex_length_tol = 0.01  # in angstroms
        right_angles = [i for i in xrange(3)
                        if abs(angles[i] - 90) < hex_angle_tol]
        hex_angles = [i for i in xrange(3)
                      if abs(angles[i] - 60) < hex_angle_tol or
                      abs(angles[i] - 120) < hex_angle_tol]

        is_hexagonal = (len(right_angles) == 2 and len(hex_angles) == 1
                        and abs(lengths[right_angles[0]] -
                                lengths[right_angles[1]]) < hex_length_tol)

        style = Kpoints.supported_modes.Gamma
        if not is_hexagonal:
            num_div = [i + i % 2 for i in num_div]
            style = Kpoints.supported_modes.Monkhorst
        comment = "pymatgen generated KPOINTS with grid density = " + \
            "{} / atom".format(kppa)
        num_kpts = 0
        return Kpoints(comment, num_kpts, style, [num_div], [0, 0, 0])

    '''@staticmethod
    def from_file(filename):
        with open(filename) as f:
            lines = [line.strip() for line in f.readlines()]
        comment = lines[0]
        num_kpts = int(lines[1].split()[0].strip())
        style = lines[2].lower()[0]

        #Fully automatic KPOINTS
        if style == "a":
            return Kpoints.automatic(int(lines[3]))

        coord_pattern = re.compile("^\s*([\d+\.\-Ee]+)\s+([\d+\.\-Ee]+)\s+"
                                   "([\d+\.\-Ee]+)")
        #Automatic gamma and Monk KPOINTS, with optional shift
        if style == "g" or style == "m":
            kpts = [int(x) for x in lines[3].split()]
            kpts_shift = (0, 0, 0)
            if len(lines) > 4 and coord_pattern.match(lines[4]):
                try:
                    kpts_shift = [int(x) for x in lines[4].split()]
                except:
                    pass
            return Kpoints.gamma_automatic(kpts, kpts_shift) if style == "g" \
                else Kpoints.monkhorst_automatic(kpts, kpts_shift)

        #Automatic kpoints with basis
        if num_kpts <= 0:
            style = Kpoints.supported_modes.Cartesian if style in "ck" \
                else Kpoints.supported_modes.Reciprocal
            kpts = [[float(x) for x in lines[i].split()] for i in xrange(3, 6)]
            kpts_shift = [float(x) for x in lines[6].split()]
            return Kpoints(comment=comment, num_kpts=num_kpts, style=style,
                           kpts=kpts, kpts_shift=kpts_shift)

        #Line-mode KPOINTS, usually used with band structures
        if style == "l":
            coord_type = "Cartesian" if lines[3].lower()[0] in "ck" \
                else "Reciprocal"
            style = Kpoints.supported_modes.Line_mode
            kpts = []
            labels = []
            patt = re.compile("([0-9\.\-]+)\s+([0-9\.\-]+)\s+([0-9\.\-]+)\s*!"
                              "\s*(.*)")
            for i in range(4, len(lines)):
                line = lines[i]
                m = patt.match(line)
                if m:
                    kpts.append([float(m.group(1)), float(m.group(2)),
                                 float(m.group(3))])
                    labels.append(m.group(4).strip())
            return Kpoints(comment=comment, num_kpts=num_kpts, style=style,
                           kpts=kpts, coord_type=coord_type, labels=labels)

        #Assume explicit KPOINTS if all else fails.
        style = Kpoints.supported_modes.Cartesian if style == "ck" \
            else Kpoints.supported_modes.Reciprocal
        kpts = []
        kpts_weights = []
        labels = []
        tet_number = 0
        tet_weight = 0
        tet_connections = None

        for i in xrange(3, 3 + num_kpts):
            toks = lines[i].split()
            kpts.append([float(toks[0]), float(toks[1]), float(toks[2])])
            kpts_weights.append(float(toks[3]))
            if len(toks) > 4:
                labels.append(toks[4])
            else:
                labels.append(None)
        try:
            #Deal with tetrahedron method
            if lines[3 + num_kpts].strip().lower()[0] == "t":
                toks = lines[4 + num_kpts].split()
                tet_number = int(toks[0])
                tet_weight = float(toks[1])
                tet_connections = []
                for i in xrange(5 + num_kpts, 5 + num_kpts + tet_number):
                    toks = lines[i].split()
                    tet_connections.append((int(toks[0]),
                                            [int(toks[j])
                                             for j in xrange(1, 5)]))
        except:
            pass
        return Kpoints(comment=comment, num_kpts=num_kpts, style=style,
                       kpts=kpts, kpts_weights=kpts_weights,
                       tet_number=tet_number, tet_weight=tet_weight,
                       tet_connections=tet_connections, labels=labels)'''

    def __str__(self):
        lines = []
        lines.append(self.comment)
        lines.append(str(self.num_kpts))
        lines.append(self.style)
        style = self.style.lower()[0]
        if style == "Line-mode":
            lines.append(self.coord_type)
        for i in xrange(len(self.kpts)):
            lines.append(" ".join([str(x) for x in self.kpts[i]]))
            if style == "l":
                lines[-1] += " ! " + self.labels[i]
            elif self.num_kpts > 0:
                lines[-1] += " %f" % (self.kpts_weights[i])

        #Print tetrahedorn parameters if the number of tetrahedrons > 0
        if style not in "lagm" and self.tet_number > 0:
            lines.append("Tetrahedron")
            lines.append("%d %f" % (self.tet_number, self.tet_weight))
            for sym_weight, vertices in self.tet_connections:
                lines.append("%d %d %d %d %d" % (sym_weight, vertices[0],
                                                 vertices[1], vertices[2],
                                                 vertices[3]))

        #Print shifts for automatic kpoints types if not zero.
        if self.num_kpts <= 0 and tuple(self.kpts_shift) != (0, 0, 0):
            lines.append(" ".join([str(x) for x in self.kpts_shift]))
        return "\n".join(lines)
        
class Incar(dict):
    """
    INCAR object for reading and writing INCAR files. Essentially consists of
    a dictionary with some helper functions
    """

    def __init__(self, params=dict()):
        """
        Creates an Incar object.

        Args:
            params:
                A set of input parameters as a dictionary.
        """
        super(Incar, self).__init__()
        self.update(params)

    def __setitem__(self, key, val):
        """
        Add parameter-val pair to Incar.  Warns if parameter is not in list of
        valid INCAR tags. Also cleans the parameter and val by stripping
        leading and trailing white spaces.
        """
        super(Incar, self).__setitem__(key.strip(), Incar.proc_val(key.strip(), val.strip()) if isinstance(val, basestring) else val)

    def get_string(self, sort_keys=False, pretty=False):
        """
        Returns a string representation of the INCAR.  The reason why this
        method is different from the __str__ method is to provide options for
        pretty printing.

        Args:
            sort_keys:
                Set to True to sort the INCAR parameters alphabetically.
                Defaults to False.
            pretty:
                Set to True for pretty aligned output. Defaults to False.
        """
        keys = self.keys()
        if sort_keys:
            keys = sorted(keys)
        lines = []
        for k in keys:
            if k == "MAGMOM" and isinstance(self[k], list):
                value = []
                for m, g in itertools.groupby(self[k]):
                    value.append("{}*{}".format(len(tuple(g)), m))
                lines.append([k, " ".join(value)])
            elif isinstance(self[k], list):
                lines.append([k, " ".join([str(i) for i in self[k]])])
            else:
                lines.append([k, self[k]])

        if pretty:
            return str_aligned(lines)
        else:
            return str_delimited(lines, None, " = ")

    def __str__(self):
        return self.get_string(sort_keys=True, pretty=False)

    @staticmethod
    def proc_val(key, val):
        """
        Static helper method to convert INCAR parameters to proper types, e.g.,
        integers, floats, lists, etc.

        Args:
            key:
                INCAR parameter key
            val:
                Actual value of INCAR parameter.
        """
        list_keys = ("LDAUU", "LDAUL", "LDAUJ", "LDAUTYPE", "MAGMOM")
        bool_keys = ("LDAU", "LWAVE", "LSCALU", "LCHARG", "LPLANE", "LHFCALC")
        float_keys = ("EDIFF", "SIGMA", "TIME", "ENCUTFOCK", "HFSCREEN")
        int_keys = ("NSW", "NELMIN", "ISIF", "IBRION", "ISPIN", "ICHARG", "NELM", "ISMEAR", "NPAR", "LDAUPRINT", "LMAXMIX", "ENCUT", "NSIM", "NKRED", "NUPDOWN", "ISPIND")

        def smart_int_or_float(numstr):
            if numstr.find(".") != -1 or numstr.lower().find("e") != -1:
                return float(numstr)
            else:
                return int(numstr)
        try:
            if key in list_keys:
                output = list()
                toks = val.split()

                for tok in toks:
                    m = re.match("(\d+)\*([\d\.\-\+]+)", tok)
                    if m:
                        output.extend([smart_int_or_float(m.group(2))]
                                      * int(m.group(1)))
                    else:
                        output.append(smart_int_or_float(tok))
                return output
            if key in bool_keys:
                m = re.search("^\W+([TtFf])", val)
                if m:
                    if m.group(1) == "T" or m.group(1) == "t":
                        return True
                    else:
                        return False
                raise ValueError(key + " should be a boolean type!")

            if key in float_keys:
                return float(val)

            if key in int_keys:
                return int(val)

        except:
            return val.capitalize()

        return val.capitalize()

    def __add__(self, other):
        """
        Add all the values of another INCAR object to this object.
        Facilitates the use of "standard" INCARs.
        """
        params = {k: v for k, v in self.items()}
        for k, v in other.items():
            if k in self and v != self[k]:
                raise ValueError("Incars have conflicting values!")
            else:
                params[k] = v
        return Incar(params)

class XML_Output(Output):
    def __init__(self, filename, ionic_step_skip=None, parse_dos=True, parse_eigen=True, parse_projected_eigen=False, **kwargs):
        Output.__init__(self)
        self.location = filename
        self.data = open(filename).read()
        self.data = re.sub('[\x00-\x09\x0B-\x1F]', '', self.data)

        self._handler = VasprunHandler( filename, parse_dos=parse_dos, parse_eigen=parse_eigen, parse_projected_eigen=parse_projected_eigen )
        if ionic_step_skip is None:
            try: self._parser = xml.sax.parseString(self.data, self._handler)
            except Exception, ex: raise RuntimeError('VASP output corrupted or not finalized: %s' % ex)
        else:
            #remove parts of the xml file and parse the string
            steps = self.data.split("<calculation>")
            new_steps = steps[::int(ionic_step_skip)]
            #add the last step from the run
            if steps[-1] != new_steps[-1]:
                new_steps.append(steps[-1])
            try: self._parser = xml.sax.parseString("<calculation>".join(new_steps), self._handler)
            except Exception: raise RuntimeError('VASP output corrupted or not finalized!')
        for k in ["vasp_version", "incar",
                "parameters", "potcar_symbols",
                "kpoints", "actual_kpoints", "structures",
                "actual_kpoints_weights", "dos_energies",
                "e_eigvals", "tdos", "pdos", "e_last",
                "ionic_steps", "dos_error",
                "dynmat", "finished"]:
            setattr(self, k, getattr(self._handler, k))
            
        self.converged = len(self.structures) - 2 < self.parameters["NSW"] or self.parameters["NSW"] == 0 # True if a relaxation run is converged. Always True for a static run
        self.energy = self.ionic_steps[-1]["electronic_steps"][-1]["e_wo_entrp"]/Hartree # Final energy from the vasp run (note: e_fr_energy vs. e_0_energy)        
        #self.eigenvalue_band_properties = self.get_eigenvalue_band_properties()
        self.prog = 'VASP ' + self.vasp_version
        self.input = str(self.incar)
        
        # basis sets
        self.potcar_sequence = [s.split()[1] for s in self.potcar_symbols]
        self.potcar_sequence = [s.split("_")[0].encode('ascii') for s in self.potcar_sequence]
        self.bs = {'ps': {}}
        for n, s in enumerate(self.potcar_sequence):
            self.bs['ps'].update( {s: self.potcar_symbols[n].encode('ascii')} )
        
        # method
        self.method = self.get_method()
        
        # phonons
        if self.dynmat['freqs']:
            self.phonons = {'0 0 0': self.dynmat['freqs'] }
            self.ph_eigvecs = {'0 0 0': self.dynmat['eigvecs'] }
            if len(self.ph_eigvecs['0 0 0'])/3 != len(self.structures[-1]['atoms']): raise RuntimeError('Number of frequencies is not equal to 3 * number of atoms!')

        if self.e_last is None:
            self.warning('Attention: Fermi energy is missing! Electronic properties are omitted.')
            self.e_eigvals = None
        else:
            # electronic properties
            self.complete_dos = self.get_complete_dos()
            
            # format k-points
            oldform = self.e_eigvals.keys()
            ix = []
            for i in oldform:
                ix.extend( map(abs, list(i)) )
            try: d = min(filter(None, ix))
            except ValueError: d = 1 # empty sequence
            for i in oldform:
                newform = ' '.join( map( str, map(lambda x: int(x/d), list(i)) ) )
                
                # scaled: E - Ef
                self.e_eigvals[newform] = {  'alpha': map(lambda x: round(x - self.e_last, 2), self.e_eigvals[i]['alpha'])  }
                if 'beta' in self.e_eigvals[i]: self.e_eigvals[newform]['beta'] = map(lambda x: round(x - self.e_last, 2), self.e_eigvals[i]['beta'])
                
                del self.e_eigvals[i]        

    @staticmethod
    def fingerprints(test_string):
        if '<modeling>' in test_string: return True
        else: return False

    def get_complete_dos(self):
        #final_struct = [i[0] for i in self.structures[-1]['atoms']]
        #pdoss = {final_struct[i]: pdos for i, pdos in enumerate(self.pdos)}
        #return [self.tdos, pdoss]
        
        if self.dos_error:
            self.warning(self.dos_error)
            return None
        
        alpha_beta = self.tdos[1]['alpha']
        if 'beta' in self.tdos[1]: alpha_beta = [sum(s) for s in zip(alpha_beta, self.tdos[1]['beta'])]
        dos_obj = {'x': map(lambda x: round(x - self.e_last, 2), self.tdos[0]), 'total': alpha_beta} # scaled: E - Ef
        dos_obj.update(self.pdos)
        return dos_obj

    '''def get_eigenvalue_band_properties(self):
        """
        Band properties from the eigenvalues as a tuple,
        (band gap, cbm, vbm, is_band_gap_direct).
        """
        vbm = -float("inf")
        vbm_kpoint = None
        cbm = float("inf")
        cbm_kpoint = None
        for k, val in self.eigenvalues.items():
            for (eigenval, occu) in val:
                if occu > 1e-8 and eigenval > vbm:
                    vbm = eigenval
                    vbm_kpoint = k[0]
                elif occu <= 1e-8 and eigenval < cbm:
                    cbm = eigenval
                    cbm_kpoint = k[0]
        return cbm - vbm, cbm, vbm, vbm_kpoint == cbm_kpoint'''
        
    def get_method(self):
        method = {'H': None, 'tol': None, 'k': None, 'spin': None, 'technique': {}, 'lockstate': None}
        
        # Hamiltonians: Hubbard U method
        if self.incar.get("LDAU", False):            
            method['H'] = 'LSDA+U'
            
            ldautype = self.incar.get("LDAUTYPE", self.parameters.get("LDAUTYPE"))[0]
            if ldautype == 2: method['H'] += '(std.)'
            elif ldautype == 1: method['H'] += '(Liecht.)'
            elif ldautype == 4: method['H'] = 'LDA+U(Liecht.)'
            else: method['H'] += '(type %s)' % ldautype
            
            us = self.incar.get("LDAUU", self.parameters.get("LDAUU")) # the effective on-site Coulomb interaction parameters
            js = self.incar.get("LDAUJ", self.parameters.get("LDAUJ")) # the effective on-site Exchange interaction parameters

            if len(us) != len(self.potcar_sequence): raise RuntimeError("Length of Hubbard U value parameters and atomic symbols are mismatched")
            
            atom_hubbard = {}
            for i in range(len(self.potcar_sequence)):
                if us[i] == 0 and js[i] == 0: continue
                repr = '%s/%s' % (round(us[i], 1), round(js[i], 1))
                if self.potcar_sequence[i] in atom_hubbard and atom_hubbard[ self.potcar_sequence[i] ] != repr:
                    n = 1
                    while 1:
                        try: atom_hubbard[ self.potcar_sequence[i] + str(n) ]
                        except KeyError:
                            atom_hubbard[ self.potcar_sequence[i] + str(n) ] = repr
                            break
                        n += 1
                else: atom_hubbard[ self.potcar_sequence[i] ] = repr
            
            for atom in sorted(atom_hubbard.keys()):
                method['H'] += ' %s:%s' % (atom, atom_hubbard[atom])
        
        # Hamiltonians: HF admixing
        elif self.parameters.get("LHFCALC", False):
            screening = self.incar.get("HFSCREEN", self.parameters.get("HFSCREEN"))
            if screening == 0.0: method['H'] = "PBE-GGA(+25%HF)/PBE-GGA" # like in CRYSTAL, todo
            elif screening == 0.2: method['H'] = "HSE06"
            else: method['H'] = "HSE %d%%screen" % round(screening*100)
        
        # Regular GGA
        else: method['H'] = "GGA"
            
        # tolerances
        method['tol'] = 'cutoff %seV' % int(self.parameters['ENMAX'])
        
        # Spin
        method['spin'] = True if self.incar.get("ISPIN", 1) == 2 else False
        
        # K-points
        if not self.kpoints.kpts: kpoints = 'x' + str(len(self.actual_kpoints))
        else: kpoints = 'x'.join(map(str, self.kpoints.kpts[0]))
        method['k'] = kpoints
        
        return method

class VasprunHandler(xml.sax.handler.ContentHandler):
    """
    Sax handler for vasprun.xml. Attributes are mirrored into Vasprun object.
    Generally should not be initiatized on its own.
    """
    def __init__(self, filename, parse_dos=True, parse_eigen=True, parse_projected_eigen=False):
        self.filename = filename
        self.parse_dos = parse_dos
        self.parse_eigen = parse_eigen
        self.parse_projected_eigen = parse_projected_eigen

        self.step_count = 0
        # variables to be filled
        self.vasp_version = None
        self.incar = Incar()
        self.parameters = Incar()
        self.potcar_symbols = []
        self.atomic_symbols = []
        self.kpoints = Kpoints()
        self.actual_kpoints = []
        self.actual_kpoints_weights = []
        self.dos_energies = None
        self.dynmat = {'freqs':[], 'eigvecs':[]}
        self.finished = False

        #  will  be  {(spin, kpoint index): [[energy, occu]]}
        self.e_eigvals = {}

        #{(spin, kpoint_index, band_index, atom_ind, orb):float}
        #self.projected_eigenvalues = {}

        self.tdos = {}
        #self.idos = {}
        self.pdos = {}
        self.e_last = None
        self.ionic_steps = []  # should be a list of dict
        self.structures = []
        #self.lattice_rec = []
        self.stress = []

        self.input_read = False
        self.read_structure = False
        self.read_rec_lattice = False
        self.read_calculation = False
        self.read_eigen = False
        self.read_dynmat = False
        #self.read_projected_eigen = False
        self.read_dos = False
        self.in_efermi = False
        self.read_atoms = False
        self.read_lattice = False
        self.read_positions = False
        self.incar_param = None

        # Intermediate variables
        self.dos_energies_val = []
        self.dos_val = []
        #self.idos_val = []
        self.raw_data = []

        # will be set to true if there is an error parsing the Dos.
        self.dos_error = False
        self.state = defaultdict(bool)
        
    def parse_parameters(self, val_type, val):
        """
        Helper function to convert a Vasprun parameter into the proper type.
        Boolean, int and float types are converted.

        Args:
            val_type : Value type parsed from vasprun.xml.
            val : Actual string value parsed for vasprun.xml.
        """
        if val_type == "logical":
            return (val == "T")
        elif val_type == "int":
            return int(val)
        elif val_type == "string":
            return val.strip()
        else:
            return float(val)

    def parse_v_parameters(self, val_type, val, filename, param_name):
        """
        Helper function to convert a Vasprun array-type parameter into the proper
        type. Boolean, int and float types are converted.

        Args:
            val_type:
                Value type parsed from vasprun.xml.
            val:
                Actual string value parsed for vasprun.xml.
            filename:
                Fullpath of vasprun.xml. Used for robust error handling.  E.g.,
                if vasprun.xml contains \*\*\* for some Incar parameters, the code
                will try to read from an INCAR file present in the same directory.
            param_name:
                Name of parameter.

        Returns:
            Parsed value.
        """
        if val_type == "logical":
            val = [True if i == "T" else False for i in val.split()]
        elif val_type == "int":
            try:
                val = [int(i) for i in val.split()]
            except ValueError:
                # Fix for stupid error in vasprun sometimes which displays
                # LDAUL/J as 2****
                val = parse_from_incar(filename, param_name)
                if val is None:
                    raise IOError("Error in parsing vasprun.xml")
        elif val_type == "string":
            val = [i for i in val.split()]
        else:
            try:
                val = [float(i) for i in val.split()]
            except ValueError:
                # Fix for stupid error in vasprun sometimes which displays
                # MAGMOM as 2****
                val = parse_from_incar(filename, param_name)
                if val is None:
                    raise IOError("Error in parsing vasprun.xml")
        return val

    def startElement(self, name, attributes):
        self.state[name] = attributes.get("name", True)
        self.read_val = False

        # Nested if loops makes reading much faster.
        if not self.input_read:  # reading input parameters
            self._init_input(name, attributes)
        else:  # reading structures, eigenvalues etc.
            self._init_calc(name, attributes)
            
        if self.read_val:
            self.val = StringIO.StringIO()

    def _init_input(self, name, attributes):
        state = self.state
        if (name == "i" or name == "v") and (state["incar"] or state["parameters"]):
            self.incar_param = attributes["name"]
            self.param_type = "float" if "type" not in attributes else attributes["type"]
            self.read_val = True
        elif name == "v" and state["kpoints"]:
            self.read_val = True
        elif name == "generation" and state["kpoints"]:
            self.kpoints.comment = "Kpoints from vasprun.xml"
            self.kpoints.num_kpts = 0
            self.kpoints.style = attributes["param"]
            self.kpoints.kpts = []
            self.kpoints.kpts_shift = [0, 0, 0]
        elif name == "c" and (state["array"] == "atoms" or state["array"] == "atomtypes"):
            self.read_val = True
        elif name == "i" and state["i"] == "version" and state["generator"]:
            self.read_val = True

    def _init_calc(self, name, attributes):
        state = self.state
        if self.read_structure and name == "v":
            if state["varray"] == "basis":
                self.read_lattice = True
            elif state["varray"] == "positions":
                self.read_positions = True
            elif state["varray"] == "rec_basis":
                self.read_rec_lattice = True
        elif self.read_calculation:
            if name == "i" and state["scstep"]:
                logger.debug("Reading scstep...")
                self.read_val = True
            elif name == "v" and (state["varray"] == "forces" or state["varray"] == "stress"):
                self.read_positions = True
            elif name == "dos" and self.parse_dos:
                logger.debug("Reading dos...")
                self.read_dos = True
            elif name == "dynmat":                
                self.read_dynmat = True
            elif name == "eigenvalues" and self.parse_eigen and not state["projected"]:
                logger.debug("Reading eigenvalues. Projected = {}".format(state["projected"]))
                self.read_eigen = True
            #elif name == "eigenvalues" and self.parse_projected_eigen and state["projected"]:
            #    logger.debug("Reading projected eigenvalues...")
            #    self.projected_eigen = {}
            #    self.read_projected_eigen = True
            #elif self.read_eigen or self.read_projected_eigen:
            elif self.read_eigen:
                if name == "r" and state["set"]:
                    self.read_val = True
                elif name == "set" and "comment" in attributes:
                    comment = attributes["comment"]
                    state["set"] = comment
                    if comment.startswith("spin"):
                        self.eigen_spin = 'alpha' if state["set"] in ["spin 1", "spin1"] else 'beta'
                        logger.debug("Reading spin {}".format(self.eigen_spin))
                    elif comment.startswith("kpoint"):
                        self.eigen_kpoint = int(comment.split(" ")[1])
                        logger.debug("Reading kpoint {}".format(self.eigen_kpoint))
                    elif comment.startswith("band"):
                        self.eigen_band = int(comment.split(" ")[1])
                        logger.debug("Reading band {}".format(self.eigen_band))
            elif self.read_dos:
                if (name == "i" and state["i"] == "efermi") or (name == "r" and state["set"]):
                    self.read_val = True
                elif name == "set" and "comment" in attributes:
                    comment = attributes["comment"]
                    state["set"] = comment
                    if state["partial"]:
                        if comment.startswith("ion"):
                            self.pdos_ion = int(comment.split(" ")[1])
                        elif comment.startswith("spin"):
                            self.pdos_spin = 'alpha' if state["set"] in ["spin 1", "spin1"] else 'beta'
            elif self.read_dynmat:
                if state["varray"] == False:
                    self.read_val = True
                elif state["varray"] == "eigenvectors":
                    self.read_val = True
                    
        if name == "calculation":
            self.step_count += 1
            self.scdata = []
            self.read_calculation = True
        elif name == "scstep":
            self.scstep = {}
        elif name == "structure":
            self.latticestr = StringIO.StringIO()
            self.latticerec = StringIO.StringIO()
            self.posstr = StringIO.StringIO()
            self.read_structure = True
        elif name == "varray" and state["varray"] in ["forces", "stress"]:
            self.posstr = StringIO.StringIO()

    def characters(self, data):
        if self.read_val:
            self.val.write(data)
        if self.read_lattice:
            self.latticestr.write(data)
        elif self.read_positions:
            self.posstr.write(data)
        elif self.read_rec_lattice:
            self.latticerec.write(data)
        elif self.read_rec_lattice:
            self.latticerec.write(data)

    def _read_input(self, name):
        state = self.state
        if name == "i":
            if state["incar"]:
                self.incar[self.incar_param] = self.parse_parameters(self.param_type, self.val.getvalue().strip())
            elif state["parameters"]:
                self.parameters[self.incar_param] = self.parse_parameters(self.param_type, self.val.getvalue().strip())
            elif state["generator"] and state["i"] == "version":
                self.vasp_version = self.val.getvalue().strip()
            self.incar_param = None
        elif name == "set":
            if state["array"] == "atoms":
                self.atomic_symbols = self.atomic_symbols[::2]
                self.atomic_symbols = [sym if sym != "X" else "Xe"for sym in self.atomic_symbols]
            elif state["array"] == "atomtypes":
                self.potcar_symbols = self.potcar_symbols[4::5]
                self.input_read = True
        elif name == "c":
            if state["array"] == "atoms":
                self.atomic_symbols.append(self.val.getvalue().strip())
            elif state["array"] == "atomtypes":
                self.potcar_symbols.append(self.val.getvalue().strip())
        elif name == "v":
            if state["incar"]:
                self.incar[self.incar_param] = self.parse_v_parameters(self.param_type, self.val.getvalue().strip(), self.filename, self.incar_param)
                self.incar_param = None
            elif state["parameters"]:
                self.parameters[self.incar_param] = self.parse_v_parameters(self.param_type, self.val.getvalue().strip(), self.filename, self.incar_param)
            elif state["kpoints"]:
                if state["varray"] == "kpointlist":
                    self.actual_kpoints.append([float(x) for x in self.val.getvalue().split()])
                if state["varray"] == "weights":
                    val = float(self.val.getvalue())
                    self.actual_kpoints_weights.append(val)
                if state["v"] == "divisions":
                    self.kpoints.kpts = [[int(x) for x in self.val.getvalue().split()]]
                elif state["v"] == "usershift":
                    self.kpoints.kpts_shift = [float(x) for x in self.val.getvalue().split()]
                elif state["v"] == "genvec1" or state["v"] == "genvec2" or state["v"] == "genvec3" or state["v"] == "shift":
                    setattr(self.kpoints, state["v"], [float(x) for x in self.val.getvalue().split()])

    def _read_calc(self, name):
        state = self.state
        if name == "i" and state["scstep"]:
            self.scstep[state["i"]] = float(self.val.getvalue())
        elif name == "scstep":
            self.scdata.append(self.scstep)
            logger.debug("Finished reading scstep...")
        elif name == "varray" and state["varray"] == "forces":
            self.forces = array([float(x) for x in self.posstr.getvalue().split()])
            self.forces.shape = (len(self.atomic_symbols), 3)
            self.read_positions = False
        elif name == "varray" and state["varray"] == "stress":
            self.stress = array([float(x) for x in self.posstr.getvalue().split()])
            self.stress.shape = (3, 3)
            self.read_positions = False
        elif name == "calculation":
            self.ionic_steps.append({"electronic_steps": self.scdata,
                                     "structure": self.structures[-1],
                                     "forces": self.forces,
                                     "stress": self.stress})
            self.read_calculation = False

    def _read_structure(self, name):
        if name == "v":
            self.read_positions = False
            self.read_lattice = False
            self.read_rec_lattice = False
        elif name == "structure":
            self.lattice = array([float(x) for x in self.latticestr.getvalue().split()])
            self.lattice.shape = (3, 3)
            pos = array([float(x) for x in self.posstr.getvalue().split()])
            pos.shape = (len(self.atomic_symbols), 3)
            
            # de-fractionize
            xyz_atoms = []
            for n, i in enumerate(pos):
                R = dot( array([i[0], i[1], i[2]]), self.lattice )
                xyz_atoms.append( [self.atomic_symbols[n].encode('ascii'), R[0], R[1], R[2]] )
            self.structures.append({'cell': cell_to_cellpar(self.lattice).tolist(), 'atoms': xyz_atoms, 'periodicity': 3})
            
            #self.lattice_rec = [float(x) for x in self.latticerec.getvalue().split()]
            self.read_structure = False
            self.read_positions = False
            self.read_lattice = False
            self.read_rec_lattice = False
            
    def _read_dynmat(self, name):
        state = self.state
        
        if name == "v" and state["varray"] == False:
            freqs = [float(x) for x in self.val.getvalue().split()]            
            for i in range(len(freqs)):
                if freqs[i]<0: freqs[i] = math.sqrt( -freqs[i] )*VaspToCm
                else: freqs[i] = -math.sqrt( freqs[i] )*VaspToCm
            freqs.reverse()
            self.dynmat["freqs"] = freqs
            
        elif name == "v" and state["varray"] == "eigenvectors":
            self.dynmat["eigvecs"].insert(0, [float(x) for x in self.val.getvalue().split()])
            
        elif name == "dynmat":
            self.read_dynmat = False
            
    def _read_dos(self, name):
        state = self.state
        try:
            if name == "i" and state["i"] == "efermi":
                self.e_last = float(self.val.getvalue().strip())
            elif name == "r" and state["total"] and str(state["set"]).startswith("spin"):
                tok = self.val.getvalue().split()
                self.dos_energies_val.append(float(tok[0]))
                self.dos_val.append(float(tok[1]))
                #self.idos_val.append(float(tok[2]))
            elif name == "r" and state["partial"] and str(state["set"]).startswith("spin"):
                tok = self.val.getvalue().split()
                self.raw_data.append([float(i) for i in tok[1:]])
            elif name == "set":
                if state["total"] and str(state["set"]).startswith("spin"):
                    spin = 'alpha' if state["set"] == "spin 1" else 'beta'
                    self.tdos[spin] = self.dos_val
                    #self.idos[spin] = self.dos_val
                    self.dos_energies = self.dos_energies_val
                    self.dos_energies_val = []
                    self.dos_val = []
                    #self.idos_val = []
                elif state["partial"] and str(state["set"]).startswith("spin"):
                    spin = 'alpha' if state["set"] == "spin 1" else 'beta'
                    self.norbitals = len(self.raw_data[0])
                    for i in xrange(self.norbitals):
                        self.pdos[(self.pdos_ion, i, spin)] = [row[i] for row in self.raw_data]
                    self.raw_data = []
            elif name == "partial":
                atomic_pdos = {}
                for k, v in self.pdos.iteritems():
                    atom = self.atomic_symbols[k[0]-1].encode('ascii')
                    if not atom in atomic_pdos:
                        atomic_pdos[atom] = v
                    else:
                        atomic_pdos[atom] = [sum(s) for s in zip(atomic_pdos[atom], v)]
                self.pdos = atomic_pdos
            elif name == "total":
                self.tdos = [self.dos_energies, self.tdos]
                #self.idos = [self.e_last, self.dos_energies, self.idos]
            elif name == "dos":
                self.read_dos = False
        except Exception, ex:
            self.dos_error = str(ex)

    def _read_eigen(self, name):
        state = self.state
        if name == "r" and str(state["set"]).startswith("kpoint"):
            tok = self.val.getvalue().split()
            #self.raw_data.append([float(i) for i in tok])
            self.raw_data.append(round(float(tok[0]), 2))
        elif name == "set" and str(state["set"]).startswith("kpoint"):
            try: k = tuple( self.actual_kpoints[self.eigen_kpoint - 1] )
            except IndexError: raise RuntimeError('Unmatched k-point index for a found eigenvalue!')

            if k in self.e_eigvals:
                self.e_eigvals[k]['beta'] = self.raw_data
            else:
                self.e_eigvals[k] = {'alpha': self.raw_data}
            self.raw_data = []
        elif name == "eigenvalues":
            logger.debug("Finished reading eigenvalues. No. eigen = {}".format(len(self.e_eigvals)))
            self.read_eigen = False

    def endElement(self, name):
        if not self.input_read:
            self._read_input(name)
        elif name == "modeling":
            self.finished = True
        else:
            if self.read_structure:
                self._read_structure(name)
            elif self.read_dos:
                self._read_dos(name)
            elif self.read_eigen:
                self._read_eigen(name)
            elif self.read_dynmat:
                self._read_dynmat(name)
            #elif self.read_projected_eigen:
            #    self._read_projected_eigen(name)
            elif self.read_calculation:
                self._read_calc(name)
        self.state[name] = False
