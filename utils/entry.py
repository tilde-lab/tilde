#!/usr/bin/env python
'''
Entry junction

Tilde is a general-purpose materials informatics framework
for intelligent organizers of the first-principles modeling data.
More info: https://tilde.pro

Author: Evgeny Blokhin
'''
import os, sys
import time
import logging
import argparse

from numpy import nan
from numpy.linalg import det

import chk_tilde_install

from tilde.core.settings import settings, connect_database, DATA_DIR, SETTINGS_PATH, DB_SCHEMA_VERSION
from tilde.core.common import write_cif, num2name
from tilde.core.symmetry import SymmetryFinder
from tilde.core.api import API

from ase.geometry import cell_to_cellpar


logging.basicConfig(level=logging.INFO)
starttime = time.time()
work = API()

parser = argparse.ArgumentParser(
    prog="[this_script]",
    usage="%(prog)s [positional / optional arguments]",
    epilog="API v%s, DB schema v%s (%s backend), settings from %s" % (API.version, DB_SCHEMA_VERSION, settings['db']['engine'], SETTINGS_PATH),
    argument_default=argparse.SUPPRESS
)
parser.add_argument("path", action="store", help="Scan file(s) / folder(s) / matching-filename(s), divide by space", metavar="PATH(S)/FILE(S)", nargs='*', default=False)
parser.add_argument("-y",   dest="symprec", action="store", help="symmetry detecting tolerance (default %.01e)" % SymmetryFinder.accuracy, type=float, metavar="float", nargs='?', const=None, default=None)
parser.add_argument("-r",   dest="recursive", action="store", help="scan recursively", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-t",   dest="terse", action="store", help="terse print during scan", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-a",   dest="add", action="store", help="add results to the database", type=str, metavar="N if sqlite", nargs='?', const=settings['db']['default_sqlite_db'], default=False)
parser.add_argument("-v",   dest="convergence", action="store", help="print calculation convergence", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-f",   dest="freqs", action="store", help="print phonons", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-i",   dest="info", action="store", help="print tags", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-m",   dest="module", action="store", help="invoke a module from the list", nargs='?', const=True, default=False, choices=list(work.Apps.keys()))
parser.add_argument("-s",   dest="structures", action="store", help="print the final lattice and the final atomic structure", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-c",   dest="cif", action="store", help="save i-th CIF structure in \"data\" folder", type=int, metavar="i", nargs='?', const=-1, default=False)
parser.add_argument("-x",   dest="service", action="store", help="print total number of items (use to create schema)", type=bool, metavar="", nargs='?', const=True, default=False)
parser.add_argument("-l",   dest="targetlist", action="store", help="file with scan targets", type=str, metavar="file", nargs='?', const=None, default=None)
args = parser.parse_args()

session = None

if not args.path and not args.service and not args.targetlist:
    #print __doc__
    sys.exit(parser.print_help())

# -a option
if args.add or args.service:
    if settings['db']['engine'] == 'sqlite':
        user_choice = args.add
    elif settings['db']['engine'] == 'postgresql':
        user_choice = None

    session = connect_database(settings, named=user_choice)
    if user_choice:
        print("The database selected:", user_choice)

# path(s)
if args.path or args.targetlist:
    finalized = 'YES' if settings['skip_unfinished'] else 'NO'
    notests = 'YES' if settings['skip_notenergy'] else 'NO'
    print("Only finalized: %s; only with total energy: %s; skip paths if they start/end with any of: %s" %
        (finalized, notests, settings['skip_if_path'])
    )

    if args.path and args.targetlist:
        args.targetlist = None
    if args.path:
        target_source = args.path
    if args.targetlist:
        if not os.path.exists(args.targetlist):
            sys.exit("Incorrect file: %s" % args.targetlist)
        target_source = (ln.strip() for ln in open(args.targetlist))

# -x option
elif args.service:
    sys.exit("Items in DB: %s" % work.count(session))

for target in target_source:

    if not os.path.exists(target):
        print('Target does not exist: ' + target)
        continue

    for task in work.savvyize(target, recursive=args.recursive, stemma=True):

        detected = False
        for calc, error in work.parse(task):
            output_lines, add_msg = '', ''

            if error:
                if args.terse and 'was read' in error:
                    continue
                logging.error("%s %s" % (task, error))
                continue

            calc, error = work.classify(calc, args.symprec)
            if error:
                logging.error("%s %s" % (task, error))
                continue

            logging.debug(task)
            header_line = (task + " (E=" + str(calc.info['energy']) + " eV)") if calc.info['energy'] else task
            if calc.info['warns']: add_msg = " (" + " ".join(calc.info['warns']) + ")"

            # -i option
            if args.info:
                found_topics = []
                skip_topics = {'location', 'elements', 'nelem', 'natom', 'spg', 'dtype', 'year', 'article_title', 'doi', 'pubdata'}
                for n, entity in enumerate(work.hierarchy):
                    if entity['cid'] > 1999 or entity['source'] in skip_topics:
                        continue # apps hierarchy

                    if entity['multiple']:
                        try:
                            found_topics.append(
                                [entity['category']] + [num2name(x, entity, work.hierarchy_values) for x in calc.info[ entity['source'] ]]
                            )
                        except KeyError:
                            pass
                    else:
                        try:
                            found_topics.append(
                                [entity['category'], num2name(calc.info.get(entity['source']), entity, work.hierarchy_values)]
                            )
                        except KeyError:
                            pass

                j, out = 0, ''
                for t in found_topics:
                    out += "\t" + t[0] + ': ' + ', '.join(map(str, t[1:]))
                    out += "\t" if not j % 2 else "\n"
                    j+=1
                output_lines += out[:-1] + "\n"

            # -v option
            if args.convergence:
                if calc.convergence:
                    output_lines += str(calc.convergence) + "\n"
                if calc.tresholds:
                    for n in range(len(calc.tresholds)):
                        try:
                            ncycles = calc.ncycles[n]
                        except IndexError:
                            ncycles = "^"
                        output_lines += "{:8f}".format(calc.tresholds[n][0] or nan) + "  " + \
                                        "{:8f}".format(calc.tresholds[n][1] or nan) + "  " + \
                                        "{:8f}".format(calc.tresholds[n][2] or nan) + "  " + \
                                        "{:8f}".format(calc.tresholds[n][3] or nan) + "  " + \
                                        "E={:12f}".format(calc.tresholds[n][4] or nan) + " eV" + "  " + \
                                        "(%s)" % ncycles + "\n"

            # -s option
            if args.structures:
                out = ''
                if len(calc.structures) > 1:
                    out += str(cell_to_cellpar(calc.structures[0].cell)) + " V=%2.2f" % (abs(det(calc.structures[0].cell))) + ' -> '
                out += str(cell_to_cellpar(calc.structures[-1].cell))
                out += " V=%2.2f\n" % calc.info['dims']
                for atom in calc.structures[-1]:
                    out += "\t%s %2.3f %2.3f %2.3f\t(q=%1.1f m=%1.1f)\n" % (atom.symbol, atom.x, atom.y, atom.z, atom.charge, atom.magmom)
                output_lines += out

            # -c option
            if args.cif:
                try:
                    calc.structures[args.cif]
                except IndexError:
                    output_lines += "Warning! Structure " + args.cif + " not found!" + "\n"
                else:
                    N = args.cif if args.cif > 0 else len(calc.structures) + 1 + args.cif
                    comment = calc.info['formula'] + " extracted from " + task + " (structure N " + str(N) + ")"
                    cif_file = os.path.realpath(os.path.abspath(DATA_DIR + os.sep + os.path.basename(task))) + '_' + str(args.cif) + '.cif'
                    if write_cif(cif_file, calc.structures[ args.cif ], comment):
                        output_lines += cif_file + " ready" + "\n"
                    else:
                        output_lines += "Warning! " + cif_file + " cannot be written!" + "\n"

            # -m option
            if args.module:
                if args.module is True:
                    calc = work.postprocess(calc, dry_run=True)
                    output_lines += "Modules to be invoked: " + str([item for item in calc.apps]) + "\n"
                else:
                    calc = work.postprocess(calc, args.module)
                    if args.module not in calc.apps:
                        output_lines += "Module \"" + args.module + "\" is not suitable for this case (outside the scope defined in module manifest)!" + "\n"
                    else:
                        out = str(calc.apps[args.module]['error']) if calc.apps[args.module]['error'] else str(calc.apps[args.module]['data'])
                        output_lines += out + "\n"

            # -f option
            if args.freqs:
                if not calc.phonons['modes']:
                    output_lines += 'no phonons'
                else:
                    for bzpoint, frqset in calc.phonons['modes'].items():
                        output_lines += "\tK-POINT: " + bzpoint + "\n"

                        for n in range(len(frqset)):
                            irreps = calc.phonons['irreps'].get(bzpoint)
                            irreps = irreps[n] if irreps else "?"
                            output_lines += "%d" % frqset[n] + " (" + irreps + ") " + (
                                ("\t" +
                                    ("IR = " if calc.phonons['ir_active'][n] else "-") +
                                        str(calc.phonons['ir_active'][n] or "-") + "\t\t\t" +
                                    ("Raman = " if calc.phonons['raman_active'][n] else "-") +
                                        str(calc.phonons['raman_active'][n] or "-")
                                ) if bzpoint == '0 0 0' and calc.phonons['ir_active'] and calc.phonons['raman_active'] else ""
                            ) + "\n"

            # -a option
            if args.add:
                checksum, error = work.save(calc, session)
                if error:
                    logging.error("%s %s" % (task, error))
                    continue
                header_line += ' added'
                detected = True

            if len(output_lines):
                output_lines = "\n" + output_lines

            print(header_line + add_msg + output_lines)

        if detected:
            logging.info(task + " successfully processed")
        # NB: from here the calc instance is not accessible anymore

if session:
    session.close()
if args.targetlist:
    target_source.close()

print("Done in %1.2f sc" % (time.time() - starttime))
