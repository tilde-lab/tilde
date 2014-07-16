
# example of ORM usage

import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps'))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, String, Table, Column, Boolean, Float, Integer, Text, ForeignKey, desc, exists
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from ase.atoms import Atoms
from ase.data import chemical_symbols

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps/ase/lattice'))
from spacegroup.cell import cell_to_cellpar

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.model import Base, Simulation, Auxiliary, Structure, Lattice_basis, Atom, Spacegroup, Struct_ratios
from core.api import API
from core.symmetry import SymmetryHandler

engine = create_engine('sqlite:///' + os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/test.db'), echo=False)
Session = sessionmaker(bind=engine)
session = Session()


if __name__ == '__main__':

    Base.metadata.create_all(engine)

    try: workpath = sys.argv[1]
    except IndexError:

        # R of CRUD

        formula_calculator = API()
        flag, pos, formula_box = None, [], []
        
        query = session.query(Structure, Struct_ratios, Spacegroup). \
            filter(Structure.id == Struct_ratios.struct_id). \
            filter(Structure.id == Spacegroup.struct_id). \
            order_by(desc(Structure.id))
        
        for struct, rat, symm in query.all():
            
            print struct.id, rat.chemical_formula, symm.n

    else: # C of CRUD

        workpath = os.path.abspath(workpath)
        if not os.path.exists(workpath): sys.exit('Invalid path!')

        work = API()

        tasks = work.savvyize(workpath, True) # True means recursive

        for task in tasks:
            print "Processing file:", task
            filename = os.path.basename(task)

            calc, error = work.parse(task)
            if error:
                print filename, error
                continue

            calc, error = work.classify(calc)
            if error:
                print filename, error
                continue
            
            checksum = calc.get_checksum()
            
            (already, ), = session.query(exists().where(Simulation.checksum==checksum))
            if already: continue
            
            sim = Simulation(checksum=checksum)
            sim.auxiliaries = Auxiliary(location = calc.info['location'], finished = calc.info['finished'])
            
            for n, ase_repr in enumerate(calc.structures):
                
                struct = Structure()
                
                if n == len(calc.structures)-1:
                    found = SymmetryHandler(calc)
                    if found.error: sys.exit(task, found.error)
                    struct.spacegroup = Spacegroup(n=found.n)

                s = cell_to_cellpar(ase_repr.cell)
                struct.lattice_basis = Lattice_basis(a=s[0], b=s[1], 
                c=s[2], alpha=s[3], beta=s[4], gamma=s[5], 
                a11=ase_repr.cell[0][0], a12=ase_repr.cell[0][1], 
                a13=ase_repr.cell[0][2], a21=ase_repr.cell[1][0], 
                a22=ase_repr.cell[1][1], a23=ase_repr.cell[1][2], 
                a31=ase_repr.cell[2][0], a32=ase_repr.cell[2][1], 
                a33=ase_repr.cell[2][2])
                struct.struct_ratios = Struct_ratios(chemical_formula=calc.info['standard'], formula_units=calc.info['expanded'])

                for i in ase_repr:
                    struct.atoms.append( Atom( number=chemical_symbols.index(i.symbol), x=i.x, y=i.y, z=i.z ) )
                
                sim.structures.append(struct)
                
            session.add(sim)
            
        session.commit()
        
    session.close()
