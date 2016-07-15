
# DB schema
# Author: Evgeny Blokhin

import os, sys
import logging
import datetime
from collections import namedtuple
import six

from tilde.core.orm_tools import UniqueMixin, get_or_create, correct_topics

from sqlalchemy import and_, or_, Index, UniqueConstraint, MetaData, String, UnicodeText, Table, Column, Boolean, Float, Integer, BigInteger, Enum, Text, Date, DateTime, UnicodeText, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.sql.expression import insert, delete
if six.PY3:
    from sqlalchemy import UnicodeText as JSONString
else:
    from sqlalchemy import LargeBinary as JSONString

import ujson as json


class NullHandler(logging.Handler): # for Python 2.6
    def emit(self, record): pass

logger = logging.getLogger('tilde')
#handler = logging.StreamHandler(sys.stdout)
handler = NullHandler()
#handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt="%d/%m %H:%M"))
logger.setLevel(logging.CRITICAL)
logger.addHandler(handler)

Base = declarative_base()

class Pragma(Base):
    __tablename__ = 'pragma'
    content = Column(String, primary_key=True)

class Hierarchy(Base):
    __tablename__ = 'hierarchy'
    cid = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)
    legend = Column(String, default="")
    html = Column(String, default="")
    slider = Column(String, default="")
    sort = Column(Integer, default=0)

    # mimic bool
    multiple = Column(Integer, default=0)
    optional = Column(Integer, default=0)
    has_summary_contrb = Column(Integer, default=0)
    has_column = Column(Integer, default=0)
    has_facet = Column(Integer, default=0)
    has_topic = Column(Integer, default=0)
    chem_formula = Column(Integer, default=0)
    plottable = Column(Integer, default=0)

    values = relationship("Hierarchy_value")
    hgroup_id = Column(Integer, ForeignKey('hierarchy_groups.hgroup_id'), default=None)

class Hierarchy_group(Base):
    __tablename__ = 'hierarchy_groups'
    hgroup_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # mimic bool
    landing_group = Column(Integer, default=0)
    settings_group = Column(Integer, default=0)

    includes = relationship("Hierarchy")

class Hierarchy_value(Base):
    __tablename__ = 'hierarchy_values'
    cid = Column(Integer, ForeignKey('hierarchy.cid'), primary_key=True)
    num = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)

class Topic(UniqueMixin, Base):
    __tablename__ = 'topics'
    tid = Column(Integer, primary_key=True)
    cid = Column(Integer, nullable=False)
    topic = Column(String) # int for enumerated topics

    @classmethod
    def unique_filter(cls, query, cid, topic):
        return query.filter(Topic.cid == cid, Topic.topic == topic)

topic = namedtuple('topic', ['cid', 'topic'])

tags = Table('tags', Base.metadata,
    Column('checksum', String, ForeignKey('calculations.checksum')),
    Column('tid', Integer, ForeignKey('topics.tid')),
    UniqueConstraint('checksum', 'tid', name='u_checksum_tid'),
    Index('checksum_to_tid', "checksum", "tid"),
)

tag = namedtuple('tag', ['checksum', 'tid'])

class Grid(Base):
    __tablename__ = 'grid'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    info = Column(JSONString, default=None)

calcsets = Table('calcsets', Base.metadata,
    Column('parent_checksum', String, ForeignKey('calculations.checksum'), primary_key=True),
    Column('children_checksum', String, ForeignKey('calculations.checksum'), primary_key=True),
    UniqueConstraint('parent_checksum', 'children_checksum', name='parent_children_checksum')
)

class Calculation(Base):
    __tablename__ = 'calculations'
    checksum = Column(String, primary_key=True, index=True)

    siblings_count = Column(Integer, default=0)
    nested_depth = Column(Integer, default=0)
    children = relationship("Calculation", backref="parent", secondary=calcsets, primaryjoin=checksum==calcsets.c.parent_checksum, secondaryjoin=checksum==calcsets.c.children_checksum)

    pottype_id = Column(Integer, ForeignKey('pottypes.pottype_id'), default=None)

    structures = relationship("Structure")
    spectra = relationship("Spectra")
    spacegroup = relationship("Spacegroup", uselist=False)
    struct_ratios = relationship("Struct_ratios", uselist=False)
    struct_optimisation = relationship("Struct_optimisation", uselist=False)
    meta_data = relationship("Metadata", uselist=False)
    basis = relationship("Basis", uselist=False)
    recipinteg = relationship("Recipinteg", uselist=False)
    energy = relationship("Energy", uselist=False)
    electrons = relationship("Electrons", uselist=False)
    phonons = relationship("Phonons", uselist=False)
    forces = relationship("Forces", uselist=False)
    uigrid = relationship("Grid", uselist=False)
    uitopics = relationship("Topic", backref="calculations", secondary=tags)
    references = relationship("Reference", backref="calculations", secondary="metadata_references")

class Metadata(Base):
    __tablename__ = 'metadata'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    version_id = Column(Integer, ForeignKey('codeversions.version_id'))
    location = Column(String, default=None)
    finished = Column(Integer, default=0)
    raw_input = Column(Text, default=None)
    modeling_time = Column(Float, default=None)
    chemical_formula = Column(String, default=None)
    added = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    download_size = Column(BigInteger, default=None)
    filenames = Column(JSONString, default=None)

class Reference(Base):
    __tablename__ = 'references'
    reference_id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False, unique=True)

metadata_references = Table('metadata_references', Base.metadata,
    Column('checksum', String, ForeignKey('calculations.checksum')),
    Column('reference_id', Integer, ForeignKey('references.reference_id')),
    UniqueConstraint('checksum', 'reference_id', name='u_checksum_reference_id')
)

class Codeversion(UniqueMixin, Base):
    __tablename__ = 'codeversions'
    version_id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('codefamilies.family_id'))
    content = Column(String, nullable=False)
    instances = relationship("Metadata")

    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codeversion.content == content)

class Codefamily(UniqueMixin, Base):
    __tablename__ = 'codefamilies'
    family_id = Column(Integer, primary_key=True)
    content = Column(Integer, nullable=False, unique=True)
    versions = relationship("Codeversion")

    @classmethod
    def unique_filter(cls, query, content):
        return query.filter(Codefamily.content == content)

class Energy(Base):
    __tablename__ = 'energies'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    convergence = Column(JSONString, default=None)
    total = Column(Float, default=None)

class Basis(Base):
    __tablename__ = 'basissets'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    kind = Column(Integer, nullable=False)
    content = Column(JSONString, default=None)

class Recipinteg(Base):
    __tablename__ = 'recipintegs'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    kgrid = Column(String, default=None)
    kshift = Column(Float, default=None)
    smearing = Column(Float, default=None)
    smeartype = Column(String, default=None)

class Pottype(UniqueMixin, Base):
    __tablename__ = 'pottypes'
    pottype_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    instances = relationship("Calculation")

    @classmethod
    def unique_filter(cls, query, name):
        return query.filter(Pottype.name == name)

class Electrons(Base):
    __tablename__ = 'electrons'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    gap = Column(Float, default=None)
    is_direct = Column(Integer, default=0)

class Phonons(Base):
    __tablename__ = 'phonons'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)

class Spectra(Base):
    __tablename__ = 'spectra'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    ELECTRON = 'ELECTRON'
    PHONON = 'PHONON'
    kind = Column(Enum(ELECTRON, PHONON, name='spectrum_kind_enum'), primary_key=True)
    dos =           Column(JSONString, default=None)
    bands =         Column(JSONString, default=None)
    projected =     Column(JSONString, default=None)
    eigenvalues =   Column(JSONString, default=None)

class Forces(Base):
    __tablename__ = 'forces'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    content = Column(JSONString, nullable=False)

class Structure(Base):
    __tablename__ = 'structures'
    struct_id = Column(Integer, primary_key=True)
    checksum = Column(String, ForeignKey('calculations.checksum'), nullable=False)
    step = Column(Integer, nullable=False)
    final = Column(Boolean, nullable=False)
    #struct_checksum = Column(String, nullable=False)
    lattice = relationship("Lattice", uselist=False)
    atoms = relationship("Atom")

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
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    n = Column(Integer, nullable=False)

class Struct_ratios(Base):
    __tablename__ = 'struct_ratios'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    chemical_formula = Column(String, nullable=False)
    is_primitive = Column(Boolean, default=False) # not filled in, FIXME
    formula_units = Column(Integer, nullable=False)
    nelem = Column(Integer, nullable=False)
    dimensions = Column(Float, default=None)

class Struct_optimisation(Base):
    __tablename__ = 'struct_optimisation'
    checksum = Column(String, ForeignKey('calculations.checksum'), primary_key=True)
    tresholds = Column(JSONString, default=None)
    ncycles = Column(JSONString, default=None)
