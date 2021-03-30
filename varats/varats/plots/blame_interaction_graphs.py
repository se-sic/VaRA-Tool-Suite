"""Module for BlameInteractionGraph plots."""

import typing as tp
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import plotly.offline as offply
from matplotlib import style
from pygit2 import Commit

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotArgMissing
from varats.plots.chord_plot_utils import make_chord_plot, make_arc_plot
from varats.plots.scatter_plot_utils import multivariate_grid
from varats.project.project_util import create_commit_lookup_for_project
from varats.utils.git_util import CommitRepoPair


def _get_commit_or_raise(
    commit_repo_pair: CommitRepoPair,
    commit_lookup: tp.Callable[[CommitRepoPair], tp.Optional[Commit]]
) -> Commit:
    commit = commit_lookup(commit_repo_pair)
    if not commit:
        raise KeyError(f"Could not find commit {commit_repo_pair}.")
    return commit


class CommitInteractionGraphPlot(Plot):
    """Creates a dot file for a commit interaction graph."""

    NAME = 'cig_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        # Nothing to do here.
        pass

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'svg'
    ) -> None:
        project_name = self.plot_kwargs["project"]
        revision = self.plot_kwargs.get("revision", None)
        if not revision:
            raise PlotArgMissing(f"'revision' was not specified.")
        cig = _get_interaction_graph(project_name, revision)

        from networkx.drawing.nx_agraph import write_dot
        write_dot(cig, self.plot_file_name("dot"))

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class CommitInteractionGraphChordPlot(Plot):
    """Chord plot for a commit interaction graph."""

    NAME = 'cig_chord_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        project_name = self.plot_kwargs["project"]
        revision = self.plot_kwargs.get("revision", None)
        if not revision:
            raise PlotArgMissing(f"'revision' was not specified.")

        commit_lookup = create_commit_lookup_for_project(project_name)

        interaction_graph = create_blame_interaction_graph(
            project_name, revision
        ).commit_interaction_graph

        def filter_nodes(node: CommitRepoPair) -> bool:
            commit = commit_lookup(node)
            if not commit:
                return False
            return datetime.utcfromtimestamp(commit.commit_time
                                            ) >= datetime(2015, 1, 1)

        nodes = [(node, {
            "info": interaction_graph.nodes[node]["commit_hash"]
        }) for node in interaction_graph.nodes if filter_nodes(node)]
        nodes.sort(
            key=lambda x:
            int(_get_commit_or_raise(x[0], commit_lookup).commit_time)
        )
        edges = [(
            source, sink, {
                "size": interaction_graph[source][sink]["amount"],
                "info":
                    f"{interaction_graph.nodes[source]['commit_hash']} "
                    f"--{{{interaction_graph[source][sink]['amount']}}}--> "
                    f"{interaction_graph.nodes[sink]['commit_hash']}"
            }
        )
                 for source, sink in interaction_graph.edges
                 if filter_nodes(source) and filter_nodes(sink)]

        figure = make_chord_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            # figure.write_image(self.plot_file_name("svg"))
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class CommitInteractionGraphArcPlot(Plot):
    """Arc plot for a commit interaction graph."""

    NAME = 'cig_arc_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        project_name = self.plot_kwargs["project"]
        revision = self.plot_kwargs.get("revision", None)
        if not revision:
            raise PlotArgMissing(f"'revision' was not specified.")

        commit_lookup = create_commit_lookup_for_project(project_name)

        interaction_graph = create_blame_interaction_graph(
            project_name, revision
        ).commit_interaction_graph

        def filter_nodes(node: CommitRepoPair) -> bool:
            commit = commit_lookup(node)
            if not commit:
                return False
            return datetime.utcfromtimestamp(commit.commit_time
                                            ) >= datetime(2015, 1, 1)

        nodes = [(
            node, {
                "info": interaction_graph.nodes[node]["commit_hash"],
                "size": interaction_graph.degree(node),
                "fill_color": interaction_graph.out_degree(node),
                "line_color": interaction_graph.in_degree(node)
            }
        ) for node in interaction_graph.nodes if filter_nodes(node)]
        nodes.sort(
            key=lambda x:
            int(_get_commit_or_raise(x[0], commit_lookup).commit_time),
            reverse=True
        )
        edges = [(
            source, sink, {
                "size": interaction_graph[source][sink]["amount"],
                "color": interaction_graph[source][sink]["amount"],
                "info":
                    f"{interaction_graph.nodes[source]['commit_hash']} "
                    f"--{{{interaction_graph[source][sink]['amount']}}}--> "
                    f"{interaction_graph.nodes[sink]['commit_hash']}"
            }
        )
                 for source, sink in interaction_graph.edges
                 if filter_nodes(source) and filter_nodes(sink)]

        figure = make_arc_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            # figure.write_image(self.plot_file_name("svg"))
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        raise NotImplementedError


class CommitInteractionGraphNodeDegreePlot(Plot):
    """
    Plot node degrees of a commit interaction graph.

    Additional arguments:
      - sort: criteria to sort the revisions [degree, time]
    """

    NAME = 'cig_node_degrees'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        sort = self.plot_kwargs.get("sort", "degree")

        if "project" not in self.plot_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.plot_kwargs:
                case_studies = [self.plot_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.plot_kwargs["project"]
                )

        style.use(self.style)
        fig, axes = plt.subplots(3, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        degree_axis = axes[0]
        out_degree_axis = axes[1]
        in_degree_axis = axes[2]

        fig.suptitle(f"Commit Interaction Graph - Node Degrees")
        degree_axis.set_ylabel("Degree")
        out_degree_axis.set_ylabel("Out-Degree")
        in_degree_axis.set_ylabel("In-Degree")
        xlabel = ""
        if sort == "time":
            xlabel = "Time (old to new)"
        elif sort == "degree":
            xlabel = "Commits"
        in_degree_axis.set_xlabel(xlabel)

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            cig = create_blame_interaction_graph(
                project_name, revision
            ).commit_interaction_graph
            commit_lookup = create_commit_lookup_for_project(project_name)

            def filter_nodes(node: CommitRepoPair) -> bool:
                return bool(commit_lookup(node))

            def commit_time(node: CommitRepoPair) -> datetime:
                return datetime.utcfromtimestamp(
                    _get_commit_or_raise(node, commit_lookup).commit_time
                )

            data = pd.DataFrame([{
                "commit_hash": node.commit_hash,
                "commit_time": commit_time(node),
                "node_degree": cig.degree(node),
                "node_out_degree": cig.out_degree(node),
                "node_in_degree": cig.in_degree(node),
            } for node in cig.nodes if filter_nodes(node)])
            data["node_degree"] = normalize(data["node_degree"])
            data["node_out_degree"] = normalize(data["node_out_degree"])
            data["node_in_degree"] = normalize(data["node_in_degree"])

            if sort == "time":
                data.sort_values(by="commit_time", inplace=True)

            node_degrees = data.loc[:, ["commit_hash", "node_degree"]]
            node_out_degrees = data.loc[:, ["commit_hash", "node_out_degree"]]
            node_in_degrees = data.loc[:, ["commit_hash", "node_in_degree"]]

            if sort == "degree":
                node_degrees.sort_values(by="node_degree", inplace=True)
                node_out_degrees.sort_values(by="node_out_degree", inplace=True)
                node_in_degrees.sort_values(by="node_in_degree", inplace=True)

            x = np.linspace(0, 1, len(data.index))
            degree_axis.plot(
                x, node_degrees["node_degree"].values, label=project_name
            )
            out_degree_axis.plot(x, node_out_degrees["node_out_degree"].values)
            in_degree_axis.plot(x, node_in_degrees["node_in_degree"].values)

        degree_axis.legend()


class CommitInteractionGraphNodeDegreeScatterPlot(Plot):
    """
    Plot node degrees of a commit interaction graph.

    Additional arguments:
      - sort: criteria to sort the revisions [degree, time]
    """

    NAME = 'cig_node_degrees_scatter'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        if "project" not in self.plot_kwargs:
            case_studies = get_loaded_paper_config().get_all_case_studies()
        else:
            if "plot_case_study" in self.plot_kwargs:
                case_studies = [self.plot_kwargs["plot_case_study"]]
            else:
                case_studies = get_loaded_paper_config().get_case_studies(
                    self.plot_kwargs["project"]
                )

        def normalize(values: pd.Series) -> pd.Series:
            max_value = values.max()
            min_value = values.min()
            return (values - min_value) / (max_value - min_value)

        degree_data: tp.List[pd.DataFrame] = []
        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            cig = create_blame_interaction_graph(
                project_name, revision
            ).commit_interaction_graph
            commit_lookup = create_commit_lookup_for_project(project_name)

            def filter_nodes(node: CommitRepoPair) -> bool:
                return bool(commit_lookup(node))

            def commit_time(node: CommitRepoPair) -> datetime:
                return datetime.utcfromtimestamp(
                    _get_commit_or_raise(node, commit_lookup).commit_time
                )

            data = pd.DataFrame([{
                "project": project_name,
                "commit_hash": node.commit_hash,
                "commit_time": commit_time(node),
                "node_degree": cig.degree(node),
                "node_out_degree": cig.out_degree(node),
                "node_in_degree": cig.in_degree(node),
            } for node in cig.nodes if filter_nodes(node)])
            data["node_degree"] = normalize(data["node_degree"])
            data["node_out_degree"] = normalize(data["node_out_degree"])
            data["node_in_degree"] = normalize(data["node_in_degree"])
            degree_data.append(data)

        multivariate_grid(
            "node_out_degree", "node_in_degree", "project",
            pd.concat(degree_data)
        )
