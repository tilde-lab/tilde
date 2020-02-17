
# Copyright Tilde Materials Informatics
# Distributed under the MIT License

from __future__ import print_function

from setuptools import setup, find_packages
from codecs import open
import os
import sys

# Search for required system packages
missing_packages = []
try:
    import numpy
    from numpy import linalg
except ImportError:
    missing_packages.append('numpy')

try:
    from distutils.sysconfig import get_makefile_filename
except ImportError:
    missing_packages.append('build-essential')
    missing_packages.append('python-dev')

import subprocess

child = subprocess.Popen(["pkg-config", "libffi"], stdout=subprocess.PIPE)
status = child.communicate()[0]
if child.returncode != 0:
    missing_packages.append('libffi-dev')

if missing_packages:
    print("Please install the following required packages (or equivalents) on your system:")
    print("".join([" * %s\n" % p for p in missing_packages]))
    print()
    print("Installation will now exit.")
    sys.exit(1)

# convert documentation to rst
try:
   import pypandoc
   long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError, RuntimeError) as e:
    if len(sys.argv) > 2 and sys.argv[2] == "upload":
        raise e.__class__("PyPI servers need reStructuredText as README! Please install pypandoc to convert markdown "
                          "to rst")
    else:
        long_description = ''

from tilde import __version__

packages = find_packages(exclude=["tests", "tests.*"])

install_requires = [
    'numpy == 1.16.6',
    'ujson',
    'bcrypt',
    'importlib',
    'pg8000',
    'sqlalchemy',
    'argparse',
    'ase',
    'spglib',
    'tornado == 4.5.3',
    'sockjs-tornado',
    'websocket-client',
    'httplib2',
    'quantum_esperanto',
    'pycrystal'
]

setup(
    name='tilde',
    version=__version__,
    description='Materials informatics framework for ab initio data repositories',
    long_description=long_description,
    url='https://github.com/tilde-lab/tilde',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    keywords='CRYSTAL Quantum-ESPRESSO VASP ab-initio materials informatics first-principles',
    packages=packages,
    include_package_data=True,
    install_requires=install_requires,
    tests_require= ['nose',],
    test_suite='nose.collector',
    scripts=[
        "utils/tilde",
        "utils/entry.py",
        "utils/gui_server.py",
        "utils/chk_tilde_install.py"
    ]
)
