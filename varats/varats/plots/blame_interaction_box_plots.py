"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd
import seaborn as sns

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    create_file_based_interaction_graph,
    AIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
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
                case_study, BlameReport
            )
            if not revision:
                continue

            caig = create_blame_interaction_graph(
                project_name, revision
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

        data = pd.DataFrame(nodes)
        ax = sns.violinplot(
            x="Project",
            y="# Interacting Authors",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="Project",
            y="# Interacting Authors",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        ax.set_ylim(-0.1, 1.1)
        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_xlabel(None)
        ax.yaxis.label.set_size(9)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


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


class AuthorBlameVsFileDegreesViolinPlot(
    Plot, plot_name='aig_file_vs_blame_authors_box'
):
    """Box plot of commit-author interaction commit node degrees."""

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        diff_data: tp.List[pd.DataFrame] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            project_names.append(project_name)

            blame_aig = create_blame_interaction_graph(
                project_name, revision
            ).author_interaction_graph()
            file_aig = create_file_based_interaction_graph(
                project_name, revision
            ).author_interaction_graph()

            file_nodes: tp.List[tp.Dict[str, tp.Any]] = []
            for node in file_aig.nodes:
                node_attrs = tp.cast(AIGNodeAttrs, file_aig.nodes[node])

                if blame_aig.has_node(node):
                    blame_neighbors = set(blame_aig.successors(node)
                                         ).union(blame_aig.predecessors(node))
                else:
                    blame_neighbors = set()

                file_neighbors = set(file_aig.successors(node)
                                    ).union(file_aig.predecessors(node))

                file_nodes.append(({
                    "Project":
                        project_name,
                    "author":
                        f"{node_attrs['author']}",
                    "# Additional Authors":
                        len(blame_neighbors.difference(file_neighbors))
                }))
            file_data = pd.DataFrame(file_nodes)
            file_data.set_index("author", inplace=True)
            diff_data.append(file_data)

        data = pd.concat(diff_data)
        ax = sns.violinplot(
            x="Project",
            y="# Additional Authors",
            data=data,
            order=sorted(project_names),
            inner=None,
            linewidth=1,
            color=".95"
        )
        sns.stripplot(
            x="Project",
            y="# Additional Authors",
            data=data,
            order=sorted(project_names),
            alpha=.25,
            size=3
        )
        ax.set_ylim(bottom=0, top=1.1 * data["# Additional Authors"].max())
        ax.set_aspect(0.3 / ax.get_data_ratio())
        ax.tick_params(axis='x', labelrotation=45, labelsize=8)
        ax.tick_params(axis='y', labelsize=8)
        ax.set_xlabel(None)
        ax.yaxis.label.set_size(9)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class AuthorBlameVsFileDegreesViolinPlotGenerator(
    PlotGenerator, generator_name="aig-file-vs-blame-authors-box", options=[]
):
    """
    Generates a violin plot showing how many additional author interactions can
    be found using commit interactions vs.

    file-based interactions.
    """

    def generate(self) -> tp.List[Plot]:
        return [
            AuthorBlameVsFileDegreesViolinPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]
