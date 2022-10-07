"""Module for BlameInteractionGraph plots."""
import os
import typing as tp
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd
import pygit2
import seaborn as sns
from benchbuild.utils.revision_ranges import RevisionRange
from pygit2 import Repository, Commit
from pygraphviz import AGraph

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    BIGNodeAttrs,
    create_blame_interaction_graph_diff,
    BIGDiffNodeAttrs,
    DiffType,
    BIGDiffEdgeAttrs,
)
from varats.data.reports.blame_report import BlameTaintData
from varats.paper.case_study import CaseStudy
from varats.paper_mgmt.case_study import processed_revisions_for_case_study
from varats.plot.plot import Plot
from varats.plot.plots import PlotGenerator
from varats.project.project_util import (
    get_local_project_git,
    get_local_project_git_path,
)
from varats.ts_utils.cli_util import make_cli_option
from varats.ts_utils.click_param_types import (
    REQUIRE_MULTI_CASE_STUDY,
    REQUIRE_BLAME_EXPERIMENT_TYPE,
)
from varats.utils.git_util import (
    FullCommitHash,
    CommitRepoPair,
    ShortCommitHash,
    UNCOMMITTED_COMMIT_HASH,
)


def _get_submodule_changes_for_commit(
    repo: Repository, commit: Commit
) -> tp.List[tp.Tuple[str, str, str]]:
    submodules = repo.listall_submodules()
    submodule_changes: tp.List[tp.Tuple[str, str, str]] = []
    for parent in commit.parents:
        diff = repo.diff(parent, commit)
        for delta in list(diff.deltas):
            if delta.new_file.path in submodules:
                submodule_name = repo.lookup_submodule(delta.new_file.path).name
                submodule_name = submodule_name.split(os.sep)[-1]
                submodule_changes.append((
                    submodule_name, str(delta.old_file.id),
                    str(delta.new_file.id)
                ))
    return submodule_changes


def _find_new_lib_regions(
    big: nx.DiGraph, project_name: str, project_repo: Repository, commit: Commit
) -> tp.Set[BlameTaintData]:
    submodule_changes = _get_submodule_changes_for_commit(project_repo, commit)
    new_lib_commits: tp.Set[CommitRepoPair] = set()
    for name, old, new in submodule_changes:
        if old == UNCOMMITTED_COMMIT_HASH.hash:
            sub_repo = get_local_project_git(project_name, name)
            old = next(
                sub_repo.walk(
                    new, pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE
                )
            ).id.hex
        rev_range = RevisionRange(old, new)
        rev_range.init_cache(
            str(get_local_project_git_path(project_name, name))
        )
        for rev in rev_range:
            new_lib_commits.add(CommitRepoPair(FullCommitHash(rev), name))
    new_regions: tp.Set[BlameTaintData] = set()
    for node in big.nodes:
        node_attrs = tp.cast(BIGNodeAttrs, big.nodes[node])
        commit = node_attrs["blame_taint_data"].commit
        if commit in new_lib_commits:
            new_regions.add(node)
    return new_regions


def _find_affected_regions(
    big: nx.DiGraph, new_regions: tp.Set[BlameTaintData]
) -> tp.Set[BlameTaintData]:
    affected_regions: tp.Set[BlameTaintData] = set()
    for node in new_regions:
        if node in big.nodes:
            affected_regions.update(big.successors(node))
            affected_regions.update(big.predecessors(node))
    return affected_regions


class LibInteractionStats(Plot, plot_name='lib_inter_stats'):
    """Library Interaction Plot."""

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["case_study"]
        project_name = case_study.project_name
        project_repo = get_local_project_git(project_name)

        experiment_type = self.plot_kwargs["experiment_type"]
        revisions = processed_revisions_for_case_study(
            case_study, experiment_type
        )

        dfs: tp.List[pd.DataFrame] = []

        for analyzed_revision in revisions:
            commit = project_repo.get(analyzed_revision.hash)
            big = create_blame_interaction_graph(
                project_name, analyzed_revision, experiment_type
            ).blame_interaction_graph()

            new_regions = _find_new_lib_regions(
                big, project_name, project_repo, commit
            )
            affected_regions = _find_affected_regions(big, new_regions)

            dfs.append(
                pd.DataFrame({
                    "revision": analyzed_revision.short_hash,
                    "commits": big.number_of_nodes(),
                    "affected": len(affected_regions)
                },
                             index=[analyzed_revision.hash])
            )

        df = pd.concat(dfs)
        ax = sns.lineplot(data=df, x="revision", y="commits")
        sns.lineplot(data=df, x="revision", y="affected", ax=ax)

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class LibInteractionStatsPlotGenerator(
    PlotGenerator,
    generator_name="lib-inter-stats",
    options=[REQUIRE_MULTI_CASE_STUDY, REQUIRE_BLAME_EXPERIMENT_TYPE]
):
    """Generates a line plot showing how many library commit regions changed and
    how many commit regions are influenced by these changes."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            LibInteractionStats(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]


class LibInteractionGraphPlot(Plot, plot_name='lib_inter_graph'):
    """Plot for a blame interaction graph diff."""

    def plot(self, view_mode: bool) -> None:
        raise NotImplementedError

    def __plot_dot(self) -> AGraph:
        case_study = self.plot_kwargs["case_study"]
        experiment_type = self.plot_kwargs["experiment_type"]
        old_revision = self.plot_kwargs["old_revision"]
        new_revision = self.plot_kwargs["new_revision"]
        diff_graph = create_blame_interaction_graph_diff(
            case_study.project_name, ShortCommitHash(old_revision),
            ShortCommitHash(new_revision), experiment_type
        )
        big = diff_graph.blame_interaction_graph()

        graph: AGraph = AGraph(strict=False, directed=True)
        clusters: tp.Dict[str, tp.Set[BlameTaintData]] = defaultdict(set)
        for node in big.nodes:
            big_node_attrs = tp.cast(BIGDiffNodeAttrs, big.nodes[node])
            diff_type = big_node_attrs["diff_type"]
            node_attrs: tp.Dict[str, tp.Any] = {
                "label": big.nodes[node]["blame_taint_data"],
                "shape": "rect",
                "style": "rounded"
            }

            if diff_type == DiffType.UNCHANGED:
                node_attrs["color"] = " #d5d8dc"
            if diff_type == DiffType.ADDITION:
                node_attrs["color"] = "green"
            if diff_type == DiffType.DELETION:
                node_attrs["color"] = "red"
            clusters[node.commit.repository_name].add(node)
            graph.add_node(node, **node_attrs)

        graph.graph_attr["overlap"] = "prism"
        graph.graph_attr["splines"] = "compound"
        for name, cluster in clusters.items():
            graph.add_subgraph(cluster, name=f"cluster_{name}")

        for start, end, data in big.edges(keys=False, data=True):
            if graph.has_node(start) and graph.has_node(end):
                big_edge_attrs = tp.cast(BIGDiffEdgeAttrs, data)
                diff_type = big_edge_attrs["diff_type"]
                edge_attrs: tp.Dict[str, tp.Any] = {}
                if diff_type == DiffType.UNCHANGED:
                    edge_attrs["color"] = " #d5d8dc"
                if diff_type == DiffType.ADDITION:
                    edge_attrs["color"] = "green"
                if diff_type == DiffType.DELETION:
                    edge_attrs["color"] = "red"
                graph.add_edge(start, end, **edge_attrs)

        print(f"N={len(graph.nodes())}, E={len(graph.edges())}")
        return graph

    def save(self, plot_dir: Path, filetype: str = 'svg') -> None:
        graph = self.__plot_dot()
        graph.draw(str(plot_dir / self.plot_file_name(filetype)), prog="fdp")

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class LibInterGraphGenerator(
    PlotGenerator,
    generator_name="lib-inter-graph",
    options=[
        REQUIRE_MULTI_CASE_STUDY, REQUIRE_BLAME_EXPERIMENT_TYPE,
        make_cli_option(
            "--old-revision",
            type=str,
            required=True,
            metavar="SHORT_COMMIT_HASH",
            help="The revision to use."
        ),
        make_cli_option(
            "--new-revision",
            type=str,
            required=True,
            metavar="SHORT_COMMIT_HASH",
            help="The revision to use."
        )
    ]
):
    """Visualizes a blame interaction graph diff."""

    def generate(self) -> tp.List[Plot]:
        case_studies: tp.List[CaseStudy] = self.plot_kwargs.pop("case_study")

        return [
            LibInteractionGraphPlot(
                self.plot_config, case_study=cs, **self.plot_kwargs
            ) for cs in case_studies
        ]
