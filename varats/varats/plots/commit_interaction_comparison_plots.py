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
    load_comparison_graphs,
    parse_analysis_comparison,
    shared_edge_weight_dataframe,
    shared_edge_weight_log_ratio_dataframe,
    shared_edge_weight_spearman,
    shared_node_degree_dataframe,
    shared_node_degree_spearman,
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


def _analysis_names(
        comparison: AnalysisComparison,
) -> tp.Tuple[str, str]:
    """Return concise labels for the two compared analyses."""
    return comparison.left_analysis.value, comparison.right_analysis.value


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
            label=f"{comparison.left_analysis.value} only",
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
            label=f"{comparison.right_analysis.value} only",
        )

        ax.set_xlim(0.0, 1.0)
        ax.set_xlabel("Share of edge union")
        ax.set_ylabel("Project")
        ax.set_title("Deduplicated edge overlap")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3)
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
    """Generate deduplicated edge-overlap composition plots."""

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
        median = float(ratios.median())
        first_quartile = float(ratios.quantile(0.25))
        third_quartile = float(ratios.quantile(0.75))
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
        axes.axvline(
            median,
            color=SHARED_COLOR,
            linewidth=1.5,
            label=f"Median: {median:.2f}",
        )
        axes.set_xlim(-absolute_bound, absolute_bound)
        axes.set_xlabel(
            f"log₂({left_name} weight / {right_name} weight)"
        )
        y_label = "Number of shared edges"
        if use_log_scale:
            y_label += " (log scale)"
        axes.set_ylabel(y_label)
        axes.set_title(
            f"{case_study.project_name}: shared-edge weight ratios"
        )
        axes.grid(axis="y", alpha=0.2)
        axes.text(
            0.02,
            0.97,
            f"n = {len(data):,}\n"
            f"median = {median:.2f}\n"
            f"IQR = [{first_quartile:.2f}, {third_quartile:.2f}]\n"
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
            Patch(color=LEFT_COLOR, label=f"{left_name} higher"),
            axes.lines[-1],
        ])
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


class CommitInteractionEdgeWeightLogRatioOverviewPlot(
    Plot,
    plot_name="edge-weight-log-ratio-overview",
):
    """Arrange project-level log-ratio distributions as small multiples."""

    def plot(self, view_mode: bool) -> None:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs["case_studies"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]
        left_name, right_name = _analysis_names(comparison)
        project_data: tp.List[tp.Tuple[str, pd.DataFrame]] = []

        for case_study in case_studies:
            try:
                left_graph, right_graph = load_comparison_graphs(
                    case_study,
                    comparison,
                )
            except PlotDataEmpty:
                continue
            data = shared_edge_weight_log_ratio_dataframe(
                left_graph,
                right_graph,
            )
            if not data.empty:
                project_data.append((case_study.project_name, data))

        if not project_data:
            raise PlotDataEmpty()

        num_projects = len(project_data)
        num_columns = min(4, math.ceil(math.sqrt(num_projects)))
        num_rows = math.ceil(num_projects / num_columns)
        absolute_bound = max(
            abs(float(data["Log2 weight ratio"].min()))
            for _, data in project_data
        )
        absolute_bound = max(
            absolute_bound,
            max(
                abs(float(data["Log2 weight ratio"].max()))
                for _, data in project_data
            ),
        )
        if absolute_bound == 0:
            absolute_bound = 1.0

        figure, axes_grid = plt.subplots(
            num_rows,
            num_columns,
            figsize=(3.5 * num_columns, 2.7 * num_rows),
            sharex=True,
            sharey=True,
            squeeze=False,
        )
        axes_list = list(axes_grid.flat)
        for axes, (project_name, data) in zip(axes_list, project_data):
            ratios = data["Log2 weight ratio"]
            median = float(ratios.median())
            _, _, bars = axes.hist(
                ratios,
                bins=31,
                range=(-absolute_bound, absolute_bound),
                weights=[1 / len(data)] * len(data),
                edgecolor="white",
                linewidth=0.25,
            )
            _color_log_ratio_bars(bars)
            axes.axvline(
                0,
                color="#333333",
                linestyle="--",
                linewidth=0.8,
            )
            axes.axvline(
                median,
                color=SHARED_COLOR,
                linewidth=1.2,
            )
            axes.set_title(project_name, fontsize=9)
            axes.text(
                0.03,
                0.95,
                f"n={len(data):,}\nmedian={median:.2f}",
                transform=axes.transAxes,
                verticalalignment="top",
                fontsize=7,
                bbox={
                    "boxstyle": "round",
                    "facecolor": "white",
                    "alpha": 0.75,
                    "edgecolor": "none",
                },
            )
            axes.grid(axis="y", alpha=0.15)

        for unused_axes in axes_list[num_projects:]:
            unused_axes.set_axis_off()

        figure.suptitle(
            "Shared-edge weight-ratio distributions",
            fontsize=14,
        )
        figure.supxlabel(
            f"log₂({left_name} weight / {right_name} weight)"
        )
        figure.supylabel("Share of shared edges")
        figure.legend(
            handles=[
                Patch(color=RIGHT_COLOR, label=f"{right_name} higher"),
                Patch(color="#9d9d9d", label="Approximately equal"),
                Patch(color=LEFT_COLOR, label=f"{left_name} higher"),
                axes_list[0].lines[-1],
            ],
            labels=[
                f"{right_name} higher",
                "Approximately equal",
                f"{left_name} higher",
                "Project median",
            ],
            loc="upper center",
            bbox_to_anchor=(0.5, 0.965),
            ncol=4,
            fontsize=8,
        )
        figure.tight_layout(rect=(0.03, 0.04, 1, 0.91))

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionEdgeWeightLogRatioOverviewPlotGenerator(
    PlotGenerator,
    generator_name="edge-weight-log-ratio-overview",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one paper-ready overview for selected case studies."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )
        return [
            CommitInteractionEdgeWeightLogRatioOverviewPlot(
                self.plot_config,
                case_studies=case_studies,
                comparison=comparison,
                **self.plot_kwargs,
            )
        ]


class CommitInteractionEdgeWeightRankPlot(
    Plot,
    plot_name="edge-weight-rank-comparison",
):
    """Compare raw weights and percentile ranks of shared edges."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]
        left_name, right_name = _analysis_names(comparison)
        left_graph, right_graph = load_comparison_graphs(
            case_study,
            comparison,
        )
        data = shared_edge_weight_dataframe(left_graph, right_graph)
        if data.empty:
            raise PlotDataEmpty()

        rho = shared_edge_weight_spearman(left_graph, right_graph)
        overlap = edge_overlap(left_graph, right_graph)
        figure, axes = plt.subplots(1, 2, figsize=(11, 5))

        axes[0].scatter(
            data["Left weight"],
            data["Right weight"],
            alpha=0.55,
            edgecolors="none",
            color=SHARED_COLOR,
        )
        maximum_weight = max(
            float(data["Left weight"].max()),
            float(data["Right weight"].max()),
        )
        _add_equality_line(axes[0], maximum_weight)
        axes[0].set_xlabel(f"{left_name} edge weight")
        axes[0].set_ylabel(f"{right_name} edge weight")
        axes[0].set_title("Shared-edge weights")

        axes[1].scatter(
            data["Left rank"],
            data["Right rank"],
            alpha=0.55,
            edgecolors="none",
            color=SHARED_COLOR,
        )
        _add_equality_line(axes[1], 1.0)
        axes[1].set_xlabel(f"{left_name} percentile rank")
        axes[1].set_ylabel(f"{right_name} percentile rank")
        axes[1].set_title(f"Spearman $\\rho$ = {_format_rho(rho)}")

        figure.suptitle(
            f"{case_study.project_name}: shared-edge weight agreement"
        )
        figure.text(
            0.5,
            0.01,
            f"Shared edges: {len(data)} of {overlap.union} union edges",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.04, 1, 0.94))

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionEdgeWeightRankPlotGenerator(
    PlotGenerator,
    generator_name="edge-weight-rank-comparison",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one shared-edge weight rank plot per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )
        return [
            CommitInteractionEdgeWeightRankPlot(
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
    """Compare all deduplicated edge weights with empirical CDFs."""

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
                label=f"{analysis} (n={len(weights)})",
                color=color,
            )

        axes.set_ylim(0.0, 1.0)
        axes.set_xlabel("Deduplicated edge weight")
        axes.set_ylabel("Empirical cumulative probability")
        axes.set_title(
            f"{case_study.project_name}: edge-weight distributions"
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


class CommitInteractionNodeDegreeRankPlot(
    Plot,
    plot_name="node-degree-rank-comparison",
):
    """Compare unique-neighbor degrees and ranks of shared nodes."""

    def plot(self, view_mode: bool) -> None:
        case_study: CaseStudy = self.plot_kwargs["case_study"]
        comparison: AnalysisComparison = self.plot_kwargs["comparison"]
        left_name, right_name = _analysis_names(comparison)
        left_graph, right_graph = load_comparison_graphs(
            case_study,
            comparison,
        )
        data = shared_node_degree_dataframe(left_graph, right_graph)
        if data.empty:
            raise PlotDataEmpty()

        rho = shared_node_degree_spearman(left_graph, right_graph)
        node_union = set(left_graph.nodes) | set(right_graph.nodes)
        figure, axes = plt.subplots(1, 2, figsize=(11, 5))

        axes[0].scatter(
            data["Left degree"],
            data["Right degree"],
            alpha=0.55,
            edgecolors="none",
            color="#b279a2",
        )
        maximum_degree = max(
            float(data["Left degree"].max()),
            float(data["Right degree"].max()),
        )
        _add_equality_line(axes[0], maximum_degree)
        axes[0].set_xlabel(f"{left_name} unique-neighbor degree")
        axes[0].set_ylabel(f"{right_name} unique-neighbor degree")
        axes[0].set_title("Shared-node degree")

        axes[1].scatter(
            data["Left rank"],
            data["Right rank"],
            alpha=0.55,
            edgecolors="none",
            color="#b279a2",
        )
        _add_equality_line(axes[1], 1.0)
        axes[1].set_xlabel(f"{left_name} percentile rank")
        axes[1].set_ylabel(f"{right_name} percentile rank")
        axes[1].set_title(f"Spearman $\\rho$ = {_format_rho(rho)}")

        figure.suptitle(
            f"{case_study.project_name}: node-degree agreement"
        )
        figure.text(
            0.5,
            0.01,
            f"Shared nodes: {len(data)} of {len(node_union)} union nodes; "
            "direction ignored, self-neighbors excluded",
            ha="center",
            fontsize=8,
        )
        figure.tight_layout(rect=(0, 0.04, 1, 0.94))

    def calc_missing_revisions(
            self,
            boundary_gradient: float,
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionNodeDegreeRankPlotGenerator(
    PlotGenerator,
    generator_name="node-degree-rank-comparison",
    options=[
        REQUIRE_MULTI_CASE_STUDY,
        REQUIRE_ANALYSIS_COMPARISON,
    ],
):
    """Generate one shared-node degree rank plot per case study."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")
        comparison = parse_analysis_comparison(
            self.plot_kwargs.pop("comparison")
        )
        return [
            CommitInteractionNodeDegreeRankPlot(
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
