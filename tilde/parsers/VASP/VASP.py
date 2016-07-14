
# VASP vasprun.xml parser
# based on pymatgen iovasp module (author: Shyue Ping Ong)
# Author: Evgeny Blokhin

from __future__ import division

import os, sys, re, math
import itertools
import traceback
import xml.sax
from collections import defaultdict
import six

from numpy import dot, array, zeros

from ase.geometry import cell_to_cellpar
from ase.data import atomic_numbers, chemical_symbols
from ase.atoms import Atoms
from ase.units import Hartree

from tilde.parsers import Output
from tilde.core.electron_structure import Edos
from tilde.core.constants import Constants


def str_delimited(results, header=None, delimiter="\t"):
    """ Given a tuple of tuples, generate a delimited string form in a table-like format. """
    returnstr = ""
    if header is not None:
        returnstr += delimiter.join(header) + "\n"
    return returnstr + "\n".join([delimiter.join([str(m) for m in result]) for result in results])

def str_aligned(results, header=None):
    """ Given a tuple, generate a nicely aligned string form  in a table-like format. """
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
            raise ValueError("For fully automatic or automatic gamma or monkhorst kpoints, only a single line for the number of divisions is allowed.")

        #self.comment = comment

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
        return Kpoints("Fully automatic kpoint scheme", 0, style=Kpoints.supported_modes.Automatic, kpts=[[subdivisions]])

    @staticmethod
    def gamma_automatic(kpts=(1, 1, 1), shift=(0, 0, 0)):
        return Kpoints("Automatic kpoint scheme", 0, Kpoints.supported_modes.Gamma, kpts=[kpts], kpts_shift=shift)

    @staticmethod
    def monkhorst_automatic(kpts=(2, 2, 2), shift=(0, 0, 0)):
        return Kpoints("Automatic kpoint scheme", 0, Kpoints.supported_modes.Monkhorst, kpts=[kpts], kpts_shift=shift)

    @staticmethod
    def automatic_density(structure, kppa):
        latt = structure.lattice
        lengths = latt.abc
        ngrid = kppa // structure.num_sites

        # FIXME: 1/3 == 0 in Python 2, hence mult is always equal to one. Possible bug?
        mult = (ngrid * lengths[0] * lengths[1] * lengths[2]) ** (1 / 3)

        num_div = [int(round(1 / lengths[i] * mult)) for i in range(3)]
        #ensure that numDiv[i] > 0
        num_div = [i if i > 0 else 1 for i in num_div]

        angles = latt.angles
        hex_angle_tol = 5  # in degrees
        hex_length_tol = 0.01  # in angstroms
        right_angles = [i for i in range(3)
                        if abs(angles[i] - 90) < hex_angle_tol]
        hex_angles = [i for i in range(3)
                      if abs(angles[i] - 60) < hex_angle_tol or
                      abs(angles[i] - 120) < hex_angle_tol]

        is_hexagonal = (len(right_angles) == 2 and len(hex_angles) == 1
                        and abs(lengths[right_angles[0]] -
                                lengths[right_angles[1]]) < hex_length_tol)

        style = Kpoints.supported_modes.Gamma
        if not is_hexagonal:
            num_div = [i + i % 2 for i in num_div]
            style = Kpoints.supported_modes.Monkhorst
        comment = "KPOINTS with grid density = {0} / atom".format(kppa)
        num_kpts = 0
        return Kpoints(comment, num_kpts, style, [num_div], [0, 0, 0])

    def __str__(self):
        lines = []
        lines.append(str(self.num_kpts))
        lines.append(self.style)
        style = self.style.lower()[0]
        if style == "Line-mode":
            lines.append(self.coord_type)
        for i in range(len(self.kpts)):
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
    def __init__(self, params=dict()):
        super(Incar, self).__init__()
        self.update(params)

    def __setitem__(self, key, val):
        super(Incar, self).__setitem__(key.strip(), Incar.proc_val(key.strip(), val.strip()) if isinstance(val, six.string_types) else val)

    def get_string(self, sort_keys=False, pretty=False):
        keys = self.keys()
        if sort_keys:
            keys = sorted(keys)
        lines = []
        for k in keys:
            if k == "MAGMOM" and isinstance(self[k], list):
                value = []
                for m, g in itertools.groupby(self[k]):
                    value.append("{0}*{1}".format(len(tuple(g)), m))
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
                        output.extend([smart_int_or_float(m.group(2))] * int(m.group(1)))
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
                raise ValueError("%s should be a boolean type!" % key)

            if key in float_keys:
                return float(val)

            if key in int_keys:
                return int(val)

        except: return val.capitalize()

        return val.capitalize()

class XML_Output(Output):
    def __init__(self, filename, **kwargs):
        Output.__init__(self, filename)
        self.related_files.append(filename)
        self._handler = VasprunHandler()

        # TODO: this will be very slow
        # use iterative parser here?
        filestring = open(filename).read()

        illegal_unichrs = [ (0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
                            (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
                            (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
                            (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
                            (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
                            (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
                            (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
                            (0x10FFFE, 0x10FFFF) ]
        illegal_ranges = ["%s-%s" % (six.unichr(low), six.unichr(high)) for (low, high) in illegal_unichrs if low < sys.maxunicode]
        illegal_xml_re = re.compile(u'[%s]' % u''.join(illegal_ranges))
        filestring = illegal_xml_re.sub('', filestring)

        try: xml.sax.parseString(six.b(filestring), self._handler)
        except:
        #     #exc_type, exc_value, exc_tb = sys.exc_info()
            raise RuntimeError('VASP output corrupted or not correctly finalized!')  #+ "".join(traceback.format_exception( exc_type, exc_value, exc_tb )))

        # TODO: reorganize
        for k in ["vasp_version", "incar",
                "parameters", "bsseq", "potcar_sequence", "potcar_symbols",
                "kpoints", "actual_kpoints", "structures",
                "actual_kpoints_weights", "dos_energies",
                "eigvals", "tdos", "pdos", "e_last",
                "tresholds", "dos_error",
                "dynmat", "finished"]:
            setattr(self, k, getattr(self._handler, k))

        try: self.info['energy'] = self.tresholds[-1][-1] # NB: e_fr_energy vs. e_0_energy
        except IndexError: pass # for unphysical cases

        self.info['framework'] = 0x2
        self.info['prog'] = self.vasp_version
        self.info['finished'] = self.finished
        self.info['input'] = str(self.incar)

        self.electrons['basis_set'] = self.potcar_symbols
        self.structures[-1].new_array('bs', self.bsseq, int)

        self.set_method()

        # phonons
        if self.dynmat['freqs']:
            self.phonons['modes'] = {'0 0 0': self.dynmat['freqs'] }
            self.phonons['ph_eigvecs'] = {'0 0 0': self.dynmat['eigvecs'] }
            if len(self.phonons['ph_eigvecs']['0 0 0'])/3 != len(self.structures[-1]): raise RuntimeError('Number of frequencies is not equal to 3 * number of atoms!')

            self.phonons['dfp_magnitude'] = self.incar.get("POTIM", False)
            if not self.phonons['dfp_magnitude']:
                self.phonons['dfp_magnitude'] = 0.02 # Standard phonon displacement in VASP for DFP method

        # electronic properties
        self.info['ansatz'] = 0x2

        if self.e_last is None:
            self.warning('Electronic properties are not found!')
        else:
            if self.dos_error:
                self.warning('Error in DOS: ' + self.dos_error)
            else:
                # spins are merged: TODO
                alpha_beta = self.tdos[1]['alpha']
                if 'beta' in self.tdos[1]: alpha_beta = [sum(s) for s in zip(alpha_beta, self.tdos[1]['beta'])]
                self.electrons['dos'] = {'x': list(map(lambda x: round(x - self.e_last, 2), self.tdos[0])), 'total': alpha_beta} # scaled: E - Ef
                self.electrons['dos'].update(self.pdos)
                self.electrons['dos'] = Edos(self.electrons['dos'])

            # format k-points
            '''oldform = self.eigvals.keys()
            ix = []
            for i in oldform:
                ix.extend( map(abs, list(i)) )
            try: d = min(filter(None, ix))
            except ValueError: d = 1 # empty sequence
            for i in oldform:
                newform = ' '.join( map( str, map(lambda x: int(x/d), list(i)) ) )

                # scaled: E - Ef
                self.electrons['eigvals'][newform] = {  'alpha': map(lambda x: round(x - self.e_last, 2), self.eigvals[i]['alpha'])  }
                if 'beta' in self.eigvals[i]: self.electrons['eigvals'][newform]['beta'] = map(lambda x: round(x - self.e_last, 2), self.eigvals[i]['beta'])

                del self.eigvals[i]'''

        if not filename.endswith('.xml'): # special filenames treatment
            cur_folder = os.path.dirname(filename)
            cur_file =   os.path.basename(filename)
            if cur_file in ['vasprun.xml.bands', 'vasprun.xml.static', 'vasprun.xml.relax1', 'vasprun.xml.relax2']:
                ext = cur_file.split('.')[-1]
                for check in [ 'CHG', 'CHGCAR', 'CONTCAR', 'DOSCAR', 'EIGENVAL', 'OUTCAR', 'POSCAR']:
                    try_file = os.path.join(cur_folder, check + '.' + ext + '.bz2')
                    if os.path.exists(try_file): self.related_files.append(try_file)

    @staticmethod
    def fingerprints(test_string):
        if '<i name="program" type="string">vasp' in test_string: return True
        else: return False

    def set_method(self):
        # Hamiltonians: Hubbard U method
        if self.incar.get("LDAU", False): # TODO check on top of other xc!
            self.info['H'] = 'GGA+U'

            ldautype = self.incar.get("LDAUTYPE", self.parameters.get("LDAUTYPE"))[0]
            if ldautype == 2: self.info['H'] += '(std.)'
            elif ldautype == 1: self.info['H'] += '(Liecht.)'
            elif ldautype == 4: self.info['H'] = 'LDA+U(Liecht.)'
            else: self.info['H'] += '(type %s)' % ldautype

            us = self.incar.get("LDAUU", self.parameters.get("LDAUU")) # the effective on-site Coulomb interaction parameters
            js = self.incar.get("LDAUJ", self.parameters.get("LDAUJ")) # the effective on-site Exchange interaction parameters

            if len(us) != len(self.potcar_sequence): raise RuntimeError("Length of Hubbard U value parameters and atomic symbols are mismatched")

            atom_hubbard = {}
            for i in range(len(self.potcar_sequence)):
                if us[i] == 0 and js[i] == 0: continue
                repr = '%s/%s' % (round(us[i], 1), round(js[i], 1))
                if self.potcar_sequence[i] in atom_hubbard and atom_hubbard[ self.potcar_sequence[i] ] != repr:
                    n = 1
                    while True:
                        try: atom_hubbard[ self.potcar_sequence[i] + str(n) ]
                        except KeyError:
                            atom_hubbard[ self.potcar_sequence[i] + str(n) ] = repr
                            break
                        n += 1
                else: atom_hubbard[ self.potcar_sequence[i] ] = repr

            for atom in sorted(atom_hubbard.keys()):
                self.info['H'] += ' %s:%s' % (atom, atom_hubbard[atom])

            self.info['H_types'].append(0x6)

        # Hamiltonians: HF admixing
        elif self.parameters.get("LHFCALC", False):
            screening = self.incar.get("HFSCREEN", self.parameters.get("HFSCREEN"))
            if screening == 0.0: self.info['H'] = "PBE0"
            elif screening == 0.2:
                self.info['H'] = "HSE06"
            else:
                self.info['H'] = "HSE06 %.2f" % screening

            self.info['H_types'].extend([0x2, 0x4])

        # Hamiltonians: GGA
        else:
            self.info['H'] = "PBE" # TODO GGA options
            self.info['H_types'].append(0x2)

        # tolerances
        self.info['tol'] = 'cutoff %seV' % int(self.parameters['ENMAX'])

        # Spin
        if self.incar.get("ISPIN", 1) == 2: self.info['spin'] = True

        # K-points
        if not self.kpoints.kpts: kpoints = 'x' + str(len(self.actual_kpoints))
        else: kpoints = 'x'.join(map(str, self.kpoints.kpts[0]))
        self.info['k'] = kpoints

class VasprunHandler(xml.sax.handler.ContentHandler):
    """ Sax handler for vasprun.xml. Attributes are mirrored into Vasprun object. """
    def __init__(self):

        # variables to be filled
        self.vasp_version = None
        self.finished = 0x2 # if we are here, we are always correct
        self.incar = Incar()
        self.parameters = Incar()
        self.bsseq = []
        self.potcar_sequence = []
        self.potcar_symbols = []
        self.atomic_symbols = []
        self.kpoints = Kpoints()
        self.actual_kpoints = []
        self.actual_kpoints_weights = []
        self.dos_energies = None
        self.dynmat = {'freqs':[], 'eigvecs':[]}

        # will be {(spin, kpoint index): [[energy, occu]]}
        self.eigvals = {}

        self.tdos = {}
        #self.idos = {}
        self.pdos = {}
        self.e_last = None
        #self.ionic_steps = [] # should be a list of dict
        self.tresholds = []
        self.structures = []
        #self.lattice_rec = []
        #self.forces = []
        #self.stress = []

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

        # will be set to true if there is an error parsing the Dos
        self.dos_error = False
        self.state = defaultdict(bool)

    def parse_parameters(self, val_type, val):
        """ Helper function to convert a Vasprun parameter into the proper type."""
        if val_type == "logical":
            return (val == "T")
        elif val_type == "int":
            return int(val)
        elif val_type == "string":
            return val.strip()
        else:
            return float(val)

    def parse_v_parameters(self, val_type, val, param_name):
        """ Helper function to convert a Vasprun array-type parameter into the proper type. """
        if val_type == "logical":
            val = [True if i == "T" else False for i in val.split()]
        elif val_type == "int":
            try:
                val = [int(i) for i in val.split()]
            except ValueError:
                # Stupid error in vasprun sometimes which displays
                # LDAUL/J as 2****
                raise IOError("Error in parsing vasprun.xml value!")
        elif val_type == "string":
            val = [i for i in val.split()]
        else:
            try:
                val = [float(i) for i in val.split()]
            except ValueError:
                # Stupid error in vasprun sometimes which displays
                # MAGMOM as 2****
                raise IOError("Error in parsing vasprun.xml value!")
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
            self.val = six.StringIO()

    def _init_input(self, name, attributes):
        if (name == "i" or name == "v") and (self.state["incar"] or self.state["parameters"]):
            self.incar_param = attributes["name"]
            self.param_type = "float" if not "type" in attributes else attributes["type"]
            self.read_val = True
        elif name == "v" and self.state["kpoints"]:
            self.read_val = True
        elif name == "generation" and self.state["kpoints"]:
            self.kpoints.comment = "Kpoints from vasprun.xml"
            self.kpoints.num_kpts = 0
            self.kpoints.style = attributes["param"]
            self.kpoints.kpts = []
            self.kpoints.kpts_shift = [0, 0, 0]
        elif name == "c" and (self.state["array"] == "atoms" or self.state["array"] == "atomtypes"):
            self.read_val = True
        elif name == "i" and self.state["i"] == "version" and self.state["generator"]:
            self.read_val = True

    def _init_calc(self, name, attributes):
        if self.read_structure and name == "v":
            if self.state["varray"] == "basis":
                self.read_lattice = True
            elif self.state["varray"] == "positions":
                self.read_positions = True
            elif self.state["varray"] == "rec_basis":
                self.read_rec_lattice = True
        elif self.read_calculation:
            if name == "i" and self.state["scstep"]:
                self.read_val = True
            elif name == "v" and (self.state["varray"] == "forces" or self.state["varray"] == "stress"):
                self.read_positions = True
            elif name == "dos":
                self.read_dos = True
            elif name == "dynmat":
                self.read_dynmat = True
            elif self.read_dos:
                if (name == "i" and self.state["i"] == "efermi") or (name == "r" and self.state["set"]):
                    self.read_val = True
                elif name == "set" and "comment" in attributes:
                    comment = attributes["comment"]
                    self.state["set"] = comment
                    if self.state["partial"]:
                        if comment.startswith("ion"):
                            self.pdos_ion = int(comment.split(" ")[1])
                        elif comment.startswith("spin"):
                            self.pdos_spin = 'alpha' if self.state["set"] in ["spin 1", "spin1"] else 'beta'
            elif self.read_dynmat:
                if self.state["varray"] == False:
                    self.read_val = True
                elif self.state["varray"] == "eigenvectors":
                    self.read_val = True
            '''elif name == "eigenvalues" and not self.state["projected"]:
                #logger.debug("Reading eigenvalues. Projected = {0}".format(self.state["projected"]))
                self.read_eigen = True
            elif self.read_eigen:
                if name == "r" and self.state["set"]:
                    self.read_val = True
                elif name == "set" and attributes.has_key("comment"):
                    comment = attributes["comment"]
                    self.state["set"] = comment
                    if comment.startswith("spin"):
                        self.eigen_spin = 'alpha' if self.state["set"] in ["spin 1", "spin1"] else 'beta'
                        #logger.debug("Reading spin {0}".format(self.eigen_spin))
                    elif comment.startswith("kpoint"):
                        self.eigen_kpoint = int(comment.split(" ")[1])
                        #logger.debug("Reading kpoint {0}".format(self.eigen_kpoint))
                    elif comment.startswith("band"):
                        self.eigen_band = int(comment.split(" ")[1])
                        #logger.debug("Reading band {0}".format(self.eigen_band))'''

        if name == "calculation":
            self.scdata = []
            self.read_calculation = True
        elif name == "scstep":
            self.scstep = {}
        elif name == "structure":
            self.latticestr = six.StringIO()
            self.latticerec = six.StringIO()
            self.posstr = six.StringIO()
            self.read_structure = True
        #elif name == "varray" and self.state["varray"] in ["forces", "stress"]:
        #    self.posstr = six.StringIO()

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
        if name == "i":
            if self.state["incar"]:
                self.incar[self.incar_param] = self.parse_parameters(self.param_type, self.val.getvalue().strip())
            elif self.state["parameters"]:
                self.parameters[self.incar_param] = self.parse_parameters(self.param_type, self.val.getvalue().strip())
            elif self.state["generator"] and self.state["i"] == "version":
                self.vasp_version = self.val.getvalue().strip()
            self.incar_param = None
        elif name == "set":
            if self.state["array"] == "atoms":
                self.bsseq = list(map(lambda x: int(x)-1, self.atomic_symbols[1::2]))
                self.atomic_symbols = self.atomic_symbols[::2]
            elif self.state["array"] == "atomtypes":
                self.potcar_sequence = self.potcar_symbols[1::5]
                self.potcar_symbols = self.potcar_symbols[4::5]
                self.input_read = True
        elif name == "c":
            if self.state["array"] == "atoms":
                self.atomic_symbols.append(self.val.getvalue().strip())
            elif self.state["array"] == "atomtypes":
                self.potcar_symbols.append(self.val.getvalue().strip())
        elif name == "v":
            if self.state["incar"]:
                self.incar[self.incar_param] = self.parse_v_parameters(self.param_type, self.val.getvalue().strip(), self.incar_param)
                self.incar_param = None
            elif self.state["parameters"]:
                self.parameters[self.incar_param] = self.parse_v_parameters(self.param_type, self.val.getvalue().strip(), self.incar_param)
            elif self.state["kpoints"]:
                if self.state["varray"] == "kpointlist":
                    self.actual_kpoints.append([float(x) for x in self.val.getvalue().split()])
                if self.state["varray"] == "weights":
                    val = float(self.val.getvalue())
                    self.actual_kpoints_weights.append(val)
                if self.state["v"] == "divisions":
                    self.kpoints.kpts = [[int(x) for x in self.val.getvalue().split()]]
                elif self.state["v"] == "usershift":
                    self.kpoints.kpts_shift = [float(x) for x in self.val.getvalue().split()]
                elif self.state["v"] == "genvec1" or self.state["v"] == "genvec2" or self.state["v"] == "genvec3" or self.state["v"] == "shift":
                    setattr(self.kpoints, self.state["v"], [float(x) for x in self.val.getvalue().split()])

    def _read_calc(self, name):
        if name == "i" and self.state["scstep"]:
            try:
                self.scstep[self.state["i"]] = float(self.val.getvalue())
            except ValueError:
                pass
        elif name == "scstep":
            self.scdata.append(self.scstep)
        #elif name == "varray" and self.state["varray"] == "forces":
        #    self.forces = array([float(x) for x in self.posstr.getvalue().split()])
        #    self.forces.shape = (len(self.atomic_symbols), 3)
        #    self.read_positions = False
        #elif name == "varray" and self.state["varray"] == "stress":
        #    self.stress = array([float(x) for x in self.posstr.getvalue().split()])
        #    self.stress.shape = (3, 3)
        #    self.read_positions = False
        elif name == "calculation":
            #self.ionic_steps.append({"electronic_steps": self.scdata, "structure": self.structures[-1], "forces": self.forces, "stress": self.stress})
            try: # for unphysical cases
                final_e = self.scdata[-1]["e_wo_entrp"]/Hartree
                self.tresholds.append([0, 0, 0, 0, final_e]) # NB final value
            except:
                pass
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

            self.structures.append(Atoms(symbols=self.atomic_symbols, cell=self.lattice, scaled_positions=pos, pbc=True))

            #self.lattice_rec = [float(x) for x in self.latticerec.getvalue().split()]
            self.read_structure = False
            self.read_positions = False
            self.read_lattice = False
            self.read_rec_lattice = False

    def _read_dynmat(self, name):
        if name == "v" and self.state["varray"] == False:
            freqs = [float(x) for x in self.val.getvalue().split()]
            for i in range(len(freqs)):
                if freqs[i]<0: freqs[i] = math.sqrt( -freqs[i] )*Constants.VaspToCm
                else: freqs[i] = -math.sqrt( freqs[i] )*Constants.VaspToCm
            freqs.reverse()
            self.dynmat["freqs"] = freqs

        elif name == "v" and self.state["varray"] == "eigenvectors":
            self.dynmat["eigvecs"].insert(0, [float(x) for x in self.val.getvalue().split()])

        elif name == "dynmat":
            self.read_dynmat = False

    def _read_dos(self, name):
        try:
            if name == "i" and self.state["i"] == "efermi":
                self.e_last = float(self.val.getvalue().strip())
            elif name == "r" and self.state["total"] and str(self.state["set"]).startswith("spin"):
                tok = self.val.getvalue().split()
                try: self.dos_energies_val.append(float(tok[0]))
                except ValueError: self.dos_energies_val.append(1000) # > 8 digits fixed place
                try: self.dos_val.append(float(tok[1]))
                except ValueError: self.dos_val.append(1000) # > 8 digits fixed place
                #self.idos_val.append(float(tok[2]))
            elif name == "r" and self.state["partial"] and str(self.state["set"]).startswith("spin"):
                tok = self.val.getvalue().split()
                self.raw_data.append([float(i) for i in tok[1:]])
            elif name == "set":
                if self.state["total"] and str(self.state["set"]).startswith("spin"):
                    spin = 'alpha' if self.state["set"] == "spin 1" else 'beta'
                    self.tdos[spin] = self.dos_val
                    #self.idos[spin] = self.dos_val
                    self.dos_energies = self.dos_energies_val
                    self.dos_energies_val = []
                    self.dos_val = []
                    #self.idos_val = []
                elif self.state["partial"] and str(self.state["set"]).startswith("spin"):
                    spin = 'alpha' if self.state["set"] == "spin 1" else 'beta'
                    self.norbitals = len(self.raw_data[0])
                    for i in range(self.norbitals):
                        self.pdos[(self.pdos_ion, i, spin)] = [row[i] for row in self.raw_data]
                    self.raw_data = []
            elif name == "partial":
                atomic_pdos = {}
                for k, v in six.iteritems(self.pdos):
                    atom = self.atomic_symbols[k[0]-1]
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
        except Exception as ex:
            self.dos_error = str(ex)

    '''def _read_eigen(self, name):
        if name == "r" and str(self.state["set"]).startswith("kpoint"):
            tok = self.val.getvalue().split()
            #self.raw_data.append([float(i) for i in tok])
            self.raw_data.append(round(float(tok[0]), 2))
        elif name == "set" and str(self.state["set"]).startswith("kpoint"):
            try: k = tuple( self.actual_kpoints[self.eigen_kpoint - 1] )
            except IndexError: raise RuntimeError('Unmatched k-point index for a found eigenvalue!')

            if k in self.eigvals:
                self.eigvals[k]['beta'] = self.raw_data
            else:
                self.eigvals[k] = {'alpha': self.raw_data}
            self.raw_data = []
        elif name == "eigenvalues":
            #logger.debug("Finished reading eigenvalues. No. eigen = {0}".format(len(self.eigvals)))
            self.read_eigen = False'''

    def endElement(self, name):
        if not self.input_read:
            self._read_input(name)
        else:
            if self.read_structure:
                self._read_structure(name)
            elif self.read_dos:
                self._read_dos(name)
            #elif self.read_eigen:
            #    self._read_eigen(name)
            elif self.read_dynmat:
                self._read_dynmat(name)
            #elif self.read_projected_eigen:
            #    self._read_projected_eigen(name)
            elif self.read_calculation:
                self._read_calc(name)
        self.state[name] = False
