def installed():
    import os
    from ase.test import NotAvailable
    try:
        abinit_pp_path = os.getenv('ABINIT_PP_PATH')
        if abinit_pp_path == None:
            raise NotAvailable('ABINIT_PP_PATH not defined')
    except NotAvailable:
        raise NotAvailable('Abinit required')
    return True
