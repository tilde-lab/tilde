
# Quantum ESPRESSO basic parser
# Author: Evgeny Blokhin
# TODO: check ibrav settings, parsing might be wrong

import os, sys
import datetime, time

from numpy import dot, array, transpose, linalg

from tilde.parsers import Output
from tilde.core.electron_structure import Ebands

from ase import Atoms
from ase.data import chemical_symbols
from ase.units import Bohr, Rydberg


class QuantumESPRESSO(Output):
    def __init__(self, filename, **kwargs):
        Output.__init__(self, filename)

        cur_folder = os.path.dirname(filename)
        self.related_files.append(filename)

        self.info['framework'] = 'Quantum ESPRESSO'
        self.info['finished'] = -1
        self.electrons['type'] = 'plane waves'

        # taken from trunk/Modules/funct.f90
        xc_internal_map = {
        "pw"           : {'name': "PW_LDA",                  'type': ['LDA'],              'setup': ["sla+pw+nogx+nogc"    ] },

        "pz"           : {'name': "PZ_LDA",                  'type': ['LDA'],              'setup': ["sla+pz+nogx+nogc"    ] },
        "bp"           : {'name': "Becke-Perdew grad.corr.", 'type': ['GGA'],              'setup': ["b88+p86+nogx+nogc"   ] },
        "pw91"         : {'name': "PW91",                    'type': ['GGA'],              'setup': ["sla+pw+ggx+ggc"      ] },
        "blyp"         : {'name': "BLYP",                    'type': ['GGA'],              'setup': ["sla+b88+lyp+blyp"    ] },
        "pbe"          : {'name': "PBE",                     'type': ['GGA'],              'setup': ["sla+pw+pbx+pbc", "sla+pw+pbe+pbe"] },
        "revpbe"       : {'name': "revPBE",                  'type': ['GGA'],              'setup': ["sla+pw+rpb+pbc", "sla+pw+rpb+pbe"] },
        "pw86pbe"      : {'name': "PW86+PBE",                'type': ['GGA'],              'setup': ["sla+pw+pw86+pbc", "sla+pw+pw86+pbe"] },
        "b86bpbe"      : {'name': "B86b+PBE",                'type': ['GGA'],              'setup': ["sla+pw+b86b+pbc", "sla+pw+b86b+pbe"] },
        "pbesol"       : {'name': "PBEsol",                  'type': ['GGA'],              'setup': ["sla+pw+psx+psc"      ] },
        "q2d"          : {'name': "PBEQ2D",                  'type': ['GGA'],              'setup': ["sla+pw+q2dx+q2dc"    ] },
        "hcth"         : {'name': "HCTH/120",                'type': ['GGA'],              'setup': ["nox+noc+hcth+hcth"   ] },
        "olyp"         : {'name': "OLYP",                    'type': ['GGA'],              'setup': ["nox+lyp+optx+blyp"   ] },
        "wc"           : {'name': "Wu-Cohen",                'type': ['GGA'],              'setup': ["sla+pw+wcx+pbc", "sla+pw+wcx+pbe"] },
        "sogga"        : {'name': "SOGGA",                   'type': ['GGA'],              'setup': ["sla+pw+sox+pbc", "sla+pw+sox+pbe"] },
        "optbk88"      : {'name': "optB88",                  'type': ['GGA'],              'setup': ["sla+pw+obk8+p86"     ] },
        "optb86b"      : {'name': "optB86",                  'type': ['GGA'],              'setup': ["sla+pw+ob86+p86"     ] },
        "ev93"         : {'name': "Engel-Vosko",             'type': ['GGA'],              'setup': ["sla+pw+evx+nogc"     ] },
        "tpss"         : {'name': "TPSS",                    'type': ['meta-GGA'],         'setup': ["sla+pw+tpss+tpss"    ] },
        "m06l"         : {'name': "M06L",                    'type': ['meta-GGA'],         'setup': ["nox+noc+m6lx+m6lc"   ] },
        "tb09"         : {'name': "TB09",                    'type': ['meta-GGA'],         'setup': ["sla+pw+tb09+tb09"    ] },
        "pbe0"         : {'name': "PBE0",                    'type': ['GGA', 'hybrid'],    'setup': ["pb0x+pw+pb0x+pbc", "pb0x+pw+pb0x+pbe"] },
        "hse"          : {'name': "HSE06",                   'type': ['GGA', 'hybrid'],    'setup': ["sla+pw+hse+pbc", "sla+pw+hse+pbe"] },
        "b3lyp"        : {'name': "B3LYP",                   'type': ['GGA', 'hybrid'],    'setup': ["b3lp+vwn+b3lp+b3lp"  ] },
        "gaupbe"       : {'name': "Gau-PBE",                 'type': ['GGA', 'hybrid'],    'setup': ["sla+pw+gaup+pbc", "sla+pw+gaup+pbe"] },
        "vdw-df"       : {'name': "vdW-DF",                  'type': ['GGA', 'vdW'],       'setup': ["sla+pw+rpb+vdw1"     ] },
        "vdw-df2"      : {'name': "vdW-DF2",                 'type': ['GGA', 'vdW'],       'setup': ["sla+pw+rw86+vdw2"    ] },
        "vdw-df-c09"   : {'name': "vdW-DF-C09",              'type': ['GGA', 'vdW'],       'setup': ["sla+pw+c09x+vdw1"    ] },
        "vdw-df2-c09"  : {'name': "vdW-DF2-C09",             'type': ['GGA', 'vdW'],       'setup': ["sla+pw+c09x+vdw2"    ] },
        "vdw-df-cx"    : {'name': "vdW-DF-cx",               'type': ['GGA', 'vdW'],       'setup': ["sla+pw+cx13+vdW1"    ] },
        "vdw-df-obk8"  : {'name': "vdW-DF-obk8",             'type': ['GGA', 'vdW'],       'setup': ["sla+pw+obk8+vdw1"    ] },
        "vdw-df-ob86"  : {'name': "vdW-DF-ob86",             'type': ['GGA', 'vdW'],       'setup': ["sla+pw+ob86+vdw1"    ] },
        "vdw-df2-b86r" : {'name': "vdW-DF2-B86R",            'type': ['GGA', 'vdW'],       'setup': ["sla+pw+b86r+vdw2"    ] },
        "rvv10"        : {'name': "rVV10",                   'type': ['GGA', 'vdW'],       'setup': ["sla+pw+rw86+pbc+vv10", "sla+pw+rw86+pbe+vv10"] },

        "hf"           : {'name': "Hartree-Fock",            'type': ['HF'],               'setup': ["hf+noc+nogx+nogc"    ] },
        "vdw-df3"      : {'name': "vdW-DF3",                 'type': ['GGA', 'vdW'],       'setup': ["sla+pw+rw86+vdw3"    ] },
        "vdw-df4"      : {'name': "vdW-DF4",                 'type': ['GGA', 'vdW'],       'setup': ["sla+pw+rw86+vdw4"    ] },
        "gaup"         : {'name': "Gau-PBE",                 'type': ['GGA', 'hybrid'],    'setup': ["sla+pw+gaup+pbc", "sla+pw+gaup+pbe"] },
        }

        self.data = open(filename).readlines()
        atomic_data, cell_data, pos_data, symbol_data, alat = None, [], [], [], 0
        e_last = None
        kpts, eigs_columns, tot_k = [], [], 0

        for n in range(len(self.data)):
            cur_line = self.data[n]

            if "This run was terminated on" in cur_line:
                self.info['finished'] = 1

            elif "     Program PWSCF" in cur_line and " starts " in cur_line:
                ver_str = cur_line.strip().replace('Program PWSCF', '')
                ver_str = ver_str[ : ver_str.find(' starts ') ].strip()
                if ver_str.startswith("v."): ver_str = ver_str[2:]
                self.info['prog'] = self.info['framework'] + " " + ver_str

            elif cur_line.startswith("     celldm"):
                if not alat:
                    alat = float(cur_line.split()[1]) * Bohr
                    if not alat: alat = 1

            elif cur_line.startswith("     crystal axes:"):
                cell_data = [x.split()[3:6] for x in self.data[n + 1:n + 4]]
                cell_data = array([[float(col) for col in row] for row in cell_data])

            elif cur_line.startswith("     site n."):
                if len(pos_data): continue

                while True:
                    n += 1
                    next_line = self.data[n].split()
                    if not next_line: break
                    pos_data.append([float(x) for x in next_line[-4:-1]])
                    symbol = next_line[1].strip('0123456789').split('_')[0]
                    if not symbol in chemical_symbols and len(symbol) > 1: symbol = symbol[:-1]
                    symbol_data.append(symbol)
                pos_data = array(pos_data)*alat
                atomic_data = Atoms(symbol_data, pos_data, cell=cell_data*alat, pbc=(1,1,1))

            elif "CELL_PARAMETERS" in cur_line:
                for i in range(3):
                    n += 1
                    next_line = self.data[n].split()
                    if not next_line: break
                    cell_data[i][:] = map(float, next_line)
                else:
                    mult = 1
                    if "bohr" in cur_line: mult = Bohr
                    elif "alat" in cur_line: mult = alat
                    atomic_data.set_cell(cell_data*mult, scale_atoms=True)

            elif "ATOMIC_POSITIONS" in cur_line:
                coord_flag = cur_line.split('(')[-1].strip()
                for i in range(len(pos_data)):
                    n += 1
                    next_line = self.data[n].split()
                    pos_data[i][:] = map(float, next_line[1:4])
                if not atomic_data: continue

                if coord_flag=='alat)':
                    atomic_data.set_positions(pos_data*alat)
                elif coord_flag=='bohr)':
                    atomic_data.set_positions(pos_data*Bohr)
                elif coord_flag=='angstrom)':
                    atomic_data.set_positions(pos_data)
                else:
                    atomic_data.set_scaled_positions(pos_data)

            elif cur_line.startswith("!    total energy"):
                self.info['energy'] = float(cur_line.split()[-2]) * Rydberg

            elif "     Exchange-correlation" in cur_line:
                if self.info['H']: continue

                xc_str = cur_line.split('=')[-1].strip()
                xc_parts = xc_str[ : xc_str.find("(") ].split()
                if len(xc_parts) == 1: xc_parts = xc_parts[0].split('+')
                if len(xc_parts) < 4: xc_parts = [ '+'.join(xc_parts) ]
                xc_parts = map(lambda x: x.lower().strip("-'\""), xc_parts)

                if len(xc_parts) == 1:
                    try:
                        self.info['H'] = xc_internal_map[xc_parts[0]]['name']
                        self.info['H_types'].extend( xc_internal_map[xc_parts[0]]['type'] )
                    except KeyError:
                        self.info['H'] = xc_parts[0]
                else:
                    xc_parts = '+'.join(xc_parts)
                    match = [ i for i in xc_internal_map.values() if xc_parts in i['setup'] ]
                    if match:
                        self.info['H'] = match[0]['name']
                        self.info['H_types'].extend( match[0]['type'] )
                    else:
                        self.info['H'] = xc_parts

            elif "PWSCF        :" in cur_line:
                if "WALL" in cur_line or "wall" in cur_line:
                    d = cur_line.split("CPU")[-1].replace("time", "").replace(",", "")
                    if d.find("s") > 0: d = d[ : d.find("s") + 1 ]
                    elif d.find("m") > 0: d = d[ : d.find("m") + 1 ]
                    elif d.find("h") > 0: d = d[ : d.find("h") + 1 ]
                    d = d.strip().replace(" ", "")
                    fmt = ""
                    if 's' in d: fmt = "%S.%fs"
                    if 'm' in d: fmt = "%Mm" + fmt
                    if 'h' in d: fmt = "%Hh" + fmt
                    if 'd' in d: fmt = "%dd" + fmt # FIXME for months!
                    d = time.strptime(d, fmt)
                    self.info['duration'] = "%2.2f" % (  datetime.timedelta(days=d.tm_mday, hours=d.tm_hour, minutes=d.tm_min, seconds=d.tm_sec).total_seconds()/3600  )
                    self.info['finished'] = 1

            elif "End of self-consistent calculation" in cur_line or "End of band structure calculation" in cur_line:
                e_last = None
                kpts, eigs_columns, tot_k = [], [], 0
                eigs_collect, eigs_failed = False, False
                eigs_spin_warning = False
                if not atomic_data: eigs_failed = True

                while not eigs_failed:
                    n += 1
                    next_line = self.data[n]
                    if eigs_collect:
                        next_line = next_line.split()
                        if next_line:
                            try: eigs_columns[-1] += map(float, next_line)
                            except ValueError: eigs_failed = True
                        else: eigs_collect = False
                        continue

                    if "Ry" in next_line or "CPU" in next_line:
                        eigs_failed = True
                    elif "    k =" in next_line:
                        tot_k += 1
                        coords = next_line.strip().replace("k =", "")[:21]
                        try: kpts.append(map(float, [coords[0:7], coords[7:14], coords[14:21]]))
                        except ValueError: eigs_failed = True
                        eigs_collect = True
                        eigs_columns.append([])
                        n += 1
                    elif "highest occupied level" in next_line:
                        e_last = float(next_line.split()[-1])
                        break
                    elif "highest occupied, lowest unoccupied" in next_line:
                        e_last = float(next_line.split()[-2])
                        break
                    elif "Fermi energy" in next_line:
                        e_last = float(next_line.split()[-2])
                        break
                    elif " SPIN UP " in next_line or " SPIN DOWN " in next_line:
                        self.info['spin'] = True
                        eigs_spin_warning = True

        # Only the last set is taken
        if kpts and eigs_columns:
            if eigs_spin_warning:
                self.warning('Attention! Spin states are currently not supported! Only spin down projection is considered.') # FIXME
                tot_k /= 2
            if e_last is None:
                self.warning('Warning: highest occupied state not found!')
            else:
                if not eigs_failed:
                    band_obj = {'ticks': [], 'abscissa': [], 'stripes': []}
                    d = 0.0
                    bz_vec_ref = [0, 0, 0]
                    k_shape = linalg.inv( atomic_data.cell ).transpose()
                    for k in kpts:
                        bz_vec_cur = dot( k, k_shape )
                        bz_vec_dir = map(sum, zip(bz_vec_cur, bz_vec_ref))
                        bz_vec_ref = bz_vec_cur
                        d += linalg.norm( bz_vec_dir )
                        band_obj['abscissa'].append(d)
                    band_obj['stripes'] = (transpose(eigs_columns) - e_last).tolist()
                    self.electrons['bands'] = Ebands(band_obj)
                    self.info['k'] = str(tot_k) + ' pts/BZ'

                else: self.warning('Error: incorrect bands data!')

        if atomic_data: self.structures.append(atomic_data)

        for check in [  filename.replace('.' + filename.split('.')[-1], '') + '.in'  ]: # NB no guarantee this file fits!
            if os.path.exists(os.path.join(cur_folder, check)): self.related_files.append(os.path.join(cur_folder, check))

    @staticmethod
    def fingerprints(test_string):
        if ("pwscf" in test_string or "PWSCF" in test_string) and "     Current dimensions of program " in test_string: return True
        else: return False
