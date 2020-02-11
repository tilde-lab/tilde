"""
A new parser for VASP (Vienna Ab initio Simulation Package)
based on quantum_esperanto
Authors: Evgeny Blokhin and Andrey Sobolev
"""
from ase.atoms import Atoms
from ase.units import Hartree

from quantum_esperanto.vasp import VaspParser

from tilde.parsers import Output
#from tilde.core.electron_structure import Edos TODO


class XML_Output(Output):

    # TODO: kpoints, dos, eigenvalues, etc.
    obligatory_tags = ['incar', 'generator', 'atominfo', 'parameters', 'structure:finalpos']
    current_parser = VaspParser(whitelist=obligatory_tags + ['energy'])

    def __init__(self, filename):
        Output.__init__(self, filename)
        self.related_files.append(filename)
        self.info['framework'] = 0x2

        try:
            repr = XML_Output.current_parser.parse_file(filename)['modeling']
        except Exception as ex:
            raise RuntimeError('VASP output issue: %s' % ex)

        for tag in XML_Output.obligatory_tags:
            if tag not in repr:
                raise RuntimeError('VASP output contains too little necessary data')

        self.incar = repr['incar']
        self.parameters = flatten_dict(repr['parameters'])
        self.info['prog'] = repr['generator'].get('version')

        self.info['ansatz'] = 0x2
        self.electrons['basis_set'] = [
            (item[1], item[4]) for item in repr['atominfo']['array:atomtypes']['values']
        ]

        try:
            self.info['energy'] = repr['calculation'][0]['energy']['e_wo_entrp'] \
                if type(repr['calculation']) == list \
                else repr['calculation']['energy']['e_wo_entrp']
        except KeyError:
            raise RuntimeError('VASP output contains no energy')

        self.info['energy'] /= Hartree # TODO handle convergence

        self.structures.append(Atoms(
            symbols=[item[0] for item in repr['atominfo']['array:atoms']['values']],
            cell=repr['structure:finalpos']['crystal']['basis'],
            scaled_positions=repr['structure:finalpos']['positions'],
            pbc=True
        ))

        self.potcar_sequence = [item[0] for item in self.electrons['basis_set']]
        self.set_method()

        self.info['finished'] = 0x2

    @staticmethod
    def fingerprints(test_string):
        if '<i name="program" type="string">vasp' in test_string:
            return True
        return False

    def set_method(self):
        # Hamiltonians: Hubbard U method
        if self.incar.get("LDAU", False): # Check with the other xc?
            self.info['H'] = 'GGA+U'

            ldautype = self.incar.get("LDAUTYPE", self.parameters.get("LDAUTYPE"))[0]
            if ldautype == 2:
                self.info['H'] += '(std.)'
            elif ldautype == 1:
                self.info['H'] += '(Liecht.)'
            elif ldautype == 4:
                self.info['H'] = 'LDA+U(Liecht.)'
            else: self.info['H'] += '(type %s)' % ldautype

            us = self.incar.get("LDAUU", self.parameters.get("LDAUU")) # the effective on-site Coulomb interaction parameters
            js = self.incar.get("LDAUJ", self.parameters.get("LDAUJ")) # the effective on-site Exchange interaction parameters

            if len(us) != len(self.potcar_sequence):
                raise RuntimeError("Length of Hubbard U value parameters and atomic symbols are mismatched")

            atom_hubbard = {}
            for i in range(len(self.potcar_sequence)):
                if us[i] == 0 and js[i] == 0: continue
                repr = '%s/%s' % (round(us[i], 1), round(js[i], 1))
                if self.potcar_sequence[i] in atom_hubbard and atom_hubbard[ self.potcar_sequence[i] ] != repr:
                    n = 1
                    while True:
                        try:
                            atom_hubbard[ self.potcar_sequence[i] + str(n) ]
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
            if screening == 0.0:
                self.info['H'] = "PBE0"
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
        if self.incar.get("ISPIN", 1) == 2:
            self.info['spin'] = True

        # K-points TODO
        #if not self.kpoints.kpts: kpoints = 'x' + str(len(self.actual_kpoints))
        #else: kpoints = 'x'.join(map(str, self.kpoints.kpts[0]))
        #self.info['k'] = kpoints

def flatten_dict(d):
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            items.extend(flatten_dict(v).items())
        else:
            items.append((k, v))
    return dict(items)
