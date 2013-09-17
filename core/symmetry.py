
# Tilde project:
#
# *SymmetryFinder*: platform-dependent symmetry finder for 3D-systems, wrapping Spglib and FINDSYM codes:
# FINDSYM is written by H. T. Stokes and D. M. Hatch: http://dx.doi.org/10.1107/S0021889804031528
# Spglib is written by Atsushi Togo: http://spglib.sourceforge.net
# their results are found to coincide in all my tests at DEFAULT_ACCURACY=1e-04;
# more info at http://sourceforge.net/mailarchive/forum.php?forum_name=spglib-users
#
# *SymmetryHandler*: symmetry inferences basing on known mapping
#
# v170913

import os
import sys

# this is done to have all third-party code in deps folder
# TODO: dealing with sys.path is malpractice
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps/ase/lattice'))
from spacegroup.cell import cellpar_to_cell

# recommended accuracy value = 0.0001
DEFAULT_ACCURACY=1e-04

if 'win' in sys.platform:
    from ase.atoms import Atoms
    import pywintypes
    import pythoncom
    import win32api
    from pyspglib import spglib

    class SymmetryFinder:
        def __init__(self, tilde_obj, accuracy):
            self.error = None
            ase_symbols = []
            for i in tilde_obj['structures'][-1]['atoms']:
                adata = i[0].capitalize()
                if adata == 'Xx': adata = 'X'
                symb = filter(None, adata.split(' '))[-1]
                ase_symbols.append(symb.encode('ascii'))
            magmoms = []
            if tilde_obj.charges:
                for j in tilde_obj.charges:
                    magmoms.append(j[2])
            xyz_matrix = cellpar_to_cell(tilde_obj['structures'][-1]['cell'])
            ase_positions = [(i[1], i[2], i[3]) for i in tilde_obj['structures'][-1]['atoms']]
            ase_obj = Atoms(symbols=ase_symbols, positions=ase_positions, cell=xyz_matrix, pbc=True, magmoms=magmoms)
            try: symmetry = spglib.get_spacegroup(ase_obj, accuracy)
            except Exception, ex:
                self.error = 'Symmetry finder error: %s' % ex
            else:
                symmetry = filter(None, symmetry.split(" "))
                self.n = int( symmetry[1].replace("(", "").replace(")", "") )
                self.i = symmetry[0]

elif 'linux' in sys.platform:
    import subprocess
    from numpy import dot
    from numpy import array
    from numpy import matrix
    
    isodata_path = os.path.realpath(os.path.dirname(__file__)) + '/deps/findsym'
    findsym = os.path.join(isodata_path, 'findsym')
    myenv = {'ISODATA': isodata_path + os.sep}
    
    if not os.access(findsym, os.X_OK): os.chmod(findsym, 0777)    
    if not os.access(os.path.join(isodata_path, 'findsym.log'), os.X_OK): os.chmod(os.path.join(isodata_path, 'findsym.log'), 0777) # TODO: how to suppress creation of log and redundant I/O?

    class SymmetryFinder:
        def __init__(self, tilde_obj, accuracy):
            self.error = None
            self.cif = None            
            input, findsym_corr, error = self.findsym_input(tilde_obj['structures'][-1], accuracy)
            #print input
            
            if error: self.error = error
            else:
                p = subprocess.Popen([findsym], shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=myenv)
                foundsym = p.communicate(input)[0]                
                #print foundsym

                if not "------------------------------------------" in foundsym:
                    self.error = 'FINDSYM program failed to run!'
                else:
                    out = foundsym.split("------------------------------------------")
                    if len(out) != 3:
                        self.error = 'FINDSYM reported error:', out[-1]
                    else:
                        # prepare CIF
                        out[2] = out[2].replace("data_ findsym-output", "data_findsym-output") # problems here with CIF grammar (tracked thanks to Materials Studio!)
                        # replace A, B, C etc. in output on real atoms
                        parts = out[2].split("_atom_site_type_symbol")
                        for symbol, letter in findsym_corr.iteritems():
                            parts[1] = parts[1].replace(letter, symbol)
                        self.cif = parts[0] + "_atom_site_type_symbol" + parts[1]
                        
                        # prepare main output
                        symmetry = out[1].splitlines()[1].replace("Space Group ", "")
                        self.n, self.s, self.i = symmetry.split()
                        self.n = int( self.n )

        def findsym_input(self, tilde_obj, accuracy):
            error = None
            findsym_atoms = 'ABCDEFGHIJKLMNOPQRSTYVWXYZ'
            out = "~\n" + "%s" % accuracy + "   accuracy\n2 form of lattice parameters lengths(angstrom) and angles\n"
            out += "%3.8f   %3.8f   %3.8f   %3.8f   %3.8f   %3.8f\n" % tuple(tilde_obj['cell'])
            out += " 2\n P\n " + "%s" % len(tilde_obj['atoms']) + "\n"
            coords = ''
            atomtypes = []
            atomlabels = {}
            N = 0
            reverse = matrix( cellpar_to_cell(tilde_obj['cell'], tilde_obj['ab_normal'], tilde_obj['a_direction']) ).I
            for i in tilde_obj['atoms']:
                fracs = dot( array([i[1], i[2], i[3]]), reverse ).tolist()[0]
                coords += "   " + "% 3.8f" % fracs[0] + "   " + "% 3.8f" % fracs[1] + "   " + "% 3.8f" % fracs[2] + "\n"
                if i[0] in atomlabels.values():
                    counter = [k for k, v in atomlabels.iteritems() if v == i[0]][0]
                    atomtypes.append(counter)
                else:
                    N += 1
                    atomlabels[N] = i[0]
                    atomtypes.append(N)
            i = 0
            for type in atomtypes:
                out += "   " + "%s" % type
                i += 1
                if not i % 20: out += "\n"
            if out[-1:] != "\n": out += "\n"
            out += coords
            findsym_corr = {}
            for i, v in atomlabels.iteritems():
                try: findsym_corr[v.capitalize()] = findsym_atoms[i-1]
                except IndexError: error = 'Too many atom types for FINDSYM!'
            return out, findsym_corr, error

else: raise RuntimeError('Cannot start platform-dependent symmetry finder!')

'''
# Dummy class for testing purposes
class SymmetryFinder:
        def __init__(self, tilde_obj):
            self.error = None
            self.n = 1
            self.i = 'P1'
'''

class SymmetryHandler(SymmetryFinder):
    def __init__(self, tilde_obj, accuracy=None):
        self.i = None
        self.s = None
        self.n = None
        self.cif = None # only given by findsym
        self.symmetry = None
        self.pg = None
        self.dg = None
        if not accuracy: accuracy=DEFAULT_ACCURACY

        SymmetryFinder.__init__(self, tilde_obj, accuracy)

        # Tables from Bandura-Evarestov book
        # "Non-emp calculations of crystals", 2004, ISBN 5-288-03401-X

        # space group 2 crystal system
        # TODO: only for 3d systems!!!
        if   195 <= self.n <= 230: self.symmetry = 'cubic'
        elif 168 <= self.n <= 194: self.symmetry = 'hexagonal'
        elif 143 <= self.n <= 167: self.symmetry = 'rhombohedral'
        elif 75  <= self.n <= 142: self.symmetry = 'tetragonal'
        elif 16  <= self.n <= 74:  self.symmetry = 'orthorhombic'
        elif 3   <= self.n <= 15:  self.symmetry = 'monoclinic'
        elif 1   <= self.n <= 2:   self.symmetry = 'triclinic'

        # space group 2 point group
        if   221 <= self.n <= 230: self.pg = 'O<sub>h</sub>'
        elif 215 <= self.n <= 220: self.pg = 'T<sub>d</sub>'
        elif 207 <= self.n <= 214: self.pg = 'O'
        elif 200 <= self.n <= 206: self.pg = 'T<sub>h</sub>'
        elif 195 <= self.n <= 199: self.pg = 'T'
        elif 191 <= self.n <= 194: self.pg = 'D<sub>6h</sub>'
        elif 187 <= self.n <= 190: self.pg = 'D<sub>3h</sub>'
        elif 183 <= self.n <= 186: self.pg = 'C<sub>6v</sub>'
        elif 177 <= self.n <= 182: self.pg = 'D<sub>6</sub>'
        elif 175 <= self.n <= 176: self.pg = 'C<sub>6h</sub>'
        elif        self.n == 174: self.pg = 'C<sub>3h</sub>'
        elif 168 <= self.n <= 173: self.pg = 'C<sub>6</sub>'
        elif 162 <= self.n <= 167: self.pg = 'D<sub>3d</sub>'
        elif 156 <= self.n <= 161: self.pg = 'C<sub>3v</sub>'
        elif 149 <= self.n <= 155: self.pg = 'D<sub>3</sub>'
        elif 147 <= self.n <= 148: self.pg = 'C<sub>3i</sub>'
        elif 143 <= self.n <= 146: self.pg = 'C<sub>3</sub>'
        elif 123 <= self.n <= 142: self.pg = 'D<sub>4h</sub>'
        elif 111 <= self.n <= 122: self.pg = 'D<sub>2d</sub>'
        elif 99 <= self.n <= 110:  self.pg = 'C<sub>4v</sub>'
        elif 89 <= self.n <= 98:   self.pg = 'D<sub>4</sub>'
        elif 83 <= self.n <= 88:   self.pg = 'C<sub>4h</sub>'
        elif 81 <= self.n <= 82:   self.pg = 'S<sub>4</sub>'
        elif 75 <= self.n <= 80:   self.pg = 'C<sub>4</sub>'
        elif 47 <= self.n <= 74:   self.pg = 'D<sub>2h</sub>'
        elif 25 <= self.n <= 46:   self.pg = 'C<sub>2v</sub>'
        elif 16 <= self.n <= 24:   self.pg = 'D<sub>2</sub>'
        elif 10 <= self.n <= 15:   self.pg = 'C<sub>2h</sub>'
        elif 6 <= self.n <= 9:     self.pg = 'C<sub>s</sub>'
        elif 3 <= self.n <= 5:     self.pg = 'C<sub>2</sub>'
        elif self.n == 2:          self.pg = 'C<sub>i</sub>'
        elif self.n == 1:          self.pg = 'C<sub>1</sub>'

        # space group 2 layer group
        if tilde_obj.structures[-1]['periodicity'] == 2:
            if self.n in [25, 26, 28, 51]:
                tilde_obj.warning('Warning! Diperiodical group setting is undefined!')
            DIPERIODIC_MAPPING = {3:8, 4:9, 5:10, 6:11, 7:12, 8:13, 10:14, 11:15, 12:16, 13:17, 14:18, 16:19, 17:20, 18:21, 21:22, 25:23, 25:24, 26:25, 26:26, 27:27, 28:28, 28:29, 29:30, 30:31, 31:32, 32:33, 35:34, 38:35, 39:36, 47:37, 49:38, 50:39, 51:40, 51:41, 53:42, 54:43, 55:44, 57:45, 59:46, 65:47, 67:48, 75:49, 81:50, 83:51, 85:52, 89:53, 90:54, 99:55, 100:56, 111:57, 113:58, 115:59, 117:60, 123:61, 125:62, 127:63, 129:64, 143:65, 147:66, 149:67, 150:68, 156:69, 157:70, 162:71, 164:72, 168:73, 174:74, 175:75, 177:76, 183:77, 187:78, 189:79, 191:80}
            if tilde_obj.structures[-1]['cell'][3] != 90 or \
            tilde_obj.structures[-1]['cell'][4] != 90 or \
            tilde_obj.structures[-1]['cell'][5] != 90:
                DIPERIODIC_MAPPING.update({1:1, 2:2, 3:3, 6:4, 7:5, 10:6, 13:7})
            try: self.dg = DIPERIODIC_MAPPING[self.n]
            except KeyError: tilde_obj.warning('No diperiodical group found because rotational axes inconsistent with 2d translations!')
            else:
                if   65 <= self.dg <= 80: self.symmetry = 'hexagonal'
                elif 49 <= self.dg <= 64: self.symmetry = 'square'
                elif 8  <= self.dg <= 48: self.symmetry = 'rectangular'
                elif 1  <= self.dg <= 7:  self.symmetry = 'oblique'
