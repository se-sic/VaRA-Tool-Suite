"""
Utility module for creating chord plots with plotly.

Much of the code is adapted from here: https://plotly.com/python/v3/filled-
chord-diagram/
"""
import typing as tp
from collections import defaultdict

import numpy as np
import plotly.colors as colors
import plotly.graph_objs as go

PointTy = np.typing.ArrayLike


def _ribbon_control_points(
    left_arc: tp.Tuple[float, float], right_arc: tp.Tuple[float, float],
    radius: float
) -> tp.Tuple[tp.List[np.typing.ArrayLike], tp.List[np.typing.ArrayLike]]:
    return ([
        _angular_to_cartesian((1, left_arc[0])),
        _angular_to_cartesian((radius, (left_arc[0] + right_arc[0]) / 2)),
        _angular_to_cartesian((1, right_arc[0]))
    ], [
        _angular_to_cartesian((1, left_arc[1])),
        _angular_to_cartesian((radius, (left_arc[1] + right_arc[0]) / 2)),
        _angular_to_cartesian((1, right_arc[1]))
    ])


def _angular_to_cartesian(angular: np.typing.ArrayLike) -> np.ndarray:
    angular = np.asarray(angular)
    return np.array([
        angular[0] * np.cos(angular[1]), angular[0] * np.sin(angular[1])
    ])


def _get_b1(b0: np.ndarray, b2: np.ndarray) -> np.ndarray:
    """Given two points b0 and b2, finds a point b1 such that b0b1b2 forms an
    equilateral triangle."""
    if len(b0) != 2 and len(b2) != 2:
        raise ValueError('b0 and b2 must have exactly 2 elements.')
    b1 = 0.5 * (b0 + b2) + 0.5 * np.asarray(
        [0, 1.0 * np.sign(b2[0] - b0[0])]
    ) * np.sqrt(3) * np.linalg.norm(b2 - b0)
    return np.asarray(b1)


def _dim_plus_1(
    points: tp.List[np.typing.ArrayLike], weights: tp.List[float]
) -> np.ndarray:
    """Add weights by lifting the points in b to 3D points."""
    if len(points) != len(weights):
        raise ValueError(
            "The number of weights must be equal to the number of points."
        )

    lifted_points = np.array([
        np.append(point, weights[i]) for (i, point) in enumerate(points)
    ])
    lifted_points[1, :2] *= weights[1]
    return lifted_points


def _make_bezier_curve(control_points: np.ndarray,
                       nr: int) -> tp.List[np.ndarray]:
    """Evaluate nr equally spaced points on a bezier curve defined by the given
    control points."""
    control_points = np.asarray(control_points)
    n = control_points.shape[0]
    nr = max(0, nr)
    t = np.linspace(0, 1, nr)
    points = []
    # For each parameter t[i] evaluate a point on the Bezier curve with the
    # de Casteljau algorithm.
    for i in range(nr):
        aa = np.copy(control_points)
        for r in range(1, n):
            aa[:n - r, :] = \
                (1 - t[i]) * aa[:n - r, :] + t[i] * aa[1:n - r + 1, :]
        points.append(aa[0, :])
    return points


def _make_arc(b0: np.ndarray, b2: np.ndarray,
              num_points: int) -> tp.List[np.ndarray]:
    """
    Make an arc (half-circle) with the given end points.

    Args:
        b0: left end-point
        b2: right end-point
        num_points: number of points to evaluate on the arc

    Returns:
        a list of points on the arc
    """
    b1 = _get_b1(b0, b2)
    a = _dim_plus_1([b0, b1, b2], [1, 0.5, 1])
    discrete_curve = _make_bezier_curve(a, num_points)
    return [p[:2] / p[2] for p in discrete_curve]


def _modulo_ab(x: float, a: float, b: float) -> float:
    """
    Map a real number onto the unit circle identified by the interval [a, b)

    with b - a = 2 * PI.
    """
    if a >= b:
        raise ValueError("Incorrect interval ends.")
    y = (x - a) % (b - a)
    return y + b if y < 0 else y + a


def _is_between_zero_and_2pi(x: float) -> bool:
    return 0 <= x < float(2 * np.pi + 0.00001)


def _calculate_ideogram_lengths(
    sizes: np.ndarray, gap: float = 0.005 * 2 * np.pi
) -> np.ndarray:
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
    lengths: np.ndarray, gap: float = 0.005 * 2 * np.pi
) -> np.ndarray:
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
) -> tp.List[np.ndarray]:
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
    nr = 5 if length <= np.pi / 4 else int(num_points * length / np.pi)

    if ends[0] <= ends[1]:
        theta = np.linspace(ends[0], ends[1], nr)
    else:
        ends = (
            _modulo_ab(ends[0], -np.pi,
                       np.pi), _modulo_ab(ends[1], -np.pi, np.pi)
        )
        theta = np.linspace(ends[0], ends[1], nr)
    points = zip([radius] * nr, theta)
    return [_angular_to_cartesian(point) for point in points]


def _calculate_ribbon_ends(
    node_size: float, ideogram_ends: tp.Tuple[float, float],
    ribbon_sizes: tp.List[float]
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

        nr = int(40 * (theta0 - theta1) / np.pi)
        if nr <= 2:
            nr = 3
        theta = np.linspace(theta0, theta1, nr)
        pts = np.exp(1j * theta)  # points on arc in polar complex form

        string_arc = ''
        for k in range(len(theta)):
            string_arc += 'L ' + str(pts.real[k]
                                    ) + ', ' + str(pts.imag[k]) + ' '
        return string_arc
    else:
        raise ValueError(
            'the angle coordinates for an arc side of a ribbon must be in [0, 2*pi]'
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


def get_color_at(colorscale: ColorScaleTy, s: float) -> str:
    """
    Plotly continuous colorscales assign colors to the range [0, 1]. This
    function computes the intermediate color for any value in that range.

    Args:
        colorscale: a plotly continuous colorscale defined with RGB string colors
        s: value in the range [0, 1]
    Returns:
        color in rgb string format
    """
    if len(colorscale) < 1:
        raise ValueError("colorscale must have at least one color")

    if s <= 0 or len(colorscale) == 1:
        return str(colors.convert_colors_to_same_type(colorscale[0][1])[0][0])
    if s >= 1:
        return str(colors.convert_colors_to_same_type(colorscale[-1][1])[0][0])

    low_color = high_color = ""
    for cutoff, color in colorscale:
        if s > float(cutoff):
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
            intermed=((s - low_cutoff) / (high_cutoff - low_cutoff)),
            colortype="rgb"
        )
    )


def add_alpha_channel(rgb_color: str, alpha: float) -> str:
    r, g, b = colors.unlabel_rgb(rgb_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


NodeTy = str
NodeInfoTy = tp.Dict[str, tp.Any]
EdgeInfoTy = tp.Dict[str, tp.Any]


def make_chord_plot(
    nodes: tp.List[tp.Tuple[NodeTy, NodeInfoTy]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, EdgeInfoTy]],
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
        nodes:
        edges: list of edges

    Returns:
    """
    # calculate size of nodes by adding the sizes of incident edges
    # group the edges by node along the way
    node_size_dict: tp.Dict[NodeTy, float] = defaultdict(lambda: 0)
    incoming_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    outgoing_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    for idx, edge in enumerate(edges):
        source, sink, info = edge
        node_size_dict[source] += info.get("size", 1)
        node_size_dict[sink] += info.get("size", 1)
        outgoing_edges[source].append(idx)
        incoming_edges[sink].append(idx)
    node_sizes = []
    # we need to keep the order of the nodes
    for node, _ in nodes:
        node_sizes.append(node_size_dict[node])

    # calculate ideograms
    gap = 2 * np.pi * 0.000
    ideogram_lengths = _calculate_ideogram_lengths(np.asarray(node_sizes), gap)
    ideogram_ends = _calculate_ideogram_ends(ideogram_lengths, gap)
    ideogram_colors = [
        get_color_at(colors.PLOTLY_SCALES["RdBu"], idx / len(ideogram_ends))
        for idx, ends in enumerate(ideogram_ends)
    ]
    # random.shuffle(ideogram_colors)
    ideogram_info: tp.List[go.Scatter] = []
    for idx, ends in enumerate(ideogram_ends):
        z = _make_ideogram_arc(1.1, ends)
        zi = _make_ideogram_arc(1.0, ends)

        points: tp.List[np.ndarray] = []
        points.extend(z)
        points.extend(zi[::-1])
        points.append(z[0])
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

    # calculate ribbon bounds per ideogram
    ribbon_bounds: tp.Dict[int, tp.List[tp.Tuple[float,
                                                 float]]] = defaultdict(list)
    ribbon_colors: tp.Dict[int, str] = {}
    ribbon_info: tp.List[go.scatter] = []
    for node_idx, (node, _) in enumerate(nodes):
        node_edges: tp.List[int] = []
        node_edge_sizes: tp.List[float] = []
        for edge_idx in sorted(
            outgoing_edges[node[0]],
            key=lambda x: float(edges[x][2]["size"]),
            reverse=True
        ):
            node_edges.append(edge_idx)
            node_edge_sizes.append(edges[edge_idx][2].get("size", 1))
            ribbon_colors[edge_idx] = add_alpha_channel(
                ideogram_colors[node_idx], 0.75
            )
        for edge_idx in sorted(
            incoming_edges[node[0]],
            key=lambda x: float(edges[x][2]["size"]),
            reverse=True
        ):
            node_edges.append(edge_idx)
            node_edge_sizes.append(edges[edge_idx][2].get("size", 1))
        ribbon_ends = _calculate_ribbon_ends(
            node_sizes[node_idx], ideogram_ends[node_idx], node_edge_sizes
        )
        for edge_idx, ribbon_end in zip(node_edges, ribbon_ends):
            ribbon_bounds[edge_idx].append(ribbon_end)

    for idx, ribbon_ends in ribbon_bounds.items():
        left_arc = ribbon_ends[0]
        right_arc = ribbon_ends[1]
        radius = 0.2
        num_points = 25
        b, c = _ribbon_control_points(left_arc, right_arc[::-1], radius)
        points = []
        points.extend(_make_bezier_curve(np.asarray(c), num_points))
        points.extend(_make_ideogram_arc(1.0, right_arc))
        points.extend(_make_bezier_curve(np.asarray(b[::-1]), num_points))
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

    layout = _make_layout(title, size)
    data = ideogram_info + ribbon_info
    figure = go.Figure(data=data, layout=layout)
    return figure


def make_arc_plot(
    nodes: tp.List[tp.Tuple[NodeTy, NodeInfoTy]],
    edges: tp.List[tp.Tuple[NodeTy, NodeTy, EdgeInfoTy]],
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
        nodes:
        edges: list of edges

    Returns:
    """
    colorswatch = colors.sequential.RdBu[::-1]
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

    # calculate size of nodes by adding the sizes of incident edges
    # group the edges by node along the way
    incoming_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    outgoing_edges: tp.Dict[NodeTy, tp.List[int]] = defaultdict(list)
    for idx, edge in enumerate(edges):
        source, sink, info = edge
        outgoing_edges[source].append(idx)
        incoming_edges[sink].append(idx)
    node_sizes = [
        np.log(max(np.e, node[1].get("size", 1))) * 5 for node in nodes
    ]
    node_indices = {node[0]: idx for idx, node in enumerate(nodes)}
    node_placements = []
    dx = 0
    for node_size in node_sizes:
        dx += node_size / 2
        node_placements.append(dx)
        dx += node_size / 2

    arc_bounds: tp.Dict[int, tp.List[tp.Tuple[float,
                                              float]]] = defaultdict(list)
    arc_sizes: tp.Dict[int, int] = {}
    for node_idx, node in enumerate(nodes):
        for i, edge_idx in enumerate(
            sorted(
                outgoing_edges[node[0]],
                key=lambda x: node_placements[node_indices[edges[x][1]]],
                reverse=True
            )
        ):
            arc_bounds[edge_idx].insert(
                0, (
                    node_placements[node_idx] + i -
                    len(outgoing_edges[node[0]]) * 0.5, 0
                )
            )
            arc_sizes[edge_idx] = edges[edge_idx][2].get("size", 1)
        for i, edge_idx in enumerate(
            sorted(
                incoming_edges[node[0]],
                key=lambda x: node_placements[node_indices[edges[x][0]]],
                reverse=True
            )
        ):
            arc_bounds[edge_idx].append((
                node_placements[node_idx] + i -
                len(incoming_edges[node[0]]) * 0.5, 0
            ))

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

    arcs: tp.List[go.scatter] = []
    for idx, arc_ends in arc_bounds.items():
        b0 = arc_ends[0]
        b2 = arc_ends[1]
        points = _make_arc(np.asarray(b0), np.asarray(b2), 25)
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

    layout = _make_layout(title, size)
    data = arcs + [node_scatter]
    figure = go.Figure(data=data, layout=layout)
    return figure
