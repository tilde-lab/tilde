
# Database schema

import os, sys

sys.path.insert(0, os.path.realpath(os.path.dirname(os.path.abspath(__file__)) + '/deps'))
from sqlalchemy import MetaData, String, Table, Column, Boolean, Float, Integer, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import UniqueConstraint


DB_SCHEMA_VERSION = '2.03'

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
    Column('id', Integer, ForeignKey('calculations.id')),
    Column('tid', Integer, ForeignKey('topics.tid'))
)
    
class uiTopic(UniqueMixin, Base):
    __tablename__ = 'topics'
    tid = Column(Integer, primary_key=True)    
    cid = Column(Integer, nullable=False)
    topic = Column(String)

    @classmethod
    def unique_filter(cls, query, cid, topic):
        return query.filter(uiTopic.cid == cid, uiTopic.topic == topic)

class uiGrid(Base):
    __tablename__ = 'grid'
    id = Column(Integer, ForeignKey('calculations.id'), nullable=False, primary_key=True)
    info = Column(Text, default=None)

# Relational paradigm tables

class Calculation(Base):
    __tablename__ = 'calculations'
    id = Column(Integer, primary_key=True)
    checksum = Column(String, nullable=False)
    
    pottype_id = Column(Integer, ForeignKey('pottypes.pottype_id'), default=None)
    
    structures = relationship("Structure", backref="calculations")
        
    spacegroup = relationship("Spacegroup", uselist=False, backref="calculations")
    struct_ratios = relationship("Struct_ratios", uselist=False, backref="calculations")
    auxiliary = relationship("Auxiliary", uselist=False, backref="calculations")
    basis = relationship("Basis", uselist=False, backref="calculations")
    recipinteg = relationship("Recipinteg", uselist=False, backref="calculations")
    energy = relationship("Energy", uselist=False, backref="calculations")
    charges = relationship("Charges", uselist=False, backref="calculations")
    electrons = relationship("Electrons", uselist=False, backref="calculations")
    phonons = relationship("Phonons", uselist=False, backref="calculations")
    forces = relationship("Forces", uselist=False, backref="calculations")
    
    uigrid = relationship("uiGrid", uselist=False, backref="calculations")
    uitopics = relationship("uiTopic", backref="calculations", secondary=tags)
    apps = relationship("Apps", backref="calculations")

class Auxiliary(Base):
    __tablename__ = 'auxiliaries'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    version_id = Column(Integer, ForeignKey('codeversions.version_id'))
    location = Column(String, nullable=False)
    finished = Column(Integer, default=0)
    raw_input = Column(Text, default=None)
    author = Column(String, default=None)
    date = Column(Date, default=None)
    
class Codeversion(UniqueMixin, Base):
    __tablename__ = 'codeversions'
    version_id = Column(Integer, primary_key=True)    
    family_id = Column(Integer, ForeignKey('codefamilies.family_id'))    
    content = Column(String, nullable=False)
    instances = relationship("Auxiliary", backref="codeversions")
    
    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codeversion.content == content)

class Codefamily(UniqueMixin, Base):
    __tablename__ = 'codefamilies'
    family_id = Column(Integer, primary_key=True)    
    content = Column(String, nullable=False)
    versions = relationship("Codeversion", backref="codefamilies")
    
    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codefamily.content == content)

class Energy(Base):
    __tablename__ = 'energies'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    convergence = Column(Text, default=None)
    total = Column(Float, default=None)
    
class Basis(Base):
    __tablename__ = 'basis_sets'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    type = Column(String, nullable=False)
    rgkmax = Column(Float, default=None)
    lmaxapw = Column(Float, default=None)
    lmaxmat = Column(Float, default=None)
    lmaxvr = Column(Float, default=None)
    gmaxvr = Column(Float, default=None)
    repr = Column(Text, default=None) # TODO
    
class Recipinteg(Base):
    __tablename__ = 'recipintegs'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    kgrid = Column(String, default=None)
    kshift = Column(Float, default=None)
    smearing = Column(Float, default=None)
    smeartype = Column(String, default=None)
    
class Pottype(UniqueMixin, Base):
    __tablename__ = 'pottypes'
    pottype_id = Column(Integer, primary_key=True)    
    name = Column(String, nullable=False)
    instances = relationship("Calculation", backref="pottypes")
    
    @classmethod
    def unique_filter(cls, query, name):
        return query.filter(Pottype.name == name)
    
class Charges(Base):
    __tablename__ = 'charges'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    core = Column(Float, nullable=False)
    leakage = Column(Float, nullable=False)
    valence = Column(Float, nullable=False)
    interstitial = Column(Float, nullable=False)
    muffintins = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

class Electrons(Base):
    __tablename__ = 'electrons'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    gap = Column(Float, default=None)
    is_direct = Column(Integer, default=0)
    eigenvalues = relationship("Eigenvalues", uselist=False, backref="electrons")

class Phonons(Base):
    __tablename__ = 'phonons'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    eigenvalues = relationship("Eigenvalues", uselist=False, backref="phonons")

class Eigenvalues(Base):
    __tablename__ = 'eigenvalues'
    eid = Column(Integer, primary_key=True)
    electrons_id = Column(Integer, ForeignKey('electrons.id'))
    phonons_id = Column(Integer, ForeignKey('phonons.id'))
    dos = Column(Text, default=None)
    bands = Column(Text, default=None)
    projected = Column(Text, default=None)
    eigenvalues = Column(Text, default=None) # TODO rename
    
class Forces(Base):
    __tablename__ = 'forces'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    values = Column(Text, nullable=False)

class Structure(Base):
    __tablename__ = 'structures'
    struct_id = Column(Integer, primary_key=True)
    id = Column(Integer, ForeignKey('calculations.id'), nullable=False)
    step = Column(Integer, nullable=False)
    final = Column(Boolean, nullable=False)
    lattice = relationship("Lattice", uselist=False, backref="structures")
    atoms = relationship("Atom", backref="structures")

class Lattice(Base):
    __tablename__ = 'lattices'
    struct_id = Column(Integer, ForeignKey('structures.struct_id'), primary_key=True)
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
    atom_id = Column(Integer, primary_key=True)
    struct_id = Column(Integer, ForeignKey('structures.struct_id'), nullable=False)
    number = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    z = Column(Float, nullable=False)
    charge = Column(Float, default=None)
    magmom = Column(Float, default=None)
    rmt = Column(Float, default=None)    

class Spacegroup(Base):
    __tablename__ = 'spacegroups'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    n = Column(Integer, nullable=False)    

class Struct_ratios(Base):
    __tablename__ = 'struct_ratios'
    id = Column(Integer, ForeignKey('calculations.id'), primary_key=True)
    chemical_formula = Column(String, nullable=False)
    is_primitive = Column(Boolean, default=False)
    formula_units = Column(Integer, nullable=False)
    nelem = Column(Integer, nullable=False)
    
# submodules table

class Apps(Base):
    __tablename__ = 'apps'
    app_id = Column(Integer, primary_key=True)
    id = Column(Integer, ForeignKey('calculations.id'), nullable=False)
    name = Column(String, nullable=False)
    data = Column(Text, default=None)
