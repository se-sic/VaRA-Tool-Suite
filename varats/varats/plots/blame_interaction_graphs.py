"""Module for BlameInteractionGraph plots."""

import typing as tp
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.offline as offply
from matplotlib import style

from varats.data.reports.blame_interaction_graph import BlameInteractionGraph
from varats.data.reports.blame_report import BlameReport
from varats.jupyterhelper.file import load_blame_report
from varats.plot.plot import Plot, PlotDataEmpty, PlotArgMissing
from varats.plots.chord_plot_utils import make_chord_plot
from varats.project.project_util import create_commit_lookup_for_project
from varats.revision.revisions import get_processed_revisions_files
from varats.utils.git_util import CommitRepoPair


def _get_interaction_graph(
    project_name: str, revision: str
) -> BlameInteractionGraph:
    """Create a blame interaction graph for a certain project revision."""
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

        interaction_graph = _get_interaction_graph(
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
        nodes.sort(key=lambda x: commit_lookup(x[0]).commit_time)
        edges = [(
            source, sink, {
                "size": interaction_graph[source][sink]["amount"],
                "info":
                    f"{interaction_graph.nodes[source]['commit_hash']} "
                    f"-> {interaction_graph.nodes[sink]['commit_hash']}"
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
    pass


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
        project_name = self.plot_kwargs["project"]
        revision = self.plot_kwargs.get("revision", None)
        sort = self.plot_kwargs.get("sort", "degree")

        if not revision:
            raise PlotArgMissing(f"'revision' was not specified.")

        cig = _get_interaction_graph(
            project_name, revision
        ).commit_interaction_graph
        commit_lookup = create_commit_lookup_for_project(project_name)

        def filter_nodes(node: CommitRepoPair) -> bool:
            return bool(commit_lookup(node))

        def commit_time(node: CommitRepoPair) -> datetime:
            return datetime.utcfromtimestamp(commit_lookup(node).commit_time)

        degree_data = pd.DataFrame([{
            "commit_hash": node.commit_hash,
            "commit_time": commit_time(node),
            "node_degree": cig.degree(node),
            "node_out_degree": cig.out_degree(node),
            "node_in_degree": cig.in_degree(node),
        } for node in cig.nodes if filter_nodes(node)])

        if sort == "time":
            degree_data.sort_values(by="commit_time", inplace=True)

        node_degrees = degree_data.loc[:, ["commit_hash", "node_degree"]]
        node_out_degrees = degree_data.loc[:,
                                           ["commit_hash", "node_out_degree"]]
        node_in_degrees = degree_data.loc[:, ["commit_hash", "node_in_degree"]]

        if sort == "degree":
            node_degrees.sort_values(by="node_degree", inplace=True)
            node_out_degrees.sort_values(by="node_out_degree", inplace=True)
            node_in_degrees.sort_values(by="node_in_degree", inplace=True)

        style.use(self.style)
        fig, axes = plt.subplots(3, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        degree_axis = axes[0]
        out_degree_axis = axes[1]
        in_degree_axis = axes[2]

        fig.suptitle(
            f"Commit Interaction Graph - Node Degrees\n"
            f"{project_name} - {revision}"
        )
        degree_axis.set_ylabel("Degree")
        out_degree_axis.set_ylabel("Out-Degree")
        in_degree_axis.set_ylabel("In-Degree")
        xlabel = ""
        if sort == "time":
            xlabel = "Time (old to new)"
        elif sort == "degree":
            xlabel = "Commits"
        in_degree_axis.set_xlabel(xlabel)

        degree_axis.plot(node_degrees["node_degree"].values)
        out_degree_axis.plot(node_out_degrees["node_out_degree"].values)
        in_degree_axis.plot(node_in_degrees["node_in_degree"].values)
