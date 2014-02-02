
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

            rels = RelationshipsElement(sheet._getRelationships())
            for i in rels.iterChildNodesByTagName(TAG_RELATIONSHIP):
                rel = RelationshipElement(i)
                conntype = rel.getTitle()
                
                if conntype == 'does': predicate = self.TILDE.does
                else: predicate = self.TILDE.belongsto
                
                self.g.add((  self.TILDE[vertices_names[ rel.getEnd1ID() ]], predicate, self.TILDE[vertices_names[ rel.getEnd2ID() ]]  ))
            
            # Main ruleset:
            
            # rule belongsto
            self.g.add((  self.TILDE.belongsto, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.belongsto, rdflib.RDF.type, self.OWL.TransitiveProperty  ))
            
            # rule belongsto = INVERSE(belongsto)
            self.g.add((  self.TILDE.inv_belongsto, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.inv_belongsto, self.OWL.inverseOf, self.TILDE.belongsto  ))
            self.g.add((  self.TILDE.inv_belongsto, self.OWL.equivalentProperty, self.TILDE.belongsto  ))
            
            # rule does
            self.g.add((  self.TILDE.does, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.does, rdflib.RDF.type, self.OWL.TransitiveProperty  ))           
            
            # rule INVERSE(does)
            self.g.add((  self.TILDE.inv_does, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.inv_does, self.OWL.inverseOf, self.TILDE.does  ))
            
            # rule actson
            self.g.add((  self.TILDE.actson, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.parse(data='''
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix tilde: <http://tilde.pro/#> .
            tilde:actson owl:propertyChainAxiom ( tilde:belongsto tilde:does ) .
            tilde:actson owl:propertyChainAxiom ( tilde:does tilde:belongsto ) .
            ''' , format='n3')
            self.g.add((  self.TILDE.actson, rdflib.RDF.type, self.OWL.TransitiveProperty  ))
            
            # rule actedby
            self.g.add((  self.TILDE.actedby, rdflib.RDF.type, self.OWL.ObjectProperty  ))
            self.g.add((  self.TILDE.actedby, self.OWL.inverseOf, self.TILDE.actson  ))
            
    def reason(self):
        edges = []
        self.org = copy.deepcopy(self.g)
        try:
            DeductiveClosure(OWLRL_Extension).expand(self.g)
        except:
            self.error = 'Unable to apply reasoner!'
        else:
            #vertices = list(set(vertices))                    
            
            # Expanded graph
            # actson and actedby
            
            # Make consistency check
            for s, o in self.g.subject_objects(predicate=self.TILDE.actson):
                s = Ontology.uri2term(s)
                o = Ontology.uri2term(o)
                if s == o:
                    self.error = 'Consistency error for term %s!' % s
                    break
                edges.append({'source': s, 'target': o, 'type': 'actson' })
            else:   
                # Here we combine some rules outside the reasoner           
                for s, o in self.g.subject_objects(predicate=self.TILDE.does):
                    edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'actson' })
                        
                for s, o in self.g.subject_objects(predicate=self.TILDE.actedby):
                    edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'actedby' })
                    
                for s, o in self.g.subject_objects(predicate=self.TILDE.inv_does):
                    edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'actedby' })
                    
                # Original graph
                # belongs and does
                for s, o in self.org.subject_objects(predicate=self.TILDE.belongsto):
                    edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'belongs' })        
                for s, o in self.org.subject_objects(predicate=self.TILDE.does):
                    edges.append({'source': Ontology.uri2term(s), 'target': Ontology.uri2term(o), 'type': 'does' })
        
        return json.dumps(edges)
            
    def dump(self):
        return self.g.serialize(format='turtle')

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
    
    print ontograph.dump()
    
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
