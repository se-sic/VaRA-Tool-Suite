"""This module provides different jupyther helpers to allow easier interaction
with varas file handling APIs."""

from pathlib import Path

from varats.data.data_manager import VDM
from varats.data.reports.blame_report import BlameReport
from varats.data.reports.blame_verifier_report import (
    BlameVerifierReportOpt,
    BlameVerifierReportNoOptTBAA,
)
from varats.data.reports.commit_report import CommitReport
from varats.data.reports.feature_analysis_report import FeatureAnalysisReport
from varats.data.reports.globals_report import (
    GlobalsReportWith,
    GlobalsReportWithout,
)
from varats.data.reports.szz_report import (
    SZZUnleashedReport,
    SZZReport,
    PyDrillerSZZReport,
)
from varats.mapping.commit_map import CommitMap


def load_commit_report(file_path: Path) -> CommitReport:
    """
    Load a CommitReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, CommitReport)


def load_blame_report(file_path: Path) -> BlameReport:
    """
    Load a BlameReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameReport)


def load_szzunleashed_report(file_path: Path) -> SZZReport:
    """
    Load a SZZUnleashedReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, SZZUnleashedReport)


def load_pydriller_szz_report(file_path: Path) -> SZZReport:
    """
    Load a PyDrillerSZZReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, PyDrillerSZZReport)


def load_commit_map(file_path: str) -> CommitMap:
    """
    Load a CommitMap from a file.

    Attributes:
        file_path (str): Full path to the file
    """
    with open(file_path, "r") as c_map_file:
        return CommitMap(c_map_file.readlines())


def load_blame_verifier_report_no_opt_tbaa(file_path: Path) -> \
        BlameVerifierReportNoOptTBAA:
    """
    Load a BlameVerifierReportNoOpt from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameVerifierReportNoOptTBAA)


def load_blame_verifier_report_opt(file_path: Path) -> \
        BlameVerifierReportOpt:
    """
    Load a BlameVerifierReportOpt from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameVerifierReportOpt)


def load_globals_with_report(file_path: Path) -> \
        GlobalsReportWith:
    """
    Load a GlobalsReportWith from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, GlobalsReportWith)


def load_globals_without_report(file_path: Path) -> \
        GlobalsReportWithout:
    """
    Load a GlobalsReportWithout from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, GlobalsReportWithout)


def load_feature_analysis_report(file_path: Path) -> \
        FeatureAnalysisReport:
    """
    Load a FeatureAnalysisReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, FeatureAnalysisReport)
