"""Module for BlameInteractionGraph plots."""

import typing as tp

import pandas as pd
import seaborn as sns

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CAIGNodeAttrs,
    CIGNodeAttrs,
    create_file_based_interaction_graph,
    AIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator, PlotConfig
from varats.project.project_util import get_local_project_gits
from varats.utils.git_util import (
    ChurnConfig,
    create_commit_lookup_helper,
    CommitRepoPair,
    calc_repo_code_churn,
    FullCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)


class CommitAuthorInteractionGraphViolinPlot(Plot, plot_name='caig_box'):
    """Box plot of commit-author interaction commit node degrees."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)

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
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_xlabel(None)

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

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)

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
        ax.tick_params(axis='x', labelrotation=45)
        ax.set_xlabel(None)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class AuthorBlameVsFileDegreesViolinViolinPlotGenerator(
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


class CommitAuthorInteractionGraphGrid(Plot, plot_name='caig_grid'):
    """Box plot of commit-author interaction commit node degrees."""

    def __init__(self, plot_config: PlotConfig, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, plot_config, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_studies = get_loaded_paper_config().get_all_case_studies()

        churn_config = ChurnConfig.create_c_style_languages_config()

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        degree_data: tp.List[pd.DataFrame] = []
        project_names: tp.List[str] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            added_project_name = False

            commit_lookup = create_commit_lookup_helper(project_name)
            repo_lookup = get_local_project_gits(project_name)
            code_churn_lookup: tp.Dict[str, tp.Dict[FullCommitHash,
                                                    tp.Tuple[int, int,
                                                             int]]] = {}
            for repo_name, repo in repo_lookup.items():
                code_churn_lookup[repo_name] = calc_repo_code_churn(
                    repo, churn_config
                )

            def filter_nodes(node: CommitRepoPair) -> bool:
                if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                    return False
                # pylint: disable=cell-var-from-loop
                return bool(commit_lookup(node))

            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            big = create_blame_interaction_graph(project_name, revision)
            cig = big.commit_interaction_graph()
            caig = big.commit_author_interaction_graph(
                outgoing_interactions=True, incoming_interactions=True
            )

            authors = len([
                1 for node in caig.nodes if caig.nodes[node]["author"]
            ])

            cig_data: tp.Dict[CommitRepoPair, int] = {}
            for node in cig.nodes:
                cig_node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
                cig_commit = cig_node_attrs["commit"]
                if not filter_nodes(cig_commit):
                    continue
                cig_data[cig_commit] = cig.degree(node)

            nodes: tp.List[tp.Dict[str, tp.Any]] = []
            for node in caig.nodes:
                caig_node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
                caig_commit = caig_node_attrs["commit"]

                if caig_commit:
                    if not filter_nodes(caig_commit):
                        continue
                    if not added_project_name:
                        project_names.append(project_name)
                        added_project_name = True

                    _, insertions, _ = code_churn_lookup[
                        caig_commit.repository_name][caig_commit.commit_hash]
                    nodes.append(({
                        "project": project_name,
                        "commit": caig_commit.commit_hash,
                        "num_authors": caig.degree(node) / authors,
                        "insertions": insertions,
                        "node_degree": cig_data[caig_commit]
                    }))

            data = pd.DataFrame(nodes)
            data["insertions"] = data["insertions"]
            data["node_degree"] = normalize(data["node_degree"])
            degree_data.append(data)

        full_data = pd.concat(degree_data)
        grid = sns.PairGrid(
            x_vars=["node_degree", "insertions"],
            y_vars=["num_authors"],
            data=full_data,
            hue="project"
        )
        grid.map(sns.scatterplot, size=2, alpha=0.25)
        grid.add_legend()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CAIGGridPlotGenerator(
    PlotGenerator, generator_name="caig-grid", options=[]
):
    """Generates a grid plot comparing the number of authors interacting with a
    commit with other metrics associated with that commit."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitAuthorInteractionGraphGrid(
                self.plot_config, **self.plot_kwargs
            )
        ]
