def installed():
    import os
    from ase.test import NotAvailable
    try:
        fleur = os.getenv('FLEUR')
        if fleur == None:
            raise NotAvailable('FLEUR not defined')
    except NotAvailable:
        raise NotAvailable('Fleur required')
    return True
