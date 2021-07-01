"""Module for representing blame interaction data in a graph/network."""
import abc
import glob
import itertools
import re
import sys
import typing as tp
from pathlib import Path

import networkx as nx
import pygit2
from benchbuild.utils.cmd import git

from varats.data.reports.blame_report import (
    BlameReport,
    gen_base_to_inter_commit_repo_pair_mapping,
    BlameReportDiff,
)
from varats.jupyterhelper.file import load_blame_report
from varats.plot.plot import PlotDataEmpty
from varats.project.project_util import (
    get_local_project_git,
    get_primary_project_source,
    get_local_project_git_path,
)
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    DUMMY_COMMIT,
    ChurnConfig,
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
    def project_name(self):
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
        ig = self._interaction_graph()

        def edge_data(
            b: tp.Set[CommitRepoPair], c: tp.Set[CommitRepoPair]
        ) -> CIGEdgeAttrs:
            assert len(b) == len(c) == 1, "Some node has more than one commit."
            return tp.cast(
                CIGEdgeAttrs, ig[next(iter(b))][next(iter(c))].copy()
            )

        def node_data(b: tp.Set[CommitRepoPair]) -> CIGNodeAttrs:
            assert len(b) == 1, "Some node has more than one commit."
            return tp.cast(CIGNodeAttrs, ig.nodes[next(iter(b))].copy())

        cig = nx.quotient_graph(
            ig,
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
        ig = self._interaction_graph()
        commit_lookup = create_commit_lookup_helper(self.project_name)

        def partition(u: CommitRepoPair, v: CommitRepoPair) -> bool:
            if u.commit_hash == DUMMY_COMMIT or v.commit_hash == DUMMY_COMMIT:
                return u.commit_hash == v.commit_hash
            return str(commit_lookup(u).author.name
                      ) == str(commit_lookup(v).author.name)

        def edge_data(
            b: tp.Set[CommitRepoPair], c: tp.Set[CommitRepoPair]
        ) -> AIGEdgeAttrs:
            amount = 0
            interactions: tp.List[tp.Tuple[CommitRepoPair, CommitRepoPair]] = []
            for source in b:
                for sink in c:
                    if ig.has_edge(source, sink):
                        amount += int(ig[source][sink]["amount"])
                        interactions.append((source, sink))

            return {"amount": amount, "interactions": interactions}

        def node_data(b: tp.Set[CommitRepoPair]) -> AIGNodeAttrs:
            authors = {
                str(commit_lookup(commit).author.name)
                if commit.commit_hash != DUMMY_COMMIT else "Unknown"
                for commit in b
            }
            assert len(authors) == 1, "Some node has more then one author."
            return {
                "author": next(iter(authors)),
                "num_commits": len(b),
                "commits": list(b)
            }

        aig = nx.quotient_graph(
            ig,
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
        ig = self._interaction_graph()
        commit_lookup = create_commit_lookup_helper(self.project_name)

        commit_author_mapping = {
            commit: commit_lookup(commit).author.name
            if commit.commit_hash != DUMMY_COMMIT else "Unknown"
            for commit in (list(ig.nodes))
        }
        caig = nx.DiGraph()
        # add commits as nodes
        caig.add_nodes_from([
            (commit, {
                "commit": ig.nodes[commit]["commit"],
                "author": None
            }) for commit in (list(ig.nodes))
        ])
        # add authors as nodes
        caig.add_nodes_from([(author, {
            "commit": None,
            "author": author
        }) for author in (set(commit_author_mapping.values()))])

        # add edges and aggregate edge attributes
        for node in ig.nodes:
            if incoming_interactions:
                for source, sink, data in ig.in_edges(node, data=True):
                    if not caig.has_edge(source, commit_author_mapping[sink]):
                        caig.add_edge(
                            source, commit_author_mapping[sink], amount=0
                        )
                    caig[source][commit_author_mapping[sink]
                                ]["amount"] += data["amount"]
            if outgoing_interactions:
                for source, sink, data in ig.out_edges(node, data=True):
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
        if self.__cached_interaction_graph:
            return self.__cached_interaction_graph

        self.__cached_interaction_graph = nx.DiGraph()
        interactions = gen_base_to_inter_commit_repo_pair_mapping(self.__report)
        commits = {
            commit for base, inters in interactions.items()
            for commit in [base, *inters.keys()]
        }

        def create_node_attrs(commit: CommitRepoPair) -> _BIGNodeAttrs:
            return {
                "commit": commit,
            }

        def create_edge_attrs(
            base: CommitRepoPair, inter: CommitRepoPair, amount: int
        ) -> _BIGEdgeAttrs:
            return {"amount": amount}

        self.__cached_interaction_graph.add_nodes_from([
            (commit, create_node_attrs(commit)) for commit in commits
        ])
        self.__cached_interaction_graph.add_edges_from([
            (base, inter, create_edge_attrs(base, inter, amount))
            for base, inters in interactions.items()
            for inter, amount in inters.items()
        ])

        return self.__cached_interaction_graph


class FileBasedInteractionGraph(InteractionGraph):

    def __init__(self, project_name: str, head_commit: str):
        super().__init__(project_name)
        self.__head_commit = head_commit
        self.__cached_interaction_graph: tp.Optional[nx.DiGraph] = None

    def _interaction_graph(self) -> nx.DiGraph:
        if self.__cached_interaction_graph:
            return self.__cached_interaction_graph

        repo = get_local_project_git(self.project_name)
        repo_name = get_primary_project_source(self.project_name).local
        repo_path = get_local_project_git_path(self.project_name)
        project_git = git["-C", str(repo_path)]
        churn_config = ChurnConfig.create_c_style_languages_config()

        self.__cached_interaction_graph = nx.DiGraph()

        file_pattern = re.compile(
            r"|".join(
                churn_config.get_extensions_repr(prefix=r"\.", suffix=r"$")
            )
        )
        file_names = project_git(
            "ls-tree", "--full-tree", "--name-only", "-r", "HEAD"
        ).split("\n")
        files: tp.List[Path] = [
            repo_path / path
            for path in file_names
            if file_pattern.search(path)
        ]
        for file in files:
            blame = repo.blame(
                str(file.relative_to(repo_path)),
                flags=pygit2.GIT_BLAME_IGNORE_WHITESPACE,
                newest_commit=self.__head_commit
            )
            commits: tp.Set[CommitRepoPair] = set()
            for hunk in blame:
                commits.add(
                    CommitRepoPair(str(hunk.final_commit_id), repo_name)
                )

            for commit in commits:
                self.__cached_interaction_graph.add_node(commit, commit=commit)
            for commit_a, commit_b in itertools.product(commits, repeat=2):
                if commit_a != commit_b:
                    if not self.__cached_interaction_graph.has_edge(
                        commit_a, commit_b
                    ):
                        self.__cached_interaction_graph.add_edge(
                            commit_a, commit_b, amount=0
                        )
                    self.__cached_interaction_graph[commit_a][commit_b]["amount"
                                                                       ] += 1

        return self.__cached_interaction_graph


def create_blame_interaction_graph(
    project_name: str, revision: str
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

        def match_revision(rev: str) -> bool:
            return True if rev == revision else False

        file_name_filter = match_revision

    report_files = get_processed_revisions_files(
        project_name, BlameReport, file_name_filter
    )
    if len(report_files) == 0:
        raise PlotDataEmpty(f"Found no BlameReport for project {project_name}")
    report = load_blame_report(report_files[0])
    return BlameInteractionGraph(project_name, report)


def create_file_based_interaction_graph(
    project_name: str, revision: str
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
