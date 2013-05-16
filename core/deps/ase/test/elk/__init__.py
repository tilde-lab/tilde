def installed():
    import os
    from ase.test import NotAvailable
    try:
        elk_species_path = os.getenv('ELK_SPECIES_PATH')
        if elk_species_path == None:
            raise NotAvailable('ELK_SPECIES_PATH not defined')
    except NotAvailable:
        raise NotAvailable('ELK required')
    return True
