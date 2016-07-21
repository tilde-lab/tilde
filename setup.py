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

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

packages=find_packages(exclude=('tests', ))
package_data = {}
for package in packages:
    if os.path.isfile(os.path.join(*(package.split('.') + ['manifest.json',]))):
        package_data[package] = ['manifest.json',]

install_requires = [
    'numpy >= 1.9',
    'ujson',
    'bcrypt',
    'importlib',
    'pg8000',
    'sqlalchemy == 1.0.12',
    'argparse',
    'ase == 3.11',
    'spglib >= 1.9.1',
    'tornado == 4.3.0',
    'sockjs-tornado',
    'websocket-client',
    'futures',
    'httplib2']

setup(
    name='tilde',
    version='0.8.0',
    description='Materials informatics framework for ab initio data repositories',
    long_description=long_description,
    url='https://github.com/tilde-lab/tilde',
    author='Evgeny Blokhin',
    author_email='eb@tilde.pro',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ],
    keywords='CRYSTAL Quantum-ESPRESSO VASP ab-initio materials informatics first-principles',
    packages=packages,
    install_requires=install_requires,
    tests_require= ['nose',],
    test_suite='nose.collector',
    data_files=[
        ('', ['init-data.sql',]),
    ],
    package_data=package_data,
    scripts=[
        "utils/tilde.sh",
        "utils/entry.py"
    ]
)
