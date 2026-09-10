"""Plots comparing commit-interaction analyses."""

import math
import typing as tp

import click
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.patches import Patch, Rectangle

from varats.data.reports.commit_interaction_comparison import (
    ALLOWED_ANALYSIS_COMPARISONS,
    AnalysisComparison,
    create_author_interaction_graph,
    edge_overlap,
    edge_weight_distribution_dataframe,
    edge_weight_difference_dataframe,
    author_centrality_dataframe,
    load_comparison_graphs,
    parse_analysis_comparison,
    shared_edge_weight_dataframe,
    shared_edge_weight_log_ratio_dataframe,
    shared_edge_weight_spearman,
    shared_node_degree_dataframe,
    shared_node_degree_spearman,
    spearman_rank_correlation,
    rank_difference_dataframe,
)
from varats.paper.case_study import CaseStudy
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash

REQUIRE_ANALYSIS_COMPARISON: CLIOptionTy = make_cli_option(
    "--comparison",
    type=click.Choice(
        sorted(ALLOWED_ANALYSIS_COMPARISONS),
        case_sensitive=False,
    ),
    required=True,
    metavar="COMPARISON",
    help=(
        "Analysis pair to compare (separated by '-'): cfd for "
        "ControlFlowDirect, cfc for ControlFlowCollective, or df for "
        "DataFlow; for example, --comparison cfd-df."
    ),
)

LEFT_COLOR = "#4c78a8"
SHARED_COLOR = "#54a24b"
RIGHT_COLOR = "#f58518"

# Paper-facing comparison plots use typography five points larger than the
# Matplotlib defaults while retaining the original figure dimensions.
plt.rcParams.update({
    "font.size": 17,
    "axes.labelsize": 20,
    "axes.titlesize": 25,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 15,
})

def _analysis_label(analysis_name: str) -> str:
    """Map an analysis name to its paper notation."""
    return {
        "CF-DIRECT": r"$\rightarrowtail_d$",
        "CF-COLLECTIVE": r"$\rightarrowtail_c$",
        "DF-PHASAR": r"$\rightsquigarrow$",
    }.get(analysis_name, analysis_name)


def _analysis_names(
        comparison: AnalysisComparison,
) -> tp.Tuple[str, str]:
    """Return paper-formatted labels for the compared analyses."""
    return (
        _analysis_label(comparison.left_analysis.value),
        _analysis_label(comparison.right_analysis.value),
    )


def _add_equality_line(axes: plt.Axes, upper_bound: float) -> None:
    """Draw an equality line and apply equal square axis bounds."""
    bound = max(upper_bound, 1.0)
    axes.plot(
        [0, bound],
        [0, bound],
        color="#666666",
        linestyle="--",
        linewidth=1,
        zorder=0,
    )
    axes.set_xlim(0, bound)
    axes.set_ylim(0, bound)
    axes.set_aspect("equal", adjustable="box")


def _format_rho(rho: float) -> str:
    """Format Spearman's rho, including its undefined state."""
    return "undefined" if math.isnan(rho) else f"{rho:.3f}"


def _color_log_ratio_bars(bars: tp.Iterable[Rectangle]) -> None:
    """Color log-ratio histogram bars by the heavier configuration."""
    for bar in bars:
        midpoint = bar.get_x() + bar.get_width() / 2
        if math.isclose(midpoint, 0.0, abs_tol=bar.get_width() / 2):
            bar.set_facecolor("#9d9d9d")
        elif midpoint < 0:
            bar.set_facecolor(RIGHT_COLOR)
        else:
            bar.set_facecolor(LEFT_COLOR)


def _shared_author_layout(
        author_graphs: tp.Iterable[nx.Graph],
) -> tp.Dict[str, tp.Any]:
    """Create a deterministic layout shared by multiple author graphs."""
    layout_graph = nx.Graph()

    for author_graph in author_graphs:
        layout_graph.add_nodes_from(author_graph.nodes)
        for source, sink, data in author_graph.edges(data=True):
            amount = int(data.get("amount", 1))
            if layout_graph.has_edge(source, sink):
                layout_graph[source][sink]["amount"] += amount
            else:
                layout_graph.add_edge(source, sink, amount=amount)

    if layout_graph.number_of_nodes() == 0:
        return {}

    return nx.spring_layout(
        layout_graph,
        seed=42,
        weight="amount",
    )


def _draw_author_graph(
        axes: plt.Axes,
        author_graph: nx.Graph,
        positions: tp.Mapping[str, tp.Any],
        title: str,
        node_color: str,
) -> None:
    """Draw one author-interaction graph on an existing set of axes."""
    node_counts = [
        max(1, int(author_graph.nodes[node].get("num_commits", 1)))
        for node in author_graph.nodes
    ]
    max_node_count = max(node_counts, default=1)
    node_sizes = [
        400 + 800 * math.log1p(count) / math.log1p(max_node_count)
        for count in node_counts
    ]

    edge_weights = [
        max(1, int(data.get("amount", 1)))
        for _, _, data in author_graph.edges(data=True)
    ]
    max_edge_weight = max(edge_weights, default=1)
    edge_widths = [
        0.5 + 3 * math.log1p(weight) / math.log1p(max_edge_weight)
        for weight in edge_weights
    ]

    nx.draw_networkx_nodes(
        author_graph,
        positions,
        ax=axes,
        node_color=node_color,
        node_size=node_sizes,
        alpha=0.85,
        linewidths=0.75,
        edgecolors="white",
    )
    nx.draw_networkx_edges(
        author_graph,
        positions,
        ax=axes,
        width=edge_widths,
        edge_color="#4a4a4a",
        alpha=0.55,
    )

    def weighted_degree(node: str) -> int:
        return sum(
            int(data.get("amount", 1))
            for _, _, data in author_graph.edges(node, data=True)
        )

    nodes_by_centrality = sorted(
        author_graph.nodes,
        key=weighted_degree,
        reverse=True,
    )
    labels = {
        node: node
        for node in nodes_by_centrality[:30]
    }
    nx.draw_networkx_labels(
        author_graph,
        positions,
        labels=labels,
        ax=axes,
        font_size=7,
    )

    if author_graph.number_of_edges() <= 20:
        edge_labels = {
            (source, sink): int(data.get("amount", 1))
            for source, sink, data in author_graph.edges(data=True)
        }
        nx.draw_networkx_edge_labels(
            author_graph,
            positions,
            edge_labels=edge_labels,
            ax=axes,
            font_size=6,
        )

    axes.set_title(title)
    axes.margins(0.15)
    axes.set_axis_off()


class CommitInteractionJaccardPlot(
    Plot,
    plot_name="jaccard-comparison-plot",
):
    """Plot common and exclusive edge shares across case studies."""

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = (
            self.plot_kwargs["case_studies"]
        )
        comparison: AnalysisComparison = (
            self.plot_kwargs["comparison"]
        )

        rows: tp.List[tp.Dict[str, tp.Any]] = []

        for case_study in case_studies:
            left_graph, right_graph = load_comparison_graphs(
                case_study,
                comparison,
            )

            overlap = edge_overlap(left_graph, right_graph)
            rows.append({
                "Project": case_study.project_name,
                "Left only": overlap.left_only_share,
                "Shared": overlap.shared_share,
                "Right only": overlap.right_only_share,
            })

        data = pd.DataFrame(rows)

        if data.empty:
            raise PlotDataEmpty()

        figure_height = max(2.5, 0.5 * len(data) + 1.5)
        fig, ax = plt.subplots(figsize=(9, figure_height))
        projects = list(data["Project"])
        left_only = list(data["Left only"])
        shared = list(data["Shared"])

        ax.barh(
            projects,
            left_only,
            color=LEFT_COLOR,
            label=f"{_analysis_label(comparison.left_analysis.value)} only",
        )
        ax.barh(
            projects,
            shared,
            left=left_only,
            color=SHARED_COLOR,
            label="Shared (Jaccard)",
        )
        ax.barh(
            projects,
            data["Right only"],
            left=[
                left_share + shared_share
                for left_share, shared_share in zip(left_only, shared)
            ],
            color=RIGHT_COLOR,
            label=f"{_analysis_label(comparison.right_analysis.value)} only",
        )

        ax.set_xlim(0.0, 1.0)
        ax.set_xlabel("Share of edge union", fontsize=25)
        ax.tick_params(axis="both", labelsize=20)
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.01),
            ncol=3,
            fontsize=17,
            handlelength=1.4,
            columnspacing=1.2,
        )
        ax.invert_yaxis()

        fig.tight_layout()

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionJaccardPlotGenerator(
    PlotGenerator,
    generator_name="jaccard-comparison-plot",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate edge-overlap composition plots."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = (
            self.plot_kwargs.pop("case_study")
        )

        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )

        return [
            CommitInteractionJaccardPlot(
                self.plot_config,
                case_studies=case_studies,
                comparison=comparison,
                **self.plot_kwargs,
            )
        ]


class CommitInteractionEdgeWeightDifferencePlot(
    Plot,
    plot_name="edge-weight-comparison",
):
    """Plot frequencies of pairwise edge-weight differences."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = (
            self.plot_kwargs["comparison"]
        )

        left_graph, right_graph = load_comparison_graphs(
            case_study,
            comparison,
        )

        data = edge_weight_difference_dataframe(
            left_graph,
            right_graph,
        )

        if data.empty:
            raise PlotDataEmpty()

        fig, ax = plt.subplots()

        ax.bar(
            data["Edge-weight difference"],
            data["Frequency"],
        )

        ax.axvline(
            0,
            linewidth=1,
            linestyle="--",
        )

        ax.set_xlabel("Edge-weight difference")
        ax.set_ylabel("Number of edges")
        ax.set_title(
            f"{case_study.project_name}: "
            f"{comparison.display_name}"
        )

        fig.tight_layout()

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionEdgeWeightDifferencePlotGenerator(
    PlotGenerator,
    generator_name="edge-weight-comparison-generator",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one edge-weight-difference plot per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = (
            self.plot_kwargs.pop("case_study")
        )

        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )

        return [
            CommitInteractionEdgeWeightDifferencePlot(
                self.plot_config,
                case_study=case_study,
                comparison=comparison,
                **self.plot_kwargs,
            )
            for case_study in case_studies
        ]


class CommitInteractionEdgeWeightLogRatioPlot(
    Plot,
    plot_name="edge-weight-log-ratio-comparison",
):
    """Plot log2 weight ratios for positive-weight shared edges."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]
        left_name, right_name = _analysis_names(comparison)
        left_graph, right_graph = load_comparison_graphs(
            case_study,
            comparison,
        )
        data = shared_edge_weight_log_ratio_dataframe(
            left_graph,
            right_graph,
        )
        if data.empty:
            raise PlotDataEmpty()

        ratios = data["Log2 weight ratio"]
        left_higher = 100 * float((ratios > 0).mean())
        right_higher = 100 * float((ratios < 0).mean())
        equal = 100 * float((ratios == 0).mean())

        absolute_bound = max(abs(float(ratios.min())),
                             abs(float(ratios.max())))
        if absolute_bound == 0:
            absolute_bound = 1.0

        figure, axes = plt.subplots(figsize=(9, 5.5))
        counts, _, bars = axes.hist(
            ratios,
            bins=41,
            range=(-absolute_bound, absolute_bound),
            edgecolor="white",
            linewidth=0.35,
        )
        _color_log_ratio_bars(bars)

        nonzero_counts = [count for count in counts if count > 0]
        use_log_scale = (
            bool(nonzero_counts)
            and max(nonzero_counts) / min(nonzero_counts) >= 100
        )
        if use_log_scale:
            axes.set_yscale("log")

        axes.axvline(
            0,
            color="#333333",
            linestyle="--",
            linewidth=1,
        )
        axes.set_xlim(-absolute_bound, absolute_bound)
        axes.set_xlabel(
            f"log₂({left_name} weight / {right_name} weight)"
        )
        y_label = "Shared edges"
        if use_log_scale:
            y_label += " (log scale)"
        axes.set_ylabel(y_label)
        axes.set_title(
            f"{case_study.project_name}"
        )
        axes.grid(axis="y", alpha=0.2)
        axes.text(
            0.02,
            0.97,
            f"{left_name} higher: {left_higher:.1f}%\n"
            f"{right_name} higher: {right_higher:.1f}%\n"
            f"equal: {equal:.1f}%",
            transform=axes.transAxes,
            verticalalignment="top",
            bbox={
                "boxstyle": "round",
                "facecolor": "white",
                "alpha": 0.85,
                "edgecolor": "#cccccc",
            },
        )
        axes.legend(handles=[
            Patch(color=RIGHT_COLOR, label=f"{right_name} higher"),
            Patch(color="#9d9d9d", label="Approximately equal"),
            Patch(color=LEFT_COLOR, label=f"{left_name} higher")
            ],
            fontsize=17,
        )
        figure.tight_layout()

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionEdgeWeightLogRatioPlotGenerator(
    PlotGenerator,
    generator_name="edge-weight-log-ratio-comparison",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one shared-edge log-ratio plot per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )
        return [
            CommitInteractionEdgeWeightLogRatioPlot(
                self.plot_config,
                case_study=case_study,
                comparison=comparison,
                **self.plot_kwargs,
            )
            for case_study in case_studies
        ]


class CommitInteractionEdgeWeightDistributionPlot(
    Plot,
    plot_name="edge-weight-distribution-comparison",
):
    """Compare all edge weights with empirical CDFs."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]
        left_name, right_name = _analysis_names(comparison)
        left_graph, right_graph = load_comparison_graphs(
            case_study,
            comparison,
        )
        data = edge_weight_distribution_dataframe(
            left_graph,
            right_graph,
            left_name,
            right_name,
        )
        if data.empty:
            raise PlotDataEmpty()

        figure, axes = plt.subplots()
        for analysis, color in (
                (left_name, LEFT_COLOR),
                (right_name, RIGHT_COLOR),
        ):
            weights = sorted(
                float(weight)
                for weight in data.loc[
                    data["Analysis"] == analysis,
                    "Weight",
                ]
            )
            if not weights:
                continue
            cumulative_probability = [
                index / len(weights)
                for index in range(1, len(weights) + 1)
            ]
            axes.step(
                weights,
                cumulative_probability,
                where="post",
                label=f"{_analysis_label(analysis)} (n={len(weights)})",
                color=color,
            )

        axes.set_ylim(0.0, 1.0)
        axes.set_xlabel("Edge weight")
        axes.set_ylabel("Cumulative probability")
        axes.set_title(
            f"{case_study.project_name}"
        )
        axes.legend()
        axes.grid(axis="y", alpha=0.25)
        figure.tight_layout()

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionEdgeWeightDistributionPlotGenerator(
    PlotGenerator,
    generator_name="edge-weight-distribution-comparison",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one edge-weight ECDF comparison per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )
        return [
            CommitInteractionEdgeWeightDistributionPlot(
                self.plot_config,
                case_study=case_study,
                comparison=comparison,
                **self.plot_kwargs,
            )
            for case_study in case_studies
        ]


class AuthorInteractionGraphComparisonPlot(
    Plot,
    plot_name="author-interaction-comparison-plot",
):
    """Plot two author-interaction graphs using a shared node layout."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]

        left_commit_graph, right_commit_graph = load_comparison_graphs(
            case_study,
            comparison,
        )
        left_author_graph = create_author_interaction_graph(
            left_commit_graph,
            case_study.project_name,
        )
        right_author_graph = create_author_interaction_graph(
            right_commit_graph,
            case_study.project_name,
        )

        positions = _shared_author_layout([
            left_author_graph,
            right_author_graph,
        ])
        if not positions:
            raise PlotDataEmpty()

        figure, axes = plt.subplots(1, 2, figsize=(14, 7))
        _draw_author_graph(
            axes[0],
            left_author_graph,
            positions,
            comparison.left_analysis.value,
            "#4c78a8",
        )
        _draw_author_graph(
            axes[1],
            right_author_graph,
            positions,
            comparison.right_analysis.value,
            "#f58518",
        )

        figure_title = self.plot_config.fig_title() or (
            f"{case_study.project_name}: Author Interaction Graphs"
        )
        figure.suptitle(figure_title)
        figure.text(
            0.5,
            0.02,
            "Node size: commits per author | "
            "Edge width: commit-interaction edges",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.04, 1, 0.95))

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class AuthorInteractionGraphComparisonPlotGenerator(
    PlotGenerator,
    generator_name="author-interaction-comparison-plot",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one author-interaction comparison per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )

        return [
            AuthorInteractionGraphComparisonPlot(
                self.plot_config,
                case_study=case_study,
                comparison=comparison,
                **self.plot_kwargs,
            )
            for case_study in case_studies
        ]


# The original comparison plots above intentionally remain available for
# backwards compatibility.  The following focused plots are the names used
# by the thesis report generation scripts; each generated figure represents
# one project, so projects can be composed into a figure in LaTeX.


class _PairPlot(Plot, plot_name=None):
    def calc_missing_revisions(
            self, boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation

    def _context(self) -> tp.Tuple[CaseStudy, AnalysisComparison, nx.DiGraph, nx.DiGraph]:
        case_study = self.plot_kwargs["case_study"]
        comparison = self.plot_kwargs["comparison"]
        left, right = load_comparison_graphs(case_study, comparison)
        return case_study, comparison, left, right


def _pair_generator(
        cls: tp.Type[Plot], generator_name: str,
) -> tp.Type[PlotGenerator]:
    """Create the standard one-plot-per-project generator class."""
    class _Generator(PlotGenerator, generator_name=generator_name, options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_ANALYSIS_COMPARISON]):
        def generate(self) -> tp.List[Plot]:
            case_studies = self.plot_kwargs.pop("case_study")
            comparison = parse_analysis_comparison(self.plot_kwargs.pop("comparison"))
            return [cls(self.plot_config, case_study=case_study, comparison=comparison, **self.plot_kwargs) for case_study in case_studies]
    _Generator.__name__ = f"{cls.__name__}Generator"
    return _Generator


class CommitInteractionEdgeRankNumericalPlot(_PairPlot, plot_name="edge-rank-agreement-numerical"):
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, left, right = self._context()
        data = shared_edge_weight_dataframe(left, right)
        if data.empty:
            raise PlotDataEmpty()
        left_name, right_name = _analysis_names(comparison)
        figure, axes = plt.subplots()
        axes.scatter(data["Left weight"], data["Right weight"], color=SHARED_COLOR, alpha=.6)
        _add_equality_line(axes, max(float(data["Left weight"].max()), float(data["Right weight"].max())))
        axes.set(xlabel=f"{left_name} edge weight", ylabel=f"{right_name} edge weight", title=f"{case_study.project_name}")
        figure.tight_layout()


CommitInteractionEdgeRankNumericalPlotGenerator = _pair_generator(CommitInteractionEdgeRankNumericalPlot, "edge-rank-agreement-numerical")


class CommitInteractionEdgeRankSpearmanPlot(_PairPlot, plot_name="edge-rank-agreement-spearman"):
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, left, right = self._context()
        data = shared_edge_weight_dataframe(left, right)
        if data.empty:
            raise PlotDataEmpty()
        rho = shared_edge_weight_spearman(left, right)
        left_name, right_name = _analysis_names(comparison)
        figure, axes = plt.subplots()
        axes.scatter(data["Left rank"], data["Right rank"], color=SHARED_COLOR, alpha=.6)
        _add_equality_line(axes, 1.0)
        axes.set(xlabel=f"{left_name} edge rank", ylabel=f"{right_name} edge rank", title=f"{case_study.project_name} ($\\rho$ = {_format_rho(rho)})")
        figure.tight_layout()


CommitInteractionEdgeRankSpearmanPlotGenerator = _pair_generator(CommitInteractionEdgeRankSpearmanPlot, "edge-rank-agreement-spearman")


class CommitInteractionNodeDegreeNumericalPlot(_PairPlot, plot_name="node-degree-comparison-numerical"):
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, left, right = self._context(); data = shared_node_degree_dataframe(left, right)
        if data.empty: raise PlotDataEmpty()
        figure, axes = plt.subplots(); axes.scatter(data["Left degree"], data["Right degree"], color="#b279a2", alpha=.6)
        _add_equality_line(axes, max(float(data["Left degree"].max()), float(data["Right degree"].max())))
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} unique-neighbor degree", ylabel=f"{right_name} unique-neighbor degree", title=f"{case_study.project_name}")
        figure.tight_layout()


CommitInteractionNodeDegreeNumericalPlotGenerator = _pair_generator(CommitInteractionNodeDegreeNumericalPlot, "node-degree-comparison-numerical")


class CommitInteractionNodeDegreeRankOnlyPlot(_PairPlot, plot_name="node-degree-comparison-rank"):
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, left, right = self._context()
        data = shared_node_degree_dataframe(left, right)
        if data.empty: raise PlotDataEmpty()
        rho = shared_node_degree_spearman(left, right); figure, axes = plt.subplots()
        axes.scatter(data["Left rank"], data["Right rank"], color="#b279a2", alpha=.6)
        _add_equality_line(axes, 1.0)
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} node rank", ylabel=f"{right_name} node rank", title=f"{case_study.project_name} ($\\rho$ = {_format_rho(rho)})")
        figure.tight_layout()


CommitInteractionNodeDegreeRankOnlyPlotGenerator = _pair_generator(CommitInteractionNodeDegreeRankOnlyPlot, "node-degree-comparison-rank")


def _author_pair_data(
        case_study: CaseStudy,
        comparison: AnalysisComparison,
        metric: str,
) -> tp.Tuple[pd.DataFrame, nx.Graph, nx.Graph]:
    left_commit, right_commit = load_comparison_graphs(case_study, comparison)
    left_author = create_author_interaction_graph(left_commit, case_study.project_name)
    right_author = create_author_interaction_graph(right_commit, case_study.project_name)
    return author_centrality_dataframe(left_author, right_author, metric), left_author, right_author


# RQ3 plots
class _AuthorPairPlot(_PairPlot, plot_name=None):
    metric = "degree"

    def _author_data(self):
        case_study, comparison, _, _ = self._context()
        data, left, right = _author_pair_data(case_study, comparison, self.metric)
        return case_study, comparison, data, left, right


class AuthorDegreeScatterPlot(_AuthorPairPlot, plot_name="scatter-plot-author-degree"):
    metric = "degree"
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, data, _, _ = self._author_data()
        if data.empty: raise PlotDataEmpty()
        figure, axes = plt.subplots(); axes.scatter(data["Left centrality"], data["Right centrality"], color=LEFT_COLOR, alpha=.65)
        _add_equality_line(axes, max(float(data["Left centrality"].max()), float(data["Right centrality"].max())))
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} weighted author degree", ylabel=f"{right_name} weighted author degree", title=f"{case_study.project_name}")
        figure.tight_layout()


AuthorDegreeScatterPlotGenerator = _pair_generator(AuthorDegreeScatterPlot, "scatter-plot-author-degree")


class AuthorEigenvectorScatterPlot(_AuthorPairPlot, plot_name="scatter-plot-author-eigenvector"):
    metric = "eigenvector"
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, data, _, _ = self._author_data()
        if data.empty: raise PlotDataEmpty()
        figure, axes = plt.subplots(); axes.scatter(data["Left centrality"], data["Right centrality"], color=RIGHT_COLOR, alpha=.65)
        _add_equality_line(axes, max(float(data["Left centrality"].max()), float(data["Right centrality"].max())))
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} eigenvector centrality", ylabel=f"{right_name} eigenvector centrality", title=f"{case_study.project_name}")
        figure.tight_layout()


AuthorEigenvectorScatterPlotGenerator = _pair_generator(AuthorEigenvectorScatterPlot, "scatter-plot-author-eigenvector")


class AuthorDegreeRankPlot(_AuthorPairPlot, plot_name="spearman-plot-author-degree-rank"):
    metric = "degree"
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, data, _, _ = self._author_data()
        if data.empty: raise PlotDataEmpty()
        rho = spearman_rank_correlation(data["Left centrality"], data["Right centrality"])
        figure, axes = plt.subplots(); axes.scatter(data["Left rank"], data["Right rank"], color=LEFT_COLOR, alpha=.65); _add_equality_line(axes, max(float(data["Left rank"].max()), float(data["Right rank"].max()), 1.0))
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} author degree rank", ylabel=f"{right_name} author degree rank", title=f"{case_study.project_name} ($\\rho$ = {_format_rho(rho)})"); figure.tight_layout()


AuthorDegreeRankPlotGenerator = _pair_generator(AuthorDegreeRankPlot, "spearman-plot-author-degree-rank")


class AuthorEigenvectorRankPlot(_AuthorPairPlot, plot_name="spearman-plot-author-eigen-rank"):
    metric = "eigenvector"
    def plot(self, view_mode: bool) -> None:
        case_study, comparison, data, _, _ = self._author_data()
        if data.empty: raise PlotDataEmpty()
        rho = spearman_rank_correlation(data["Left centrality"], data["Right centrality"])
        figure, axes = plt.subplots(); axes.scatter(data["Left rank"], data["Right rank"], color=RIGHT_COLOR, alpha=.65); _add_equality_line(axes, max(float(data["Left rank"].max()), float(data["Right rank"].max()), 1.0))
        left_name, right_name = _analysis_names(comparison)
        axes.set(xlabel=f"{left_name} eigenvector rank", ylabel=f"{right_name} eigenvector rank", title=f"{case_study.project_name} ($\\rho$ = {_format_rho(rho)})"); figure.tight_layout()


AuthorEigenvectorRankPlotGenerator = _pair_generator(AuthorEigenvectorRankPlot, "spearman-plot-author-eigen-rank")


class _RankDifferencePlot(_PairPlot, plot_name=None):
    metric = "node"

    def _rank_difference(self) -> tp.Tuple[CaseStudy, AnalysisComparison, pd.DataFrame]:
        case_study, comparison, left_commit, right_commit = self._context()
        if self.metric == "node":
            left_values = __import__("varats.data.reports.commit_interaction_comparison", fromlist=["unique_neighbor_degrees"]).unique_neighbor_degrees(left_commit)
            right_values = __import__("varats.data.reports.commit_interaction_comparison", fromlist=["unique_neighbor_degrees"]).unique_neighbor_degrees(right_commit)
        else:
            left_author = create_author_interaction_graph(left_commit, case_study.project_name)
            right_author = create_author_interaction_graph(right_commit, case_study.project_name)
            data = author_centrality_dataframe(left_author, right_author, self.metric)
            left_values = data.set_index("Author")["Left centrality"].to_dict()
            right_values = data.set_index("Author")["Right centrality"].to_dict()
        return case_study, comparison, rank_difference_dataframe(left_values, right_values, 10)

    def plot(self, view_mode: bool) -> None:
        case_study, comparison, data = self._rank_difference()
        if data.empty: raise PlotDataEmpty()
        labels = [_display for _display in map(str, data["Item"])]
        figure, axes = plt.subplots(figsize=(9, max(4, .35 * len(labels))))
        y = list(range(len(labels))); axes.barh(y, data["Right rank"] - data["Left rank"], color=SHARED_COLOR); axes.axvline(0, color="#555", linewidth=.8)
        axes.set_yticks(y, labels); axes.invert_yaxis(); axes.set(xlabel="Right rank − left rank", title=f"{case_study.project_name}"); figure.tight_layout()


class NodeTop10RankDifferencePlot(_RankDifferencePlot, plot_name="node-rank-difference"):
    metric = "node"


NodeTop10RankDifferencePlotGenerator = _pair_generator(NodeTop10RankDifferencePlot, "node-rank-difference")


class AuthorDegreeRankDifferencePlot(_RankDifferencePlot, plot_name="author-degree-rank-difference"):
    metric = "degree"


AuthorDegreeRankDifferencePlotGenerator = _pair_generator(AuthorDegreeRankDifferencePlot, "author-degree-rank-difference")


class AuthorEigenvectorRankDifferencePlot(_RankDifferencePlot, plot_name="author-eigenvector-rank-difference"):
    metric = "eigenvector"


AuthorEigenvectorRankDifferencePlotGenerator = _pair_generator(AuthorEigenvectorRankDifferencePlot, "author-eigenvector-rank-difference")
