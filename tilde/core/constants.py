
# Data bank of various const values
# Author: Evgeny Blokhin

from __future__ import division
from math import pi, sqrt


# Phonopy constants, extended
# initial compilation by Atsushi Togo, http://phonopy.sf.net

class Constants:
    kb_J = 1.3806504e-23 # [J/K]
    PlanckConstant = 4.13566733e-15 # [eV s]
    Hbar = PlanckConstant/(2*pi) # [eV s]
    Avogadro = 6.02214179e23
    SpeedOfLight = 299792458 # [m/s]
    AMU = 1.6605402e-27 # [kg]
    Newton = 1.0        # [kg m / s^2]
    Joule = 1.0         # [kg m^2 / s^2]
    EV = 1.60217733e-19 # [J]
    Angstrom = 1.0e-10  # [m]
    THz = 1.0e12        # [/s]
    Mu0 = 4.0e-7 * pi
    Epsilon0 = 1.0 / Mu0 / SpeedOfLight**2
    Me = 9.10938215e-31

    Bohr = 4e10 * pi * Epsilon0 * Hbar**2 / Me  # Bohr radius [A] 0.5291772
    Hartree = Me * EV / 16 / pi**2 / Epsilon0**2 / Hbar**2 # Hartree [eV] 27.211398
    Rydberg = Hartree / 2 # Rydberg [eV] 13.6056991

    THzToEv = PlanckConstant * 1e12 # [eV]
    Kb = kb_J / EV  # [eV/K] 8.6173383e-05
    THzToCm = 1.0e12 / (SpeedOfLight * 100) # [cm^-1] 33.356410
    CmToEv = THzToEv / THzToCm # [eV] 1.2398419e-4
    VaspToEv = sqrt(EV/AMU)/Angstrom/(2*pi)*PlanckConstant # [eV] 6.46541380e-2
    VaspToTHz = sqrt(EV/AMU)/Angstrom/(2*pi)/1e12 # [THz] 15.633302
    VaspToCm =  VaspToTHz * THzToCm # [cm^-1] 521.47083
    EvTokJmol = EV / 1000 * Avogadro # [kJ/mol] 96.4853910
    Wien2kToTHz = sqrt(Rydberg/1000*EV/AMU)/(Bohr*1e-10)/(2*pi)/1e12 # [THz] 3.44595837
    EVAngstromToGPa = EV * 1e21

    ha2rcm = 2.194746313708e05

    kJmolToAucel = 0.00038088
    cm2THz = 0.0299792458


# Perovskite elements

class Perovskite_Structure:
    A = 'Li, Na, K, Rb, Cs, Fr, Mg, Ca, Sr, Ba, Ra, Sc, Sc, Y, La, Ce, Pr, Nd, Pm, Sm, Eu, Gd, Tb, Dy, Ho, Er, Tm, Yb, Lu, Ag, Pb, Bi, Th, In, Mn, Zn'.split(', ')
    B = 'Ti, V, Cr, Mn, Fe, Co, Ni, Cu, Zn, Ga, Zr, Nb, Mo, Tc, Ru, Rh, Pd, Ag, Cd, In, Sn, Sb, Hf, Ta, W, Re, Se, La, Pr'.split(', ')
    C = 'O, F'.split(', ') # todo: add elements to C site
