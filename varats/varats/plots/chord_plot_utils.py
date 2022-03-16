"""
Utility module for creating chord plots with plotly.

Much of the code is adapted from here: https://plotly.com/python/v3/filled-
chord-diagram/
"""
import sys
import typing as tp
from collections import defaultdict
from itertools import accumulate

import numpy as np
import numpy.typing as npt
import plotly.graph_objs as go
from plotly import colors

if sys.version_info <= (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

FloatArray = npt.NDArray[np.float64]
PointTy = FloatArray


def _ribbon_control_points(
    left_arc: tp.Tuple[float, float], right_arc: tp.Tuple[float, float],
    radius: float
) -> tp.Tuple[tp.List[FloatArray], tp.List[FloatArray]]:
    return ([
        _angular_to_cartesian((1, left_arc[0])),
        _angular_to_cartesian((radius, (left_arc[0] + right_arc[0]) / 2)),
        _angular_to_cartesian((1, right_arc[0]))
    ], [
        _angular_to_cartesian((1, left_arc[1])),
        _angular_to_cartesian((radius, (left_arc[1] + right_arc[0]) / 2)),
        _angular_to_cartesian((1, right_arc[1]))
    ])


def _angular_to_cartesian(angular: npt.ArrayLike) -> FloatArray:
    """Convert angular coordinates to cartesian."""
    angular = np.asarray(angular)
    return np.array([
        angular[0] * np.cos(angular[1]), angular[0] * np.sin(angular[1])
    ])


def _make_equilateral_triangle(
    point0: FloatArray, point2: FloatArray
) -> FloatArray:
    """Given two points p0 and p2, finds a point p1 such that p0p1p2 forms an
    equilateral triangle."""
    if len(point0) != 2 and len(point2) != 2:
        raise ValueError('p0 and p2 must have exactly 2 elements.')
    p0p2 = point2 - point0
    point1 = 0.5 * (point0 + point2) + 0.5 * np.asarray(
        [-p0p2[1], p0p2[0]]
    ) * np.sqrt(3) * np.linalg.norm(p0p2)
    return np.asarray(point1)


def _make_bezier_curve(control_points: FloatArray,
                       num_points: int) -> tp.List[FloatArray]:
    """Evaluate nr equally spaced points on a bezier curve defined by the given
    control points."""
    num_control_points = control_points.shape[0]
    num_points = max(0, num_points)
    distances = np.linspace(0, 1, num_points)
    points = []
    # For each parameter t[i] evaluate a point on the Bezier curve with the
    # de Casteljau algorithm.
    for i in range(num_points):
        control_points_copy = np.copy(control_points)  # type: ignore
        for ctrl_idx in range(1, num_control_points):
            control_points_copy[:num_control_points - ctrl_idx, :] = (
                (1 - distances[i]) *
                control_points_copy[:num_control_points - ctrl_idx, :] +
                distances[i] *
                control_points_copy[1:num_control_points - ctrl_idx + 1, :]
            )
        points.append(control_points_copy[0, :])
    return points


def _make_arc(point_a: FloatArray, point_b: FloatArray,
              num_points: int) -> tp.List[FloatArray]:
    """
    Make an arc (half-circle) with the given end points.

    Args:
        point_a: left end-point
        point_b: right end-point
        num_points: number of points to evaluate on the arc

    Returns:
        a list of points on the arc
    """
    center = (point_a + point_b) / 2
    point = point_a - center
    theta = np.pi / (num_points - 1)
    rot_mat: FloatArray = np.array([[np.cos(theta), -np.sin(theta)],
                                    [np.sin(theta),
                                     np.cos(theta)]])

    def rotation(vector: FloatArray, _: FloatArray) -> FloatArray:
        return tp.cast(FloatArray, np.dot(rot_mat, vector))

    points: tp.List[FloatArray] = list(
        accumulate([point for _ in range(num_points)], rotation)
    )
    return [center + p for p in points]


def _modulo_ab(x: float, a: float, b: float) -> float:
    """Map a real number onto the interval [a, b)."""
    if a >= b:
        raise ValueError("Incorrect interval ends.")
    y = (x - a) % (b - a)
    return y + b if y < 0 else y + a


def _is_between_zero_and_2pi(x: float) -> bool:
    return 0 <= x < float(2 * np.pi + 0.00001)


def _calculate_ideogram_lengths(
    sizes: FloatArray, gap: float = 0.005 * 2 * np.pi
) -> FloatArray:
    """
    Calculate the lengths for the ideograms.

    Args:
        sizes: sizes of the ideograms relative to each other
        gap: the gap between ideograms; by default 0.5% of a unit circle

    Returns:
        lengths of the ideograms on the unit circle
    """
    return np.asarray(
        2 * np.pi * np.asarray(sizes) / sum(sizes) - gap * np.ones(len(sizes))
    )


def _calculate_ideogram_ends(
    lengths: FloatArray, gap: float = 0.005 * 2 * np.pi
) -> FloatArray:
    """
    Calculate the ends of the ideograms as azimuths.

    Args:
        lengths: lengths of the ideograms
        gap: gap between the ideograms

    Returns:
        ends for the ideograms as azimuths
    """
    ideogram_ends: tp.List[tp.Tuple[float, float]] = []
    left = 0.0
    for length in lengths:
        right = left + length
        ideogram_ends.append((left, right))
        left = right + gap
    return np.asarray(ideogram_ends)


def _make_ideogram_arc(
    radius: float,
    ends: tp.Tuple[float, float],
    num_points: int = 50
) -> tp.List[FloatArray]:
    """
    Create a set of points defining an ideogram arc.

    Args:
        radius: the circle radius
        ends: ends of the arc
        num_points: number of points on the arc to evaluate

    Returns:
        a list of points defining the ideogram arc
    """
    if not _is_between_zero_and_2pi(ends[0]
                                   ) or not _is_between_zero_and_2pi(ends[1]):
        ends = (
            _modulo_ab(ends[0], 0,
                       2 * np.pi), _modulo_ab(ends[1], 0, 2 * np.pi)
        )
    length = (ends[1] - ends[0]) % 2 * np.pi
    num_points = 5 if length <= np.pi / 4 else int(num_points * length / np.pi)

    if ends[0] <= ends[1]:
        theta = np.linspace(ends[0], ends[1], num_points)
    else:
        ends = (
            _modulo_ab(ends[0], -np.pi,
                       np.pi), _modulo_ab(ends[1], -np.pi, np.pi)
        )
        theta = np.linspace(ends[0], ends[1], num_points)
    points = zip([radius] * num_points, theta)
    return [_angular_to_cartesian(point) for point in points]


def _calculate_ribbon_ends(
    node_size: float, ideogram_ends: tp.Tuple[float, float],
    ribbon_sizes: FloatArray
) -> tp.List[tp.Tuple[float, float]]:
    ideogram_length = ideogram_ends[1] - ideogram_ends[0]
    lengths = [
        ideogram_length * ribbon_size / node_size
        for ribbon_size in ribbon_sizes
    ]
    ribbon_ends: tp.List[tp.Tuple[float, float]] = []
    left = ideogram_ends[0]
    for length in lengths:
        right = left + length
        ribbon_ends.append((left, right))
        left = right
    return ribbon_ends


def _make_ribbon_arc(theta0: float, theta1: float) -> str:
    if _is_between_zero_and_2pi(theta0) and _is_between_zero_and_2pi(theta1):
        if theta0 < theta1:
            theta0 = _modulo_ab(theta0, -np.pi, np.pi)
            theta1 = _modulo_ab(theta1, -np.pi, np.pi)
            if theta0 * theta1 > 0:
                raise ValueError('incorrect angle coordinates for ribbon')

        num_points = int(40 * (theta0 - theta1) / np.pi)
        if num_points <= 2:
            num_points = 3
        theta = np.linspace(theta0, theta1, num_points)
        pts = np.exp(1j * theta)  # points on arc in polar complex form

        string_arc = ''
        for k in range(len(theta)):
            string_arc += 'L ' + str(pts.real[k]
                                    ) + ', ' + str(pts.imag[k]) + ' '
        return string_arc

    raise ValueError(
        "The angle coordinates for an arc side of a ribbon "
        "must be in [0, 2*pi]"
    )


def _make_layout(title: str, plot_size: int) -> go.Layout:
    axis = {
        "showline": False,
        "zeroline": False,
        "showgrid": False,
        "showticklabels": False,
        "title": ""
    }

    return go.Layout(
        title=title,
        xaxis=dict(axis),
        yaxis=dict(axis),
        showlegend=False,
        width=plot_size * 2,
        height=plot_size,
        margin=dict(t=25, b=25, l=25, r=25),
        hovermode='closest'
    )


ColorScaleTy = tp.List[tp.List[tp.Union[str, float]]]


def get_color_at(colorscale: ColorScaleTy, offset: float) -> str:
    """
    Plotly continuous colorscales assign colors to the range [0, 1]. This
    function computes the intermediate color for any value in that range.

    Args:
        colorscale:
            a plotly continuous colorscale defined with RGB string colors
        offset: value in the range [0, 1]
    Returns:
        color in rgb string format
    """
    if len(colorscale) < 1:
        raise ValueError("colorscale must have at least one color")

    if offset <= 0 or len(colorscale) == 1:
        return str(colors.convert_colors_to_same_type(colorscale[0][1])[0][0])
    if offset >= 1:
        return str(colors.convert_colors_to_same_type(colorscale[-1][1])[0][0])

    low_color = high_color = ""
    for cutoff, color in colorscale:
        if offset > float(cutoff):
            low_cutoff, low_color = float(cutoff), str(color)
        else:
            high_cutoff, high_color = float(cutoff), str(color)
            break

    low_color = colors.convert_colors_to_same_type(low_color)[0][0]
    high_color = colors.convert_colors_to_same_type(high_color)[0][0]

    # noinspection PyUnboundLocalVariable
    return str(
        colors.find_intermediate_color(
            lowcolor=low_color,
            highcolor=high_color,
            intermed=((offset - low_cutoff) / (high_cutoff - low_cutoff)),
            colortype="rgb"
        )
    )


def add_alpha_channel(rgb_color: str, alpha: float) -> str:
    """
    Add an alpha channel to a rgb color string.

    Test:
    >>> add_alpha_channel("rgb(0.0 ,0.0 ,0.0)", 0.0)
    'rgba(0.0, 0.0, 0.0, 0.0)'
    >>> add_alpha_channel("rgb(0.0 ,0.0 ,0.0)", 0.7)
    'rgba(0.0, 0.0, 0.0, 0.7)'
    """
    red, green, blue = colors.unlabel_rgb(rgb_color)
    return f"rgba({red}, {green}, {blue}, {alpha})"


NodeTy = str


class ChordPlotNodeInfo(TypedDict):
    color: int
    info: str


class ChordPlotEdgeInfo(TypedDict):
    color: int
    info: str
    size: int


def _calculate_ideogram_data(
    node_sizes: tp.List[float]
) -> tp.Tuple[FloatArray, tp.List[str]]:
    gap = 2 * np.pi * 0.000
    ideogram_lengths = _calculate_ideogram_lengths(np.asarray(node_sizes), gap)
    ideogram_ends = _calculate_ideogram_ends(ideogram_lengths, gap)
    ideogram_colors = [
        get_color_at(colors.PLOTLY_SCALES["RdBu"], idx / len(ideogram_ends))
        for idx, ends in enumerate(ideogram_ends)
    ]
    return ideogram_ends, ideogram_colors


def _create_ideograms(
    nodes: tp.List[tp.Tuple[NodeTy, ChordPlotNodeInfo]],
    ideogram_ends: FloatArray, ideogram_colors: tp.List[str]
) -> tp.List[go.Scatter]:
    ideogram_info: tp.List[go.Scatter] = []
    for idx, ends in enumerate(ideogram_ends):
        outer_arc_points = _make_ideogram_arc(1.1, ends)
        inner_arc_points = _make_ideogram_arc(1.0, ends)

        points: tp.List[FloatArray] = []
        points.extend(outer_arc_points)
        points.extend(inner_arc_points[::-1])
        points.append(outer_arc_points[0])
        x, y = zip(*points)

        ideogram_info.append(
            go.Scatter(
                x=x,
                y=y,
                mode='lines',
                line=dict(color='rgb(50,50,50)', width=1),
                fill="toself",
                fillcolor=ideogram_colors[idx],
                text=nodes[idx][1].get("info", ""),
                hoverinfo="text"
            )
        )
    return ideogram_info


def _calculate_ribbon_data(
    nodes: tp.List[tp.Tuple[NodeTy, ChordPlotNodeInfo]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy,
                            ChordPlotEdgeInfo]], node_sizes: tp.List[float],
    ideogram_ends: FloatArray, ideogram_colors: tp.List[str]
) -> tp.Tuple[tp.Dict[int, tp.List[tp.Tuple[float, float]]], tp.Dict[int, str]]:
    incoming_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    outgoing_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    # group the edges by node
    for idx, (source, sink, _) in sorted(
        enumerate(edges), key=lambda x: float(x[1][2]["size"]), reverse=True
    ):
        outgoing_edges[source].append(idx)
        incoming_edges[sink].append(idx)

    ribbon_bounds: tp.Dict[int, tp.List[tp.Tuple[float,
                                                 float]]] = defaultdict(list)
    ribbon_colors: tp.Dict[int, str] = {}
    for node_idx, (node, _) in enumerate(nodes):
        node_edges: tp.List[int] = []
        node_edge_sizes: tp.List[float] = []
        for edge_idx in outgoing_edges[node]:
            node_edges.append(edge_idx)
            node_edge_sizes.append(edges[edge_idx][2].get("size", 1))
            ribbon_colors[edge_idx] = add_alpha_channel(
                ideogram_colors[node_idx], 0.75
            )
        for edge_idx in incoming_edges[node]:
            node_edges.append(edge_idx)
            node_edge_sizes.append(edges[edge_idx][2].get("size", 1))
        ribbon_ends = _calculate_ribbon_ends(
            node_sizes[node_idx], ideogram_ends[node_idx],
            np.asarray(node_edge_sizes)
        )
        for edge_idx, ribbon_end in zip(node_edges, ribbon_ends):
            ribbon_bounds[edge_idx].append(ribbon_end)

    return ribbon_bounds, ribbon_colors


def _create_ribbons(
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, ChordPlotEdgeInfo]],
    ribbon_bounds: tp.Dict[int, tp.List[tp.Tuple[float, float]]],
    ribbon_colors: tp.Dict[int, str]
) -> tp.List[go.Scatter]:
    ribbon_info: tp.List[go.scatter] = []
    for idx, ribbon_ends in ribbon_bounds.items():
        left_arc = ribbon_ends[0]
        right_arc = ribbon_ends[1]
        radius = 0.2
        num_points = 25
        control_points_left, control_points_right = _ribbon_control_points(
            left_arc, right_arc[::-1], radius
        )
        points = []
        points.extend(
            _make_bezier_curve(np.asarray(control_points_right), num_points)
        )
        points.extend(_make_ideogram_arc(1.0, right_arc))
        points.extend(
            _make_bezier_curve(
                np.asarray(control_points_left[::-1]), num_points
            )
        )
        points.extend(_make_ideogram_arc(1.0, left_arc))
        x, y = zip(*points)

        ribbon_info.append(
            go.Scatter(
                x=x,
                y=y,
                mode='lines',
                line=dict(width=0, color=ribbon_colors[idx]),
                fill="toself",
                text=edges[idx][2].get("info", ""),
                hoverinfo='text'
            )
        )
    return ribbon_info


def make_chord_plot(
    nodes: tp.List[tp.Tuple[NodeTy, ChordPlotNodeInfo]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, ChordPlotEdgeInfo]],
    title: str,
    size: int = 400
) -> go.Figure:
    """
    Create a chord plot from the given graph.

    Based on this guide: https://plotly.com/python/v3/filled-chord-diagram/

    Nodes can have the following information in their NodeInfo dict:
      - color:
      - info:

    Edges can have the following information in their EdgeInfo dict:
      - color:
      - info:
      - size: size of the transition relation relative to others; 1 by default

    Args:
        nodes: list of nodes
        edges: list of edges
        title: plot title
        size: plot size

    Returns:
    """
    # calculate size of nodes by adding the sizes of incident edges
    node_size_dict: tp.Dict[NodeTy, float] = defaultdict(lambda: 0)
    for edge in edges:
        source, sink, info = edge
        node_size_dict[source] += info.get("size", 1)
        node_size_dict[sink] += info.get("size", 1)
    node_sizes: tp.List[float] = []
    # we need to keep the order of the nodes
    for node, _ in nodes:
        node_sizes.append(node_size_dict[node])

    ideogram_ends, ideogram_colors = _calculate_ideogram_data(node_sizes)
    ribbon_bounds, ribbon_colors = _calculate_ribbon_data(
        nodes, edges, node_sizes, ideogram_ends, ideogram_colors
    )
    ideogram_info = _create_ideograms(nodes, ideogram_ends, ideogram_colors)
    ribbon_info = _create_ribbons(edges, ribbon_bounds, ribbon_colors)

    layout = _make_layout(title, size)
    data = ideogram_info + ribbon_info
    return go.Figure(data=data, layout=layout)


class ArcPlotNodeInfo(TypedDict):
    """Data attached to arc plot nodes."""
    fill_color: int
    line_color: int
    info: str
    size: int


class ArcPlotEdgeInfo(TypedDict):
    """Data attached to arc plot edges."""
    color: int
    info: str
    size: int


def _calculate_node_placements(node_sizes: tp.List[float]) -> tp.List[float]:
    node_placements: tp.List[float] = []
    offset_x = 0.0
    for node_size in node_sizes:
        offset_x += node_size / 2.0
        node_placements.append(offset_x)
        offset_x += node_size / 2.0
    return node_placements


def _calculate_arc_bounds(
    nodes: tp.List[tp.Tuple[NodeTy, ArcPlotNodeInfo]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy,
                            ArcPlotEdgeInfo]], node_placements: tp.List[float]
) -> tp.Dict[int, tp.List[tp.Tuple[float, float]]]:
    # group the edges by node
    node_indices = {node[0]: idx for idx, node in enumerate(nodes)}
    incoming_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    outgoing_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    for idx, edge in enumerate(edges):
        source, sink, _ = edge
        outgoing_edges[source].append(idx)
        incoming_edges[sink].append(idx)
    arc_bounds: tp.Dict[int, tp.List[tp.Tuple[float,
                                              float]]] = defaultdict(list)
    arc_sizes: tp.Dict[int, int] = {}
    for node_idx, node in enumerate(nodes):
        for edge_idx in sorted(
            outgoing_edges[node[0]],
            key=lambda x: node_placements[node_indices[edges[x][1]]],
            reverse=True
        ):
            arc_bounds[edge_idx].insert(0, (node_placements[node_idx], 0))
            arc_sizes[edge_idx] = edges[edge_idx][2].get("size", 1)
        for edge_idx in sorted(
            incoming_edges[node[0]],
            key=lambda x: node_placements[node_indices[edges[x][0]]],
            reverse=True
        ):
            arc_bounds[edge_idx].append((node_placements[node_idx], 0))
    return arc_bounds


def _create_arcs(
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, ArcPlotEdgeInfo]],
    arc_bounds: tp.Dict[int, tp.List[tp.Tuple[float, float]]],
    edge_colors: tp.List[str]
) -> tp.List[go.Scatter]:
    arcs: tp.List[go.scatter] = []
    for idx, arc_ends in arc_bounds.items():
        point0 = arc_ends[0]
        point2 = arc_ends[1]
        points = _make_arc(np.asarray(point0), np.asarray(point2), 25)
        x, y = zip(*points)

        arcs.append(
            go.Scatter(
                x=x,
                y=y,
                name='',
                mode='lines',
                line=go.scatter.Line(
                    width=1, color=edge_colors[idx], shape='spline'
                ),
                text=edges[idx][2].get("info", ""),
                hoverinfo="text"
            )
        )
    return arcs


def make_arc_plot(
    nodes: tp.List[tp.Tuple[NodeTy, ArcPlotNodeInfo]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, ArcPlotEdgeInfo]],
    title: str,
    size: int = 400
) -> go.Figure:
    """
    Create a chord plot from the given graph.

    Code based on this plot:
    https://github.com/empet/Plotly-plots/blob/master/Arc-diagram-Force-Awakens.ipynb

    Nodes can have the following information in their NodeInfo dict:
      - fill_color:
      - line_color:
      - size:
      - info:

    Edges can have the following information in their EdgeInfo dict:
      - color:
      - info:
      - size: size of the transition relation relative to others; 1 by default

    Args:
        nodes: list of nodes
        edges: list of edges
        title: figure title
        size: figure size

    Returns:
    """
    colorswatch = [
        "rgb(103,0,31)",
        "rgb(178,24,43)",
        "rgb(214,96,77)",
        "rgb(234,155,120)",
        "rgb(146,197,222)",
        "rgb(67,147,195)",
        "rgb(33,102,172)",
        "rgb(5,48,97)",
    ][::-1]
    colorscheme = colors.make_colorscale(colorswatch)
    node_fill_color_values = [node[1].get("fill_color", 0) for node in nodes]
    node_line_color_values = [node[1].get("line_color", 0) for node in nodes]
    edge_color_values = [edge[2].get("color", 0) for edge in edges]
    edge_min_value = min(edge_color_values)
    edge_max_value = max(edge_color_values)
    edge_diff_value = edge_max_value - edge_min_value
    edge_colors = [
        get_color_at(colorscheme, (v - edge_min_value) / edge_diff_value)
        for v in edge_color_values
    ]

    node_infos = [node[1].get("info", "") for node in nodes]

    node_sizes = [
        np.log(max(np.e, node[1].get("size", 1))) * 5 for node in nodes
    ]
    node_placements = _calculate_node_placements(node_sizes)
    arc_bounds = _calculate_arc_bounds(nodes, edges, node_placements)

    node_scatter = go.Scatter(
        x=node_placements,
        y=[0] * len(nodes),
        mode='markers',
        opacity=1,
        marker=go.scatter.Marker(
            size=node_sizes,
            color=node_fill_color_values,
            colorscale=colorswatch,
            opacity=1,
            showscale=False,
            line=go.scatter.marker.Line(
                color=node_line_color_values,
                colorscale=colorscheme,
                width=[node_size / 3 for node_size in node_sizes]
            )
        ),
        text=node_infos,
        hoverinfo="text"
    )

    layout = _make_layout(title, size)
    data = _create_arcs(edges, arc_bounds, edge_colors) + [node_scatter]
    return go.Figure(data=data, layout=layout)
