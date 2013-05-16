def installed():
    # do some tests here before we import
    # Right version of Scientific?
    import os
    from ase.test import NotAvailable
    try:
        import Scientific
        version = Scientific.__version__.split(".")
        print 'Found ScientificPython version: ',Scientific.__version__
        if map(int,version) < [2,8]:
            print 'ScientificPython 2.8 or greater required for numpy support in NetCDF'
            raise NotAvailable('ScientificPython version 2.8 or greater is required')
    except (ImportError, NotAvailable):
        print "No Scientific python found. Check your PYTHONPATH"
        raise NotAvailable('ScientificPython version 2.8 or greater is required')

    if not (os.system('which dacapo.run > /dev/null 2>&1') == 0):
        print "No Dacapo Fortran executable (dacapo.run) found. Check your path settings."
        raise NotAvailable('dacapo.run is not installed on this machine or not in the path')
    return True
