"""Module for BlameInteractionGraph plots."""

import typing as tp
from math import ceil, floor

import networkx as nx
import pandas as pd
import seaborn as sns
from matplotlib.ticker import Locator, FixedLocator, StrMethodFormatter

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    create_file_based_interaction_graph,
    AIGNodeAttrs,
    create_callgraph_based_interaction_graph,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment,
)
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_loaded_paper_config
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.ts_utils.click_param_types import REQUIRE_MULTI_CASE_STUDY
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import FullCommitHash


class CommitAuthorInteractionGraphViolinPlot(Plot, plot_name='caig_box'):
    """Box plot of commit-author interaction commit node degrees."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            added_project_name = False
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReportExperiment
            )
            if not revision:
                continue

            caig = create_blame_interaction_graph(
                project_name, revision, BlameReportExperiment
            ).commit_author_interaction_graph(
                outgoing_interactions=True, incoming_interactions=True
            )

            authors = len([
                1 for node in caig.nodes if caig.nodes[node]["author"]
            ])

            for node in caig.nodes:
                node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
                commit = node_attrs["commit"]

                if commit:
                    if not added_project_name:
                        project_names.append(project_name)
                        added_project_name = True
                    nodes.append(({
                        "Project": project_name,
                        "commit": commit.commit_hash,
                        "# Interacting Authors": caig.degree(node) / authors
                    }))

        data = pd.DataFrame(nodes).sort_values(by=["Project"])
        ax = sns.violinplot(
            x="Project",
            y="# Interacting Authors",
            data=data,
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="Project",
            y="# Interacting Authors",
            hue="Project",
            data=data,
            palette=sns.color_palette("husl", len(project_names)),
            alpha=.25,
            size=3
        )
        ax.set_ylim(-0.1, 1.1)
        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_xlabel(None)
        ax.yaxis.label.set_size(9)
        ax.get_legend().remove()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CAIGViolinPlotGenerator(
    PlotGenerator, generator_name="caig-box", options=[]
):
    """Generates a violin plot showing the distribution of interacting authors
    for each case study."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitAuthorInteractionGraphViolinPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


def _get_graph(
    graph_type: str, project_name: str, revision: FullCommitHash
) -> nx.DiGraph:
    return {
        "blame":
            create_blame_interaction_graph(
                project_name, revision, BlameReportExperiment
            ).author_interaction_graph(),
        "callgraph":
            create_callgraph_based_interaction_graph(
                project_name, revision, BlameReportExperiment
            ).author_interaction_graph(),
        "file":
            create_file_based_interaction_graph(project_name, revision
                                               ).author_interaction_graph()
    }[graph_type]


def _create_tick_locator(
    max_val: int, min_val: int, threshold: float = 0.15
) -> Locator:
    ticks = {min_val, max_val}
    val_range = max_val - min_val

    if val_range == 0:
        return FixedLocator([0])

    max_frac = max_val / val_range
    min_frac = abs(min_val) / val_range
    if min_frac > threshold and max_frac > threshold:
        ticks.add(0)
    return FixedLocator(list(ticks))


class AuthorGraphDiffPlot(Plot, plot_name='aig_diff_authors_box'):
    """Plot showing the difference between two author interaction graphs."""

    def __init__(
        self, baseline_graph: str, compared_graph: str, plot_config: PlotConfig,
        **kwargs: tp.Any
    ):
        super().__init__(plot_config, **kwargs)
        self.__baseline_graph = baseline_graph
        self.__compared_graph = compared_graph

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["case_study"]

        revision = newest_processed_revision_for_case_study(
            case_study, BlameReportExperiment
        )
        if not revision:
            raise PlotDataEmpty()

        baseline_aig = _get_graph(
            self.__baseline_graph, case_study.project_name, revision
        )
        compared_aig = _get_graph(
            self.__compared_graph, case_study.project_name, revision
        )

        node_data: tp.List[tp.Dict[str, tp.Any]] = []
        for node in baseline_aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, baseline_aig.nodes[node])

            if compared_aig.has_node(node):
                blame_neighbors = set(compared_aig.successors(node)
                                     ).union(compared_aig.predecessors(node))
            else:
                blame_neighbors = set()

            file_neighbors = set(baseline_aig.successors(node)
                                ).union(baseline_aig.predecessors(node))

            node_data.append(({
                "Project":
                    case_study.project_name,
                "author":
                    f"{node_attrs['author']}",
                "additional_authors":
                    len(blame_neighbors.difference(file_neighbors)),
                "removed_authors":
                    -len(file_neighbors.difference(blame_neighbors)),
            }))
        file_data = pd.DataFrame(node_data)

        colors = sns.color_palette(n_colors=2)

        ax = sns.barplot(
            data=file_data,
            x="author",
            y="additional_authors",
            color=colors[0],
        )
        sns.barplot(
            data=file_data,
            x="author",
            y="removed_authors",
            color=colors[1],
            ax=ax
        )

        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.set_xticks([])
        ax.tick_params(axis='y', labelsize=15)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x: >4}"))
        ax.yaxis.set_major_locator(
            _create_tick_locator(
                floor(file_data["additional_authors"].max()),
                ceil(file_data["removed_authors"].min())
            )
        )

        for label in ax.get_yticklabels():
            label.set_fontproperties({"family": "monospace", "size": 15})

        ax.set_xlabel(None)
        ax.set_ylabel(None)
        ax.set_title(case_study.project_name, fontsize=25)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class FileVsBlameGraphDiffPlot(
    AuthorGraphDiffPlot, plot_name='aig_file_vs_blame_authors'
):
    """Plot showing the difference between file-based and ci-based author
    interaction graphs."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__("file", "blame", plot_config, **kwargs)


class CallgraphVsBlameGraphDiffPlot(
    AuthorGraphDiffPlot, plot_name='aig_callgraph_vs_blame_authors'
):
    """Plot showing the difference between callgraph-based and ci-based author
    interaction graphs."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any):
        super().__init__("callgraph", "blame", plot_config, **kwargs)


class AuthorBlameVsFilePlotGenerator(
    PlotGenerator,
    generator_name="aig-file-vs-blame",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a plot showing the difference between file-based and CI-based
    author interactions."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            FileVsBlameGraphDiffPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]


class AuthorBlameVsCallgraphPlotGenerator(
    PlotGenerator,
    generator_name="aig-callgraph-vs-blame",
    options=[REQUIRE_MULTI_CASE_STUDY]
):
    """Generates a plot showing the difference between callgraph-based and CI-
    based author interactions."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            CallgraphVsBlameGraphDiffPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
