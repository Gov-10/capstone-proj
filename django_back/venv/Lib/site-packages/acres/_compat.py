"""Compatibility module for importing the importlib.resources API.

There is a bug in 3.9 handling of zip modules on Windows, so keep this
around until the Python 3.9 end-of-life.
"""

import sys

if sys.version_info >= (3, 10):
    from importlib.resources import files, as_file
else:
    from importlib_resources import files, as_file


__all__ = ['files', 'as_file']
