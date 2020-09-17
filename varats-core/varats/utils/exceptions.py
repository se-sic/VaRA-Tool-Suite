#!/usr/bin/env python3
"""This module contains custom exceptions."""


class ProcessTerminatedError(Exception):
    """Raised if a process was terminated."""


class ConfigurationLookupError(Exception):
    """Raised if a paper config could not be found."""
