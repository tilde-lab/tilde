# -*- coding: utf-8 -*-
#
"""
Module to datatype restrictions, ie, data ranges.
 
The module implements the following aspects of datatype restrictions:

 - a new datatype is created run-time and added to the allowed and accepted datatypes; literals are checked whether they abide to the restrictions
 - the new datatype is defined to be a 'subClass' of the restricted datatype
 - literals of the restricted datatype and that abide to the restrictions defined by the facets are also assigned to be of the new type
 
The last item is important to handle the following structures::
 ex:RE a owl:Restriction ;
	owl:onProperty ex:p ;
	owl:someValuesFrom [
		a rdfs:Datatype ;
		owl:onDatatype xsd:string ;
		owl:withRestrictions (
			[ xsd:minLength "3"^^xsd:integer ]
			[ xsd:maxLength "6"^^xsd:integer ]
		)
	]
 .
 ex:q ex:p "abcd"^^xsd:string.
In the case above the system can then infer that C{ex:q} is also of type C{ex:RE}.

Datatype restrictions are used by the L{OWL RL Extensions<OWLRLExtras.OWLRL_Extension>} extension class.

The implementation is not 100% complete. Some things that an ideal implementation should do are not done yet like:

 - checking whether a facet is of a datatype that is allowed for that facet
 - handling of non-literals in the facets (ie, if the resource is defined to be of type literal, but whose value
 is defined via a separate 'owl:sameAs' somewhere else)

@requires: U{RDFLib<http://rdflib.net>}, 2.2.2. and higher
@license: This software is available for use under the U{W3C Software License<http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}
@author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}

"""

"""
$Id: RestrictedDatatype.py,v 1.5 2011/08/04 12:41:58 ivan Exp $ $Date: 2011/08/04 12:41:58 $
"""

__author__  = 'Ivan Herman'
__contact__ = 'Ivan Herman, ivan@w3.org'
__license__ = u'W3C® SOFTWARE NOTICE AND LICENSE, http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231'

import re

from OWL 			import *
from OWL			import OWLNS as ns_owl
from RDFClosure.RDFS 	import Datatype
from RDFClosure.RDFS 	import type
from RDFClosure.RDFS 	import RDFNS as ns_rdf

import rdflib
if rdflib.__version__ >= "3.0.0" :
	from rdflib	import Literal as rdflibLiteral
	from rdflib.namespace import Namespace
	from rdflib.namespace 	import XSD as ns_xsd
else :
	from rdflib.Literal 	import _XSD_NS as ns_xsd
	from rdflib.Literal	import Literal as rdflibLiteral


from DatatypeHandling import AltXSDToPYTHON

#: Constant for datatypes using min, max (inclusive and exclusive):
MIN_MAX					= 0
#: Constant for datatypes using length, minLength, and maxLength (and nothing else)
LENGTH					= 1
#: Constant for datatypes using length, minLength, maxLength, and pattern
LENGTH_AND_PATTERN 		= 2
#: Constat for datatypes using length, minLength, maxLength, pattern, and lang range
LENGTH_PATTERN_LRANGE 	= 3

#: Dictionary of all the datatypes, keyed by category
Datatypes_per_facets = {
	MIN_MAX					: [ ns_owl["rational"], ns_xsd["decimal"], ns_xsd["integer"],
								ns_xsd["nonNegativeInteger"], ns_xsd["nonPositiveInteger"],
								ns_xsd["positiveInteger"], ns_xsd["negativeInteger"],
								ns_xsd["long"], ns_xsd["short"], ns_xsd["byte"],
								ns_xsd["unsignedLong"], ns_xsd["unsignedInt"], ns_xsd["unsignedShort"], ns_xsd["unsignedByte"],
								ns_xsd["double"], ns_xsd["float"],
								ns_xsd["dateTime"], ns_xsd["dateTimeStamp"], ns_xsd["time"], ns_xsd["date"]
							],
	LENGTH					: [ ns_xsd["hexBinary"], ns_xsd["base64Binary"] ],
	LENGTH_AND_PATTERN		: [ ns_xsd["anyURI"], ns_xsd["string"], ns_xsd["NMTOKEN"], ns_xsd["Name"], ns_xsd["NCName"],
								ns_xsd["language"], ns_xsd["normalizedString"]
							],
	LENGTH_PATTERN_LRANGE	: [ ns_rdf["plainLiteral"] ]
}

#: a simple list containing C{all} datatypes that may have a facet
facetable_datatypes = reduce(lambda x,y: x+y, Datatypes_per_facets.values())

#######################################################################################################

def _lit_to_value(dt, v) :
	"""
	This method is used to convert a string to a value with facet checking. RDF Literals are converted to
	Python values using this method; if there is a problem, an exception is raised (and caught higher
	up to generate an error message).
	
	The method is the equivalent of all the methods in the L{DatatypeHandling} module, and is registered
	to the system run time, as new restricted datatypes are discovered.
	
	(Technically, the registration is done via a C{lambda v: _lit_to_value(self,v)} setting from within a
	L{RestrictedDatatype} instance)
	@param dt: faceted datatype
	@type dt: L{RestrictedDatatype}
	@param v: literal to be converted and checked
	@raise ValueError: invalid literal value
	"""
	# This may raise an exception...
	value = dt.converter(v)
	
	# look at the different facet categories and try to find which is
	# is, if any, the one that is of relevant for this literal
	for cat in Datatypes_per_facets.keys() :
		if dt.base_type in Datatypes_per_facets[cat] :
			# yep, this is to be checked.
			if not dt.checkValue(value) :
				raise ValueError("Literal value %s does not fit the faceted datatype %s" % (v,dt))			
	# got here, everything should be fine
	return value

def _lang_range_check(range, lang) :
	"""
	Implementation of the extended filtering algorithm, as defined in point 3.3.2,
	of U{RFC 4647<http://www.rfc-editor.org/rfc/rfc4647.txt>}, on matching language ranges and language tags.
	Needed to handle the C{rdf:PlainLiteral} datatype.
	@param range: language range
	@param lang: language tag
	@rtype: boolean
	"""
	def _match(r,l) :
		"""Matching of a range and language item: either range is a wildcard or the two are equal
		@param r: language range item
		@param l: language tag item
		@rtype: boolean
		"""
		return r == '*' or r == l
	
	rangeList = range.strip().lower().split('-')
	langList  = lang.strip().lower().split('-')
	if not _match(rangeList[0], langList[0]) : return False
	
	rI = 1
	rL = 1
	while rI < len(rangeList) :
		if rangeList[rI] == '*' :
			rI += 1
			continue
		if rL >= len(langList) :
			return False
		if _match(rangeList[rI], langList[rL]) :
			rI += 1
			rL += 1
			continue
		if len(langList[rL]) == 1 :
			return False
		else :
			rL += 1
			continue
	return True

#######################################################################################################

def extract_faceted_datatypes(core, graph) :
	"""
	Extractions of restricted (ie, faceted) datatypes from the graph.
	@param core: the core closure instance that is being handled
	@type core: L{Closure.Core}
	@param graph: RDFLib graph
	@return: array of L{RestrictedDatatype} instances
	"""
	retval = []
	for dtype in graph.subjects(type, Datatype) :
		base_type = None
		facets    = []
		try :
			base_types = [ x for x in graph.objects(dtype, onDatatype) ]
			if len(base_types) > 0 :
				if len(base_types) > 1 :
					raise Exception("Several base datatype for the same restriction %s" % dtype)
				else :
					base_type = base_types[0]
					if base_type in facetable_datatypes :
						rlists = [ x for x in graph.objects(dtype, withRestrictions) ]
						if len(rlists) > 1 :
							raise Exception("More than one facet lists for the same restriction %s" % dtype)
						elif len(rlists) > 0 :
							final_facets = []
							for r in graph.items(rlists[0]) :
								for (facet,lit) in graph.predicate_objects(r) :
									if isinstance(lit, rdflibLiteral) :
										# the python value of the literal should be extracted
										# note that this call may lead to an exception, but that is fine,
										# it is caught some lines below anyway...
										try :
											if lit.datatype == None or lit.datatype == ns_xsd["string"]:
												final_facets.append((facet, str(lit)))
											else :
												final_facets.append((facet, AltXSDToPYTHON[lit.datatype](str(lit))))
										except Exception, msg :
											core.add_error(msg)
											continue
								# We do have everything we need:
							new_datatype = RestrictedDatatype(dtype, base_type, final_facets)
							retval.append(new_datatype)
		except Exception, msg :
			#import sys
			#print sys.exc_info()
			#print sys.exc_type
			#print sys.exc_value
			#print sys.exc_traceback
			core.add_error(msg)
			continue
	return retval


class RestrictedDatatypeCore :
	"""An 'abstract' superclass for datatype restrictions. The instance variables liste here are
	used in general, without the specificities of the concrete restricted datatype.
	
	This module defines the L{RestrictedDatatype} class that corresponds to the datatypes and their restrictions
	defined in the OWL 2 standard. Other modules may subclass this class to define new datatypes with restrictons.
	@ivar datatype  : the URI for this datatype
	@ivar base_type : URI of the datatype that is restricted
	@ivar toPython  : function to convert a Literal of the specified type to a Python value.	
	"""
	def __init__(self, type_uri, base_type) :
		self.datatype  = type_uri
		self.base_type = base_type
		self.toPython  = None
		
	def checkValue(self, value) :
		"""
		Check whether the (python) value abides to the constraints defined by the current facets.
		@param value: the value to be checked
		@rtype: boolean
		"""
		raise Exception("This class should not be used by itself, only via its subclasses!")

class RestrictedDatatype(RestrictedDatatypeCore) :
	"""
	Implementation of a datatype with facets, ie, datatype with restrictions.
	
	@ivar datatype  : the URI for this datatype
	@ivar base_type : URI of the datatype that is restricted
	@ivar converter : method to convert a literal of the base type to a Python value (drawn from L{DatatypeHandling.AltXSDToPYTHON})
	@ivar minExclusive : value for the C{xsd:minExclusive} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar minInclusive : value for the C{xsd:minInclusive} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar maxExclusive : value for the C{xsd:maxExclusive} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar maxInclusive : value for the C{xsd:maxInclusive} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar minLength : value for the C{xsd:minLength} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar maxLength : value for the C{xsd:maxLength} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar length : value for the C{xsd:length} facet, initialized to C{None} and set to the right value if a facet is around
	@ivar pattern : array of patterns for the C{xsd:pattern} facet, initialized to C{[]} and set to the right value if a facet is around
	@ivar langRange : array of language ranges for the C{rdf:langRange} facet, initialized to C{[]} and set to the right value if a facet is around
	@ivar check_methods : list of class methods that are relevant for the given C{base_type}
	@ivar toPython : function to convert a Literal of the specified type to a Python value. Is defined by C{lambda v : _lit_to_value(self, v)}, see L{_lit_to_value}	
	"""
	
	def __init__(self, type_uri, base_type, facets) :
		"""
		@param type_uri: URI of the datatype being defined
		@param base_type: URI of the base datatype, ie, the one being restricted
		@param facets : array of C{(facetURI, value)} pairs
		"""
		RestrictedDatatypeCore.__init__(self, type_uri, base_type)
		if self.base_type not in AltXSDToPYTHON :
			raise Exception( "No facet is implemented for datatype %s" % self.base_type )
		self.converter = AltXSDToPYTHON[ self.base_type ]

		self.minExclusive = None
		self.maxExclusive = None
		self.minInclusive = None
		self.maxInclusive = None
		self.length       = None
		self.maxLength    = None
		self.minLength    = None
		self.pattern      = []
		self.langRange    = []
		for (facet, value) in facets :
			if   facet == ns_xsd["minInclusive"] and (self.minInclusive == None or self.minInclusive < value) :
				self.minInclusive = value
			elif facet == ns_xsd["minExclusive"] and (self.minExclusive == None or self.minExclusive < value) :
				self.minExclusive = value
			elif facet == ns_xsd["maxInclusive"] and (self.maxInclusive == None or value < self.maxInclusive) :
				self.maxInclusive = value
			elif facet == ns_xsd["maxExclusive"] and (self.maxExclusive == None or value < self.maxExclusive) :
				self.maxExclusive = value
			elif facet == ns_rdf["langRange"] :
				self.langRange.append(value)
			elif facet == ns_xsd["length"]	:
				self.length = value
			elif facet == ns_xsd["maxLength"] and (self.maxLength == None or value < self.maxLength) :
				self.maxLength = value
			elif facet == ns_xsd["minLength"] and (self.maxLength == None or value < self.maxLength) :
				self.minLength 	= value
			elif facet == ns_xsd["pattern"]	:
				self.pattern.append(re.compile(value))
			
		# Choose the methods that are relevant for this datatype, based on the base type
		facet_to_method = {
			MIN_MAX					: [ RestrictedDatatype._check_max_exclusive, RestrictedDatatype._check_min_exclusive,
										RestrictedDatatype._check_max_inclusive, RestrictedDatatype._check_min_inclusive ],
			LENGTH					: [ RestrictedDatatype._check_min_length, RestrictedDatatype._check_max_length,
										RestrictedDatatype._check_length ],
			LENGTH_AND_PATTERN 		: [ RestrictedDatatype._check_min_length, RestrictedDatatype._check_max_length,
										RestrictedDatatype._check_length, RestrictedDatatype._check_pattern ],
			LENGTH_PATTERN_LRANGE 	: [ RestrictedDatatype._check_min_length, RestrictedDatatype._check_max_length,
										RestrictedDatatype._check_length, RestrictedDatatype._check_lang_range]
		}
		self.check_methods = []
		for cat in Datatypes_per_facets.keys() :
			if self.base_type in Datatypes_per_facets[cat] :
				self.check_methods = facet_to_method[cat]
				break
		self.toPython = lambda v : _lit_to_value(self, v)		

	def checkValue(self, value) :
		"""
		Check whether the (python) value abides to the constraints defined by the current facets.
		@param value: the value to be checked
		@rtype: boolean
		"""
		for method in self.check_methods :
			if not method(self, value) :
				return False
		return True

	def _check_min_exclusive(self, value) :
		"""
		Check  the (python) value against min exclusive facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if self.minExclusive != None :
			return sel.minExclusive < value
		else :
			return True
					
	def _check_min_inclusive(self, value) :
		"""
		Check  the (python) value against min inclusive facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if self.minInclusive != None :
			return self.minInclusive <= value
		else :
			return True
					
	def _check_max_exclusive(self, value) :
		"""
		Check  the (python) value against max exclusive facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if self.maxExclusive != None :
			return value < self.maxExclusive
		else :
			return True
					
	def _check_max_inclusive(self, value) :
		"""
		Check  the (python) value against max inclusive facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if self.maxInclusive != None :
			return value <= self.maxInclusive
		else :
			return True
		
	def _check_min_length(self, value) :
		"""
		Check  the (python) value against minimum length facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if isinstance(value, rdflibLiteral) :
			val = str(value)
		else :
			val = value
		if self.minLength != None :
			return self.minLength <= len(val)
		else :
			return True

	def _check_max_length(self, value) :
		"""
		Check  the (python) value against maximum length facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if isinstance(value, rdflibLiteral) :
			val = str(value)
		else :
			val = value
		if self.maxLength != None :
			return self.maxLength >= len(val)
		else :
			return True
		
	def _check_length(self, value) :
		"""
		Check  the (python) value against exact length facet.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if isinstance(value, rdflibLiteral) :
			val = str(value)
		else :
			val = value
		if self.length != None :
			return self.length == len(val)
		else :
			return True
		
	def _check_pattern(self, value) :
		"""
		Check  the (python) value against array of regular expressions.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if isinstance(value, rdflibLiteral) :
			val = str(value)
		else :
			val = value
		for p in self.pattern :
			if p.match(val) == None :
				return False
		return True

	def _check_lang_range(self, value) :
		"""
		Check  the (python) value against array of language ranges.
		@param value: the value to be checked
		@rtype: boolean
		"""
		if isinstance(value, rdflibLiteral) :
			lang = value.language
		else :
			return False
		for r in self.langRange :
			if _lang_range_check(r, lang) == False :
				return False
		return True
	