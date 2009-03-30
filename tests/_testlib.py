import sys, os

thisdir = os.path.dirname(__file__)
scotchdir = os.path.join(thisdir, '../scotch/')

def _add_scotchdir_to_path():
    if scotchdir not in sys.path:
        sys.path.insert(0, scotchdir)
