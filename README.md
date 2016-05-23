Tilde
==========
[![DOI](https://zenodo.org/badge/18811/tilde-lab/tilde.svg)](https://zenodo.org/badge/latestdoi/18811/tilde-lab/tilde)

Tilde is an intelligent data organizer and Python framework for computational _ab initio_ materials science. Tilde creates systemized data repositories from the simulation logs of [VASP](http://www.vasp.at), [CRYSTAL](http://www.crystal.unito.it) and [Quantum ESPRESSO](http://www.quantum-espresso.org) packages. Other data formats can be added relatively easily. The folders with the log files can be scanned and the results added into a repository. A simple usecase is described in [this blog post](https://blog.tilde.pro/simple-ab-initio-materials-data-mining-tutorial-6127c777dabc). Web-based repository GUI is [separately available](https://github.com/tilde-lab/berlinium).

## Installation

System packages ```build-essential python-dev python-numpy libffi-dev``` (**-dev** or **-devel**) must be present. Please, [set up Python virtualenv](https://virtualenv.readthedocs.org) inside the Tilde folder (and mind ```--system-site-packages``` option to access ```python-numpy```):

```shell
virtualenv --system-site-packages tilde
```

Then activate virtualenv:

```shell
. bin/activate
```

Virtualenv should be always used while working with the codebase.
Run ```pip install -r requirements.txt``` to install Python dependencies.
Finally, ensure if the framework is ready:

```shell
./utils/tilde.sh -x
```

Additionally, installation is covered in [this blog post](https://blog.tilde.pro/simple-ab-initio-materials-data-mining-tutorial-6127c777dabc).

## Usage

```shell
./utils/tilde.sh --help
```

For example, to scan folder(s) recursively (**-r**), with terse print (**-t**), showing information on calculation metadata (**-i**) and convergence (**-v**) and adding results to a database (**-a**):

```shell
./utils/tilde.sh /home/user/work1 /home/work2 -r -t -v -a -i
```

Other example: for the perovskite structures (shipped with Tilde), extract the distortion of the MO6-octahedra wrt cubic phase (in Euler angles). Here the **-m** switch invokes **perovskite_tilting** module (see **apps** folder):

```shell
./utils/tilde.sh tilde/tests/apps/perovskite_tilting/outputs -m perovskite_tilting
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
- AFLOW framework and Aflowlib repository, http://www.aflowlib.org
- AiiDA: Automated Infrastructure and Database for Ab-initio design, Bosch LLC (**Python**), http://aiida.net
- Automated Topology Builder (ATB), http://compbio.biosci.uq.edu.au/atb
- Blue Obelisk Data Repository (**XSLT, XML**), http://bodr.sourceforge.net
- Catapp, http://www.slac.stanford.edu/~strabo/catapp
- CCLib (**Python**), http://cclib.sf.net
- cctbx: Computational Crystallography Toolbox, http://cctbx.sourceforge.net
- CEPDB: Harvard Clean Energy Project and distributed volunteer computing, http://cepdb.molecularspace.org
- CMR (**Python**), https://wiki.fysik.dtu.dk/cmr
- Computational Chemistry Comparison and Benchmark Database, http://cccbdb.nist.gov
- Crystallography Open Database (including Theoretical Database
- Delta project: Comparing Solid State DFT Codes, http://molmod.ugent.be/deltacodesdft
- Electronic Structure Project, http://gurka.fysik.uu.se/ESP
- ESTEST (**Python, XQuery**), http://estest.ucdavis.edu
- Exabyte.io, Materials Discover Cloud, http://exabyte.io
- J-ICE (based on **Jmol, Java**), http://j-ice.sourceforge.net
- ioChem-BD (**Java**), http://www.iochem-bd.org
- Materials Project (**Python**), http://www.materialsproject.org
- MatNavi and AtomWork Materials Databases, Materials Information Station, Tsukuba, http://mits.nims.go.jp/matnavi/
- MedeA Computational environment, http://www.materialsdesign.com/medea
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
- WebMO: Web-based interface to computational chemistry packages (Java, Perl), http://webmo.net
- WURM: database of computed physical properties of minerals, http://wurm.info

## Openness principle

Tilde adopts the principle of open data, open source code and open standards declared by an initiative group with a symbolic name [Blue Obelisk](http://www.jcheminf.com/content/3/1/37).

![Blue Obelisk](https://raw.githubusercontent.com/tilde-lab/tilde/master/blue_obelisk.gif "Blue Obelisk")

## Contact

Please, send your feedback, bugreports and feature requests via [email](mailto:eb@tilde.pro), [Twitter](http://twitter.com/tildepro) or [GitHub](http://github.com/tilde-lab/tilde/issues).
