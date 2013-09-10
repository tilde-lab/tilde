
# tilda project: EXCITING calculations parser
# v060913

import os
import sys
import math

from numpy import dot
from numpy import array
from numpy import matrix

from ase.lattice.spacegroup.cell import cell_to_cellpar
from ase.units import Bohr, Hartree

from parsers import Output

# INFO.OUT parser
Hartree=1
class INFOOUT(Output):
	def __init__(self, file, **kwargs):
		Output.__init__(self, file)
		self.data = open(file).readlines()
		
		cur_folder = os.path.dirname(file)
		
		self.info['finished'] = -1
		
		fracts_holder = [[]]
		cell = []
		forces, energies, energies_opt, optmethods = [], [], [], []
		
		first_cycle_lithium, opt_flag = True, False
		
		H_mapping = {
		3: 'LSDAPerdew-Wang',
		22: 'PBEsol',
		20: 'PBE-GGA/PBE-GGA',
		100:'PBE-GGA/PBE-GGA'
		}
		
		for n in range(len(self.data)):
			line = self.data[n]
			if ' EXCITING ' in line:
				if 'started' in line:
					version = line.split()[2].capitalize()
					if version not in ['Helium', 'Lithium', 'Beryllium']: raise RuntimeError("This Exciting version is currently not supported!")
					self.info['prog'] = 'Exciting ' + version
				#elif 'stopped' in line:
				#	self.info['finished'] = 1
					
			elif 'Convergence targets achieved' in line:
				if not energies_opt: self.info['finished'] = 1
				
			elif 'Force convergence target achieved' in line:
				self.info['finished'] = 1
				
			elif 'Lattice vectors' in line:
				for i in range(n+1, n+4):
					cell.append(  array(map(lambda x: float(x) * Bohr, self.data[i].split()))  )
				n += 3
					
			elif 'Species : ' in line:				
				symb = line.split('(')[-1][:-2]
				while 1:					
					n += 1
					if 'atomic positions (lattice)' in self.data[n]:
						while 1:
							n += 1
							a = self.data[n].split()
							try: int(a[0])
							except (ValueError, IndexError): break
							else:
								fracts_holder[-1].append([symb])
								fracts_holder[-1][-1].extend( map(float, [a[2], a[3], a[4]]) )
						break
					#elif 'muffin-tin radius' in self.data[n]:
				
			#elif 'Spin treatment ' in line:
			#	self.method['spin'] = "x".join(line.split(":")[-1].split())
				
			elif 'k-point grid ' in line:
				self.method['k'] = "x".join(line.split(":")[-1].split())
				
			elif 'Smallest muffin-tin radius times maximum |G+k|' in line: # Lithium
				self.method['tol'] = 'rkmax %s' % float(line.split(":")[-1].strip())
				
			elif 'R^MT_min * |G+k|_max (rgkmax)' in line: # Beryllium
				self.method['tol'] = 'rkmax %s' % float(line.split(":")[-1].strip())
				
			elif 'orrelation type :' in line:
				
				#if 'Correlation type :' in line:					
				#if 'Exchange-correlation type :' in line:					
				
				h = int(line.split(":")[-1])
				try: self.method['H'] = H_mapping[h]
				except KeyError: self.method['H'] = h
				
			elif 'otal energy               ' in line:
				try: energies.append(  float(line.split(":")[-1]) * Hartree  )
				except ValueError: energies.append(0.0)

			elif 'Structure-optimization module started' in line:
				opt_flag = True
				# First cycle convergence statuses
				for n in range(len(energies)):
					try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
					except IndexError: pass
				self.ncycles.append(len(self.convergence))				
				
			elif '| Updated atomic positions ' in line: # Lithium
				fracts_holder.append([])
				
				if first_cycle_lithium:
					# First cycle convergence statuses
					for n in range(len(energies)):
						try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
						except IndexError: pass
					first_cycle_lithium = False				
			
			elif '| Optimization step ' in line: # Beryllium
				self.info['finished'] = -1
				fracts_holder.append([])
				optmethods.append(line.split('method =')[-1][:-2])
				while 1:
					n += 1
					
					try: self.data[n]
					except IndexError:
						fracts_holder.pop()
						optmethods.pop()
						break
					
					if ' scf iterations ' in self.data[n]:
						self.ncycles.append(  int(self.data[n].split(":")[-1])  )
					elif 'Maximum force magnitude' in self.data[n]:
						f = self.data[n].split(":")[-1].split("(")
						forces.append( float(f[0]) - float(f[-1][:-2]) )
					elif 'Total energy' in self.data[n]:
						try: energies_opt.append(  float(self.data[n].split(":")[-1]) * Hartree  )
						except ValueError: energies_opt.append(0.0)
					elif 'Atomic positions' in self.data[n]:
						while 1:					
							n += 1
							if 'atom' in self.data[n]:
								a = self.data[n].split()
								fracts_holder[-1].append([a[2]])
								fracts_holder[-1][-1].extend( map(float, a[4:]) )
							else: break
						break
						
			elif 'Timings (CPU seconds) ' in line: # Lithium
				while 1:
					n += 1
					if ' total ' in self.data[n]:
						self.info['duration'] = "%2.2f" % (float(self.data[n].split(":")[-1])/3600)
						break
					elif len(self.data[n]) < 4: break
				self.info['duration']
				
			elif 'Total time spent ' in line: # Beryllium
				self.info['duration'] = "%2.2f" % (float(self.data[n].split(":")[-1])/3600)
		
		if not cell or not fracts_holder[-1]: raise RuntimeError("Structure not found!")
		
		if energies_opt: self.energy = energies_opt[-1]
		else:
			try: self.energy = energies[-1]
			except IndexError: pass
		
		if not self.convergence:
			# First cycle convergence statuses
			for n in range(len(energies)):
				try: self.convergence.append( int( math.floor( math.log( abs( energies[n] - energies[n+1] ), 10 ) ) )  )
				except (IndexError, ValueError): pass
		
		if len(forces) != len(energies_opt) or len(forces) != len(optmethods) or len(forces) != len(self.ncycles): self.warning("Warning! Unexpected convergence data format!")
		else:
			for n in range(len(energies_opt)):
				self.tresholds.append([forces[n], 0.0, 0.0, 0.0, energies_opt[n]])
			
		# de-fractionize
		# lattice is always the same
		cell = array(cell)
		for fract in fracts_holder:
			xyz_atoms = []
			for i in fract:
				R = dot( array([i[1], i[2], i[3]]), cell )
				xyz_atoms.append( [i[0], R[0], R[1], R[2]] )
			self.structures.append({'cell': cell_to_cellpar( cell ).tolist(), 'atoms': xyz_atoms, 'periodicity': 3})
		
		# Check if convergence achieved right away from the first cycle and account that
		if opt_flag and len(self.structures) == 1:
			self.structures.append(self.structures[-1])
			self.tresholds.append([0.0, 0.0, 0.0, 0.0, energies[-1]])
		
		# Forces
		
		# Warnings
		#try: w = map(lambda x: x.strip(), open(cur_folder + '/WARNINGS.OUT').readlines())
		#except IOError: pass
		#else:
		#	# TODO: Get rid of redundant messages
		#	# Warning(charge)
		#	self.warning( " ".join(w) )
			
		self.data = "".join(self.data)
		
		
	@staticmethod
	def fingerprints(test_string):
		if test_string.startswith('All units are atomic (Hartree, Bohr, etc.)') or test_string.startswith('| All units are atomic (Hartree, Bohr, etc.)'): return True
		else: return False
		
