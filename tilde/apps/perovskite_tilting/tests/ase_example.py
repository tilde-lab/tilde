'''
An example of using Tilting module with ASE
'''

from ase.lattice.spacegroup import crystal

import set_path
from tilde.core.settings import settings
from tilde.core.api import API
from tilde.parsers import Output


crystal_obj = crystal(
    ('Sr', 'Ti', 'O', 'O'),
    basis=[(0, 0.5, 0.25), (0, 0, 0), (0, 0, 0.25), (0.255, 0.755, 0)],
    spacegroup=140, cellpar=[5.511, 5.511, 7.796, 90, 90, 90],
    primitive_cell=True
)

settings['skip_unfinished'], settings['skip_notenergy'] = False, False
work = API(settings)

searched_category = (8, 'perovskite')       # defined in /init-data.sql
searched_category_id = None                 # defined in hierarchy
found = False
for cid, series in work.hierarchy_values.iteritems():
    if found: break
    elif cid == searched_category[0]:
        for num, name in series.iteritems():
            if name == searched_category[1]:
                found, searched_category_id = True, num
                break
else: raise RuntimeError("Cannot determine the category id in the hierarchy!")

virtual_calc = Output() # we always consider "calculation" while using tilde
virtual_calc.structures = [ crystal_obj ]
virtual_calc, error = work.classify(virtual_calc)
if error:
    raise RuntimeError(error)

virtual_calc = work.postprocess(virtual_calc)
is_perovskite = searched_category_id in virtual_calc.info['tags']

print "Object:", virtual_calc.info['standard']
print "Is perovskite?", is_perovskite
if is_perovskite:
    print virtual_calc.apps
    #print "Extracted tilting is:", virtual_calc.apps['perovskite_tilting']['data']
