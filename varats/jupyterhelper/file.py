"""
This module provides different jupyther helpers to allow easier interaction
with varas file handling APIs.
"""

import typing as tp
from pathlib import Path

from varats.data.data_manager import VDM
from varats.data.reports.commit_report import CommitReport, CommitMap
from varats.data.reports.blame_report import BlameReport


def load_commit_report(file_path: Path) -> CommitReport:
    """
    Load a CommitReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return tp.cast(CommitReport,
                   VDM.load_data_class_sync(file_path, CommitReport))


def load_blame_report(file_path: Path) -> BlameReport:
    """
    Load a BlameReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return tp.cast(BlameReport,
                   VDM.load_data_class_sync(file_path, BlameReport))


def load_commit_map(file_path: str) -> CommitMap:
    """
    Load a CommitMap from a file.

    Attributes:
        file_path (str): Full path to the file
    """
    with open(file_path, "r") as c_map_file:
        return CommitMap(c_map_file.readlines())
