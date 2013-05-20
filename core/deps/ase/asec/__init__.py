import sys
import traceback

from ase.asec.asec import run


def main(calculator=None):
    try:
        run(calculator=calculator)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        traceback.print_exc()
        sys.stderr.write("""
An exception occurred!  Please report the issue to
ase-developer@listserv.fysik.dtu.dk - thanks!  Please also report this
if it was a user error, so that a better error message can be provided
next time.""")
        raise
