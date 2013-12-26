
#
# converts XMind drawing format to graphs and applies OWL-RL reasoner by Ivan Herman
# outputs json for in-browser SVG plotting
#

import os, sys
import json
import copy

import xmind
from xmind.core.relationship import RelationshipElement, RelationshipsElement
from xmind.core.const import TAG_TOPIC, TAG_TOPICS, TAG_CHILDREN, TAG_TITLE, TAG_RELATIONSHIP

import rdflib
from rdflib.namespace import NamespaceManager, OWL, XSD

from RDFClosure import DeductiveClosure, OWLRL_Extension


class Ontology:
    @staticmethod
    def term2uri(str):
        return str.replace(' ', '_')
    
    @staticmethod
    def uri2term(str):
        return str.replace('_', ' ').replace("http://tilde.pro/#", "")
    
    def __init__(self):        
        self.OWL = rdflib.Namespace("http://www.w3.org/2002/07/owl#")
        self.TILDE = rdflib.Namespace("http://tilde.pro/#")
        
    def compile(self, mindmap):
        
        self.error = None
        
        self.g = rdflib.Graph()
        namespace_manager = NamespaceManager(self.g)
        namespace_manager.bind('tilde', self.TILDE, override=True)
        namespace_manager.bind('owl', self.OWL, override=True)
        
        try:            
            workbook = xmind.load(mindmap)
        except:
            self.error = 'Unable to parse a mind map: %s' % sys.exc_info()[1]
        else:
            sheet = workbook.getPrimarySheet()          
            
            # Classes
            vertices_names, detached_topics = {}, []
            try:
                detached_topics = sheet.getChildNodesByTagName(TAG_TOPIC)[0].getElementsByTagName(TAG_CHILDREN)[0].getElementsByTagName(TAG_TOPICS)[0].getElementsByTagName(TAG_TOPIC)
            except IndexError:
                self.error = 'Internal error! The XMind format is invalid!'
            for i in detached_topics:
                node = { 'title': Ontology.term2uri(i.getElementsByTagName(TAG_TITLE)[0].firstChild.nodeValue) }
                node['label'] = i.getElementsByTagName('labels')[0].firstChild.firstChild.nodeValue if i.getElementsByTagName('labels') else ''
                vertices_names[ i.attributes['id'].value ] = node['title']
                self.g.add((  self.TILDE[ node['title'] ], rdflib.RDF.type, self.OWL.Class  ))
                self.g.add((  self.TILDE[ node['title'] ], self.TILDE.participates, self.TILDE.true  ))

            rels = RelationshipsElement(sheet._getRelationships())
            for i in rels.iterChildNodesByTagName(TAG_RELATIONSHIP):
                rel = RelationshipElement(i)
                conntype = rel.getTitle()
                
                if conntype == 'influences': predicate = self.TILDE.influences
                else: predicate = self.TILDE.belongsto
                
                self.g.add((  self.TILDE[vertices_names[ rel.getEnd1ID() ]], predicate, self.TILDE[vertices_names[ rel.getEnd2ID() ]]  ))
                        
            self.g.add((  self.TILDE.belongsto, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.belongsto, rdflib.RDF.type, self.OWL.TransitiveProperty  ))

            self.g.add((  self.TILDE.influences, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.influences, rdflib.RDF.type, self.OWL.TransitiveProperty  ))

            self.g.add((  self.TILDE.comprises, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.comprises, rdflib.RDF.type, self.OWL.TransitiveProperty  ))
            self.g.add((  self.TILDE.comprises, self.OWL.inverseOf, self.TILDE.belongsto  ))

            self.g.add((  self.TILDE.actson, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.actson, self.OWL.equivalentProperty, self.TILDE.influences  ))
            self.g.add((  self.TILDE.actedby, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.parse(data='''
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix tilde: <http://tilde.pro/#> .
            tilde:actson owl:propertyChainAxiom ( tilde:belongsto tilde:influences ) .
            tilde:actson owl:propertyChainAxiom ( tilde:influences tilde:comprises ) .
            tilde:actson owl:propertyChainAxiom ( tilde:belongsto tilde:influences tilde:comprises ) .
            ''' , format='n3') # How to input self.OWL.propertyChainAxiom in rdflib?
            self.g.add((  self.TILDE.actson, rdflib.RDF.type, self.OWL.TransitiveProperty  ))
            self.g.add((  self.TILDE.actedby, self.OWL.inverseOf, self.TILDE.actson  ))
            
            self.g.add((  self.TILDE.participates, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            
    def reason(self):
        self.org = copy.deepcopy(self.g)
        try:
            DeductiveClosure(OWLRL_Extension).expand(self.g)
        except:
            self.error = 'Unable to apply reasoner!'        
        
    def dump(self):
        return self.g.serialize(format='turtle')
        
    def to_json(self):
        edges = []
        
        #vertices = list(set(vertices))
        
        for s, o in self.org.subject_objects(predicate=self.TILDE.belongsto):
            edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'belongs' })        
        for s, o in self.org.subject_objects(predicate=self.TILDE.influences):
            edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'influences' })
            
        for s, o in self.g.subject_objects(predicate=self.TILDE.actson):
            edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'actson' })            
        for s, o in self.g.subject_objects(predicate=self.TILDE.actedby):
            edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'actedby' })
        
        return json.dumps(edges)   

if __name__ == '__main__':
    
    try: workpath = sys.argv[1]
    except IndexError: sys.exit('No path defined!')
    workpath = os.path.abspath(workpath)
    if not os.path.exists(workpath): sys.exit('Invalid path!')

    ontograph = Ontology()
    ontograph.compile(workpath)
    error = ontograph.error
    if not error:
        ontograph.reason()
    error = ontograph.error
    
    print ontograph.to_json()
    
    '''if not error:
        try:
            f = open(workpath + '.out', 'w')
            f.writelines(ontograph.dump())
            f.close()
        except IOError:
            raise RuntimeError('Cannot write file ' + workpath + '.out')
        else:
            print workpath + '.out ready'
    else:
        print error'''
