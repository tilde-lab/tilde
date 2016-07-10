# Copyright Tilde Materials Informatics
# Distributed under the MIT License

try:
    import numpy
    from numpy import linalg
except ImportError:
    raise RuntimeError("Please, install *numpy*")

try:
    from distutils.sysconfig import get_makefile_filename
except ImportError:
    raise RuntimeError("Please, install *build-essential* and *python-dev*")

import subprocess

child = subprocess.Popen(["pkg-config", "libffi"], stdout=subprocess.PIPE)
status = child.communicate()[0]
if child.returncode != 0:
    raise RuntimeError("Please, install *libffi-dev*")

from setuptools import setup, find_packages
from codecs import open
import os


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

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
        'Topic :: Software Development :: Libraries :: Python Modules'
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ],
    keywords='CRYSTAL Quantum-ESPRESSO VASP ab-initio materials informatics first-principles',
    packages=find_packages(),
    install_requires=['numpy>=1.9', 'ujson', 'bcrypt', 'nose', 'importlib', 'pg8000', 'sqlalchemy==1.0.12', 'argparse', 'ase==3.10.0', 'spglib==1.9.1', 'tornado==4.3.0', 'sockjs-tornado', 'websocket-client', 'futures', 'httplib2'],
    package_data={
        'tilde': ['init-data.sql']
    },
    scripts=os.path.join(here, "utils", "tilde.sh")
)
