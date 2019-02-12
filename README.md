Tilde
==========
[![Build Status](https://travis-ci.org/tilde-lab/tilde.svg?branch=master)](https://travis-ci.org/tilde-lab/tilde)
[![DOI](https://zenodo.org/badge/18811/tilde-lab/tilde.svg)](https://zenodo.org/badge/latestdoi/18811/tilde-lab/tilde)
![PyPI](https://img.shields.io/pypi/v/tilde.svg?style=flat)

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

See this [curated list](https://github.com/tilde-lab/awesome-materials-informatics).

## Openness principle

Tilde adopts the principle of open data, open source code and open standards declared by an initiative group with a symbolic name [Blue Obelisk](http://www.jcheminf.com/content/3/1/37).

![Blue Obelisk](https://raw.githubusercontent.com/tilde-lab/tilde/master/blue_obelisk.gif "Blue Obelisk")

## Contact

Please, send your feedback, bugreports and feature requests via [email](mailto:eb@tilde.pro), [Twitter](http://twitter.com/tildepro) or [GitHub](http://github.com/tilde-lab/tilde/issues).
