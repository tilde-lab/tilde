
# libxc.py path/to/libxc_funcs.f90

import os, sys
import json
import pprint

try: libxc_master_loc = sys.argv[1]
except IndexError: sys.exit('libxc_funcs.f90 path is needed')

libxc_db = {}

f = open(libxc_master_loc)
for line in f:
    m1 = line.find(' XC_')
    m2 = line.find('=')
    if m1>0 and m2>0:
        name = line[m1:m2].strip()        
        num_and_c = line[m2 + 1:].split(None, 2)
        number = int(num_and_c[0])
        comment = num_and_c[2].strip()
        libxc_db[number] = {'name': name, 'comment': comment}
#print json.dumps(libxc_db)
pp = pprint.PrettyPrinter(width=500)
pp.pprint(libxc_db)
