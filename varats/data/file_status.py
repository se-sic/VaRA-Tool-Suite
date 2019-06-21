"""
Module for file status handling.
"""

from enum import Enum


class FileStatusExtension(Enum):
    """
    Enum to abstract the status of a file.
    Specific report files can map these to their own specific representation.
    """

    success = 0
    failure = 1
