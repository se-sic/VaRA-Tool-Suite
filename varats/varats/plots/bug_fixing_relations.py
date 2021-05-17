import logging
import typing as tp
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objs as gob
import pygit2

from varats.plot.plot import Plot, PlotDataEmpty
from varats.project.project_util import (
    get_project_cls_by_name,
    get_local_project_git,
)
from varats.provider.bug.bug import RawBug
from varats.provider.bug.bug_provider import BugProvider

LOG = logging.getLogger(__name__)


def _plot_chord_diagram_for_raw_bugs(
    project_name: str, bug_set: tp.FrozenSet[RawBug]
) -> gob.FigureWidget:
    """Creates a chord diagram representing relations between introducing/fixing
    commits for a given set of RawBugs."""
    project_repo = get_local_project_git(project_name)

    # maps commit hex -> node id
    map_commit_to_id: tp.Dict[str, int] = _map_commits_to_nodes(project_repo)
    commit_count = len(map_commit_to_id.keys())
    commit_type: tp.Dict[str, str] = {}

    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        commit_type[commit.hex] = 'default'

    # if less than 2 commits, no graph can be drawn!
    if commit_count < 2:
        raise PlotDataEmpty

    commit_coordinates = _compute_node_placement(commit_count)

    commit_distance_thresholds = [
        0,
        round(0.25 * commit_count),
        round(0.5 * commit_count),
        round(0.75 * commit_count), commit_count
    ]

    def _get_commit_interval(distance: float) -> int:
        """Get right interval for given commit distance using distance
        thresholds, interval indices are in [0,3] for 5 thresholds."""
        k = 0
        while commit_distance_thresholds[k] < distance:
            k += 1
        return k - 1

    edge_colors = ['#d4daff', '#84a9dd', '#5588c8', '#6d8acf']

    node_colors = {
        'fix': 'rgba(0, 177, 106, 1)',
        'introduction': 'rgba(240, 52, 52, 1)',
        'introducing fix': 'rgba(235, 149, 50, 1)',
        'head': 'rgba(142, 68, 173, 1)',
        'fixing head': 'rgba(142, 68, 173, 1)',
        'default': 'rgba(232, 236, 241, 1)'
    }

    # draw relations and preprocess commit types
    nodes = []
    lines = []
    for bug in bug_set:
        bug_fix = bug.fixing_commit
        fix_ind = map_commit_to_id[bug_fix]
        fix_coordinates = commit_coordinates[fix_ind]

        commit_type[bug_fix] = 'introducing fix' if commit_type[
            bug_fix] == 'introduction' else 'fix'

        for bug_introduction in bug.introducing_commits:
            intro_ind = map_commit_to_id[bug_introduction]
            intro_coordinates = commit_coordinates[intro_ind]

            commit_type[bug_introduction] = 'introducing fix' if commit_type[
                bug_introduction] == 'fix' else 'introduction'

            commit_dist = map_commit_to_id[bug_introduction] - map_commit_to_id[
                bug_fix]
            commit_interval = _get_commit_interval(commit_dist)
            color = edge_colors[commit_interval]

            lines.append(
                _create_line(fix_coordinates, intro_coordinates, color)
            )

    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        # draw commit nodes using preprocessed commit types
        commit_id = map_commit_to_id[commit.hex]

        if commit.hex == project_repo.head.target.hex:
            commit_type[commit.hex
                       ] = 'fixing head' if commit_type[commit.hex
                                                       ] == 'fix' else 'head'

        # set node data according to commit type
        node_size = 10 if commit_type[commit.hex] == 'head' or commit_type[
            commit.hex] == 'fixing head' else 8
        displayed_message = commit.message.partition('\n')[0]
        node_label = f'Type: {commit_type[commit.hex]}<br>' \
                     f'Hash: {commit.hex}<br>' \
                     f'Author: {commit.author.name}<br>' \
                     f'Date: {datetime.fromtimestamp(commit.commit_time)}<br>' \
                     f'Message: {displayed_message}'
        node_color = node_colors[commit_type[commit.hex]]

        node_scatter = _create_node(
            commit_coordinates[commit_id], node_color, node_label
        )

        nodes.append(node_scatter)

    data = nodes + lines
    layout = _create_layout(f'Bug fixing relations for {project_name}')
    return gob.FigureWidget(data=data, layout=layout)


def _create_line(start: np.array, end: np.array, color: str) -> gob.Scatter:
    dist = _get_distance(start, end)
    interval = _get_interval(dist)

    control_points = [
        start,
        np.true_divide(start, (__cp_parameters[interval])),
        np.true_divide(end, (__cp_parameters[interval])), end
    ]
    curve_points = _get_bezier_curve(control_points)

    return gob.Scatter(
        x=curve_points[:, 0],
        y=curve_points[:, 1],
        mode='lines',
        line=dict(color=color, shape='spline'),
        hoverinfo='none'
    )


def _create_node(coordinates: np.array, color: str, text: str) -> gob.Scatter:
    return gob.Scatter(
        x=[coordinates[0]],
        y=[coordinates[1]],
        mode='markers',
        name='',
        marker=dict(symbol='circle', size=8, color=color),
        text=text,
        hoverinfo='text'
    )


def _create_layout(title: str) -> gob.Layout:
    axis = dict(
        showline=False,
        zeroline=False,
        showgrid=False,
        showticklabels=False,
        title=''
    )  # hide the axis

    width = 900
    height = 900
    return gob.Layout(
        title=title,
        showlegend=False,
        autosize=False,
        width=width,
        height=height,
        xaxis=dict(axis),
        yaxis=dict(axis),
        hovermode='closest',
        clickmode='event',
        margin=dict(l=0, r=0, b=0, t=50),
        plot_bgcolor='rgba(0,0,0,0)'
    )


def _get_distance(p1: tp.List[float], p2: tp.List[float]) -> float:
    """Returns distance between two points."""
    return float(np.linalg.norm(np.array(p1) - np.array(p2)))


def _get_interval(distance: float) -> int:
    """Get right interval for given node distance using distance thresholds,
    interval indices are in [0,3] for 5 thresholds."""
    k = 0
    while __distance_thresholds[k] < distance:
        k += 1
    return k - 1


#defining some constants for diagram generation
__cp_parameters = [1.2, 1.5, 1.8, 2.1]
__distance_thresholds = [
    0,
    _get_distance([1, 0], 2 * [np.sqrt(2) / 2]),
    np.sqrt(2),
    _get_distance([1, 0], [-np.sqrt(2) / 2, np.sqrt(2) / 2]), 2.0
]


def _get_bezier_curve(ctrl_points: np.array, num_points: int = 5) -> np.array:
    """Implements bezier edges to display between commit nodes."""
    n = len(ctrl_points)

    def get_coordinate_on_curve(factor: float) -> np.array:
        points_cp = np.copy(ctrl_points)
        for r in range(1, n):
            points_cp[:n - r, :] = (
                1 - factor
            ) * points_cp[:n - r, :] + factor * points_cp[1:n - r + 1, :]
        return np.array(points_cp[0, :])

    point_space = np.linspace(0, 1, num_points)
    return np.array([
        get_coordinate_on_curve(point_space[k]) for k in range(num_points)
    ])


def _compute_node_placement(commit_count: int) -> tp.List[np.array]:
    """Compute unit circle coordinates for each commit; move unit circle such
    that HEAD is on top."""
    # use commit_count + 1 since first and last coordinates are equal
    theta_vals = np.linspace(-3 * np.pi / 2, np.pi / 2, commit_count + 1)
    commit_coordinates: tp.List[np.array] = list()
    for theta in theta_vals:
        commit_coordinates.append(np.array([np.cos(theta), np.sin(theta)]))
    return commit_coordinates


def _map_commits_to_nodes(project_repo: pygit2.Repository) -> tp.Dict[str, int]:
    """Maps commit hex -> node id."""
    commits_to_nodes_map: tp.Dict[str, int] = {}
    commit_count = 0
    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        # node ids are sorted by time
        commits_to_nodes_map[commit.hex] = commit_count
        commit_count += 1
    return commits_to_nodes_map


class BugFixingRelationPlot(Plot):
    """Plot showing which commit fixed a bug introduced by which commit."""

    NAME = 'bug_relation_graph'

    def __init__(self, **kwargs: tp.Any) -> None:
        super().__init__(self.NAME, **kwargs)

    @staticmethod
    def supports_stage_separation() -> bool:
        return False

    def plot(self, view_mode: bool) -> None:
        """Plots bug plot for the whole project."""
        project_name = self.plot_kwargs['project']

        self.__szz_tool = self.plot_kwargs.get('szz_tool', 'provider')

        if self.__szz_tool == 'provider':
            bug_provider = BugProvider.get_provider_for_project(
                get_project_cls_by_name(project_name)
            )
            raw_bugs = bug_provider.find_all_raw_bugs()
        elif self.__szz_tool == 'szz_unleashed':
            pass
        else:
            raise PlotDataEmpty

        self.__figure = _plot_chord_diagram_for_raw_bugs(project_name, raw_bugs)

    def show(self) -> None:
        """Show the finished plot."""
        try:
            self.plot(True)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return
        self.__figure.show()

    def save(
        self, path: tp.Optional[Path] = None, filetype: str = 'html'
    ) -> None:
        """
        Save the current plot to a file. Supports html, json and image
        filetypes.

        Args:
            path: The path where the file is stored (excluding the file name).
            filetype: The file type of the plot.
        """
        try:
            self.plot(False)
        except PlotDataEmpty:
            LOG.warning(f"No data for project {self.plot_kwargs['project']}.")
            return

        if path is None:
            plot_dir = Path(self.plot_kwargs["plot_dir"])
        else:
            plot_dir = path

        if filetype == 'html':
            self.__figure.write_html(self.plot_file_name(filetype))
        elif filetype == 'json':
            self.__figure.write_json(self.plot_file_name(filetype))
        else:
            self.__figure.write_image(self.plot_file_name(filetype))

    def plot_file_name(self, filetype: str) -> str:
        """
        Get the file name for this plot; will be stored to when calling save.

        Args:
            filetype: the file type for the plot

        Returns:
            the file name the plot will be stored to
        """
        plot_indent = ''
        if 'project' in self.plot_kwargs:
            plot_indent = f"{self.plot_kwargs['project']}_"

        return f"{plot_indent}{self.name}_{self.__szz_tool}.{filetype}"

    def calc_missing_revisions(self, boundary_gradient: float) -> tp.Set[str]:
        """Plot always includes all revisions."""
        return set()
