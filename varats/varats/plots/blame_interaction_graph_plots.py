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

from varats.data.reports.blame_interaction_graph import (
    create_blame_interaction_graph,
    CIGNodeAttrs,
    CIGEdgeAttrs,
    AIGNodeAttrs,
    CAIGNodeAttrs,
)
from varats.data.reports.blame_report import BlameReport
from varats.paper_mgmt.case_study import (
    newest_processed_revision_for_case_study,
)
from varats.paper_mgmt.paper_config import get_loaded_paper_config
from varats.plot.plot import Plot, PlotArgMissing, PlotDataEmpty
from varats.plots.chord_plot_utils import (
    make_chord_plot,
    make_arc_plot,
    NodeTy,
    ChordPlotNodeInfo,
    ChordPlotEdgeInfo,
    ArcPlotEdgeInfo,
    ArcPlotNodeInfo,
)
from varats.utils.git_util import (
    CommitRepoPair,
    create_commit_lookup_helper,
    UNCOMMITTED_COMMIT_HASH,
    FullCommitHash,
)


class CommitInteractionGraphPlot(Plot):
    """Creates a dot file for a commit interaction graph."""

    NAME = 'cig_plot'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        # Nothing to do here.
        pass

        # project_name = self.plot_kwargs["project"]
        # revision = self.plot_kwargs.get("revision", None)
        # if not revision:
        #     raise PlotArgMissing(f"'revision' was not specified.")
        # cig = _get_interaction_graph(project_name, revision).commit_interaction_graph
        # nx.draw_circular(cig)

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'svg'
    ) -> None:
        project_name = self.plot_kwargs["project"]
        revision = self.plot_kwargs.get("revision", None)
        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()
        nx.set_node_attributes(
            cig, {node: cig.nodes[node]["commit_hash"] for node in cig.nodes},
            "label"
        )

        from networkx.drawing.nx_agraph import write_dot
        write_dot(cig, self.plot_file_name("dot"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
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

        commit_lookup = create_commit_lookup_helper(project_name)

        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()

        def filter_nodes(node: CommitRepoPair) -> bool:
            if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                return False
            commit = commit_lookup(node)
            if not commit:
                return False
            return datetime.utcfromtimestamp(commit.commit_time
                                            ) >= datetime(2015, 1, 1)

        nodes: tp.List[tp.Tuple[NodeTy, ChordPlotNodeInfo]] = []
        for node in sorted(
            cig.nodes,
            key=lambda x: int(
                commit_lookup(tp.cast(CIGNodeAttrs, cig.nodes[x])["commit"]).
                commit_time
            )
        ):
            node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
            commit = node_attrs["commit"]
            if not filter_nodes(commit):
                continue
            nodes.append(
                (node, {
                    "info": commit.commit_hash.short_hash,
                    "color": 1,
                })
            )

        edges: tp.List[tp.Tuple[NodeTy, NodeTy, ChordPlotEdgeInfo]] = []
        for source, sink in cig.edges:
            edge_attrs = tp.cast(CIGEdgeAttrs, cig[source][sink])
            source_commit = tp.cast(CIGNodeAttrs, cig.nodes[source])["commit"]
            sink_commit = tp.cast(CIGNodeAttrs, cig.nodes[sink])["commit"]
            if not filter_nodes(source_commit) or not filter_nodes(sink_commit):
                continue
            edges.append((
                source, sink, {
                    "size": edge_attrs["amount"],
                    "color": 1,
                    "info":
                        f"{source_commit.commit_hash.short_hash} "
                        f"--{{{edge_attrs['amount']}}}--> "
                        f"{sink_commit.commit_hash.short_hash}"
                }
            ))

        figure = make_chord_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            # figure.write_image(self.plot_file_name("svg"))
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
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

        commit_lookup = create_commit_lookup_helper(project_name)

        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()

        def filter_nodes(node: CommitRepoPair) -> bool:
            if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                return False
            commit = commit_lookup(node)
            if not commit:
                return False
            return datetime.utcfromtimestamp(commit.commit_time
                                            ) >= datetime(2015, 1, 1)

        nodes: tp.List[tp.Tuple[NodeTy, ArcPlotNodeInfo]] = []
        for node in sorted(
            cig.nodes,
            key=lambda x: int(
                commit_lookup(tp.cast(CIGNodeAttrs, cig.nodes[x])["commit"]).
                commit_time
            )
        ):
            node_attrs = tp.cast(CIGNodeAttrs, cig.nodes[node])
            commit = node_attrs["commit"]
            if not filter_nodes(commit):
                continue
            nodes.append((
                node, {
                    "info": commit.commit_hash.short_hash,
                    "size": cig.degree(node),
                    "fill_color": cig.out_degree(node),
                    "line_color": cig.in_degree(node)
                }
            ))

        edges: tp.List[tp.Tuple[NodeTy, NodeTy, ArcPlotEdgeInfo]] = []
        for source, sink in cig.edges:
            edge_attrs = tp.cast(CIGEdgeAttrs, cig[source][sink])
            source_commit = tp.cast(CIGNodeAttrs, cig.nodes[source])["commit"]
            sink_commit = tp.cast(CIGNodeAttrs, cig.nodes[sink])["commit"]
            if not filter_nodes(source_commit) or not filter_nodes(sink_commit):
                continue
            edges.append((
                source, sink, {
                    "size": edge_attrs["amount"],
                    "color": edge_attrs["amount"],
                    "info":
                        f"{source_commit.commit_hash.short_hash} "
                        f"--{{{edge_attrs['amount']}}}--> "
                        f"{sink_commit.commit_hash.short_hash}"
                }
            ))

        figure = make_arc_plot(nodes, edges, "Commit Interaction Graph")

        if view_mode:
            figure.show()
        else:
            # figure.write_image(self.plot_file_name("svg"))
            offply.plot(figure, filename=self.plot_file_name("html"))

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
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

        case_study = self.plot_kwargs["plot_case_study"]

        style.use(self.style)
        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle(f"Commit Interaction Graph - Node Degrees")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Degree")
        xlabel = ""
        if sort == "time":
            xlabel = "Time (old to new)"
        elif sort == "degree":
            xlabel = "Commits"
        axes.set_xlabel(xlabel)

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

        cig = create_blame_interaction_graph(project_name, revision
                                            ).commit_interaction_graph()
        commit_lookup = create_commit_lookup_helper(project_name)

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

        # x = np.linspace(0, 1, len(data.index))
        axes.plot(node_degrees["node_degree"].values, label="degree")
        axes.plot(
            node_out_degrees["node_out_degree"].values, label="out_degree"
        )
        axes.plot(node_in_degrees["node_in_degree"].values, label="in_degree")

        axes.legend()

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class CommitInteractionGraphNodeDegreeOverviewPlot(Plot):
    """
    Plot node degrees of all commit interaction graphs in the current paper
    config.

    Additional arguments:
      - sort: criteria to sort the revisions [degree, time]
    """

    NAME = 'cig_node_degrees_overview'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        sort = self.plot_kwargs.get("sort", "degree")
        case_studies = get_loaded_paper_config().get_all_case_studies()

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

        def normalize(
            values: pd.Series,
            min_value: tp.Optional[float] = None,
            max_value: tp.Optional[float] = None
        ) -> pd.Series:
            if not min_value:
                min_value = values.min()
            if not max_value:
                max_value = values.max()
            # mypy cannot infer that min_value/max_value are never None here
            return (values -
                    min_value) / (max_value - min_value)  # type: ignore

        for case_study in case_studies:
            project_name = case_study.project_name
            revision = newest_processed_revision_for_case_study(
                case_study, BlameReport
            )
            if not revision:
                continue

            cig = create_blame_interaction_graph(project_name, revision
                                                ).commit_interaction_graph()
            commit_lookup = create_commit_lookup_helper(project_name)

            def filter_nodes(node: CommitRepoPair) -> bool:
                if node.commit_hash == UNCOMMITTED_COMMIT_HASH:
                    return False
                return bool(commit_lookup(node))

            def commit_time(node: CommitRepoPair) -> datetime:
                return datetime.utcfromtimestamp(
                    commit_lookup(node).commit_time
                )

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
            data_min = 0
            data_max = data["node_degree"].max()
            data["node_degree"] = normalize(
                data["node_degree"], min_value=data_min, max_value=data_max
            )
            data["node_out_degree"] = normalize(
                data["node_out_degree"], min_value=data_min, max_value=data_max
            )
            data["node_in_degree"] = normalize(
                data["node_in_degree"], min_value=data_min, max_value=data_max
            )

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

    def calc_missing_revisions(
        self, boundary_gradient: float
    ) -> tp.Set[FullCommitHash]:
        raise NotImplementedError


class AuthorInteractionGraphNodeDegreePlot(Plot):
    """Plot node degrees of a author interaction graph."""

    NAME = 'aig_node_degrees'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]

        style.use(self.style)
        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle(f"Author Interaction Graph - Node Degrees")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Degree")
        axes.set_xlabel("Authors")

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

        aig = create_blame_interaction_graph(project_name, revision
                                            ).author_interaction_graph()

        nodes: tp.List[tp.Dict[str, tp.Any]] = []
        for node in aig.nodes:
            node_attrs = tp.cast(AIGNodeAttrs, aig.nodes[node])
            author = node_attrs["author"]
            num_commits = node_attrs["num_commits"]
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
        raise NotImplementedError


class CommitAuthorInteractionGraphNodeDegreePlot(Plot):
    """Plot node degrees of commits in a commit-author interaction graph."""

    NAME = 'caig_node_degrees'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    def plot(self, view_mode: bool) -> None:
        case_study = self.plot_kwargs["plot_case_study"]

        style.use(self.style)
        fig, axes = plt.subplots(1, 1, sharey="all")
        fig.subplots_adjust(hspace=0.5)

        fig.suptitle(f"Commit-Author Interaction Graph - # Interacting Authors")
        axes.set_title(case_study.project_name)
        axes.set_ylabel("Authors")
        axes.set_xlabel("Commits")

        project_name = case_study.project_name
        revision = newest_processed_revision_for_case_study(
            case_study, BlameReport
        )
        if not revision:
            raise PlotDataEmpty()

        caig = create_blame_interaction_graph(project_name, revision
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
        raise NotImplementedError
