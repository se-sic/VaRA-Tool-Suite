"""Module for representing blame interaction data in a graph/network."""

import typing as tp

import networkx as nx

from varats.data.reports.blame_report import (
    BlameReport,
    gen_base_to_inter_commit_repo_pair_mapping,
    BlameReportDiff,
)


class BlameInteractionGraph():
    """Graph/Network built from blame interaction data."""

    def __init__(
        self, project_name: str, report: tp.Union[BlameReport, BlameReportDiff]
    ):
        self.__report = report
        self.__interaction_graph: tp.Optional[nx.DiGraph] = None
        self.__project_name = project_name

    def __build_interaction_graph(self) -> nx.DiGraph:
        interaction_graph = nx.DiGraph()
        interactions = gen_base_to_inter_commit_repo_pair_mapping(self.__report)
        commits = {
            commit for base, inters in interactions.items()
            for commit in [base, *inters.keys()]
        }
        interaction_graph.add_nodes_from([
            (commit, {
                "commit_hash": commit.commit_hash[:10],
            }) for commit in commits
        ])
        interaction_graph.add_edges_from([
            (base, inter, {
                "amount": amount
            })
            for base, inters in interactions.items()
            for inter, amount in inters.items()
        ])

        return interaction_graph

    @property
    def commit_interaction_graph(self) -> nx.DiGraph:
        """
        Return a digraph with commits as nodes and interactions as edges.

        The graph has the following attributes:
        Nodes:
          - commit_hash: commit hash of the commit represented by the node
        Edges:
          - amount: how often this interaction was found

        Returns:
            the commit interaction graph
        """
        if self.__interaction_graph is None:
            self.__interaction_graph = self.__build_interaction_graph()
        return self.__interaction_graph.copy(as_view=False)

    @property
    def author_interaction_graph(self) -> nx.Graph:
        # TODO
        pass
