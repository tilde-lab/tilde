
import os, sys

import xmind
from xmind.core.relationship import RelationshipElement, RelationshipsElement
from xmind.core.const import TAG_TOPIC, TAG_TOPICS, TAG_CHILDREN, TAG_TITLE, TAG_RELATIONSHIP

import rdflib
from rdflib.namespace import NamespaceManager, OWL, XSD

from RDFClosure import DeductiveClosure, OWLRL_Extension

# Graph creation

g = rdflib.Graph()
OWL = rdflib.Namespace("http://www.w3.org/2002/07/owl#")
TILDE = rdflib.Namespace("http://tilde.pro/#")
namespace_manager = NamespaceManager(g)
namespace_manager.bind('tilde', TILDE, override=True)
namespace_manager.bind('owl', OWL, override=True)

workpath = '/data/nomad/results/hierarchy.xmind'

def term2uri(str):
    return str.replace(' ', '_')
def uri2term(str):
    return str.replace('_', ' ').replace("http://tilde.pro/#", "")

workbook = xmind.load(workpath)
sheet = workbook.getPrimarySheet()

# Object properties

g.add((  TILDE.belongsto, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.belongsto, rdflib.RDF.type, OWL.TransitiveProperty  ))

g.add((  TILDE.influences, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.influences, rdflib.RDF.type, OWL.TransitiveProperty  ))

g.add((  TILDE.affectedby, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.affectedby, rdflib.RDF.type, OWL.TransitiveProperty  ))
g.add((  TILDE.affectedby, OWL.inverseOf, TILDE.influences  ))

g.add((  TILDE.comprises, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.comprises, rdflib.RDF.type, OWL.TransitiveProperty  ))
g.add((  TILDE.comprises, OWL.inverseOf, TILDE.belongsto  ))

g.add((  TILDE.actson, rdflib.RDF.type, OWL.ObjectProperty  ))
chain_axiom = '''
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix tilde: <http://tilde.pro/#> .
tilde:actson owl:propertyChainAxiom ( tilde:belongsto tilde:influences ) .
tilde:actson owl:propertyChainAxiom ( tilde:belongsto tilde:influences tilde:comprises ) .
tilde:actedby owl:propertyChainAxiom ( tilde:belongsto tilde:affectedby ) .
tilde:actedby owl:propertyChainAxiom ( tilde:belongsto tilde:affectedby tilde:comprises ) .
''' # How to input OWL.propertyChainAxiom in rdflib?
g.parse(data=chain_axiom, format='n3')

g.add((  TILDE.participates, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.participates, rdflib.RDF.type, OWL.FunctionalProperty  ))
g.add((  TILDE.organizes, rdflib.RDF.type, OWL.ObjectProperty  ))
g.add((  TILDE.organizes, rdflib.RDF.type, OWL.FunctionalProperty  ))

# Classes

vertices_names = {}
try: detached_topics = sheet.getChildNodesByTagName(TAG_TOPIC)[0].getElementsByTagName(TAG_CHILDREN)[0].getElementsByTagName(TAG_TOPICS)[0].getElementsByTagName(TAG_TOPIC)
except IndexError: sys.exit('Please, re-save mind map under the other name!')
for i in detached_topics:
    node = {
    'title': term2uri(i.getElementsByTagName(TAG_TITLE)[0].firstChild.nodeValue),
    'label': ''
    }
    node['label'] = i.getElementsByTagName('labels')[0].firstChild.firstChild.nodeValue if i.getElementsByTagName('labels') else ''
    vertices_names[ i.attributes['id'].value ] = node['title']
    g.add((  TILDE[ node['title'] ], rdflib.RDF.type, OWL.Class  ))
        
    if node['label'] == 'gen':
        g.add((  TILDE[ node['title'] ], TILDE.organizes, TILDE.true  ))
    elif node['label'] == 'abs':
       continue
    else:
        g.add((  TILDE[ node['title'] ], TILDE.participates, TILDE.true  ))     

rels = RelationshipsElement(sheet._getRelationships())
for i in rels.iterChildNodesByTagName(TAG_RELATIONSHIP):
    rel = RelationshipElement(i)
    conntype = rel.getTitle()
    
    if conntype == 'influences': predicate = TILDE.influences
    else: predicate = TILDE.belongsto
    
    g.add((  TILDE[vertices_names[ rel.getEnd1ID() ]], predicate, TILDE[vertices_names[ rel.getEnd2ID() ]]  ))

# Reasoning

DeductiveClosure(OWLRL_Extension).expand(g)

# Extracting

def actson(entity, graph):
    output = []
    try:
        for entity in graph.objects(subject=TILDE[ term2uri(entity) ], predicate=TILDE.actson):
            output.append(uri2term(entity))
    except: pass
    return output

def actedby(entity, graph):
    output = []
    try:
        for entity in graph.objects(subject=TILDE[ term2uri(entity) ], predicate=TILDE.actedby):
            output.append(uri2term(entity))
        for entity in graph.objects(subject=TILDE[ term2uri(entity) ], predicate=TILDE.affectedby):
            output.append(uri2term(entity))
        output = list(set(output))
    except: pass
    return output
