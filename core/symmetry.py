
# Tilde project: platform-dependent symmetry finder for 3D-systems, wrapping Spglib and Findsym codes;
# their results are found to coincide in all my tests;
# more info at http://sourceforge.net/mailarchive/forum.php?forum_name=spglib-users

import os
import sys

# this is done to have all third-party code in deps folder
# TODO: dealing with sys.path is malpractice
sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/deps/ase/lattice'))
from spacegroup.cell import cellpar_to_cell


if 'win' in sys.platform:
    from ase.atoms import Atoms
    import pywintypes
    import pythoncom
    import win32api
    from pyspglib import spglib
    
    class SymmetryFinder:
        def __init__(self, tilde_obj):
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
            try: symmetry = spglib.get_spacegroup(ase_obj, 1e-04)
            except Exception, ex:
                self.error = 'Symmetry finder error: %s' % ex
            else:
                symmetry = filter(None, symmetry.split(" "))
                self.n = int( symmetry[1].replace("(", "").replace(")", "") )
                self.i = symmetry[0]

elif 'linux' in sys.platform:
    import subprocess
    import tempfile
    from numpy import dot
    from numpy import array
    from numpy import matrix
    
    if not os.access(os.path.dirname(__file__) + '/deps/findsym/findsym', os.X_OK):
        os.chmod(os.path.abspath( os.path.realpath( os.path.dirname(__file__) + '/deps/findsym/findsym' )), 0777)
    
    class SymmetryFinder:
        def __init__(self, tilde_obj):
            self.error = None
            self.cif = None
            input, findsym_corr, error = self.findsym_input(tilde_obj['structures'][-1]['atoms'], tilde_obj['structures'][-1]['cell'])
            if error: self.error = error
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.write(input)
                tmp.seek(0)
                tmp.close()
                p = subprocess.Popen('cd ' + os.path.realpath(os.path.dirname(__file__) + '/deps/findsym/') + ' && ./findsym < ' + tmp.name + ' 2>&1', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                foundsym = p.communicate()[0]
                os.remove(tmp.name)
                
                if not "------------------------------------------" in foundsym:
                    self.error = 'FINDSYM program failed to run!'
                else:
                    out = foundsym.split("------------------------------------------")
                    if len(out) != 3:
                        self.error = 'FINDSYM reported error:', out[-1]
                    else:
                        self.cif = out[2] # <- CIF
                        symmetry = out[1].splitlines()[1].replace("Space Group ", "")
                        self.n, self.s, self.i = symmetry.split()
                        self.n = int( self.n )
            
        def findsym_input(self, atoms, parameters, accuracy=1e-04): # recommended value = 0.0001
            error = None
            findsym_atoms = 'ABCDEFGHIJKLMNOPQRSTYVWXYZ'
            out = "~\n" + "%s" % accuracy + "   accuracy\n2 form of lattice parameters lengths(angstrom) and angles\n"
            out += "%3.8f" % parameters[0] + "   " + "%3.8f" % parameters[1] + "   " + "%3.8f" % parameters[2] + "   "
            out += "%3.8f" % parameters[3] + "   " + "%3.8f" % parameters[4] + "   " + "%3.8f" % parameters[5] + "\n"
            out += " 1\n1 0 0\n0 1 0\n0 0 1\n " + "%s" % len(atoms) + "\n"
            coords = ''
            atomtypes = []
            atomlabels = {}
            N = 0            
            reverse = matrix( cellpar_to_cell(parameters) ).I
            for i in atoms:
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
