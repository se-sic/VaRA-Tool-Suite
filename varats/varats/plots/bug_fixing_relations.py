import logging
import typing as tp
from datetime import datetime
from pathlib import Path

import numpy as np
import plotly.graph_objs as gob
import pygit2

from varats.data.reports.szz_report import SZZUnleashedReport
from varats.plot.plot import Plot, PlotDataEmpty
from varats.project.project_util import (
    get_project_cls_by_name,
    get_local_project_git,
)
from varats.provider.bug.bug import RawBug
from varats.provider.bug.bug_provider import BugProvider
from varats.revision.revisions import get_processed_revisions_files

LOG = logging.getLogger(__name__)


def _plot_chord_diagram_for_raw_bugs(
    project_name: str, bug_set: tp.FrozenSet[RawBug]
) -> gob.FigureWidget:
    """Creates a chord diagram representing relations between introducing/fixing
    commits for a given set of RawBugs."""
    project_repo = get_local_project_git(project_name)

    # maps commit hex -> node id
    map_commit_to_id: tp.Dict[str, int] = _map_commits_to_nodes(project_repo)
    commit_type: tp.Dict[str, str] = {}
    commit_count = len(map_commit_to_id.keys())

    for commit in project_repo.walk(
        project_repo.head.target.hex, pygit2.GIT_SORT_TIME
    ):
        commit_type[commit.hex] = 'default'

    # if less than 2 commits, no graph can be drawn!
    if commit_count < 2:
        raise PlotDataEmpty

    commit_coordinates = _compute_node_placement(commit_count)

    # draw relations and preprocess commit types
    lines = _generate_line_data(
        bug_set, commit_coordinates, map_commit_to_id, commit_type
    )
    nodes = _generate_node_data(
        project_repo, commit_coordinates, map_commit_to_id, commit_type
    )

    data = nodes + lines
    layout = _create_layout(f'Bug fixing relations for {project_name}')
    return gob.FigureWidget(data=data, layout=layout)


def _bug_data_diff_plot(
    project_name: str, bugs_a: tp.FrozenSet[RawBug],
    bugs_b: tp.FrozenSet[RawBug]
) -> gob.Figure:
    project_repo = get_local_project_git(project_name)

    commits_to_nodes_map = _map_commits_to_nodes(project_repo)
    commit_count = len(commits_to_nodes_map.keys())
    commit_coordinates = _compute_node_placement(commit_count)

    init_color = 'rgba(207, 0, 15, 1)'
    node_color_default = 'rgba(0,51,181, 0.85)'
    node_color_a = "#ff0000"
    node_color_b = "#00ff00"
    edge_color_a = "#ff5555"
    edge_color_b = "#55ff55"

    lines: tp.List[gob.Scatter] = []
    nodes: tp.List[gob.Scatter] = []
    for revision, diff_a, diff_b in _diff_raw_bugs(bugs_a, bugs_b):
        bug_fix = revision
        fix_ind = commits_to_nodes_map[bug_fix]
        fix_coordinates = commit_coordinates[fix_ind]

        if diff_a:
            for introducer in diff_a:
                lines.append(
                    _create_line(
                        fix_coordinates,
                        commit_coordinates[commits_to_nodes_map[introducer]],
                        edge_color_a, f'introduced by {introducer}'
                    )
                )
        if diff_b:
            for introducer in diff_b:
                lines.append(
                    _create_line(
                        fix_coordinates,
                        commit_coordinates[commits_to_nodes_map[introducer]],
                        edge_color_b, f'introduced by {introducer}'
                    )
                )

        node_color = node_color_default
        if diff_a is None and diff_b is not None:
            node_color = node_color_b
        if diff_b is None and diff_a is not None:
            node_color = node_color_a
        if diff_a is None and diff_b is None:
            node_color = "#ffff00"

        nodes.append(
            _create_node(fix_coordinates, node_color, f'bug fix: {bug_fix}')
        )

    init = _create_node(commit_coordinates, init_color, "HEAD")
    data = lines + nodes + [init]
    layout = _create_layout(f'SZZ diff {project_name}')
    return gob.Figure(data=data, layout=layout)


KeyT = tp.TypeVar("KeyT")
ValueT = tp.TypeVar("ValueT")


def _generate_line_data(
    bug_set: tp.FrozenSet[RawBug], commit_coordinates: tp.List[np.array],
    map_commit_to_id: tp.Dict[str, int], commit_type: tp.Dict[str, str]
) -> tp.List[gob.Scatter]:
    lines = []

    for bug in bug_set:
        bug_fix = bug.fixing_commit
        fix_id = map_commit_to_id[bug_fix]
        fix_coordinates = commit_coordinates[fix_id]

        commit_type[bug_fix] = 'introducing fix' if commit_type[
            bug_fix] == 'introduction' else 'fix'

        for bug_introduction in bug.introducing_commits:
            intro_ind = map_commit_to_id[bug_introduction]
            intro_coordinates = commit_coordinates[intro_ind]

            commit_type[bug_introduction] = 'introducing fix' if commit_type[
                bug_introduction] == 'fix' else 'introduction'

            commit_dist = map_commit_to_id[bug_introduction] - map_commit_to_id[
                bug_fix]
            commit_interval = _get_commit_interval(
                commit_dist, len(map_commit_to_id.keys())
            )
            color = __EDGE_COLORS[commit_interval]

            lines.append(
                _create_line(fix_coordinates, intro_coordinates, color)
            )

    return lines


def _generate_node_data(
    project_repo: pygit2.Repository, commit_coordinates: tp.List[np.array],
    map_commit_to_id: tp.Dict[str, int], commit_type: tp.Dict[str, str]
) -> tp.List[gob.Scatter]:
    nodes = []

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
        node_color = __NODE_COLORS[commit_type[commit.hex]]

        node_scatter = _create_node(
            commit_coordinates[commit_id], node_color, node_label
        )

        nodes.append(node_scatter)

    return nodes


def _create_line(start: np.array, end: np.array, color: str) -> gob.Scatter:
    dist = _get_distance(start, end)
    interval = _get_interval(dist)

    control_points = [
        start,
        np.true_divide(start, (__CP_PARAMETERS[interval])),
        np.true_divide(end, (__CP_PARAMETERS[interval])), end
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
    while __DISTANCE_THRESHOLDS[k] < distance:
        k += 1
    return k - 1


#defining some constants for diagram generation
__CP_PARAMETERS = [1.2, 1.5, 1.8, 2.1]
__DISTANCE_THRESHOLDS = [
    0,
    _get_distance([1, 0], 2 * [np.sqrt(2) / 2]),
    np.sqrt(2),
    _get_distance([1, 0], [-np.sqrt(2) / 2, np.sqrt(2) / 2]), 2.0
]
__EDGE_COLORS = ['#d4daff', '#84a9dd', '#5588c8', '#6d8acf']

__NODE_COLORS = {
    'fix': 'rgba(0, 177, 106, 1)',
    'introduction': 'rgba(240, 52, 52, 1)',
    'introducing fix': 'rgba(235, 149, 50, 1)',
    'head': 'rgba(142, 68, 173, 1)',
    'fixing head': 'rgba(142, 68, 173, 1)',
    'default': 'rgba(232, 236, 241, 1)'
}


def _get_commit_interval(distance: float, commit_count: int) -> int:
    """Get right interval for given commit distance using distance thresholds,
    interval indices are in [0,3] for 5 thresholds."""
    commit_distance_thresholds = [
        0,
        round(0.25 * commit_count),
        round(0.5 * commit_count),
        round(0.75 * commit_count), commit_count
    ]

    k = 0
    while commit_distance_thresholds[k] < distance:
        k += 1
    return k - 1


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


def _diff_raw_bugs(
    bugs_a: tp.FrozenSet[RawBug], bugs_b: tp.FrozenSet[RawBug]
) -> tp.Generator[tp.Tuple[str, tp.Optional[tp.FrozenSet[str]],
                           tp.Optional[tp.FrozenSet[str]]], None, None]:
    for fixing_commit, introducers_a, introducers_b in _zip_dicts({
        bug.fixing_commit: bug.introducing_commits for bug in bugs_a
    }, {bug.fixing_commit: bug.introducing_commits for bug in bugs_b}):
        diff_a: tp.Optional[tp.FrozenSet[str]] = None
        diff_b: tp.Optional[tp.FrozenSet[str]] = None
        if introducers_a:
            diff_a = introducers_a
            if introducers_b:
                diff_a = introducers_a.difference(introducers_b)
        if introducers_b:
            diff_b = introducers_b
            if introducers_a:
                diff_b = introducers_b.difference(introducers_a)

        yield fixing_commit, diff_a, diff_b


def _zip_dicts(
    a: tp.Dict[KeyT, ValueT], b: tp.Dict[KeyT, ValueT]
) -> tp.Generator[tp.Tuple[KeyT, tp.Optional[ValueT], tp.Optional[ValueT]],
                  None, None]:
    for i in a.keys() | b.keys():
        yield i, a.get(i, None), b.get(i, None)


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

        self.__szz_tool = self.plot_kwargs.get('szz_tool', 'pydriller')

        bug_provider = BugProvider.get_provider_for_project(
            get_project_cls_by_name(project_name)
        )
        pydriller_bugs = bug_provider.find_all_raw_bugs()

        # reports = get_processed_revisions_files(
        #     project_name, SZZUnleashedReport
        # )
        # szzunleashed_bugs = SZZUnleashedReport(reports[0]).get_all_raw_bugs()

        if self.__szz_tool == 'pydriller':
            self.__figure = _plot_chord_diagram_for_raw_bugs(
                project_name, pydriller_bugs
            )
        elif self.__szz_tool == 'szz_unleashed':
            pass
            # self.__figure = _plot_chord_diagram_for_raw_bugs(
            #     project_name, szzunleashed_bugs
            # )
        elif self.__szz_tool == 'diff':
            pass
            # self.__figure = _bug_data_diff_plot(
            #     project_name, pydriller_bugs, szzunleashed_bugs
            # )
        else:
            raise PlotDataEmpty

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
