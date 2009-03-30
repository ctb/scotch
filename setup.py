try:
    from setuptools import setup
except ImportError:
    print '(WARNING: importing distutils, not setuptools!)'
    from distutils.core import setup

#### scotch info.

setup(name = 'scotch',
      
      version = '0.1',
      author = 'C. Titus Brown',
      author_email = 'titus@caltech.edu',

      packages = ['scotch']
)
