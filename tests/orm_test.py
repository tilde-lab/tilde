
# example of ORM usage

import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps'))
from sqlalchemy import create_engine, MetaData, String, Table, Column, Boolean, Float, Integer, Text, ForeignKey, desc
from sqlalchemy.orm import mapper, relationship, sessionmaker, backref
from sqlalchemy.ext.declarative import declarative_base

from ase.atoms import Atoms

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../core/deps/ase/lattice'))
from spacegroup.cell import cell_to_cellpar

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/../'))
from core.api import API
from core.symmetry import SymmetryHandler

Base = declarative_base()
engine = create_engine('sqlite:///' + os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/test.db'), echo=False)
Session = sessionmaker(bind=engine)
session = Session()


class Structure(Base):
    __tablename__ = 'structures'
    id = Column(Integer, primary_key=True)
    lattice_basis = relationship("Lattice_basis", uselist=False, backref="structures", cascade="all, delete, delete-orphan")
    atoms = relationship("Atom", backref="structures")
    spacegroup = relationship("Spacegroup", uselist=False, backref="structures", cascade="all, delete, delete-orphan")
    struct_ratios = relationship("Struct_ratios", uselist=False, backref="struct_ratios", cascade="all, delete, delete-orphan")

class Lattice_basis(Base):
    __tablename__ = 'lattice_basises'
    id = Column(Integer, primary_key=True)
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    c = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    beta = Column(Float, nullable=False)
    gamma = Column(Float, nullable=False)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)

class Atom(Base):
    __tablename__ = 'atoms'
    id = Column(Integer, primary_key=True)
    element = Column(String, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    charge = Column(Float, default=0)
    magmom = Column(Float, default=0)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)

class Spacegroup(Base):
    __tablename__ = 'spacegroup'
    id = Column(Integer, primary_key=True)
    n = Column(Integer, nullable=False)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)

class Struct_ratios(Base):
    __tablename__ = 'struct_ratios'
    id = Column(Integer, primary_key=True)
    chemical_formula = Column(String, nullable=False)
    is_primitive = Column(Boolean, default=False)
    formula_units = Column(Float, nullable=False)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)


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

            my_struct = Structure()

            ase_repr = calc.structures[-1]
            
            found = SymmetryHandler(calc)
            if found.error:
                print found.error
                continue
            my_struct.spacegroup = Spacegroup(n=found.i)

            s = cell_to_cellpar(ase_repr.cell)
            my_struct.lattice_basis = Lattice_basis(a=s[0], b=s[1], c=s[2], alpha=s[3], beta=s[4], gamma=s[5])
            my_struct.struct_ratios = Struct_ratios(chemical_formula=calc.info['standard'], formula_units=calc.info['expanded'])

            for i in ase_repr:
                my_struct.atoms.append( Atom( element=i.symbol, x=i.x, y=i.y, z=i.z ) )

            session.add(my_struct)
            session.commit()
