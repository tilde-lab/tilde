
# Tilde project: plotting interfaces
# for flot.js browser-side plotting library
# Author: Evgeny Blokhin

import math

from numpy import dot, array, linalg, arange

from tilde.berlinium.cubicspline import NaturalCubicSpline
from tilde.berlinium.dos import TotalDos, PartialDos

from ase.data.colors import jmol_colors
from ase.data import chemical_symbols


def frac2float(num):
    if '/' in str(num):
        fract = map(float, num.split('/'))
        return fract[0] / fract[1]
    else: return float(num)

def jmol_to_hex(ase_jmol):
    r, g, b = map(lambda x: x*255, ase_jmol)
    return '#%02x%02x%02x' % ( r, g, b )

def bdplotter(task, **kwargs):
    '''
    bdplotter is based on the fact that phonon DOS/bands and
    electron DOS/bands are the objects of the same kind.
    1) DOS is formatted precomputed / smeared according to a normal distribution
    2) bands are formatted precomputed / interpolated through natural cubic spline function
    '''
    if task == 'bands': # CRYSTAL, "VASP", EXCITING

        results = []

        if 'precomputed' in kwargs:
            for n in range(len(kwargs['precomputed']['ticks'])):
                if kwargs['precomputed']['ticks'][n][1] == 'GAMMA': kwargs['precomputed']['ticks'][n][1] = '&#915;'

            for stripe in kwargs['precomputed']['stripes']:
                results.append({'color':'#000000', 'data':[], 'ticks':kwargs['precomputed']['ticks']})
                for n, val in enumerate(stripe):
                    results[-1]['data'].append([ kwargs['precomputed']['abscissa'][n], val])

        else:
            if not 'order' in kwargs: order = sorted( kwargs['values'].keys() ) # TODO
            else: order = kwargs['order']

            nullstand = '0 0 0'
            if not '0 0 0' in kwargs['values']: # possible case when there is shifted Gamma point
                nullstand = order[0]

            # reduce k if too much
            if len(order)>20:
                red_order = []
                for i in range(0, len(order), int(math.floor(len(order)/10))):
                    red_order.append(order[i])
                order = red_order

            for N in range(len( kwargs['values'][nullstand] )):
                # interpolate for each curve throughout the BZ
                results.append({'color':'#000000', 'data':[], 'ticks':[]})
                d = 0.0
                x = []
                y = []
                bz_vec_ref = [0, 0, 0]

                for bz in order:
                    y.append( kwargs['values'][bz][N] )
                    bz_coords = map(frac2float, bz.split() )
                    bz_vec_cur = dot( bz_coords, linalg.inv( kwargs['xyz_matrix'] ).transpose() )
                    bz_vec_dir = map(sum, zip(bz_vec_cur, bz_vec_ref))
                    bz_vec_ref = bz_vec_cur
                    d += linalg.norm( bz_vec_dir )
                    x.append(d)
                    results[-1]['ticks'].append( [d, bz.replace(' ', '')] )

                # end in nullstand point (normally, Gamma)
                #y.append(kwargs['values'][nullstand][N])
                #if d == 0: d+=0.5
                #else: d += linalg.norm( bz_vec_ref )
                #x.append(d)
                #results[-1]['ticks'].append( [d, nullstand.replace(' ', '')] )

                divider = 10 if len(order)<10 else 1.5
                step = (max(x)-min(x)) / len(kwargs['values']) / divider

                xnew = arange(min(x), max(x)+step/2, step).tolist()
                ynew = []
                f = NaturalCubicSpline( array(x), array(y) )
                for i in xnew:
                    results[-1]['data'].append([ round(  i, 3  ), round(  f(i), 3  ) ]) # round to reduce output

        return results

    elif task == 'dos': # CRYSTAL, VASP, EXCITING

        results = []

        if 'precomputed' in kwargs:
            total_dos = [[i, kwargs['precomputed']['total'][n]] for n, i in enumerate(kwargs['precomputed']['x'])]

        else:
            tdos = TotalDos( kwargs['eigenvalues'], sigma=kwargs['sigma'] )
            tdos.set_draw_area(omega_min=kwargs['omega_min'], omega_max=kwargs['omega_max'], omega_pitch=kwargs['omega_pitch'])
            total_dos = tdos.calculate()

        results.append({'label':'total', 'color': '#000000', 'data': total_dos})

        if 'precomputed' in kwargs:
            partial_doses = []
            for k in kwargs['precomputed'].keys():
                if k in ['x', 'total']: continue
                partial_doses.append({ 'label': k, 'data': [[i, kwargs['precomputed'][k][n]] for n, i in enumerate(kwargs['precomputed']['x'])] })

        elif 'impacts' in kwargs and 'atomtypes' in kwargs:
            # get the order of atoms to evaluate their partial impact
            labels = {}
            types = []
            index, subtractor = 0, 0
            for k, atom in enumerate(kwargs['atomtypes']): # determine the order of atoms for the partial impact of every type
                if atom not in labels:
                    #if atom == 'X' and not calc.phonons: # artificial GHOST case for phonons, decrease atomic index
                    #    subtractor += 1
                    #    continue
                    labels[atom] = index
                    types.append([k+1-subtractor])
                    index += 1
                else:
                    types[ labels[atom] ].append(k+1-subtractor)

            pdos = PartialDos( kwargs['eigenvalues'], kwargs['impacts'], sigma=kwargs['sigma'] )
            pdos.set_draw_area(omega_min=kwargs['omega_min'], omega_max=kwargs['omega_max'], omega_pitch=kwargs['omega_pitch'])
            partial_doses = pdos.calculate( types, labels )

            # add colors to partials
            for i in range(len(partial_doses)):
                if partial_doses[i]['label'] == 'X': color = '#000000'
                elif partial_doses[i]['label'] == 'H': color = '#CCCCCC'
                else:
                    try: color = jmol_to_hex( jmol_colors[ chemical_symbols.index(partial_doses[i]['label']) ] )
                    except ValueError: color = '#FFCC66'
                partial_doses[i].update({'color': color})
            results.extend(partial_doses)

        return results


def eplotter(task, data): # CRYSTAL, VASP, EXCITING
    '''
    eplotter is like bdplotter but less complicated
    '''
    results, color, fdata = [], None, []

    if task == 'optstory':
        color = '#CC0000'
        clickable = True
        for n, i in enumerate(data):
            fdata.append([n, i[4]])
        fdata = array(fdata)
        fdata[:,1] -= min(fdata[:,1]) # this normalizes values to minimum (by 2nd col)
        fdata = fdata.tolist()

    elif task == 'convergence':
        color = '#0066CC'
        clickable = False
        for n, i in enumerate(data):
            fdata.append([n, i])

    for n in range(len(fdata)):
        #fdata[n][1] = "%10.5f" % fdata[n][1]
        fdata[n][1] = round(fdata[n][1], 5)

    results.append({'color': color, 'clickable:': clickable, 'data': fdata})
    return results
