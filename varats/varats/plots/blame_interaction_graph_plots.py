"""Module for BlameInteractionGraph plots."""
import configparser
import subprocess
import typing as tp
from datetime import datetime
from pathlib import Path

import click
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.offline as offply
import pygit2

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
    CIGEdgeAttrs,
    AIGNodeAttrs,
    CAIGNodeAttrs,
)
from varats.experiments.vara.blame_report_experiment import (
    BlameReportExperiment, BlameReportExperimentRegion,
)
from varats.mapping.commit_map import get_commit_map
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.plot.plot import Plot, PlotDataEmpty
from varats.plot.plots import PlotGenerator
from varats.plots.chord_plot_utils import (
    make_chord_plot,
    make_arc_plot,
    NodeTy,
    ChordPlotNodeInfo,
    ChordPlotEdgeInfo,
    ArcPlotEdgeInfo,
    ArcPlotNodeInfo,
)
from varats.ts_utils.cli_util import CLIOptionTy, make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_REVISION,
    REQUIRE_CASE_STUDY,
)
from varats.utils.exceptions import UnsupportedOperation
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
    ShortCommitHash,
)


class CommitInteractionGraphPlot(Plot, plot_name='cig_plot'):
    """Creates a dot file for a commit interaction graph."""

    def plot(self, view_mode: bool) -> None:
        # Nothing to do here.
        pass

    def save(self, plot_dir: Path, filetype: str = 'svg') -> None:
        project_name = self.plot_kwargs["case_study"].project_name
        commit_map = get_commit_map(project_name)
        short_revision = ShortCommitHash(self.plot_kwargs["revision"])
        revision = commit_map.convert_to_full_or_warn(short_revision)

        cig = create_blame_interaction_graph(
            project_name, revision, BlameReportExperimentRegion
        ).commit_interaction_graph()
        nx.set_node_attributes(
            cig,
            {node: cig.nodes[node]["commit"].commit_hash for node in cig.nodes},
            "label"
        )

        # pylint: disable=import-outside-toplevel
        from networkx.drawing.nx_agraph import write_dot
        write_dot(cig, plot_dir / self.plot_file_name("dot"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CommitInteractionGraphPlotGenerator(
    PlotGenerator,
    generator_name="cig-plot",
    options=[REQUIRE_CASE_STUDY, REQUIRE_REVISION]
):
    """Plot a commit interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitInteractionGraphPlot(self.plot_config, **self.plot_kwargs)
        ]


NodeInfoTy = tp.TypeVar("NodeInfoTy", ChordPlotNodeInfo, ArcPlotNodeInfo)
EdgeInfoTy = tp.TypeVar("EdgeInfoTy", ChordPlotEdgeInfo, ArcPlotEdgeInfo)


def _prepare_cig_plotly(
    project_name: str, revision: FullCommitHash,
    create_node_info: tp.Callable[[NodeTy, CommitRepoPair, nx.DiGraph],
                                  NodeInfoTy],
    create_edge_info: tp.Callable[[CommitRepoPair, CommitRepoPair, int],
                                  EdgeInfoTy]
) -> tp.Tuple[tp.List[tp.Tuple[NodeTy, NodeInfoTy]], tp.List[tp.Tuple[
    NodeTy, NodeTy, EdgeInfoTy]]]:
    commit_lookup = create_commit_lookup_helper(project_name)
    cig = create_blame_interaction_graph(
        project_name, revision, BlameReportExperimentRegion
    ).commit_interaction_graph()

    def filter_nodes(node: CommitRepoPair) -> bool:
        if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
            return False
        commit = commit_lookup(node)
        if not commit:
            return False
        # make filter configurable
        return datetime.utcfromtimestamp(commit.commit_time
                                        ) >= datetime(2015, 1, 1)

    nodes: tp.List[tp.Tuple[NodeTy, NodeInfoTy]] = []
    node_meta: tp.Dict[NodeTy, CommitRepoPair] = {}
    for node in cig.nodes:
        node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
        commit = node_attrs["commit"]
        if not filter_nodes(commit):
            continue
        node_meta[node] = commit
        nodes.append((node, create_node_info(node, commit, cig)))

    nodes = sorted(
        nodes, key=lambda x: int(commit_lookup(node_meta[x[0]]).commit_time)
    )

    edges: tp.List[tp.Tuple[NodeTy, NodeTy, EdgeInfoTy]] = []
    for source, sink in cig.edges:
        amount = tp.cast(CIGEdgeAttrs, cig[source][sink])["amount"]
        source_commit = tp.cast(CIGNodeAttrs, cig.nodes[source])["commit"]
        sink_commit = tp.cast(CIGNodeAttrs, cig.nodes[sink])["commit"]
        if not filter_nodes(source_commit) or not filter_nodes(sink_commit):
            continue
        edges.append((
            source, sink, create_edge_info(source_commit, sink_commit, amount)
        ))

    return nodes, edges


class CommitInteractionGraphChordPlot(Plot, plot_name='cig_chord_plot'):
    """Chord plot for a commit interaction graph."""

    def plot(self, view_mode: bool) -> None:
        project_name: str = self.plot_kwargs["case_study"].project_name
        revision = get_commit_map(project_name).convert_to_full_or_warn(
            ShortCommitHash(self.plot_kwargs["revision"])
        )

        def create_node_data(
            node: NodeTy, commit: CommitRepoPair, cig: nx.DiGraph
        ) -> ChordPlotNodeInfo:
            del node
            del cig
            return {"info": commit.commit_hash.short_hash, "color": 1}

        def create_edge_data(
            source_commit: CommitRepoPair, sink_commit: CommitRepoPair,
            amount: int
        ) -> ChordPlotEdgeInfo:
            return {
                "size": amount,
                "color": 1,
                "info":
                    f"{source_commit.commit_hash.short_hash} "
                    f"--{{{amount}}}--> "
                    f"{sink_commit.commit_hash.short_hash}"
            }

        nodes, edges = _prepare_cig_plotly(
            project_name, revision, create_node_data, create_edge_data
        )
        figure = make_chord_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CIGChordPlotGenerator(
    PlotGenerator,
    generator_name="cig-chord-plot",
    options=[REQUIRE_CASE_STUDY, REQUIRE_REVISION]
):
    """Generates a chord plot for a commit interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitInteractionGraphChordPlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class CommitInteractionGraphArcPlot(Plot, plot_name='cig_arc_plot'):
    """Arc plot for a commit interaction graph."""

    def plot(self, view_mode: bool) -> None:
        project_name: str = self.plot_kwargs["case_study"].project_name
        revision = get_commit_map(project_name).convert_to_full_or_warn(
            ShortCommitHash(self.plot_kwargs["revision"])
        )

        def create_node_data(
            node: NodeTy, commit: CommitRepoPair, cig: nx.DiGraph
        ) -> ArcPlotNodeInfo:
            return {
                "info": commit.commit_hash.short_hash,
                "size": cig.degree(node),
                "fill_color": cig.out_degree(node),
                "line_color": cig.in_degree(node)
            }

        def create_edge_data(
            source_commit: CommitRepoPair, sink_commit: CommitRepoPair,
            amount: int
        ) -> ArcPlotEdgeInfo:
            return {
                "size": amount,
                "color": amount,
                "info":
                    f"{source_commit.commit_hash.short_hash} "
                    f"--{{{amount}}}--> "
                    f"{sink_commit.commit_hash.short_hash}"
            }

        nodes, edges = _prepare_cig_plotly(
            project_name, revision, create_node_data, create_edge_data
        )
        figure = make_arc_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CIGArcPlotGenerator(
    PlotGenerator,
    generator_name="cig-arc-plot",
    options=[REQUIRE_CASE_STUDY, REQUIRE_REVISION]
):
    """Generates an arc plot for a commit interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitInteractionGraphArcPlot(self.plot_config, **self.plot_kwargs)
        ]


OPTIONAL_SORT_METHOD: CLIOptionTy = make_cli_option(
    "--sort-by",
    type=click.Choice(["degree", "time"]),
    default="degree",
    required=False,
    help="Sort method for commit interaction graph nodes."
)


def get_gitmodules_info():
    repo = pygit2.Repository(REPO_PATH)
    # Get the .gitmodules blob object
    commit = repo[repo.head.target]
    tree = commit.tree
    gitmodules_entry = tree[".gitmodules"]
    gitmodules_blob = repo[gitmodules_entry.oid]

    # Parse the .gitmodules file contents
    gitmodules_data = gitmodules_blob.data
    gitmodules_config = configparser.ConfigParser()
    gitmodules_config.read_string(gitmodules_data.decode('utf-8'))

    # Collect the submodule path and URL information
    submodules = []
    for section in gitmodules_config.sections():
        if section.startswith('submodule '):
            submodule_name = section[len('submodule '):]
            submodule_path = gitmodules_config.get(section, 'path')
            submodule_url = gitmodules_config.get(section, 'url')
            submodules.append((submodule_name, submodule_path, submodule_url))

    return submodules


def pull_commit_history_information(submodules):

    # Get the tree object for the specified commit
    repo = pygit2.Repository(REPO_PATH)

    commits = []
    i = 0
    for submodule in submodules:
        walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE)
        subdirectory_path = submodule[1]
        for commit in walker:
            # Initialize a flag to check if the 'third_party' has changes in this commit
            # has_changes = False
            # Compare the tree of this commit with its parent
            if len(commit.parents) == 0:
                continue
            diff = repo.diff(commit.parents[0], commit)
            # Loop through all patches in the diff
            files_changed = [patch.delta.new_file.path for patch in diff]
            if any([file.startswith(subdirectory_path) for file in files_changed]):
                i += 1
                print(i)  # total 1864 times commits is for third party
                commits.append({
                    'author_name': commit.author.name,
                    'author_email': commit.author.email,
                    # 'message': commit.message,
                    'commit_hash': commit.hex,
                    'commit_time': datetime.datetime.fromtimestamp(commit.commit_time)
                    # 'changed_folder': get_change_folder(commit)
                })

    df = pd.DataFrame(commits)
    # df.to_csv(TASK_PATH + 'openssl_commit_history2.csv', index=False)

    return df


class SubCommitInteractionGraphPlot(Plot, plot_name='sub-cig-plot'):
    submodule_info = get_gitmodules_info()
    df = pull_commit_history_information(submodule_info)

    def is_submodule_change(self, commit_hash):
        for index, row in self.df.iterrows():
            if row['commit_hash'] == commit_hash:
                return True
            else:
                return False

    def plot(self, view_mode: bool) -> None:
        project_name = self.plot_kwargs["case_study"].project_name
        commit_map = get_commit_map(project_name)
        short_revision = ShortCommitHash(self.plot_kwargs["revision"])
        revision = commit_map.convert_to_full_or_warn(short_revision)

        cig = create_blame_interaction_graph(
            project_name, revision, BlameReportExperimentRegion
        ).commit_interaction_graph()
        nx.set_node_attributes(
            cig,
            {node: cig.nodes[node]["commit"].commit_hash for node in cig.nodes},
            "label"
        )

        # Find nodes representing commits that changed submodules
        submodule_commit_nodes = [node for node in cig.nodes if
                                  self.is_submodule_change(cig.nodes[node]["commit"].commit_hash)]

        # Count the number of unique authors for main repository and submodule changes
        main_repo_authors = set()
        submodule_change_authors = set()

        for node in cig.nodes:
            commit_info = cig.nodes[node]["commit"]
            author = commit_info.author_name  # Assuming the existence of the author_name attribute, modify as needed

            main_repo_authors.add(author)

            if node in submodule_commit_nodes:
                submodule_change_authors.add(author)

        main_repo_author_count = len(main_repo_authors)
        submodule_change_author_count = len(submodule_change_authors)

        print(f"Main Repository Authors: {main_repo_author_count}")
        print(f"Authors with Submodule Changes: {submodule_change_author_count}")



    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class SubCIGPlotGenerator(
    PlotGenerator,
    generator_name="sub-cig-plot",
    options=[REQUIRE_CASE_STUDY, REQUIRE_REVISION]
):
    """Generates a plot for a submodule's commit interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            SubCommitInteractionGraphPlot(self.plot_config, **self.plot_kwargs)
        ]


class CommitInteractionGraphNodeDegreePlot(Plot, plot_name='cig_node_degrees'):
    """
    Plot node degrees of a commit interaction graph.

    Additional arguments:
      - sort: criteria to sort the revisions [degree, time]
    """

    def plot(self, view_mode: bool) -> None:
        sort = self.plot_kwargs["sort"]
        case_study = self.plot_kwargs["plot_case_study"]

        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle("Commit Interaction Graph - Node Degrees")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Degree")
        xlabel = ""
        if sort == "time":
            xlabel = "Time (old to new)"
        elif sort == "degree":
            xlabel = "Commits"
        axes.set_xlabel(xlabel)

        revision = newest_processed_revision_for_case_study(
            case_study, BlameReportExperiment
        )
        if not revision:
            raise PlotDataEmpty()

        cig = create_blame_interaction_graph(
            case_study.project_name, revision, BlameReportExperiment
        ).commit_interaction_graph()
        commit_lookup = create_commit_lookup_helper(case_study.project_name)

        def filter_nodes(node: CommitRepoPair) -> bool:
            if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                return False
            return bool(commit_lookup(node))

        def commit_time(node: CommitRepoPair) -> datetime:
            return datetime.utcfromtimestamp(commit_lookup(node).commit_time)

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in cig.nodes:
            node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
            commit = node_attrs["commit"]
            if not filter_nodes(commit):
                continue
            nodes.append(({
                "commit_hash": commit.commit_hash,
                "commit_time": commit_time(commit),
                "node_degree": cig.degree(node),
                "node_out_degree": cig.out_degree(node),
                "node_in_degree": cig.in_degree(node),
            }))

        data = pd.DataFrame(nodes)

        if sort == "time":
            data.sort_values(by="commit_time", inplace=True)

        node_degrees = data.loc[:, ["commit_hash", "node_degree"]]
        node_out_degrees = data.loc[:, ["commit_hash", "node_out_degree"]]
        node_in_degrees = data.loc[:, ["commit_hash", "node_in_degree"]]

        if sort == "degree":
            node_degrees.sort_values(by="node_degree", inplace=True)
            node_out_degrees.sort_values(by="node_out_degree", inplace=True)
            node_in_degrees.sort_values(by="node_in_degree", inplace=True)

        axes.plot(node_degrees["node_degree"].values, label="degree")
        axes.plot(
            node_out_degrees["node_out_degree"].values, label="out_degree"
        )
        axes.plot(node_in_degrees["node_in_degree"].values, label="in_degree")

        axes.legend()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CIGNodeDegreePlotGenerator(
    PlotGenerator,
    generator_name="cig-node-degrees",
    options=[REQUIRE_CASE_STUDY, OPTIONAL_SORT_METHOD]
):
    """Generates a plot of node degrees of a commit interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitInteractionGraphNodeDegreePlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class AuthorInteractionGraphNodeDegreePlot(Plot, plot_name='aig_node_degrees'):
    """Plot node degrees of a author interaction graph."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]

        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle("Author Interaction Graph - Node Degrees")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Degree")
        axes.set_xlabel("Authors")

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReportExperiment
        )
        if not revision:
            raise PlotDataEmpty()

        aig = create_blame_interaction_graph(
            project_name, revision, BlameReportExperiment
        ).author_interaction_graph()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, aig.nodes[node])
            author = node_attrs["author"]
            nodes.append(({
                "author": author,
                "node_degree": aig.degree(node),
                "node_out_degree": aig.out_degree(node),
                "node_in_degree": aig.in_degree(node),
            }))

        data = pd.DataFrame(nodes)
        node_degrees = data.loc[:, ["author", "node_degree"]]
        node_out_degrees = data.loc[:, ["author", "node_out_degree"]]
        node_in_degrees = data.loc[:, ["author", "node_in_degree"]]

        node_degrees.sort_values(by="node_degree", inplace=True)
        node_out_degrees.sort_values(by="node_out_degree", inplace=True)
        node_in_degrees.sort_values(by="node_in_degree", inplace=True)

        axes.plot(node_degrees["node_degree"].values, label="degree")
        axes.plot(
            node_out_degrees["node_out_degree"].values, label="out_degree"
        )
        axes.plot(node_in_degrees["node_in_degree"].values, label="in_degree")

        axes.legend()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class AIGNodeDegreePlotGenerator(
    PlotGenerator,
    generator_name="aig-node-degrees",
    options=[REQUIRE_CASE_STUDY]
):
    """Generates a plot of node degrees of a author interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            AuthorInteractionGraphNodeDegreePlot(
                self.plot_config, **self.plot_kwargs
            )
        ]


class CommitAuthorInteractionGraphNodeDegreePlot(
    Plot, plot_name='caig_node_degrees'
):
    """Plot node degrees of commits in a commit-author interaction graph."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]

        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle("Commit-Author Interaction Graph - # Interacting Authors")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Authors")
        axes.set_xlabel("Commits")

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReportExperiment
        )
        if not revision:
            raise PlotDataEmpty()

        caig = create_blame_interaction_graph(
            project_name, revision, BlameReportExperiment
        ).commit_author_interaction_graph()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in caig.nodes:
            node_attrs = tp.cast(CAIGNodeAttrs, caig.nodes[node])
            commit = node_attrs["commit"]

            if commit:
                nodes.append(({
                    "commit": commit.commit_hash,
                    "num_authors": caig.degree(node)
                }))

        data = pd.DataFrame(nodes)
        num_authors = data.loc[:, ["commit", "num_authors"]]
        num_authors.sort_values(by="num_authors", inplace=True)
        axes.plot(num_authors["num_authors"].values)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise UnsupportedOperation


class CAIGNodeDegreePlotGenerator(
    PlotGenerator,
    generator_name="caig-node-degrees",
    options=[REQUIRE_CASE_STUDY]
):
    """Generates a plot of node degrees of a commit-author interaction graph."""

    def generate(self) -> tp.List[Plot]:
        return [
            CommitAuthorInteractionGraphNodeDegreePlot(
                self.plot_config, **self.plot_kwargs
            )
        ]
