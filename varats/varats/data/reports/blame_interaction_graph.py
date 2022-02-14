"""Module for representing blame interaction data in a graph/network."""
import abc
import itertools
import re
import sys
import typing as tp
from pathlib import Path

import networkx as nx
from benchbuild.utils.cmd import git

from varats.data.cache_helper import build_cached_graph
from varats.data.reports.blame_report import (
    BlameReport,
    gen_base_to_inter_commit_repo_pair_mapping,
    BlameReportDiff,
)
from varats.jupyterhelper.file import load_blame_report
from varats.project.project_util import (
    get_local_project_git_path,
    get_local_project_gits,
)
from varats.report.report import ReportFilename
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    ChurnConfig,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
    get_submodule_head,
)

if sys.version_info <= (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict


class _BIGNodeAttrs(TypedDict):
    """Blame interaction graph node attributes."""
    commit: CommitRepoPair


class _BIGEdgeAttrs(TypedDict):
    """Blame interaction graph edge attributes."""
    amount: int


class CIGNodeAttrs(TypedDict):
    """Commit interaction graph node attributes."""
    commit: CommitRepoPair


class CIGEdgeAttrs(TypedDict):
    """Commit interaction graph edge attributes."""
    amount: int


class AIGNodeAttrs(TypedDict):
    """Author interaction graph node attributes."""
    author: str
    num_commits: int
    commits: tp.List[CommitRepoPair]


class AIGEdgeAttrs(TypedDict):
    """Author interaction graph edge attributes."""
    amount: int
    interactions: tp.List[tp.Tuple[CommitRepoPair, CommitRepoPair]]


class CAIGNodeAttrs(TypedDict):
    """Commit-author interaction graph node attributes."""
    commit: tp.Optional[CommitRepoPair]
    author: tp.Optional[str]


class CAIGEdgeAttrs(TypedDict):
    """Commit-author interaction graph edge attributes."""
    amount: int


class InteractionGraph(abc.ABC):
    """Graph/Network built from interaction data."""

    def __init__(self, project_name: str):
        self.__project_name = project_name

    @property
    def project_name(self) -> str:
        return self.__project_name

    @abc.abstractmethod
    def _interaction_graph(self) -> nx.DiGraph:
        pass

    def commit_interaction_graph(self) -> nx.DiGraph:
        """
        Return a digraph with commits as nodes and interactions as edges.

        Nodes can be referenced via their ``CommitRepoPair``.
        The graph has the following attributes:
        Nodes:
          - commit: CommitRepoPair for this commit
        Edges:
          - amount: how often this interaction was found

        Returns:
            the commit interaction graph
        """
        interaction_graph = self._interaction_graph()

        def edge_data(
            source: tp.Set[CommitRepoPair], sink: tp.Set[CommitRepoPair]
        ) -> CIGEdgeAttrs:
            assert len(source) == len(
                sink
            ) == 1, "Some node has more than one commit."
            return tp.cast(
                CIGEdgeAttrs,
                interaction_graph[next(iter(source))][next(iter(sink))].copy()
            )

        def node_data(node: tp.Set[CommitRepoPair]) -> CIGNodeAttrs:
            assert len(node) == 1, "Some node has more than one commit."
            return tp.cast(
                CIGNodeAttrs, interaction_graph.nodes[next(iter(node))].copy()
            )

        cig = nx.quotient_graph(
            interaction_graph,
            partition=lambda u, v: False,
            edge_data=edge_data,
            node_data=node_data,
            create_using=nx.DiGraph
        )
        relabel_dict: tp.Dict[tp.FrozenSet[CommitRepoPair], CommitRepoPair] = {}
        for node in cig.nodes:
            relabel_dict[node] = tp.cast(CIGNodeAttrs,
                                         cig.nodes[node])["commit"]
        nx.relabel_nodes(cig, relabel_dict, copy=False)
        return cig

    def author_interaction_graph(self) -> nx.DiGraph:
        """
        Return a digraph with authors as nodes and interactions as edges.

        Nodes can be referenced via their author.
        The graph has the following attributes:
        Nodes:
          - author: name of the author
          - num_commits: number of commits aggregated in this node
        Edges:
          - amount: how often an interaction between two authors was found

        Returns:
            the author interaction graph
        """
        interaction_graph = self._interaction_graph()
        commit_lookup = create_commit_lookup_helper(self.project_name)

        def partition(node_u: CommitRepoPair, node_v: CommitRepoPair) -> bool:
            if UNCOMMITTED_COMMIT_HASH in (
                node_u.commit_hash, node_v.commit_hash
            ):
                return node_u.commit_hash == node_v.commit_hash
            return str(commit_lookup(node_u).author.name
                      ) == str(commit_lookup(node_v).author.name)

        def edge_data(
            partition_a: tp.Set[CommitRepoPair],
            partition_b: tp.Set[CommitRepoPair]
        ) -> AIGEdgeAttrs:
            amount = 0
            interactions: tp.List[tp.Tuple[CommitRepoPair, CommitRepoPair]] = []
            for source in partition_a:
                for sink in partition_b:
                    if interaction_graph.has_edge(source, sink):
                        amount += int(interaction_graph[source][sink]["amount"])
                        interactions.append((source, sink))

            return {"amount": amount, "interactions": interactions}

        def node_data(node: tp.Set[CommitRepoPair]) -> AIGNodeAttrs:
            authors = {
                str(commit_lookup(commit).author.name)
                if commit.commit_hash != UNCOMMITTED_COMMIT_HASH else "Unknown"
                for commit in node
            }
            assert len(authors) == 1, "Some node has more then one author."
            return {
                "author": next(iter(authors)),
                "num_commits": len(node),
                "commits": list(node)
            }

        aig = nx.quotient_graph(
            interaction_graph,
            partition=partition,
            edge_data=edge_data,
            node_data=node_data,
            create_using=nx.DiGraph
        )
        relabel_dict: tp.Dict[tp.FrozenSet[CommitRepoPair], str] = {}
        for node in aig.nodes:
            relabel_dict[node] = tp.cast(AIGNodeAttrs,
                                         aig.nodes[node])["author"]
        nx.relabel_nodes(aig, relabel_dict, copy=False)
        return aig

    def commit_author_interaction_graph(
        self,
        outgoing_interactions: bool = True,
        incoming_interactions: bool = False
    ) -> nx.DiGraph:
        """
        Return a digraph connecting commits to interacting authors.

        Nodes can be referenced via their ``CommitRepoPair`` or author,
        whichever is present.
        The graph has the following attributes:
        Nodes:
          - commit: commit hash if the node is a commit
          - author: name of the author if the node is an author
        Edges:
          - amount: how often a commit interacts with an author

        Args:
            outgoing_interactions: whether to include outgoing interactions
            incoming_interactions: whether to include incoming interactions

        Returns:
            the commit-author interaction graph
        """
        interaction_graph = self._interaction_graph()
        commit_lookup = create_commit_lookup_helper(self.project_name)

        commit_author_mapping = {
            commit: commit_lookup(commit).author.name
            if commit.commit_hash != UNCOMMITTED_COMMIT_HASH else "Unknown"
            for commit in (list(interaction_graph.nodes))
        }
        caig = nx.DiGraph()
        # add commits as nodes
        caig.add_nodes_from([(
            commit, {
                "commit": interaction_graph.nodes[commit]["commit"],
                "author": None
            }
        ) for commit in list(interaction_graph.nodes)])
        # add authors as nodes
        caig.add_nodes_from([(author, {
            "commit": None,
            "author": author
        }) for author in set(commit_author_mapping.values())])

        # add edges and aggregate edge attributes
        for node in interaction_graph.nodes:
            if incoming_interactions:
                for source, sink, data in interaction_graph.in_edges(
                    node, data=True
                ):
                    if not caig.has_edge(source, commit_author_mapping[sink]):
                        caig.add_edge(
                            source, commit_author_mapping[sink], amount=0
                        )
                    caig[source][commit_author_mapping[sink]
                                ]["amount"] += data["amount"]
            if outgoing_interactions:
                for source, sink, data in interaction_graph.out_edges(
                    node, data=True
                ):
                    if not caig.has_edge(sink, commit_author_mapping[source]):
                        caig.add_edge(
                            sink, commit_author_mapping[source], amount=0
                        )
                    caig[sink][commit_author_mapping[source]
                              ]["amount"] += data["amount"]
        return caig


class BlameInteractionGraph(InteractionGraph):
    """Graph/Network built from blame interaction data."""

    def __init__(
        self, project_name: str, report: tp.Union[BlameReport, BlameReportDiff]
    ):
        super().__init__(project_name)
        self.__report = report
        self.__cached_interaction_graph: tp.Optional[nx.DiGraph] = None

    def _interaction_graph(self) -> nx.DiGraph:

        def create_graph() -> nx.DiGraph:
            interaction_graph = nx.DiGraph()
            interactions = gen_base_to_inter_commit_repo_pair_mapping(
                self.__report
            )
            commits = {
                commit for base, inters in interactions.items()
                for commit in [base, *inters.keys()]
            }

            def create_node_attrs(commit: CommitRepoPair) -> _BIGNodeAttrs:
                return {
                    "commit": commit,
                }

            # pylint: disable=unused-argument
            def create_edge_attrs(
                base: CommitRepoPair, inter: CommitRepoPair, amount: int
            ) -> _BIGEdgeAttrs:
                return {"amount": amount}

            interaction_graph.add_nodes_from([
                (commit, create_node_attrs(commit)) for commit in commits
            ])
            interaction_graph.add_edges_from([
                (base, inter, create_edge_attrs(base, inter, amount))
                for base, inters in interactions.items()
                for inter, amount in inters.items()
            ])
            return interaction_graph

        if not self.__cached_interaction_graph:
            self.__cached_interaction_graph = build_cached_graph(
                f"ig-blame-{self.project_name}", create_graph
            )
        return self.__cached_interaction_graph


class FileBasedInteractionGraph(InteractionGraph):
    """Graph/Network built from file-based interaction data."""

    def __init__(self, project_name: str, head_commit: FullCommitHash):
        super().__init__(project_name)
        self.__head_commit = head_commit
        self.__cached_interaction_graph: tp.Optional[nx.DiGraph] = None

    def _interaction_graph(self) -> nx.DiGraph:

        def create_graph() -> nx.DiGraph:
            repos = get_local_project_gits(self.project_name)
            interaction_graph = nx.DiGraph()
            churn_config = ChurnConfig.create_c_style_languages_config()
            file_pattern = re.compile(
                r"|".join(
                    churn_config.get_extensions_repr(prefix=r"\.", suffix=r"$")
                )
            )

            blame_regex = re.compile(r"^([0-9a-f]+)\s+(?:.+\s+)?[\d]+\) ?(.*)$")

            for repo_name in repos:
                repo_path = get_local_project_git_path(
                    self.project_name, repo_name
                )
                project_git = git["-C", str(repo_path)]
                head_commit = get_submodule_head(
                    self.project_name, repo_name, self.__head_commit
                )

                file_names = project_git(
                    "ls-tree", "--full-tree", "--name-only", "-r", head_commit
                ).split("\n")
                files: tp.List[Path] = [
                    repo_path / path
                    for path in file_names
                    if file_pattern.search(path)
                ]
                for file in files:
                    commits: tp.Set[CommitRepoPair] = set()
                    blame_lines: str = project_git(
                        "blame", "-w", "-s", "-l", "--root", head_commit, "--",
                        str(file.relative_to(repo_path))
                    )

                    for line in blame_lines.strip().split("\n"):
                        match = blame_regex.match(line)
                        if not match:
                            raise AssertionError

                        if match.group(2):
                            commits.add(
                                CommitRepoPair(
                                    FullCommitHash(match.group(1)), repo_name
                                )
                            )

                    for commit in commits:
                        interaction_graph.add_node(commit, commit=commit)
                    for commit_a, commit_b in itertools.product(
                        commits, repeat=2
                    ):
                        if commit_a != commit_b:
                            if not interaction_graph.has_edge(
                                commit_a, commit_b
                            ):
                                interaction_graph.add_edge(
                                    commit_a, commit_b, amount=0
                                )
                            interaction_graph[commit_a][commit_b]["amount"] += 1
            return interaction_graph

        if not self.__cached_interaction_graph:
            self.__cached_interaction_graph = build_cached_graph(
                f"ig-file-{self.project_name}", create_graph
            )
        return self.__cached_interaction_graph


def create_blame_interaction_graph(
    project_name: str, revision: FullCommitHash
) -> BlameInteractionGraph:
    """
    Create a blame interaction graph for a certain project revision.

    Args:
        project_name: name of the project
        revision: project revision

    Returns:
        the blame interaction graph
    """
    file_name_filter: tp.Callable[[str], bool] = lambda x: False

    if revision:

        def match_revision(file_name: str) -> bool:
            return ReportFilename(
                file_name
            ).commit_hash != revision.to_short_commit_hash()

        file_name_filter = match_revision

    report_files = get_processed_revisions_files(
        project_name, BlameReport, file_name_filter
    )
    if len(report_files) == 0:
        raise LookupError(f"Found no BlameReport for project {project_name}")
    report = load_blame_report(report_files[0])
    return BlameInteractionGraph(project_name, report)


def create_file_based_interaction_graph(
    project_name: str, revision: FullCommitHash
) -> FileBasedInteractionGraph:
    """
    Create a file-based interaction graph for a certain project revision.

    Args:
        project_name: name of the project
        revision: project revision

    Returns:
        the blame interaction graph
    """
    return FileBasedInteractionGraph(project_name, revision)


def get_author_data(aig: nx.DiGraph, author: str) -> tp.Dict[str, tp.Any]:
    """
    Collect information for a specific author from an author interaction graph.

    Args:
        aig: a author interaction graph
        author: name of the author

    Returns:
        a dict with information about the author
    """
    node_attrs = tp.cast(AIGNodeAttrs, aig.nodes[author])
    in_attrs = [
        d["interactions"] for u, v, d in aig.in_edges().data() if v == author
    ]
    out_attrs = [
        d["interactions"] for u, v, d in aig.out_edges().data() if u == author
    ]
    neighbors = set(aig.successors(author)).union(aig.predecessors(author))

    return {
        "node_attrs": node_attrs,
        "neighbors": neighbors,
        "in_attrs": in_attrs,
        "out_attrs": out_attrs
    }
