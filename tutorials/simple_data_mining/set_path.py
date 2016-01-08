import os, sys

base_path = os.path.realpath(os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..")))

if not base_path in sys.path:
    sys.path.insert(0, base_path)

VIS_PATH = os.path.join(base_path, "tutorials", "simple_data_mining", "visualization")
