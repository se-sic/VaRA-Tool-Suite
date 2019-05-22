"""
This module provides different jupyther helpers to allow easier interaction
with varas file handling APIs.
"""

from varats.data.data_manager import VDM
from varats.data.commit_report import CommitReport, CommitMap


def load_commit_report(file_path: str) -> CommitReport:
    """
    Load a CommitReport from a file.

    Attributes:
        file_path (str): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, CommitReport)


def load_commit_map(file_path: str) -> CommitMap:
    """
    Load a CommitMap from a file.

    Attributes:
        file_path (str): Full path to the file
    """
    with open(file_path, "r") as c_map_file:
        return CommitMap(c_map_file.readlines())
