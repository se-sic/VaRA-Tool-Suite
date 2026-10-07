"""This module contains utility functions for benchbuild."""

from contextlib import contextmanager  # contextmanager

from benchbuild.settings import CFG  #  import CFG for the main change

"""Utility functions mainly to change benchbuild settings.
"""


@contextmanager
def temporary_tmp_dir():
    """Temporarily change CFG.tmp_dir and restore it on exit."""
    old_tmp_dir = CFG["tmp_dir"].value
    try:
        CFG["tmp_dir"] = str(old_tmp_dir) + "/patch-sources"
        yield
    finally:
        CFG["tmp_dir"] = str(old_tmp_dir)
