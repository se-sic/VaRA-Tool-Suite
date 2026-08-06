"""Metrics for comparing commit-interaction graphs."""

import typing as tp
from collections import Counter

import networkx as nx
import pandas as pd

from varats.data.reports.blame_report import AnalysisType
from varats.experiment.experiment_util import (
    exec_func_with_pe_error_handler,
    VersionExperiment,
    ExperimentHandle,
    wrap_unlimit_stack_size,
    create_default_compiler_error_handler,
    create_default_analysis_failure_handler,
    create_new_success_result_filepath,
)
from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
    BlameReportExperimentRegion
)
from varats.experiments.vara.cfg_report_experiment import (
    CFDirectReportExperiment,
    CFCollectiveReportExperiment
)
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import PlotDataEmpty
from varats.utils.git_util import CommitRepoPair


class AnalysisConfig:
    """Configuration needed to locate one analysis report."""

    analysis_type: AnalysisType
    experiment_type: tp.Type[VersionExperiment]

    def __init__(self,
                 analysis_type: AnalysisType,
    ):
        self.analysis_type = analysis_type
        self.experiment_type = {
            AnalysisType.DF_ANALYSIS: BlameReportExperimentRegion,
            AnalysisType.CF_DIRECT_ANALYSIS: CFDirectReportExperiment,
            AnalysisType.CF_COLLECTIVE_ANALYSIS: CFCollectiveReportExperiment,
        }[analysis_type]


ANALYSIS_CONFIGS: dict[str, AnalysisConfig] = {
    "df": AnalysisConfig(
        analysis_type=AnalysisType.DF_ANALYSIS
    ),
    "cfd": AnalysisConfig(
        analysis_type=AnalysisType.CF_DIRECT_ANALYSIS
    ),
    "cfc": AnalysisConfig(
        analysis_type=AnalysisType.CF_COLLECTIVE_ANALYSIS
    ),
}

ALLOWED_ANALYSIS_COMPARISONS = {
    ("cfd-cfc"),
    ("cfd-df"),
    ("cfc-df"),
    ("cfc-cfd"),
    ("df-cfd"),
    ("df-cfc"),
}

class AnalysisComparison:
    """Supported pairwise analysis comparisons."""

    left: AnalysisConfig
    right: AnalysisConfig

    def __init__(self, left, right):
        self.left = left
        self.right = right

    @property
    def left_analysis(self) -> AnalysisType:
        return self.left.analysis_type

    @property
    def left_experiment_type(self) -> tp.Type[VersionExperiment]:
        return self.left.experiment_type

    @property
    def right_analysis(self) -> AnalysisType:
        return self.right.analysis_type

    @property
    def right_experiment_type(self) -> tp.Type[VersionExperiment]:
        return self.right.experiment_type

    @property
    def display_name(self) -> str:
        return f"{self.left_analysis.name} vs {self.right_analysis.name}"


def parse_analysis_comparison(value: str) -> AnalysisComparison:
    """
    Parse an analysis comparison such as ``cfd-cfc``.

    The analysis before the hyphen is the left analysis and the analysis after
    the hyphen is the right analysis.
    """
    normalized = value.strip().lower()
    parts = normalized.split("-")

    if len(parts) != 2:
        raise ValueError(
            f"Invalid comparison {value!r}. "
            "Expected '<left>-<right>', for example 'cfd-df'."
        )

    left_name, right_name = parts

    try:
        left_config = ANALYSIS_CONFIGS[left_name]
    except KeyError as error:
        raise ValueError(
            f"Unknown left analysis {left_name!r}. "
            f"Available analyses: {', '.join(ANALYSIS_CONFIGS)}."
        ) from error

    try:
        right_config = ANALYSIS_CONFIGS[right_name]
    except KeyError as error:
        raise ValueError(
            f"Unknown right analysis {right_name!r}. "
            f"Available analyses: {', '.join(ANALYSIS_CONFIGS)}."
        ) from error

    if left_name == right_name:
        raise ValueError(
            "An analysis cannot be compared with itself."
        )

    return AnalysisComparison(left_config, right_config)

def load_comparison_graphs(
    case_study: CaseStudy,
    comparison: AnalysisComparison,
) -> tp.Tuple[nx.DiGraph, nx.DiGraph]:
    """Load the two CIGs required for one comparison."""


    # bruh fix the revision
    left_revision = newest_processed_revision_for_case_study(
        case_study,
        comparison.left_experiment_type,
    )
    right_revision = newest_processed_revision_for_case_study(
        case_study,
        comparison.right_experiment_type,
    )

    if not left_revision or not right_revision:
        raise PlotDataEmpty()

    left_graph = create_blame_interaction_graph(
        case_study.project_name,
        left_revision,
        comparison.left_experiment_type,
    ).commit_interaction_graph()

    right_graph = create_blame_interaction_graph(
        case_study.project_name,
        right_revision,
        comparison.right_experiment_type,
    ).commit_interaction_graph()

    return left_graph, right_graph


def edge_jaccard_similarity(
    left_graph: nx.DiGraph,
    right_graph: nx.DiGraph,
) -> float:
    """Calculate edge-set Jaccard similarity."""
    left_edges = set(left_graph.edges())
    right_edges = set(right_graph.edges())

    edge_union = left_edges | right_edges

    if not edge_union:
        return 1.0

    return len(left_edges & right_edges) / len(edge_union)

def edge_weight_differences(
    left_graph: nx.DiGraph,
    right_graph: nx.DiGraph,
) -> tp.Dict[tp.Tuple[CommitRepoPair, CommitRepoPair], int]:
    """
    Calculate left edge weight minus right edge weight.

    Missing edges have weight zero.
    """
    all_edges = set(left_graph.edges()) | set(right_graph.edges())

    differences = {}

    for source, target in all_edges:
        left_weight = (
            int(left_graph[source][target]["amount"])
            if left_graph.has_edge(source, target)
            else 0
        )
        right_weight = (
            int(right_graph[source][target]["amount"])
            if right_graph.has_edge(source, target)
            else 0
        )

        differences[(source, target)] = left_weight - right_weight

    return differences

def edge_weight_difference_dataframe(
    left_graph: nx.DiGraph,
    right_graph: nx.DiGraph,
) -> pd.DataFrame:
    """Build a frequency table for edge-weight differences."""
    differences = edge_weight_differences(
        left_graph,
        right_graph,
    )
    frequencies = Counter(differences.values())

    return pd.DataFrame([
        {
            "Edge-weight difference": difference,
            "Frequency": frequency,
        }
        for difference, frequency in sorted(frequencies.items())
    ])

