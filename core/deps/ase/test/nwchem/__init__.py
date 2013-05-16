def installed():
    import os
    from ase.test import NotAvailable
    try:
        nwchem_command = os.getenv('NWCHEM_COMMAND')
        if nwchem_command == None:
            raise NotAvailable('NWCHEM_COMMAND not defined')
    except NotAvailable:
        raise NotAvailable('Nwchem required')
    return True
