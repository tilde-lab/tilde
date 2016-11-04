
try:
    import tilde
except ImportError:
    import os, sys
    chk_path = os.path.realpath(os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../"
    )))
    if not chk_path in sys.path: sys.path.insert(0, chk_path)
