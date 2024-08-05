"""This module provides different jupyther helpers to allow easier interaction
with varas file handling APIs."""

from varats.data.data_manager import VDM, PathLikeTy
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
from varats.data.reports.performance_interaction_report import (
    PerformanceInteractionReport,
    MPRPerformanceInteractionReport,
)
from varats.data.reports.szz_report import (
    SZZUnleashedReport,
    SZZReport,
    PyDrillerSZZReport,
)
from varats.experiments.vara.feature_perf_precision import (
    MPRTimeReportAggregate,
)
from varats.report.function_overhead_report import (
    WLFunctionOverheadReportAggregate,
    MPRWLFunctionOverheadReportAggregate,
)
from varats.report.gnu_time_report import (
    WLTimeReportAggregate,
    MPRWLTimeReportAggregate,
)
from varats.report.tef_report import TEFReport


def load_commit_report(file_path: PathLikeTy) -> CommitReport:
    """
    Load a CommitReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, CommitReport)


def load_blame_report(file_path: PathLikeTy) -> BlameReport:
    """
    Load a BlameReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameReport)


def load_szzunleashed_report(file_path: PathLikeTy) -> SZZReport:
    """
    Load a SZZUnleashedReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, SZZUnleashedReport)


def load_pydriller_szz_report(file_path: PathLikeTy) -> SZZReport:
    """
    Load a PyDrillerSZZReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, PyDrillerSZZReport)


def load_blame_verifier_report_no_opt_tbaa(file_path: PathLikeTy) -> \
        BlameVerifierReportNoOptTBAA:
    """
    Load a BlameVerifierReportNoOpt from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameVerifierReportNoOptTBAA)


def load_blame_verifier_report_opt(file_path: PathLikeTy) -> \
        BlameVerifierReportOpt:
    """
    Load a BlameVerifierReportOpt from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, BlameVerifierReportOpt)


def load_globals_with_report(file_path: PathLikeTy) -> \
        GlobalsReportWith:
    """
    Load a GlobalsReportWith from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, GlobalsReportWith)


def load_globals_without_report(file_path: PathLikeTy) -> \
        GlobalsReportWithout:
    """
    Load a GlobalsReportWithout from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, GlobalsReportWithout)


def load_feature_analysis_report(file_path: PathLikeTy) -> \
        FeatureAnalysisReport:
    """
    Load a FeatureAnalysisReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, FeatureAnalysisReport)


def load_tef_report(file_path: PathLikeTy) -> TEFReport:
    """
    Load a FeatureAnalysisReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, TEFReport)


def load_mpr_time_report_aggregate(
    file_path: PathLikeTy
) -> MPRTimeReportAggregate:
    """
    Load a MPRTimeReportAggregate from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, MPRTimeReportAggregate)


def load_wl_time_report_aggregate(
    file_path: PathLikeTy
) -> WLTimeReportAggregate:
    """
    Load a WLTimeReportAggregate from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, WLTimeReportAggregate)


def load_mpr_wl_time_report_aggregate(
    file_path: PathLikeTy
) -> MPRWLTimeReportAggregate:
    """
    Load a MPRWLTimeReportAggregate from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, MPRWLTimeReportAggregate)


def load_performance_interaction_report(
    file_path: PathLikeTy
) -> PerformanceInteractionReport:
    """
    Load a PerformanceInteractionReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, PerformanceInteractionReport)


def load_mpr_performance_interaction_report(
    file_path: PathLikeTy
) -> MPRPerformanceInteractionReport:
    """
    Load a MPRPerformanceInteractionReport from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(file_path, MPRPerformanceInteractionReport)


def load_wl_function_overhead_report_aggregate(
    file_path: PathLikeTy
) -> WLFunctionOverheadReportAggregate:
    """
    Load a WLFunctionOverheadReportAggregate from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(
        file_path, WLFunctionOverheadReportAggregate
    )


def load_mpr_wl_function_overhead_report_aggregate(
    file_path: PathLikeTy
) -> MPRWLFunctionOverheadReportAggregate:
    """
    Load a MPRWLFunctionOverheadReportAggregate from a file.

    Attributes:
        file_path (Path): Full path to the file
    """
    return VDM.load_data_class_sync(
        file_path, MPRWLFunctionOverheadReportAggregate
    )
