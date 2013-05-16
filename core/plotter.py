
import os
import sys
import math
from numpy import dot
from numpy import array
from numpy import linalg
from numpy import arange
from cubicspline import NaturalCubicSpline
from dos import TotalDos, PartialDos

sys.path.append(os.path.realpath(os.path.dirname(__file__) + '/deps'))
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

def plotter(task, **kwargs):
    if task == 'bands':
    
        results = []
        
        if not 'order' in kwargs: order = sorted( kwargs['values'].keys() )
        else: order = kwargs['order']
        
        nullstand = '0 0 0'
        if not '0 0 0' in kwargs['values']: # possible case when there is no Gamma point in VASP - WTF?
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
            y.append(kwargs['values'][nullstand][N])
            if d == 0: d+=0.5
            else: d += linalg.norm( bz_vec_ref )
            x.append(d)
            results[-1]['ticks'].append( [d, nullstand.replace(' ', '')] )
            
            divider = 10 if len(order)<10 else 1.5
            step = (max(x)-min(x)) / len(kwargs['values']) / divider
            
            xnew = arange(min(x), max(x)+step/2, step).tolist()
            ynew = []
            f = NaturalCubicSpline( array(x), array(y) )
            for i in xnew:
                results[-1]['data'].append([ round(  i, 3  ), round(  f(i), 3  ) ]) # round to reduce output

        return results
        
    elif task == 'dos':
        results = []
        
        if 'precomputed' in kwargs:
            total_dos = [[i, kwargs['precomputed']['total'][n]] for n, i in enumerate(kwargs['precomputed']['x'])]
            
        else:        
            # get the order of atoms to evaluate their partial impact
            labels = {}
            types = []        
            
            index, subtractor = 0, 0
            for k, atom in enumerate(kwargs['atomtypes']): # determine the order of atoms for the partial impact of every type
                if atom not in labels:
                    #if atom == 'Xx' and not calc.phonons: # artificial GHOST case for phonons, decrease atomic index
                    #    subtractor += 1
                    #    continue
                    labels[atom] = index
                    types.append([k+1-subtractor])
                    index += 1
                else:
                    types[ labels[atom] ].append(k+1-subtractor)

            tdos = TotalDos( kwargs['eigenvalues'], sigma=kwargs['sigma'] )
            tdos.set_draw_area(omega_min=kwargs['omega_min'], omega_max=kwargs['omega_max'], omega_pitch=kwargs['omega_pitch'])
            total_dos = tdos.calculate()
        
        results.append({'label':'total', 'color': '#000000', 'data': total_dos})
        
        if 'precomputed' in kwargs:
            partial_doses = []
            for k in kwargs['precomputed'].keys():
                if k in ['x', 'total']: continue
                partial_doses.append({ 'label': k, 'data': [[i, kwargs['precomputed'][k][n]] for n, i in enumerate(kwargs['precomputed']['x'])] })
            
        else:        
            pdos = PartialDos( kwargs['eigenvalues'], kwargs['impacts'], sigma=kwargs['sigma'] )
            pdos.set_draw_area(omega_min=kwargs['omega_min'], omega_max=kwargs['omega_max'], omega_pitch=kwargs['omega_pitch'])
            partial_doses = pdos.calculate( types, labels )
        
        # add colors to partials
        for i in range(len(partial_doses)):
            if partial_doses[i]['label'] == 'Xx': color = '#000000'
            elif partial_doses[i]['label'] == 'H': color = '#CCCCCC'
            else: color = jmol_to_hex( jmol_colors[ chemical_symbols.index(partial_doses[i]['label']) ] )
            partial_doses[i].update({'color': color})
        
        results.extend(partial_doses)        
        return results
        