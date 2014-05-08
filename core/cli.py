#!/usr/bin/env python
#
# Tilde project: cross-platform entry point
# this is a junction; all the end user actions are done from here
# v080514

import sys
import os
import subprocess
import json
import time

starttime = time.time() # benchmarking

if sys.version_info < (2, 6):
    sys.exit('\n\nI cannot proceed. Your python is too old. At least version 2.6 is required!\n\n')

try: import argparse
except ImportError: from deps.argparse import argparse

try:
    from numpy import dot
    from numpy import array
    from numpy.linalg import det
except ImportError: sys.exit('\n\nI cannot proceed. Please, install numerical python (numpy)!\n\n')

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))

from settings import settings, connect_database, user_db_choice, check_db_version, repositories, DATA_DIR
from common import write_cif
from symmetry import SymmetryFinder
from api import API

from deps.ase.lattice.spacegroup.cell import cell_to_cellpar


registered_modules = []
for appname in os.listdir( os.path.realpath(os.path.dirname(__file__) + '/../apps') ):
    if os.path.isfile( os.path.realpath(os.path.dirname(__file__) + '/../apps/' + appname + '/manifest.json') ):
        registered_modules.append(appname)

parser = argparse.ArgumentParser(prog="[this_script]", usage="%(prog)s [positional / optional arguments]", epilog="Version: "+API.version+" (" + settings['db']['type'] + " backend)", argument_default=argparse.SUPPRESS)

parser.add_argument("path", action="store", help="Scan file(s) / folder(s) / matching-filename(s), divide by space", metavar="PATH(S)/FILE(S)", nargs='*', default=False)
parser.add_argument("-u", dest="daemon", action="store", help="run GUI service (default)", nargs='?', const='shell', default=False, choices=['shell', 'noshell'])
parser.add_argument("-a", dest="add", action="store", help="if PATH(S): add results to database", type=str, metavar="file.db", nargs='?', const='DIALOG', default=False)
parser.add_argument("-r", dest="recursive", action="store", help="scan recursively", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-t", dest="terse", action="store", help="terse print", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-v", dest="convergence", action="store", help="calculation convergence print", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-f", dest="freqs", action="store", help="if PATH(S): extract and print phonons", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-i", dest="info", action="store", help="if PATH(S): analyze all", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-m", dest="module", action="store", help="if PATH(S): invoke a module", nargs='?', const=False, default=False, choices=registered_modules)
parser.add_argument("-s", dest="structures", action="store", help="if PATH(S): show lattice", type=int, metavar="i", nargs='?', const=True, default=False)
parser.add_argument("-c", dest="cif", action="store", help="if FILE: save i-th CIF structure in \"data\" folder", type=int, metavar="i", nargs='?', const=-1, default=False)
parser.add_argument("-y", dest="symprec", action="store", help="symmetry detecting tolerance (default %.01e)" % SymmetryFinder.accuracy, type=float, metavar="N", nargs='?', const=None, default=None)
parser.add_argument("-x", dest="xdebug", action="store", help="debug", type=bool, metavar="", nargs='?', const=True, default=None)
parser.add_argument("-d", dest="datamining", action="store", help="query on data (experimental)", type=str, metavar="QUERY", nargs='?', const='COUNT(*)', default=None)

args = parser.parse_args()

if settings['demo_regime']: print "\nRestricted mode (demo_regime): on\n"

# GUI
# WHEN: run GUI service daemon if no other commands are given

if not args.path and not args.daemon and not args.datamining: #if not len(vars(args)):
    args.daemon = 'shell'
if args.daemon:
    print "\nPlease, wait a bit while Tilde application is starting.....\n"

    # invoke windows GUI frame
    if args.daemon == 'shell' and 'win' in sys.platform and not settings['debug_regime'] and not settings['demo_regime']:
       subprocess.Popen(sys.executable + ' ' + os.path.realpath(os.path.dirname(__file__)) + '/winui.py')

    # replace current process with Tilde daemon process
    try:
        os.execv(sys.executable, [sys.executable, os.path.realpath(os.path.dirname(__file__)) + '/daemon.py'])
    except OSError: # taken from Tornado
        os.spawnv(os.P_NOWAIT, sys.executable, [sys.executable, os.path.realpath(os.path.dirname(__file__)) + '/daemon.py'])

    sys.exit()

if not args.path and not args.datamining:
    parser.print_help()
    sys.exit()

# CLI
# WHEN: if there are particular commands, run command-line text interface
    
db = None
if args.add:
    
    user_choice = None
    
    if settings['db']['type'] == 'sqlite':
        if args.add == 'DIALOG':
            user_choice = user_db_choice(repositories) # NB. this spoils benchmarking
        else:
            user_choice = user_db_choice(repositories, choice=args.add) # NB. this spoils benchmarking

        if not os.access(os.path.abspath(DATA_DIR + os.sep + user_choice), os.W_OK): sys.exit("Sorry, database file is write-protected!")
    
    elif settings['db']['type'] == 'postgres':
        pass    
    
    db = connect_database(settings, user_choice) # NB. at this stage DB connection is already checked
    
    # check DB_SCHEMA_VERSION
    incompatible = check_db_version(db)
    if incompatible:
        if user_choice: uc = DATA_DIR + os.sep + user_choice # sqlite
        else: uc = 'at server' # postgres
        sys.exit('Sorry, database ' + uc + ' is incompatible.')
    else:
        if user_choice: print "The database selected:", user_choice
    
if args.datamining:
    
    user_choice = None
    
    if settings['db']['type'] == 'sqlite':
        user_choice = user_db_choice(repositories, create_allowed=False) # NB. this spoils benchmarking
    
    db = connect_database(settings, user_choice) # NB. at this stage DB connection is already checked
    
    # check DB_SCHEMA_VERSION
    incompatible = check_db_version(db)
    if incompatible:
        if user_choice: uc = DATA_DIR + os.sep + user_choice # sqlite
        else: uc = 'at server' # postgres
        sys.exit('Sorry, database ' + uc + ' is incompatible.')
    else:
        if user_choice: print "The database selected:", user_choice

Tilde = API(db_conn=db, settings=settings)

if args.path:
    if settings['skip_unfinished']: finalized = 'YES'
    else: finalized = 'NO'
    print "Only finalized:", finalized, "and skip paths if they start/end with any of:", settings['skip_if_path']

# PROCESSING THE CALCULATIONS IN THE DATABASE
# (ONLY EXPERIMENTAL SUPPORT HERE, REFER TO MINERS IN TESTS FOLDER FOR FURTHER INFO)

if args.datamining:
    N = 10
    cursor = db.cursor()
    
    clause, statement = [], []
    input = args.datamining.split()
    for word in input:
        if '=' in word or '>' in word or '<' in word:
            clause.append(word)
        else:
            statement.append(word)
    
    statement = ", ".join(statement) if len(statement) else 'COUNT(*)'
    statement = 'SELECT ' + statement + ' FROM results'
    clause = ' WHERE ' + " AND ".join(clause) if len(clause) else ""
    out, postmessage = '', ''
    query = statement + clause
    
    print 'Query: ' + query
    
    try: cursor.execute( query ) # this is risky, but we trust our user
    except: print 'Error for query: ' + "%s" % sys.exc_info()[1]
    else:
        result = cursor.fetchall()
        postmessage = ''
        L = len(result)
        if L > 50:
            result = result[:50]
            postmessage = "\n...\n%s more" % (L-50)        
        i=0
        for row in result:
            if settings['db']['type'] == 'sqlite':
                if i==0: out += " ".join( row.keys() ) + "\n"
                for k in row.keys():
                    out += str(row[k]) + " "
            elif settings['db']['type'] == 'postgres':
                out += str(row)
            out += "\n"
            i+=1
    print out + postmessage
    db.close()
    sys.exit()

# PROCESSING THE CALCULATIONS AT THE TARGET PATHS IN FILE SYSTEM
# (BASIC USAGE)

for target in args.path:
    
    if not os.path.exists(target):
        print 'Target does not exist: ' + target
        continue

    tasks = Tilde.savvyize(target, recursive=args.recursive, stemma=True)

    for task in tasks:
        filename = os.path.basename(task)
        output_lines, add_msg = '', ''

        calc, error = Tilde.parse(task)
        if error:
            if args.terse and 'nothing found' in error: continue
            else: print task, error
            continue

        calc, error = Tilde.classify(calc, args.symprec)
        if error:
            print task, error
            continue

        header_line = task + " (E=" + str(calc.energy) + " eV)"
        if calc.info['warns']: add_msg = " (" + " ".join(calc.info['warns']) + ")"
        
        if args.info:
            found_topics = []
            skip_topics = ['location', 'refinedcell', 'element#', 'nelem', 'natom', ]
            for n, i in enumerate(Tilde.hierarchy):
                if i['cid'] > 1999 or i['source'] in skip_topics: continue # apps hierarchy
                if '#' in i['source']:
                    n=0
                    while 1:
                        try: topic = calc.info[ i['source'].replace('#', str(n)) ]
                        except KeyError:
                            if 'negative_tagging' in i and n==0: found_topics.append( [ i['category'], 'none' ] )
                            break
                        else:
                            if n==0: found_topics.append( [ i['category'], topic ] )
                            else: found_topics[-1].append( topic )
                            n+=1
                else:
                    try: found_topics.append( [   i['category'], calc.info[ i['source'] ]   ] )
                    except KeyError:
                        if 'negative_tagging' in i: found_topics.append( [ i['category'], 'none' ] )

            j, out = 0, ''
            for t in found_topics:
                out += "\t" + t[0] + ': ' + ', '.join(map(str, t[1:]))
                out += "\t" if not j%2 else "\n"
                j+=1
            output_lines += out[:-1] + "\n"

        if args.convergence:
            if calc.info['convergence']:
                output_lines += str(calc.info['convergence']) + "\n"
            if calc.info['tresholds']:
                for i in range(len(calc.info['tresholds'])):
                    output_lines += "%1.2e" % calc.info['tresholds'][i][0] + " "*2 + "%1.5f" % calc.info['tresholds'][i][1] + " "*2 + "%1.4f" % calc.info['tresholds'][i][2] + " "*2 + "%1.4f" % calc.info['tresholds'][i][3] + " "*2 + "E=" + "%1.4f" % calc.info['tresholds'][i][4] + " eV" + " "*2 + "(%s)" % calc.info['ncycles'][i] + "\n"
            
        if args.structures:
            out = ''
            if len(calc.structures) > 1:
                out += str(cell_to_cellpar(calc.structures[0].cell)) + " V=%2.2f" % (abs(det(calc.structures[0].cell))) + ' -> '
            out += str(cell_to_cellpar(calc.structures[-1].cell))
            out += " V=%2.2f" % calc.info['dims']
            output_lines += out + "\n"
        
        if args.cif:
            try: calc.structures[ args.cif ]
            except IndexError: output_lines += "Warning! Structure "+args.cif+" not found!" + "\n"
            else:
                N = args.cif if args.cif>0 else len(calc.structures) + 1 + args.cif
                comment = calc.info['formula'] + " extracted from " + task + " (structure N " + str(N) + ")"
                cif_file = os.path.realpath(os.path.abspath(DATA_DIR + os.sep + filename)) + '_' + str(args.cif) + '.cif'
                if write_cif(cif_file, calc.structures[ args.cif ], comment):
                    output_lines += cif_file + " ready" + "\n"
                else:
                    output_lines += "Warning! " + cif_file + " cannot be written!" + "\n"        
        
        if args.module:
            hooks = Tilde.postprocess(calc)
            if args.module not in hooks: output_lines += "Module \"" + args.module + "\" is not suitable for this case (outside the scope defined in module manifest)!" + "\n"
            else:
                out = str(hooks[args.module]['error']) if hooks[args.module]['error'] else str(hooks[args.module]['data'])
                output_lines += out + "\n"
            
        if args.xdebug:
            output_lines += str(calc) + "\n"

        if args.freqs:
            if not calc.phonons['modes']:
                output_lines += 'no phonons'
            else:
                for bzpoint, frqset in calc.phonons['modes'].iteritems():
                    output_lines += "\tK-POINT: " + bzpoint + "\n"
                    compare = 0
                    for i in range(len(frqset)):
                        # if compare == frqset[i]: continue
                        output_lines += "%d" % frqset[i] + " (" + calc.phonons['irreps'][bzpoint][i] + ")" + "\n"
                        compare = frqset[i]
                    
        if args.add:
            checksum, error = Tilde.save(calc)
            if error:
                print task, error
                continue
            header_line += ' added'
        
        
        if len(output_lines): output_lines = "\n" + output_lines
        print header_line + add_msg + output_lines
        # NB: from here the calc instance is not functional anymore!

if db: db.close()
print "Done in %1.2f sc" % (time.time() - starttime)
