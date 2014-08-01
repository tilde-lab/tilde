
import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps'))
from sqlalchemy import MetaData, String, Table, Column, Boolean, Float, Integer, Text, ForeignKey, and_
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import UniqueConstraint


Base = declarative_base()

# https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/UniqueObject

def _unique(session, cls, queryfunc, constructor, arg, kw):
    with session.no_autoflush:
        q = session.query(cls)
        q = queryfunc(q, *arg, **kw)
        obj = q.first()
        if not obj:
            obj = constructor(*arg, **kw)
            session.add(obj)
    return obj

class UniqueMixin(object):
    @classmethod
    def unique_filter(cls, query, *arg, **kw):
        raise NotImplementedError()

    @classmethod
    def as_unique(cls, session, *arg, **kw):
        return _unique(
                    session,
                    cls,
                    cls.unique_filter,
                    cls,
                    arg, kw)

# Versioning table

class Pragma(Base):
    __tablename__ = 'pragma'
    content = Column(String, primary_key=True)

# UI caching tables
    
tags = Table('tags', Base.metadata,
    Column('simulations_id', Integer, ForeignKey('simulations.id')),
    Column('topics_id', Integer, ForeignKey('topics.id'))
)
    
class uiTopic(UniqueMixin, Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True)    
    cid = Column(Integer, nullable=False)
    topic = Column(String)

    @classmethod
    def unique_filter(cls, query, cid, topic):
        return query.filter(and_(uiTopic.cid == cid, uiTopic.topic == topic))

class uiGrid(Base):
    __tablename__ = 'grid'
    sid = Column(Integer, ForeignKey('simulations.id'), nullable=False, primary_key=True)
    info = Column(Text, default=None)

# Relational paradigm tables

class Simulation(Base):
    __tablename__ = 'simulations'
    id = Column(Integer, primary_key=True)
    checksum = Column(String, nullable=False)
    
    pottype_id = Column(Integer, ForeignKey('pottypes.id'), default=None)
    
    structures = relationship("Structure", backref="simulations")
    auxiliary = relationship("Auxiliary", uselist=False, backref="simulations")
    basis = relationship("Basis", uselist=False, backref="simulations")
    recipinteg = relationship("Recipinteg", uselist=False, backref="simulations")
    energy = relationship("Energy", uselist=False, backref="simulations")
    charges = relationship("Charges", uselist=False, backref="simulations")
    electrons = relationship("Electrons", uselist=False, backref="simulations")
    phonons = relationship("Phonons", uselist=False, backref="simulations")
    forces = relationship("Forces", uselist=False, backref="simulations")
    
    uigrid = relationship("uiGrid", uselist=False, backref="simulations")
    uitopics = relationship("uiTopic", backref="simulations", secondary=tags)
    apps = relationship("Apps", backref="simulations")

class Auxiliary(Base):
    __tablename__ = 'auxiliaries'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    codeversion_id = Column(Integer, ForeignKey('codeversions.id'))
    location = Column(String, nullable=False)
    finished = Column(Integer, default=0)
    raw_input = Column(Text, default=None)    
    
class Codeversion(UniqueMixin, Base):
    __tablename__ = 'codeversions'
    id = Column(Integer, primary_key=True)    
    codefamily_id = Column(Integer, ForeignKey('codefamilies.id'))    
    content = Column(String, nullable=False)
    instances = relationship("Auxiliary", backref="codeversions")
    
    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codeversion.content == content)

class Codefamily(UniqueMixin, Base):
    __tablename__ = 'codefamilies'
    id = Column(Integer, primary_key=True)    
    content = Column(String, nullable=False)
    versions = relationship("Codeversion", backref="codefamilies")
    
    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codefamily.content == content)

class Energy(Base):
    __tablename__ = 'energies'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    convergence = Column(Text, default=None)
    total = Column(Float, default=None)
    
class Basis(Base):
    __tablename__ = 'basises'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    type = Column(String, nullable=False)
    rgkmax = Column(Float, default=None)
    lmaxapw = Column(Float, default=None)
    lmaxmat = Column(Float, default=None)
    lmaxvr = Column(Float, default=None)
    gmaxvr = Column(Float, default=None)
    repr = Column(Text, default=None)
    
class Recipinteg(Base):
    __tablename__ = 'recipintegs'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    kgrid = Column(String, default=None)
    kshift = Column(Float, default=None)
    smearing = Column(Float, default=None)
    smeartype = Column(String, default=None)
    
class Pottype(UniqueMixin, Base):
    __tablename__ = 'pottypes'
    id = Column(Integer, primary_key=True)    
    name = Column(String, nullable=False)
    instances = relationship("Simulation", backref="pottypes")
    
    @classmethod
    def unique_filter(cls, query, name):
        return query.filter(Pottype.name == name)
    
class Charges(Base):
    __tablename__ = 'charges'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    core = Column(Float, nullable=False)
    leakage = Column(Float, nullable=False)
    valence = Column(Float, nullable=False)
    interstitial = Column(Float, nullable=False)
    muffintins = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

class Electrons(Base):
    __tablename__ = 'electrons'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    gap = Column(Float, default=None)
    is_direct = Column(Integer, default=0)
    eigenvalues = relationship("Eigenvalues", uselist=False, backref="electrons")

class Phonons(Base):
    __tablename__ = 'phonons'
    sid = Column(Integer, ForeignKey('simulations.id'), primary_key=True)
    eigenvalues = relationship("Eigenvalues", uselist=False, backref="phonons")

class Eigenvalues(Base):
    __tablename__ = 'eigenvalues'
    id = Column(Integer, primary_key=True)
    electrons_id = Column(Integer, ForeignKey('electrons.sid'))
    phonons_id = Column(Integer, ForeignKey('phonons.sid'))
    dos = Column(Text, default=None)
    bands = Column(Text, default=None)
    projected = Column(Text, default=None)
    eigenvalues = Column(Text, default=None)
    
class Forces(Base):
    __tablename__ = 'forces'
    id = Column(Integer, primary_key=True)
    sid = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    values = Column(Text, nullable=False)

class Structure(Base):
    __tablename__ = 'structures'
    id = Column(Integer, primary_key=True)
    sid = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    lattice_basis = relationship("Lattice_basis", uselist=False, backref="structures", cascade="all, delete, delete-orphan")
    atoms = relationship("Atom", backref="structures", cascade="all, delete, delete-orphan")
    spacegroup = relationship("Spacegroup", uselist=False, backref="structures", cascade="all, delete, delete-orphan")
    struct_ratios = relationship("Struct_ratios", uselist=False, backref="structures", cascade="all, delete, delete-orphan")

class Lattice_basis(Base):
    __tablename__ = 'lattice_basises'
    struct_id = Column(Integer, ForeignKey('structures.id'), primary_key=True)
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    c = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False)
    beta = Column(Float, nullable=False)
    gamma = Column(Float, nullable=False)
    a11 = Column(Float, nullable=False)
    a12 = Column(Float, nullable=False)
    a13 = Column(Float, nullable=False)
    a21 = Column(Float, nullable=False)
    a22 = Column(Float, nullable=False)
    a23 = Column(Float, nullable=False)
    a31 = Column(Float, nullable=False)
    a32 = Column(Float, nullable=False)
    a33 = Column(Float, nullable=False)    

class Atom(Base):
    __tablename__ = 'atoms'
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    charge = Column(Float, default=None)
    magmom = Column(Float, default=None)
    rmt = Column(Float, default=None)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)

class Spacegroup(Base):
    __tablename__ = 'spacegroups'
    struct_id = Column(Integer, ForeignKey('structures.id'), primary_key=True)
    n = Column(Integer, nullable=False)    

class Struct_ratios(Base):
    __tablename__ = 'struct_ratios'
    id = Column(Integer, primary_key=True)
    chemical_formula = Column(String, nullable=False)
    is_primitive = Column(Boolean, default=False)
    formula_units = Column(Integer, nullable=False)
    struct_id = Column(Integer, ForeignKey('structures.id'), nullable=False)

# submodules table

class Apps(Base):
    __tablename__ = 'apps'
    id = Column(Integer, primary_key=True)
    sid = Column(Integer, ForeignKey('simulations.id'), nullable=False)
    name = Column(String, nullable=False)
    data = Column(Text, default=None)
