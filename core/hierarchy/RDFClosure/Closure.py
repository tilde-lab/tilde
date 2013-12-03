#!/d/Bin/Python/python.exe
# -*- coding: utf-8 -*-
#
"""
The generic superclasses for various rule based semantics and the possible extensions.

@requires: U{RDFLib<http://rdflib.net>}, 2.2.2. and higher
@license: This software is available for use under the U{W3C Software License<http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231>}
@organization: U{World Wide Web Consortium<http://www.w3.org>}
@author: U{Ivan Herman<a href="http://www.w3.org/People/Ivan/">}

"""

"""
$Id: Closure.py,v 1.18 2011/08/04 12:41:57 ivan Exp $ $Date: 2011/08/04 12:41:57 $
"""

__author__  = 'Ivan Herman'
__contact__ = 'Ivan Herman, ivan@w3.org'
__license__ = u'W3C® SOFTWARE NOTICE AND LICENSE, http://www.w3.org/Consortium/Legal/2002/copyright-software-20021231'

import rdflib
if rdflib.__version__ >= "3.0.0" :
	from rdflib			import BNode
	from rdflib			import Literal as rdflibLiteral
	from rdflib			import Namespace
else :
	from rdflib.BNode		import BNode
	from rdflib.Literal		import Literal as rdflibLiteral
	from rdflib.Namespace	import Namespace
	
from RDFClosure.RDFS	import RDFNS as ns_rdf
from RDFClosure.RDFS	import type

from RDFClosure.Literals	import LiteralProxies

debugGlobal 		= False
offlineGeneration 	= False

######################################################################################################

class Core :
	"""Core of the semantics management, dealing with the RDFS and other Semantic triples. The only
	reason to have it in a separate class is for an easier maintainability.

	This is a common superclass only. In the present module, it is subclassed by
	a L{RDFS Closure<RDFClosure.RDFSClosure.RDFS_Semantics>} class and a L{OWL RL Closure<RDFClosure.OWLRL.OWLRL_Semantics>} classes.
	There are some methods that are implemented in the subclasses only, ie, this class cannot be used by itself!

	@ivar IMaxNum: maximal index of C{rdf:_i} occurence in the graph
	@ivar literal_proxies: L{Literal Proxies with BNodes<RDFClosure.Literals.LiteralProxies>} for the graph
	@type literal_proxies: L{LiteralProxies<RDFClosure.Literals.LiteralProxies>}
	@ivar graph: the real graph
	@type graph: rdflib.Graph
	@ivar axioms: whether axioms should be added or not
	@type axioms: boolean
	@ivar daxioms: whether datatype axioms should be added or not
	@type daxioms: boolean
	@ivar added_triples: triples added to the graph, conceptually, during one processing cycle
	@type added_triples: set of triples
	@ivar error_messages: error messages (typically inconsistency messages in OWL RL) found during processing. These are added to the final graph at the very end as separate BNodes with error messages
	@type error_messages: array of strings
	@ivar rdfs: whether RDFS inference is also done (used in subclassed only)
	@type rdfs: boolean
	"""
	def __init__(self, graph, axioms, daxioms, rdfs = False) :
		"""
		@param graph: the RDF graph to be extended
		@type graph: rdflib.Graph
		@param axioms: whether axioms should be added or not
		@type axioms: boolean
		@param daxioms: whether datatype axioms should be added or not
		@type daxioms: boolean
		@param rdfs: whether RDFS inference is also done (used in subclassed only)
		@type rdfs: boolean
		"""
		self._debug = debugGlobal

		# Calculate the maximum 'n' value for the '_i' type predicates (see Horst's paper)
		n      = 1;
		maxnum = 0
		cont   = True
		while cont :
			cont = False
			predicate = ns_rdf[("_%d" % n)]
			for (s,p,o) in graph.triples((None,predicate,None)) :
				# there is at least one if we got here
				maxnum = n
				n += 1
				cont = True
		self.IMaxNum = maxnum

		self.graph   = graph
		self.axioms  = axioms
		self.daxioms = daxioms
		
		self.rdfs	 = rdfs

		self.error_messages = []
		self.empty_stored_triples()

	def add_error(self,message) :
		"""
		Add an error message
		@param message: error message
		@type message: string
		"""
		if message not in self.error_messages :
			self.error_messages.append(message)

	def pre_process(self) :
		"""
		Do some pre-processing step. This method before anything else in the closure. By default, this method is empty, subclasses
		can add content to it by overriding it.
		"""
		pass

	def post_process(self) :
		"""
		Do some post-processing step. This method when all processing is done, but before handling possible
		errors (ie, the method can add its own error messages). By default, this method is empty, subclasses
		can add content to it by overriding it.
		"""
		pass

	def rules(self,t,cycle_num) :
		"""
		The core processing cycles through every tuple in the graph and dispatches it to the various methods implementing
		a specific group of rules. By default, this method raises an exception; indeed, subclasses
		I{must} add content to by overriding it.
		@param t: one triple on which to apply the rules
		@type t: tuple
		@param cycle_num: which cycle are we in, starting with 1. This value is forwarded to all local rules; it is also used
		locally to collect the bnodes in the graph.
		"""
		raise Exception("This method should not be called directly; subclasses should override it")

	def add_axioms(self) :
		"""
		Add axioms.
		This is only a placeholder and raises an exception by default; subclasses I{must} fill this with real content
		"""
		raise Exception("This method should not be called directly; subclasses should override it")

	def add_d_axioms(self) :
		"""
		Add d axioms.
		This is only a placeholder and raises an exception by default; subclasses I{must} fill this with real content
		"""
		raise Exception("This method should not be called directly; subclasses should override it")

	def one_time_rules(self) :
		"""
		This is only a placeholder; subclasses should fill this with real content. By default, it is just an empty call.
		This set of rules is invoked only once and not in a cycle.
		"""
		pass

	def get_literal_value(self, node) :
		"""
		Return the literal value corresponding to a Literal node. Used in error messages.
		@param node: literal node
		@return: the literal value itself
		"""
		try :
			return self.literal_proxies.bnode_to_lit[node].lex
		except :
			return "????"

	def empty_stored_triples(self) :
		"""
		Empty the internal store for triples
		"""
		self.added_triples = set()
		
	def flush_stored_triples(self) :
		"""
		Send the stored triples to the graph, and empty the container
		"""
		for t in self.added_triples : self.graph.add(t)
		self.empty_stored_triples()

	def store_triple(self, t) :
		"""
		In contrast to its name, this does not yet add anything to the graph itself, it just stores the tuple in an
		L{internal set<Core.added_triples>}. (It is important for this to be a set: some of the rules in the various closures may
		generate the same tuples several times.) Before adding the tuple to the set, the method checks whether
		the tuple is in the final graph already (if yes, it is not added to the set).

		The set itself is emptied at the start of every processing cycle; the triples are then effectively added to the
		graph at the end of such a cycle. If the set is
		actually empty at that point, this means that the cycle has not added any new triple, and the full processing can stop.

		@param t: the triple to be added to the graph, unless it is already there
		@type t: a 3-element tuple of (s,p,o)
		"""
		(s,p,o) = t
		if not( isinstance(s, rdflibLiteral) or isinstance(p, rdflibLiteral) ) and t not in self.graph :
			if self._debug or offlineGeneration : print t
			self.added_triples.add(t)

	def closure(self) :
		"""
		   Generate the closure the graph. This is the real 'core'.

		   The processing rules store new triples via the L{separate method<store_triple>} which stores
		   them in the L{added_triples<added_triples>} array. If that array is emtpy at the end of a cycle,
		   it means that the whole process can be stopped.

		   If required, the relevant axiomatic triples are added to the graph before processing in cycles. Similarly
		   the exchange of literals against bnodes is also done in this step (and restored after all cycles are over).
		"""
		self.pre_process()

		# Handling the axiomatic triples. In general, this means adding all tuples in the list that
		# forwarded, and those include RDF or RDFS. In both cases the relevant parts of the container axioms should also
		# be added.
		if self.axioms :
			self.add_axioms()

		# Create the bnode proxy structure
		self.literal_proxies = LiteralProxies(self.graph)

		# Add the datatype axioms, if needed (note that this makes use of the literal proxies, the order of the call is important!
		if self.daxioms :
			self.add_d_axioms()

		self.flush_stored_triples()

		# Get first the 'one-time rules', ie, those that do not need an extra round in cycles down the line
		self.one_time_rules()
		self.flush_stored_triples()

		# Go cyclically through all rules until no change happens
		new_cycle = True
		cycle_num = 0
		error_messages = []
		while new_cycle :
			# yes, there was a change, let us go again
			cycle_num += 1

			# DEBUG: print the cycle number out
			if self._debug: print "----- Cycle #:%d" % cycle_num

			# go through all rules, and collect the replies (to see whether any change has been done)
			# the new triples to be added are collected separately not to interfere with
			# the current graph yet
			self.empty_stored_triples()

			# Execute all the rules; these might fill up the added triples array
			for t in self.graph :
				self.rules(t, cycle_num)

			# Add the tuples to the graph (if necessary, that is). If any new triple has been generated, a new cycle
			# will be necessary...
			new_cycle = len(self.added_triples) > 0

			for t in self.added_triples : self.graph.add(t)

		# All done, but we should restore the literals from their proxies
		self.literal_proxies.restore()

		self.post_process()
		self.flush_stored_triples()

		# Add possible error messages
		if self.error_messages :
			# I am not sure this is the right vocabulary to use for this purpose, but I haven't found anything!
			# I could, of course, come up with my own, but I am not sure that would be kosher...
			ERRNS  = Namespace("http://www.daml.org/2002/03/agents/agent-ont#")
			self.graph.bind("err","http://www.daml.org/2002/03/agents/agent-ont#")
			for m in self.error_messages :
				message = BNode()
				self.graph.add((message,type,ERRNS['ErrorMessage']))
				self.graph.add((message,ERRNS['error'],rdflibLiteral(m)))

