"""Plots comparing commit-interaction analyses."""

import typing as tp

import click
import matplotlib.pyplot as plt
import pandas as pd

from varats.data.reports.commit_interaction_comparison import (
    ALLOWED_ANALYSIS_COMPARISONS,
    AnalysisComparison,
    edge_jaccard_similarity,
    edge_weight_difference_dataframe,
    load_comparison_graphs,
    parse_analysis_comparison
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
        [comparison for comparison in ALLOWED_ANALYSIS_COMPARISONS],
        case_sensitive=False,
    ),
    required=True,
    metavar="COMPARISON",
    help=(
        "Analysis pair to compare (seperated by -): \n"
        "cfd: ControlFlowDirect\n, cfc: ControlFlowCollective\n, or df: DataFlow.\n"
        "e.g, --comparison cfd-df"
    ),
)

class CommitInteractionJaccardPlot(
    Plot,
    plot_name="jaccard-comparison-plot",
):
    """Plot edge-set Jaccard similarities across case studies."""

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

            rows.append({
                "Project": case_study.project_name,
                "Jaccard similarity": edge_jaccard_similarity(
                    left_graph,
                    right_graph,
                ),
            })

        data = pd.DataFrame(rows)

        if data.empty:
            raise PlotDataEmpty()

        fig, ax = plt.subplots()

        ax.bar(
            data["Project"],
            data["Jaccard similarity"],
        )

        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Project")
        ax.set_ylabel("Jaccard similarity")
        ax.set_title(comparison.display_name)
        ax.tick_params(axis="x", labelrotation=45)

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
    """Generate commit-interaction Jaccard plots."""

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
        print(f"{case_study.project_name}: {comparison.display_name}")
        print(f"c")

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