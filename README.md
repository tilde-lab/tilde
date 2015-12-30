Tilde
==========
[![DOI](https://zenodo.org/badge/18811/tilde-lab/tilde.svg)](https://zenodo.org/badge/latestdoi/18811/tilde-lab/tilde)

Tilde is an intelligent data organizer and Python framework for computational (**ab initio**) materials science. Tilde creates systemized repositories from the simulation logs of [VASP](http://www.vasp.at), [CRYSTAL](http://www.crystal.unito.it) and [Quantum ESPRESSO](http://www.quantum-espresso.org) packages. The folders with the log files can be scanned and the results added into a repository. Repository GUI is coming.

## Installation

System packages ```build-essential python-dev libffi-dev``` (-dev or -devel) should be present. Also, Python package ```python-numpy``` should be present. [Set up Python virtualenv](https://virtualenv.readthedocs.org) inside the Tilde folder (note ```--system-site-packages``` option to access ```python-numpy```):

```shell
virtualenv --system-site-packages tilde
```

Then activate virtualenv:

```shell
. bin/activate
```

Virtualenv should be always used while working with the codebase.
Run ```pip install -r requirements.txt``` to install Python dependencies.
Note, that **pip** manager should be minimum of version 7.1.
Then test if the framework is ready:

```shell
./utils/tilde.sh -x
```

## Usage

```shell
./utils/tilde.sh --help
```

For example, to scan folder(s) recursively (-r), with terse print (-t), showing information on calculation convergence (-v) and adding results to a database (-a):

```shell
./utils/tilde.sh /home/user/work1 /home/work2 -r -t -v -a
```

Other example: for the perovskite structures, extract the distortion of the MO6-octahedra wrt cubic phase (in Euler angles) and detailed calculation info:

```shell
./utils/tilde.sh tilde/apps/perovskite_tilting/tests/outputs -m perovskite_tilting -i
```

## GUI

Experimental GUI server is started as follows:

```shell
python utils/gui_server.py
```

GUI client is the separate project called [Berlinium](https://github.com/tilde-lab/berlinium).

## Testing

```shell
sh tests/run_tests.sh
```

## Licensing

[MIT](https://en.wikipedia.org/wiki/MIT_License)

## Similar projects

Other known similar initiatives are listed below:

- Accelrys (BIOVIA) Pipeline Pilot and Materials Studio, http://accelrys.com/products
- ADMIRAL framework: Advanced Data-Mining for Improved Research And Learning, Trinity College, Dublin
- AFLOW framework and Aflowlib repository, http://www.aflowlib.org
- AiiDA: Automated Infrastructure and Database for Ab-initio design, Bosch LLC (**Python**), http://aiida.net
- Automated Topology Builder (ATB), http://compbio.biosci.uq.edu.au/atb
- Blue Obelisk Data Repository (**XSLT, XML**), http://bodr.sourceforge.net
- Catapp, http://www.slac.stanford.edu/~strabo/catapp
- CCLib (**Python**), http://cclib.sf.net
- CDF (**Python**), http://kitchingroup.cheme.cmu.edu/cdf
- CEPDB: Harvard Clean Energy Project and distributed volunteer computing, http://cepdb.molecularspace.org
- CMR (**Python**), https://wiki.fysik.dtu.dk/cmr
- Computational Chemistry Comparison and Benchmark Database, http://cccbdb.nist.gov
- cctbx: Computational Crystallography Toolbox, http://cctbx.sourceforge.net
- Delta project: Comparing Solid State DFT Codes, http://molmod.ugent.be/deltacodesdft
- Electronic Structure Project, http://gurka.fysik.uu.se/ESP
- ESTEST (**Python, XQuery**), http://estest.ucdavis.edu
- J-ICE (based on **Jmol, Java**), http://j-ice.sourceforge.net
- ioChem-BD (**Java**), http://www.iochem-bd.org
- Materials Project (**Python**), http://www.materialsproject.org
- MatNavi Materials Database, Materials Information Station, Tsukuba, http://caldb.nims.go.jp/CALDB/
- MSE: Test Set for Materials Science and Engineering, http://mse.fhi-berlin.mpg.de
- NoMaD: Novel Materials Discovery, http://nomad-repository.eu
- NREL MatDB, http://materials.nrel.gov
- Open Materials Database and High-Throughput Toolkit (**Python**), http://openmaterialsdb.se
- OQMD and qmpy (**Python**), http://oqmd.org
- Phonon database at Kyoto university, http://phonondb.mtl.kyoto-u.ac.jp
- PAULING FILE, world largest database for inorganic compounds, http://paulingfile.com
- pyCMW (**Python**), a framework of Max Planck Institute for Iron Research GmbH
- QMForge (**Python**), http://qmforge.sourceforge.net
- Quixote, http://quixote.wikispot.org
- Scipio (**Java**), currently inactive, https://scipio.iciq.es
- WebMO: Web-based interface to computational chemistry packages (Java, Perl), http://webmo.net
- WURM: database of computed physical properties of minerals, http://wurm.info

## Openness principle

Tilde adopts the principle of open data, open source code and open standards declared by an initiative group with a symbolic name [Blue Obelisk](http://www.jcheminf.com/content/3/1/37).

## Contact

Please, send your feedback, bugreports and feature requests via [email](mailto:eb@tilde.pro), [Twitter](http://twitter.com/tildepro) or [GitHub](http://github.com/tilde-lab/tilde/issues).
