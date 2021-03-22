"""
Utility module for creating chord plots with plotly.

Much of the code is adapted from here: https://plotly.com/python/v3/filled-
chord-diagram/
"""
import random
import typing as tp
from collections import defaultdict

import numpy as np
import plotly.colors as colors
import plotly.graph_objs as go


def _modulo_ab(x: float, a: float, b: float) -> float:
    """
    Map a real number onto the unit circle identified by the interval [a, b)

    with b - a = 2 * PI.
    """
    if a >= b:
        raise ValueError("Incorrect interval ends.")
    y = (x - a) % (b - a)
    return y + b if y < 0 else y + a


def _is_between_zero_and_2pi(x: float):
    return 0 <= x < 2 * np.pi + 0.00001


def _calculate_ideogram_lengths(
    sizes: tp.List[float], gap: float = 0.005 * 2 * np.pi
) -> tp.List[float]:
    """
    Calculate the lengths for the ideograms.

    Args:
        sizes: sizes of the ideograms relative to each other
        gap: the gap between ideograms; by default 0.5% of a unit circle

    Returns:
        lengths of the ideograms on the unit circle
    """
    return 2 * np.pi * np.asarray(sizes) / sum(sizes
                                              ) - gap * np.ones(len(sizes))


def _calculate_ideogram_ends(
    lengths: tp.List[float],
    gap: float = 0.005 * 2 * np.pi
) -> tp.List[tp.Tuple[float, float]]:
    """
    Calculate the ends of the ideograms as azimuths.

    Args:
        lengths: lengths of the ideograms
        gap: gap between the ideograms

    Returns:
        ends for the ideograms as azimuths
    """
    ideogram_ends: tp.List[tp.Tuple[float, float]] = []
    left = 0
    for length in lengths:
        right = left + length
        ideogram_ends.append((left, right))
        left = right + gap
    return ideogram_ends


def _make_ideogram_arc(
    radius: float,
    ends: tp.Tuple[float, float],
    num_points: int = 50
) -> np.array:
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

    if ends[0] < ends[1]:
        theta = np.linspace(ends[0], ends[1], nr)
    else:
        ends = (
            _modulo_ab(ends[0], -np.pi,
                       np.pi), _modulo_ab(ends[1], -np.pi, np.pi)
        )
        theta = np.linspace(ends[0], ends[1], nr)
    return radius * np.exp(1j * theta)


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


def _control_pts(angle: tp.List[float],
                 radius: float) -> tp.List[tp.Tuple[float, float]]:
    if len(angle) != 3:
        raise ValueError("angle must have len = 3")
    b_cplx = np.array([np.exp(1j * angle[k]) for k in range(3)])
    b_cplx[1] = radius * b_cplx[1]
    return list(zip(b_cplx.real, b_cplx.imag))


def _ctrl_rib_chords(
    left_arc: tp.Tuple[float, float], right_arc: tp.Tuple[float, float],
    radius: float
) -> tp.Tuple[tp.List[tp.Tuple[float, float]], tp.List[tp.Tuple[float, float]]]:
    return (
        _control_pts([
            left_arc[0], (left_arc[0] + right_arc[0]) / 2, right_arc[0]
        ], radius),
        _control_pts([
            left_arc[1], (left_arc[1] + right_arc[1]) / 2, right_arc[1]
        ], radius)
    )


def _make_q_bezier(b):
    if len(b) != 3:
        raise ValueError("Control poligon must have 3 points")
    A, B, C = b
    return 'M ' + str(A[0]) + ',' + str(A[1]) + ' ' + 'Q ' + \
           str(B[0]) + ', ' + str(B[1]) + ' ' + \
           str(C[0]) + ', ' + str(C[1])


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


def _make_layout(title, plot_size, shapes):
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
        width=plot_size,
        height=plot_size,
        margin=dict(t=25, b=25, l=25, r=25),
        hovermode='closest',
        shapes=shapes
    )


def _make_ideogram_shape(path, line_color, fill_color):
    return dict(
        line={
            "color": line_color,
            "width": 0.45
        },
        path=path,
        type="path",
        fillcolor=fill_color,
        layer="below"
    )


def _make_ribbon(
    left_arc: tp.Tuple[float, float],
    right_arc: tp.Tuple[float, float],
    line_color,
    fill_color,
    radius=0.2
):
    b, c = _ctrl_rib_chords(left_arc, right_arc, radius)
    path = _make_q_bezier(b) + _make_ribbon_arc(right_arc[0], right_arc[1]) + \
             _make_q_bezier(c[::-1]) + _make_ribbon_arc(left_arc[1], left_arc[0])

    return dict(
        line={
            "color": line_color,
            "width": 0.45
        },
        path=path,
        type="path",
        fillcolor=fill_color,
        layer="below"
    )


ColorScaleTy = tp.List[tp.List[tp.Union[str, float]]]


def get_color_at(colorscale: ColorScaleTy, s: float) -> str:
    """
    Plotly continuous colorscales assign colors to the range [0, 1]. This
    function computes the intermediate color for any value in that range.

    Args:
        colorscale: a plotly continuous colorscale defined with RGB string colors
        intermed: value in the range [0, 1]
    Returns:
        color in rgb string format
    """
    if len(colorscale) < 1:
        raise ValueError("colorscale must have at least one color")

    if s <= 0 or len(colorscale) == 1:
        return colors.convert_colors_to_same_type(colorscale[0][1])[0][0]
    if s >= 1:
        return colors.convert_colors_to_same_type(colorscale[-1][1])[0][0]

    for cutoff, color in colorscale:
        if s > cutoff:
            low_cutoff, low_color = cutoff, color
        else:
            high_cutoff, high_color = cutoff, color
            break

    low_color = colors.convert_colors_to_same_type(low_color)[0][0]
    high_color = colors.convert_colors_to_same_type(high_color)[0][0]

    # noinspection PyUnboundLocalVariable
    return colors.find_intermediate_color(
        lowcolor=low_color,
        highcolor=high_color,
        intermed=((s - low_cutoff) / (high_cutoff - low_cutoff)),
        colortype="rgb"
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
):
    """
    Create a chord plot from the given graph.

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

    shapes = []

    # calculate ideograms
    gap = 2 * np.pi * 0.000
    ideogram_lengths = _calculate_ideogram_lengths(node_sizes, gap)
    ideogram_ends = _calculate_ideogram_ends(ideogram_lengths, gap)
    ideogram_colors = [
        get_color_at(colors.PLOTLY_SCALES["Viridis"], idx / len(ideogram_ends))
        for idx, ends in enumerate(ideogram_ends)
    ]
    # random.shuffle(ideogram_colors)
    ideogram_info: tp.List[go.Scatter] = []
    for idx, ends in enumerate(ideogram_ends):
        z = _make_ideogram_arc(1.1, ends)
        zi = _make_ideogram_arc(1.0, ends)
        ideogram_info.append(
            go.Scatter(
                x=z.real,
                y=z.imag,
                mode='lines',
                line=dict(
                    color=ideogram_colors[idx], shape='spline', width=0.25
                ),
                text=nodes[idx][1].get("info", ""),
                hoverinfo="text"
            )
        )

        path = "M "
        for s in range(len(z)):
            path += f"{z.real[s]}, {z.imag[s]} L "

        Zi = np.array(zi.tolist()[::-1])

        for s in range(len(Zi)):
            path += str(Zi.real[s]) + ', ' + str(Zi.imag[s]) + ' L '
        path += str(z.real[0]) + ' ,' + str(z.imag[0])

        shapes.append(
            _make_ideogram_shape(
                path, 'rgb(150,150,150)', ideogram_colors[idx]
            )
        )

    # calculate ribbon bounds per ideogram
    ribbon_bounds: tp.Dict[int, tp.List[tp.Tuple[float,
                                                 float]]] = defaultdict(list)
    ribbon_colors: tp.Dict[int, str] = {}
    ribbon_info: tp.List[go.scatter] = []
    for node_idx, node in enumerate(nodes):
        node_edges: tp.List[int] = []
        node_edge_sizes: tp.List[float] = []
        for edge_idx in sorted(
            outgoing_edges[node[0]],
            key=lambda x: edges[x][2]["size"],
            reverse=True
        ):
            node_edges.append(edge_idx)
            node_edge_sizes.append(edges[edge_idx][2].get("size", 1))
            ribbon_colors[edge_idx] = add_alpha_channel(
                ideogram_colors[node_idx], 0.75
            )
        for edge_idx in sorted(
            incoming_edges[node[0]],
            key=lambda x: edges[x][2]["size"],
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
        l = ribbon_ends[0]
        r = ribbon_ends[1]
        zi = 0.9 * np.exp(1j * (l[0] + l[1]) / 2)
        zf = 0.9 * np.exp(1j * (r[0] + r[1]) / 2)
        ribbon_info.append(
            go.Scatter(
                x=[zi.real],
                y=[zi.imag],
                mode='markers',
                marker=dict(size=0.5, color=ribbon_colors[idx]),
                text=edges[idx][2].get("info", ""),
                hoverinfo='text'
            )
        ),
        ribbon_info.append(
            go.Scatter(
                x=[zf.real],
                y=[zf.imag],
                mode='markers',
                marker=dict(size=0.5, color=ribbon_colors[idx]),
                text=edges[idx][2].get("info", ""),
                hoverinfo='text'
            )
        )
        shapes.append(
            _make_ribbon(
                ribbon_ends[0], tuple(reversed(ribbon_ends[1])),
                ribbon_colors[idx], ribbon_colors[idx]
            )
        )

    layout = _make_layout(title, size, shapes)
    data = ideogram_info + ribbon_info
    figure = go.Figure(data=data, layout=layout)
    return figure
