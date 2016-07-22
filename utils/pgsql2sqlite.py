#!/usr/bin/env python

from __future__ import print_function

import os, sys


try: target = sys.argv[1]
except IndexError:
    print('Usage: %s path_to_postgres_dump_in_SQL_format' % os.path.basename(sys.argv[0]))
    sys.exit(1)

if not os.path.exists(target):
    print('File does not exist')
    sys.exit(1)

if target.endswith('.sql'): result = target + 'ite'
else: result = target + '.sqlite'

if os.path.exists(result):
    print('Result file exists')
    sys.exit(1)

with open(result, "w") as r:
    r.write("BEGIN;\n")
    with open(target) as f:
        for line in f:
            if line.startswith('SET') or line.startswith('SELECT pg_catalog.setval'): continue
            line = line.replace('TRUE', '1').replace('true', '1').replace('FALSE', '0').replace('false', '0') # FIXME
            r.write(line)
    r.write("END;\n")

sys.exit(0)
