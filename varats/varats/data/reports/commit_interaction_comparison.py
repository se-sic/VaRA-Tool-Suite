"""Metrics for comparing commit-interaction graphs."""

import math
import typing as tp
from collections import Counter

import networkx as nx
import numpy as np
import pandas as pd

from varats.data.reports.blame_report import AnalysisType
from varats.data.reports.blame_interaction_graph import (
    AIGEdgeAttrs,
    AIGNodeAttrs,
    create_blame_interaction_graph,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperimentRegion,
)
from varats.experiments.vara.cfg_report_experiment import (
    CFCollectiveReportExperiment,
    CFDirectReportExperiment,
)
from varats.experiment.experiment_util import VersionExperiment
from varats.mapping.commit_map import get_commit_map
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import (
    processed_revisions_for_case_study,
)
from varats.plot.plot import PlotDataEmpty
from varats.project.project_util import create_project_commit_lookup_helper
from varats.utils.git_util import (
    CommitRepoPair,
    FullCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)


class AnalysisConfig:
    """Configuration needed to locate one analysis report."""

    analysis_type: AnalysisType
    experiment_type: tp.Type[VersionExperiment]

    def __init__(self, analysis_type: AnalysisType) -> None:
        self.analysis_type = analysis_type
        self.experiment_type = {
            AnalysisType.DF_ANALYSIS: BlameReportExperimentRegion,
            AnalysisType.CF_DIRECT_ANALYSIS: CFDirectReportExperiment,
            AnalysisType.CF_COLLECTIVE_ANALYSIS: CFCollectiveReportExperiment,
        }[analysis_type]


ANALYSIS_CONFIGS: tp.Dict[str, AnalysisConfig] = {
    "df": AnalysisConfig(analysis_type=AnalysisType.DF_ANALYSIS),
    "cfd": AnalysisConfig(analysis_type=AnalysisType.CF_DIRECT_ANALYSIS),
    "cfc": AnalysisConfig(analysis_type=AnalysisType.CF_COLLECTIVE_ANALYSIS),
}

ALLOWED_ANALYSIS_COMPARISONS = {
    "cfd-cfc",
    "cfd-df",
    "cfc-df",
    "cfc-cfd",
    "df-cfd",
    "df-cfc",
}


class AnalysisComparison:
    """Supported pairwise analysis comparisons."""

    left: AnalysisConfig
    right: AnalysisConfig

    def __init__(self, left: AnalysisConfig, right: AnalysisConfig) -> None:
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
        raise ValueError("An analysis cannot be compared with itself.")

    return AnalysisComparison(left_config, right_config)


def load_comparison_graphs(
        case_study: CaseStudy,
        comparison: AnalysisComparison,
) -> tp.Tuple[nx.DiGraph, nx.DiGraph]:
    """Load both CIGs at their newest commonly processed revision."""
    left_revisions = processed_revisions_for_case_study(
        case_study,
        comparison.left_experiment_type,
    )
    right_revisions = set(processed_revisions_for_case_study(
        case_study,
        comparison.right_experiment_type,
    ))
    common_revisions = [
        revision for revision in left_revisions
        if revision in right_revisions
    ]

    if not common_revisions:
        raise PlotDataEmpty()

    commit_map = get_commit_map(case_study.project_name)
    revision = max(common_revisions, key=commit_map.time_id)

    left_graph = create_blame_interaction_graph(
        case_study.project_name,
        revision,
        comparison.left_experiment_type,
    ).commit_interaction_graph()

    right_graph = create_blame_interaction_graph(
        case_study.project_name,
        revision,
        comparison.right_experiment_type,
    ).commit_interaction_graph()

    return left_graph, right_graph


def load_analysis_graph(
        case_study: CaseStudy,
        analysis: str,
        revision: tp.Optional[FullCommitHash] = None,
) -> nx.DiGraph:
    """Load one analysis graph, optionally at an explicitly selected revision."""
    try:
        config = ANALYSIS_CONFIGS[analysis.lower()]
    except KeyError as error:
        raise ValueError(f"Unknown analysis {analysis!r}.") from error

    revisions = processed_revisions_for_case_study(
        case_study, config.experiment_type
    )
    if revision is None:
        if not revisions:
            raise PlotDataEmpty()
        commit_map = get_commit_map(case_study.project_name)
        revision = max(revisions, key=commit_map.time_id)
    elif revision not in revisions:
        raise PlotDataEmpty()

    return create_blame_interaction_graph(
        case_study.project_name,
        revision,
        config.experiment_type,
    ).commit_interaction_graph()


def load_all_analysis_graphs(
        case_study: CaseStudy,
) -> tp.Dict[str, nx.DiGraph]:
    """Load DF, CFD, and CFC graphs at their newest common revision."""
    revision_sets = {
        name: set(processed_revisions_for_case_study(
            case_study, config.experiment_type
        ))
        for name, config in ANALYSIS_CONFIGS.items()
    }
    common_revisions = set.intersection(*revision_sets.values())
    if not common_revisions:
        raise PlotDataEmpty()
    commit_map = get_commit_map(case_study.project_name)
    revision = max(common_revisions, key=commit_map.time_id)
    return {
        name: load_analysis_graph(case_study, name, revision)
        for name in ANALYSIS_CONFIGS
    }


class GraphSummary:
    """Graph-level summary based on deduplicated directed edges."""

    nodes: int
    edges: int
    density: float
    gini: float

    def __init__(
            self,
            nodes: int,
            edges: int,
            density: float,
            gini: float,
    ) -> None:
        self.nodes = nodes
        self.edges = edges
        self.density = density
        self.gini = gini

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GraphSummary):
            return NotImplemented

        return (
            self.nodes == other.nodes and
            self.edges == other.edges and
            self.density == other.density and
            self.gini == other.gini
        )

    def __repr__(self) -> str:
        return (
            f"GraphSummary(nodes={self.nodes!r}, edges={self.edges!r}, "
            f"density={self.density!r}, gini={self.gini!r})"
        )

    @property
    def gini_coef(self) -> float:
        """Backward-compatible name for the graph's Gini coefficient."""
        return self.gini


class EdgeOverlap:
    """Counts and union-relative shares of two edge sets."""

    shared: int
    left_only: int
    right_only: int
    union: int

    def __init__(
            self,
            shared: int,
            left_only: int,
            right_only: int,
            union: int,
    ) -> None:
        self.shared = shared
        self.left_only = left_only
        self.right_only = right_only
        self.union = union

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EdgeOverlap):
            return NotImplemented

        return (
            self.shared == other.shared and
            self.left_only == other.left_only and
            self.right_only == other.right_only and
            self.union == other.union
        )

    def __repr__(self) -> str:
        return (
            f"EdgeOverlap(shared={self.shared!r}, "
            f"left_only={self.left_only!r}, "
            f"right_only={self.right_only!r}, union={self.union!r})"
        )

    @property
    def jaccard(self) -> float:
        """Return the intersection-over-union similarity."""
        return self.shared / self.union if self.union else 1.0

    @property
    def shared_share(self) -> float:
        """Return the union share occupied by common edges."""
        return self.jaccard

    @property
    def left_only_share(self) -> float:
        """Return the union share occupied only by the left graph."""
        return self.left_only / self.union if self.union else 0.0

    @property
    def right_only_share(self) -> float:
        """Return the union share occupied only by the right graph."""
        return self.right_only / self.union if self.union else 0.0


def deduplicated_edges(
        graph: nx.Graph,
) -> tp.Set[tp.Tuple[tp.Hashable, tp.Hashable]]:
    """Return unique valid edges, retaining direction where applicable.

    Self-loops are excluded because a commit interacting with itself is not a
    valid commit interaction. This also protects comparisons that receive a
    graph constructed outside the normal report-loading path.
    """
    return {
        (source, target)
        for source, target in graph.edges()
        if source != target
    }


def unique_neighbor_degrees(
        graph: nx.Graph,
) -> tp.Dict[tp.Hashable, int]:
    """Calculate unique-neighbor count for each node."""
    degrees: tp.Dict[tp.Hashable, int] = {}
    directed = graph.is_directed()

    for node in graph.nodes:
        if directed:
            directed_graph = tp.cast(nx.DiGraph, graph)
            neighbors = set(directed_graph.predecessors(node))
            neighbors.update(directed_graph.successors(node))
        else:
            neighbors = set(graph.neighbors(node))
        neighbors.discard(node)
        degrees[node] = len(neighbors)

    return degrees


def gini_coefficient(values: tp.Iterable[float]) -> float:
    """Calculate the Gini coefficient for a graph"""
    sorted_values = sorted(float(value) for value in values)
    if any(value < 0 for value in sorted_values):
        raise ValueError("Gini coefficient requires non-negative values.")

    value_sum = sum(sorted_values)
    num_values = len(sorted_values)
    if num_values == 0 or value_sum == 0:
        return 0.0

    weighted_sum = sum(
        (2 * index - num_values - 1) * value
        for index, value in enumerate(sorted_values, start=1)
    )
    return weighted_sum / (num_values * value_sum)


def graph_summary(graph: nx.Graph) -> GraphSummary:
    """Summarize size, density, and unique-neighbor degree inequality."""
    num_nodes = graph.number_of_nodes()
    edges = deduplicated_edges(graph)
    non_loop_edges = {
        (source, target) for source, target in edges if source != target
    }

    if num_nodes < 2:
        density = 0.0
    elif graph.is_directed():
        density = len(non_loop_edges) / (num_nodes * (num_nodes - 1))
    else:
        density = 2 * len(non_loop_edges) / (
                num_nodes * (num_nodes - 1)
        )

    return GraphSummary(
        nodes=num_nodes,
        edges=len(edges),
        density=density,
        gini=gini_coefficient(unique_neighbor_degrees(graph).values()),
    )


def edge_overlap(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> EdgeOverlap:
    """Calculate common and exclusive deduplicated edge counts."""
    left_edges = deduplicated_edges(left_graph)
    right_edges = deduplicated_edges(right_graph)
    return EdgeOverlap(
        shared=len(left_edges & right_edges),
        left_only=len(left_edges - right_edges),
        right_only=len(right_edges - left_edges),
        union=len(left_edges | right_edges),
    )


def edge_jaccard_similarity(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> float:
    """Calculate edge-set Jaccard similarity."""
    return edge_overlap(left_graph, right_graph).jaccard


def _edge_weight(
        graph: nx.Graph,
        edge: tp.Tuple[tp.Hashable, tp.Hashable],
) -> float:
    """Read an edge's interaction amount, defaulting to one."""
    source, target = edge
    return float(graph[source][target].get("amount", 1))


def shared_edge_weight_dataframe(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> pd.DataFrame:
    """Build matched weights and percentile ranks for common edges."""
    shared_edges = deduplicated_edges(left_graph) & deduplicated_edges(
        right_graph
    )
    rows = [
        {
            "Edge": edge,
            "Left weight": _edge_weight(left_graph, edge),
            "Right weight": _edge_weight(right_graph, edge),
        }
        for edge in sorted(shared_edges, key=repr)
    ]
    data = pd.DataFrame(
        rows,
        columns=["Edge", "Left weight", "Right weight"],
    )
    if data.empty:
        data["Left rank"] = pd.Series(dtype=float)
        data["Right rank"] = pd.Series(dtype=float)
        return data

    data["Left rank"] = data["Left weight"].rank(method="average", pct=True)
    data["Right rank"] = data["Right weight"].rank(
        method="average",
        pct=True,
    )
    return data


# A better visual representation for the edge weight number comparison
def shared_edge_weight_log_ratio_dataframe(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> pd.DataFrame:
    """Calculate log2 weight ratios for shared positive-weight edges."""
    data = shared_edge_weight_dataframe(left_graph, right_graph)
    positive_weights = data.loc[
        (data["Left weight"] > 0) & (data["Right weight"] > 0)
    ].copy()
    positive_weights["Log2 weight ratio"] = [
        math.log2(left_weight / right_weight)
        for left_weight, right_weight in zip(
            positive_weights["Left weight"],
            positive_weights["Right weight"],
        )
    ]
    return positive_weights


def spearman_rank_correlation(
        left_values: tp.Iterable[float],
        right_values: tp.Iterable[float],
) -> float:
    """Calculate Spearman's rank correlation coefficient."""
    data = pd.DataFrame({
        "left": list(left_values),
        "right": list(right_values),
    })
    if (len(data) < 2 or data["left"].nunique() < 2 or data["right"].nunique() < 2):
        return float("nan")

    left_ranks = data["left"].rank(method="average")
    right_ranks = data["right"].rank(method="average")
    return float(left_ranks.corr(right_ranks))


def shared_edge_weight_spearman(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> float:
    """Calculate weight-rank agreement for edges present in both graphs."""
    data = shared_edge_weight_dataframe(left_graph, right_graph)
    return spearman_rank_correlation(
        data["Left weight"],
        data["Right weight"],
    )


def edge_weight_distribution_dataframe(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
        left_name: str = "Left",
        right_name: str = "Right",
) -> pd.DataFrame:
    """Collect all deduplicated edge weights for distribution comparison."""
    rows = [
        {
            "Analysis": analysis,
            "Weight": _edge_weight(graph, edge),
        }
        for analysis, graph in (
            (left_name, left_graph),
            (right_name, right_graph),
        )
        for edge in deduplicated_edges(graph)
    ]
    return pd.DataFrame(rows, columns=["Analysis", "Weight"])


def shared_node_degree_dataframe(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> pd.DataFrame:
    """Build unique-neighbor degrees and ranks for common nodes."""
    left_degrees = unique_neighbor_degrees(left_graph)
    right_degrees = unique_neighbor_degrees(right_graph)
    shared_nodes = set(left_degrees) & set(right_degrees)
    rows = [
        {
            "Node": node,
            "Left degree": left_degrees[node],
            "Right degree": right_degrees[node],
        }
        for node in sorted(shared_nodes, key=repr)
    ]
    data = pd.DataFrame(
        rows,
        columns=["Node", "Left degree", "Right degree"],
    )
    if data.empty:
        data["Left rank"] = pd.Series(dtype=float)
        data["Right rank"] = pd.Series(dtype=float)
        return data

    data["Left rank"] = data["Left degree"].rank(method="average", pct=True)
    data["Right rank"] = data["Right degree"].rank(
        method="average",
        pct=True,
    )
    return data


def shared_node_degree_spearman(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
) -> float:
    """Calculate degree-rank agreement for nodes present in both graphs."""
    data = shared_node_degree_dataframe(left_graph, right_graph)
    return spearman_rank_correlation(
        data["Left degree"],
        data["Right degree"],
    )


def author_centrality_dataframe(
        left_graph: nx.Graph,
        right_graph: nx.Graph,
        metric: str = "degree",
) -> pd.DataFrame:
    """Build matched weighted author-centrality values and ranks."""
    if metric == "degree":
        left_values = dict(left_graph.degree(weight="amount"))
        right_values = dict(right_graph.degree(weight="amount"))
    elif metric == "eigenvector":
        def eigenvalues(graph: nx.Graph) -> tp.Dict[tp.Hashable, float]:
            if graph.number_of_nodes() == 0:
                return {}
            try:
                # scipy's sparse eigensolver cannot handle k >= N - 1,
                # which occurs for the one- and two-author graphs that are
                # common after filtering a project. The iterative solver is
                # stable for these small graphs.
                if graph.number_of_nodes() <= 2:
                    return {
                        node: float(value)
                        for node, value in nx.eigenvector_centrality(
                            graph, max_iter=1000, weight="amount"
                        ).items()
                    }
                return tp.cast(
                    tp.Dict[tp.Hashable, float],
                    nx.eigenvector_centrality_numpy(graph, weight="amount"),
                )
            except (nx.NetworkXException, np.linalg.LinAlgError, TypeError):
                # Small or disconnected graphs can make the numpy solver fail.
                try:
                    return {
                        node: float(value)
                        for node, value in nx.eigenvector_centrality(
                            graph, max_iter=1000, weight="amount"
                        ).items()
                    }
                except nx.NetworkXException:
                    return {node: 0.0 for node in graph.nodes}
        left_values = eigenvalues(left_graph)
        right_values = eigenvalues(right_graph)
    else:
        raise ValueError(f"Unknown author centrality metric {metric!r}.")

    shared = set(left_values) & set(right_values)
    rows = [{
        "Author": author,
        "Left centrality": float(left_values[author]),
        "Right centrality": float(right_values[author]),
    } for author in sorted(shared, key=repr)]
    data = pd.DataFrame(rows, columns=[
        "Author", "Left centrality", "Right centrality"
    ])
    if data.empty:
        data["Left rank"] = pd.Series(dtype=float)
        data["Right rank"] = pd.Series(dtype=float)
        return data
    data["Left rank"] = data["Left centrality"].rank(
        method="average", ascending=False
    )
    data["Right rank"] = data["Right centrality"].rank(
        method="average", ascending=False
    )
    return data


def author_centrality_spearman(
        left_commit_graph: nx.DiGraph,
        right_commit_graph: nx.DiGraph,
        project_name: str,
        metric: str = "degree",
) -> float:
    """Compare author centrality ranks for two commit-interaction graphs."""
    left_authors = create_author_interaction_graph(
        left_commit_graph, project_name
    )
    right_authors = create_author_interaction_graph(
        right_commit_graph, project_name
    )
    data = author_centrality_dataframe(left_authors, right_authors, metric)
    return spearman_rank_correlation(
        data["Left centrality"], data["Right centrality"]
    )


def top_ranked_items(
        values: tp.Mapping[tp.Hashable, float],
        limit: int = 10,
) -> tp.List[tp.Tuple[tp.Hashable, int]]:
    """Return top-k ranked items."""
    ordered = sorted(values.items(), key=lambda item: (-float(item[1]), repr(item[0])))
    return [(item, index) for index, (item, _) in enumerate(ordered[:limit], 1)]


def rank_difference_dataframe(
        left_values: tp.Mapping[tp.Hashable, float],
        right_values: tp.Mapping[tp.Hashable, float],
        limit: int = 10,
) -> pd.DataFrame:
    """Return ranks for the union of both analyses' top-*limit* items."""
    left_top = dict(top_ranked_items(left_values, limit))
    right_top = dict(top_ranked_items(right_values, limit))
    items = sorted(set(left_top) | set(right_top), key=repr)
    missing_rank = limit + 1
    return pd.DataFrame([
        {
            "Item": item,
            "Left rank": left_top.get(item, missing_rank),
            "Right rank": right_top.get(item, missing_rank),
            "Rank difference": left_top.get(item, missing_rank)
            - right_top.get(item, missing_rank),
        }
        for item in items
    ], columns=["Item", "Left rank", "Right rank", "Rank difference"])


def edge_weight_differences(
        left_graph: nx.DiGraph,
        right_graph: nx.DiGraph,
) -> tp.Dict[tp.Tuple[CommitRepoPair, CommitRepoPair], int]:
    """
    Calculate left edge weight minus right edge weight.

    Missing edges have weight zero.
    """
    all_edges = deduplicated_edges(left_graph) | deduplicated_edges(right_graph)

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


# RQ3
def create_author_interaction_graph(
        commit_interaction_graph: nx.DiGraph,
        project_name: str,
) -> nx.Graph:
    """Create the thesis-specific author-interaction graph from a CIG.

    The resulting graph is undirected and contains one node for every author
    present in the commit-interaction graph. Interactions between commits by
    the same author are discarded. An author-edge's ``amount`` is the number
    of commit-interaction edges connecting the two authors; the instruction-
    level ``amount`` stored on a CIG edge is deliberately not propagated.

    Args:
        commit_interaction_graph: directed commit-interaction graph to convert
        project_name: project used to resolve commit authors from git metadata

    Returns:
        the undirected author-interaction graph
    """
    commit_lookup = create_project_commit_lookup_helper(project_name)

    def author_of(commit_node: CommitRepoPair) -> str:
        if commit_node.commit_hash == UNCOMMITTED_COMMIT_HASH:
            return "Unknown"
        return str(commit_lookup(commit_node).author.name)

    author_graph = nx.Graph()
    author_commits: tp.Dict[str, tp.List[CommitRepoPair]] = {}
    commit_authors: tp.Dict[CommitRepoPair, str] = {}

    for commit in commit_interaction_graph.nodes:
        author = author_of(commit)
        commit_authors[commit] = author
        author_commits.setdefault(author, []).append(commit)

    for author, commits in author_commits.items():
        node_attrs: AIGNodeAttrs = {
            "author": author,
            "num_commits": len(commits),
            "commits": commits,
        }
        author_graph.add_node(author, **node_attrs)

    for source, sink in commit_interaction_graph.edges:
        source_author = commit_authors[source]
        sink_author = commit_authors[sink]

        if source_author == sink_author:
            continue

        interaction = (source, sink)
        if author_graph.has_edge(source_author, sink_author):
            edge_attrs = tp.cast(
                AIGEdgeAttrs, author_graph[source_author][sink_author]
            )
            edge_attrs["amount"] += 1
            edge_attrs["interactions"].append(interaction)
        else:
            edge_attrs = {
                "amount": 1,
                "interactions": [interaction],
            }
            author_graph.add_edge(
                source_author,
                sink_author,
                **edge_attrs,
            )

    return author_graph
