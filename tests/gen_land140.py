#!/usr/bin/env python

import sys
import os
import math
import json

sys.path.insert(0, '/home/eb/wwwtilda/core/deps')

from ase.units import Bohr
from ase.lattice.spacegroup import crystal
from ase.calculators.exciting import Exciting
from ase.lattice.spacegroup.cell import cell_to_cellpar

sys.path.insert(0, os.path.realpath(os.path.dirname(__file__) + '/../'))
import psycopg2

from core.common import dict2ase
from core.settings import check_db_version


curdir = os.path.realpath(os.path.dirname(__file__))
basedir = curdir + os.sep + 'workdir'
calcdir = basedir + os.sep + 'calc_'
bin = "dummy" #"/usr/global/mpi/bin/mpirun -np 4 /home/eb/software/mortadella/bin/excitingmpi"
speciespath = '/scratch/eb/sto140'

if not os.path.exists(basedir): os.makedirs(basedir)

db = psycopg2.connect("dbname=tilde user=eb")
cursor = db.cursor()

# check DB_SCHEMA_VERSION
incompatible = check_db_version(db)
if incompatible:
    sys.exit('Sorry, database ' + workpath + ' is incompatible.')

# ^^^ above was the obligatory formal code, the actual procedures of interest are below VVV

try: cursor.execute( 'SELECT structures FROM results' )
except: sys.exit('Fatal error: ' + "%s" % sys.exc_info()[1])

p=1
while 1:
    row = cursor.fetchone()
    if not row: break
    
    target = dict2ase( json.loads(row[0])[-1] )  
    
    # define ASE object extensions
    rmts = {'Sr':1.6*Bohr, 'Ti':1.6*Bohr, 'O':1.6*Bohr}
    speciesfiles = {'Sr':'Sr.xml', 'Ti':'Ti.xml', 'O':'O_n.xml'}

    # apply ASE object extensions
    rmt_array, speciesfiles_array = [], []
    for i in target:    
        rmt_array.append(rmts[i.symbol])
        speciesfiles_array.append(speciesfiles[i.symbol])
    target.new_array('rmt', rmt_array, float)
    target.new_array('speciesfiles', speciesfiles_array, str)

    calc = Exciting(dir=calcdir + "%s" % p, bin=bin, speciespath=speciespath, paramdict={"title":{"text()": "STO140 landscape optimization"},
        "groundstate":{"xctype": "GGA_PBE", "gmaxvr": "16", "epsengy": "1d-5", "maxscl": "75", "fracinr": "2d-2", "SymmetricKineticEnergy": "true", "lorecommendation": "false", "ngridk": "8 8 8", "rgkmax": "9"},
        "properties":{
        "dos":{},
        "bandstructure":{
            "plot1d":{
            "path":{
            "steps": "75",
            "point":[
            # here all the points are not from Bilbao server, but from Heifets article
            {"coord":"0.0 0.0 0.0", "label":"GAMMA"},
            {"coord":"-0.25 0.75 -0.25", "label":"P"},
            {"coord":"-0.5 0.5 0.0", "label":"X"},
            {"coord":"0.0 0.0 0.0", "label":"GAMMA"},
            {"coord":"0.5 0.5 -0.5", "label":"Z"}, # point introduced by Heifets
            {"coord":"0.25 0.75 -0.5", "label":"Q"}, # point introduced by Heifets
            {"coord":"0.0 0.0 0.0", "label":"GAMMA"},
            {"coord":"0.0 0.5 0.0", "label":"N"},
            ]}}}}})
    
    p+=1 
    target.set_calculator(calc)
    
    # to generate input files but not run them
    try: target.get_potential_energy()
    except: pass
