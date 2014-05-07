Tilde
==========

Tilde (alias wwwtilda) is a data organizer for computational (**ab initio**) materials science. Tilde creates systemized repositories from the simulation logs of [EXCITING](http://exciting-code.org), [VASP](http://www.vasp.at) and [CRYSTAL](http://www.crystal.unito.it) packages (support is also coming for [WIEN2K](http://www.wien2k.at), [GAUSSIAN](http://gaussian.com) and [FHI-aims](http://aims.fhi-berlin.mpg.de)). The folders with logs can be scanned and the results added into a repository, systemized and visualized. Command-line interface (**CLI**) and graphical user interface (**GUI**) are implemented.

## Requirements

On Windows no additional installations are required.
On Unix/Mac:

- Python 2.x (x > 5)
- numpy Python module
- sqlite3 Python module

Tilde was tested on Windows XP, 7, 8, Linux Debian and Suse operating systems.

## Usage

Warning! This is an early pre-release, not fully tested, may work unstable. However, the user data are sacred and will never be affected.

Unpack, avoiding spaces and non-latin characters in the path. Run with "tilde.bat" (for Windows) or "tilde.sh" (for Unix). The run with a parameter (e.g. "-h" or "--help") starts command-line interface (**CLI**), the run without parameters starts graphical user interface (**GUI**). To terminate **GUI** on Windows, close the DOS box, on Unix hit Ctrl+C. On Unix **GUI** may also run in a background / daemon mode. Adding data is possible using both **CLI** and **GUI**.

## Example

To scan folder(s) recursively (-r), with terse print (-t), showing information on calculation convergence (-v) and adding results to a database (-a):

    $ D:\wwwtilda\tilde.bat C:\work1 C:\work2 -r -t -v -a
    $ /home/user/wwwtilda/tilde.sh /home/user/work1 /home/work2 -r -t -v -a

## GUI hints

Hit key "q" to close all the active windows. Use CTRL+mouse wheel to increase font size to your taste. Avoid using **GUI** on large folders with data (more than several gigabytes), as **CLI** is much faster in this case.

## Licensing

Tilde has [MIT-license](http://en.wikipedia.org/wiki/MIT_License). This means everybody is welcomed to use it for own needs for free or modify and adopt its source code.

## Similar projects

Other known similar projects are collected below (in an alphabetic order):

- Accelrys Pipeline Pilot and Materials Studio, http://accelrys.com/products
- ADMIRAL framework: Advanced Data-Mining for Improved Research And Learning, Trinity College, Dublin
- AFLOW framework and Aflowlib.org repository, http://www.aflowlib.org
- AIDA: Automated Infrastructure and Database for Ab-initio design, Bosch LLC, http://www.cecam.org/workshop-4-717.html?presentation_id=9102
- Blue Obelisk Data Repository (XSLT, XML), http://bodr.sourceforge.net
- Catapp, http://www.slac.stanford.edu/~strabo/catapp
- CCLib (Python), http://cclib.sf.net
- CDF (Python), http://kitchingroup.cheme.cmu.edu/cdf
- CMR (Python), https://wiki.fysik.dtu.dk/cmr
- Computational Chemistry Comparison and Benchmark Database, http://cccbdb.nist.gov
- cctbx: Computational Crystallography Toolbox, http://cctbx.sourceforge.net
- ESTEST (Python, XQuery), http://estest.ucdavis.edu
- J-ICE (based on Jmol, Java), http://j-ice.sourceforge.net
- Materials Project (Python), http://www.materialsproject.org
- OQMD and qmpy (Python), http://oqmd.org
- PAULING FILE world largest database for inorganic compounds, http://paulingfile.com
- pyCMW (Python), a framework of Max Planck Institute for Iron Research GmbH
- QMForge (Python), http://qmforge.sourceforge.net
- Quixote, http://quixote.wikispot.org
- Scipio (Java), https://scipio.iciq.es
- WebMO: Web-based interface to computational chemistry packages (Java, Perl), http://webmo.net

## Openness principle

Tilde adopts the principle of open data, open source code and open standards declared by an initiative group with a symbolic name [Blue Obelisk](http://www.jcheminf.com/content/3/1/37).

![Blue Obelisk logo and tagline](https://wwwtilda.googlecode.com/files/blue_obelisk.gif)

## Contact

Please, send your feedback, bugreports and feature requests via [email](mailto:eb@tilde.pro), [Twitter](http://twitter.com/wwwtilda) or [GitHub](http://github.com/jam31/wwwtilda/issues).

## Links

- http://github.com/jam31/wwwtilda
- http://twitter.com/wwwtilda
