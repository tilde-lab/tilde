
# Tilde project: compiler for C-extensions
# v301113

import os, sys

if not 'win' in sys.platform and not os.path.exists( os.path.join( os.path.dirname(__file__), "_spglib.so" ) ):
    
    # this currently compiles spglib at Unix
    
    prev_location = os.getcwd()
    print 'Preparation in progress...\n'
    os.chdir(os.path.dirname(__file__))
    
    from distutils.core import Extension, Distribution
    from distutils.command.build_ext import build_ext
    from numpy.distutils.misc_util import get_numpy_include_dirs
    
    spglibdir = os.path.realpath(os.path.dirname(__file__) + '/deps/spglib')
    spgsrcdir = os.path.join(spglibdir, 'src')
    include_dirs = [spgsrcdir]
    sources = ["cell.c", "debug.c", "hall_symbol.c", "kpoint.c", "lattice.c", "mathfunc.c", "pointgroup.c", "primitive.c", "refinement.c", "sitesym_database.c", "site_symmetry.c", "spacegroup.c", "spin.c", "spg_database.c", "spglib.c", "symmetry.c"]
    sources = [os.path.join(spgsrcdir, srcfile) for srcfile in sources]
    ext = Extension("_spglib", include_dirs=include_dirs + get_numpy_include_dirs(), sources=[os.path.join(spglibdir, "_spglib.c")] + sources)
    dist = Distribution({'name': '_spglib', 'ext_modules': [ext]})
    cmd = build_ext(dist)
    cmd.ensure_finalized()
    cmd.inplace = 1
    cmd.run()
    
    os.chdir(prev_location)
    
    print '\nPrepared to run successfully!\n'
