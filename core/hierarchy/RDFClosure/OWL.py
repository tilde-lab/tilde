"""
OWL and OWL2 terms. Note that the set of terms is I{complete}, ie, it includes I{all} OWL 2 terms, regardless of whether the term is
used in OWL 2 RL or not.

@requires: U{RDFLib<http://rdflib.net>}, 2.2.2. and higher
@license: This software is available for use under the U{W3C Software License<http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}
@author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}
"""

"""
$Id: OWL.py,v 1.10 2011/08/04 12:41:58 ivan Exp $ $Date: 2011/08/04 12:41:58 $
"""

import rdflib
if rdflib.__version__ >= "3.0.0" :
	from rdflib				import Namespace
else :
	from rdflib.Namespace	import Namespace

#: The OWL namespace as used for RDFLib
OWLNS  = Namespace("http://www.w3.org/2002/07/owl#")

annotatedSource				= OWLNS["annotatedSource"]
annotatedTarget				= OWLNS["annotatedTarget"]
annotatedProperty			= OWLNS["annotatedProperty"]
allValuesFrom				= OWLNS["allValuesFrom"]
assertionProperty			= OWLNS["assertionProperty"]
backwardCompatibleWith		= OWLNS["backwardCompatibleWith"]
cardinality					= OWLNS["cardinality"]
complementOf				= OWLNS["complementOf"]
BottomDataProperty			= OWLNS["BottomDataProperty"]
BottomObjectProperty		= OWLNS["BottomObjectProperty"]
datatypeComplementOf     	= OWLNS["datatypeComplementOf"]
deprecated					= OWLNS["deprecated"]
differentFrom				= OWLNS["differentFrom"]
disjointUnionOf				= OWLNS["disjointUnionOf"]
disjointClasses				= OWLNS["disjointClasses"]
disjointWith				= OWLNS["disjointWith"]
distinctMembers				= OWLNS["distinctMembers"]
equivalentClass				= OWLNS["equivalentClass"]
equivalentProperty			= OWLNS["equivalentProperty"]
hasKey						= OWLNS["hasKey"]
hasValue					= OWLNS["hasValue"]
hasSelf						= OWLNS["hasSelf"]
imports						= OWLNS["imports"]
incompatibleWith			= OWLNS["incompatibleWith"]
intersectionOf				= OWLNS["intersectionOf"]
inverseOf					= OWLNS["inverseOf"]
maxCardinality				= OWLNS["maxCardinality"]
maxQualifiedCardinality		= OWLNS["maxQualifiedCardinality"]
members						= OWLNS["members"]
minCardinality				= OWLNS["minCardinality"]
minQualifiedCardinality		= OWLNS["minQualifiedCardinality"]
onClass						= OWLNS["onClass"]
onDataRange					= OWLNS["onDataRange"]
onDatatype					= OWLNS["onDatatype"]
oneOf						= OWLNS["oneOf"]
onProperty					= OWLNS["onProperty"]
onProperties				= OWLNS["onProperties"]
OWLpredicate				= OWLNS["predicate"]
priorVersion				= OWLNS["priorVersion"]
propertyChainAxiom			= OWLNS["propertyChainAxiom"]
propertyDisjointWith		= OWLNS["propertyDisjointWith"]
qualifiedCardinality		= OWLNS["qualifiedCardinality"]
sameAs						= OWLNS["sameAs"]
someValuesFrom				= OWLNS["someValuesFrom"]
sourceIndividual			= OWLNS["sourceIndividual"]
OWLsubject					= OWLNS["subject"]
targetIndividual			= OWLNS["targetIndividual"]
targetValue					= OWLNS["targetValue"]
TopDataProperty				= OWLNS["TopDataProperty"]
TopObjectProperty			= OWLNS["TopObjectProperty"]
unionOf						= OWLNS["unionOf"]
versionInfo					= OWLNS["versionInfo"]
versionIRI					= OWLNS["versionIRI"]
withRestrictions			= OWLNS["withRestrictions"]

AllDisjointProperties		= OWLNS["AllDisjointProperties"]
AllDifferent				= OWLNS["AllDifferent"]
AllDisjointClasses			= OWLNS["AllDisjointClasses"]
Annotation					= OWLNS["Annotation"]
AnnotationProperty			= OWLNS["AnnotationProperty"]
AsymmetricProperty			= OWLNS["AsymmetricProperty"]
Axiom						= OWLNS["Axiom"]
OWLClass					= OWLNS["Class"]
DataRange					= OWLNS["DataRange"]
DatatypeProperty			= OWLNS["DatatypeProperty"]
DeprecatedClass				= OWLNS["DeprecatedClass"]
DeprecatedProperty			= OWLNS["DeprecatedProperty"]
FunctionalProperty			= OWLNS["FunctionalProperty"]
InverseFunctionalProperty	= OWLNS["InverseFunctionalProperty"]
IrreflexiveProperty			= OWLNS["IrreflexiveProperty"]
NamedIndividual				= OWLNS["NamedIndividual"]
NegativePropertyAssertion	= OWLNS["NegativePropertyAssertion"]
Nothing						= OWLNS["Nothing"]
ObjectProperty				= OWLNS["ObjectProperty"]
Ontology					= OWLNS["Ontology"]
OntologyProperty			= OWLNS["OntologyProperty"]
ReflexiveProperty			= OWLNS["ReflexiveProperty"]
Restriction					= OWLNS["Restriction"]
Thing						= OWLNS["Thing"]
SelfRestriction				= OWLNS["SelfRestriction"]
SymmetricProperty			= OWLNS["SymmetricProperty"]
TransitiveProperty			= OWLNS["TransitiveProperty"]

