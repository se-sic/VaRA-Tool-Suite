"""Test chord plot utils."""
import typing as tp
import unittest

import numpy as np
import numpy.typing as nptp

from varats.plots.chord_plot_utils import (
    _angular_to_cartesian,
    _make_equilateral_triangle,
    _make_bezier_curve,
    _modulo_ab,
    get_color_at,
    _make_arc,
    _calculate_ideogram_data,
    _calculate_ribbon_data,
    _calculate_arc_bounds,
    _calculate_node_placements,
)


class TestChordPlotUtils(unittest.TestCase):
    """Test chord plot utils."""

    def _assert_point_equals(self, point_a, point_b):
        self.assertAlmostEqual(point_a[0], point_b[0])
        self.assertAlmostEqual(point_a[1], point_b[1])

    def _assert_points_equal(self, points_a, points_b):
        self.assertEqual(len(points_a), len(points_b))
        for a, b in zip(points_a, points_b):
            self._assert_point_equals(a, b)

    def test_angular_to_cartesian(self):
        result = _angular_to_cartesian([0, 0])
        self._assert_point_equals([0, 0], result)

        result = _angular_to_cartesian([1, 0])
        self._assert_point_equals([1, 0], result)

        result = _angular_to_cartesian([1, 0.5 * np.pi])
        self._assert_point_equals([0, 1], result)

        result = _angular_to_cartesian([0.5, np.pi])
        self._assert_point_equals([-0.5, 0], result)

    def test_equilateral_triangle(self):
        result = _make_equilateral_triangle(np.array([0, 0]), np.array([1, 0]))
        self._assert_point_equals([0.5, 0.5 * np.sqrt(3)], result)

    def test_make_bezier_curve_parabola(self):
        result = _make_bezier_curve(
            np.array([[0, 0], [0.5, 0.5 * np.sqrt(3)], [1, 0]]), 5
        )
        # A quadratic Bézier curve is a parabola of the form a*t^2 + b*t + c.
        # Since the first and last control point in this test have x=0,
        # we can simplify this formula:
        a = -np.sqrt(3)
        b = np.sqrt(3)

        def curve(t: float) -> float:
            return a * t * t + b * t

        self._assert_points_equal([(t, curve(t)) for t in np.linspace(0, 1, 5)],
                                  result)

    def test_make_arc(self):
        result = _make_arc(np.array([1, 0]), np.array([-1, 0]), 5)
        self._assert_points_equal([
            (np.cos(t), np.sin(t)) for t in np.linspace(0, np.pi, 5)
        ], result)

    def test_modulo_ab(self):
        self.assertAlmostEqual(3, _modulo_ab(3, 2, 4))
        self.assertAlmostEqual(3, _modulo_ab(1, 2, 4))
        self.assertAlmostEqual(3, _modulo_ab(5, 2, 4))
        self.assertAlmostEqual(2, _modulo_ab(2, 2, 4))
        self.assertAlmostEqual(2, _modulo_ab(4, 2, 4))

    def test_get_color_at(self):
        colorscale = [[0, "rgb(100.0, 0.0, 0.0)"], [1, "rgb(0.0, 0.0, 0.0)"]]
        self.assertEqual("rgb(100.0, 0.0, 0.0)", get_color_at(colorscale, -0.5))
        self.assertEqual("rgb(0.0, 0.0, 0.0)", get_color_at(colorscale, 1.5))
        self.assertEqual("rgb(50.0, 0.0, 0.0)", get_color_at(colorscale, 0.5))
        self.assertEqual("rgb(75.0, 0.0, 0.0)", get_color_at(colorscale, 0.25))

    def test_calculate_ideogram_data(self):
        ends, colors = _calculate_ideogram_data([1, 2, 3])
        self._assert_points_equal([[0, np.pi / 3], [np.pi / 3, np.pi],
                                   [np.pi, 2 * np.pi]], ends)
        self.assertEqual(3, len(colors))

    def test_calculate_ribbon_data(self):
        node_a = "a"
        node_b = "b"
        node_c = "c"
        node_data = {"color": 0, "info": ""}
        edges = [
            (node_a, node_c, {
                "color": 0,
                "info": "",
                "size": 1
            }),
            (node_b, node_c, {
                "color": 0,
                "info": "",
                "size": 2
            }),
        ]
        nodes = [
            (node_a, node_data),
            (node_b, node_data),
            (node_c, node_data),
        ]
        node_sizes = [1, 2, 3]
        ideo_ends, ideo_colors = _calculate_ideogram_data([1, 2, 3])
        bounds, colors = _calculate_ribbon_data(
            nodes, edges, node_sizes, ideo_ends, ideo_colors
        )
        self._assert_points_equal([[0, np.pi / 3], [5 * np.pi / 3, 2 * np.pi]],
                                  bounds[0])
        self._assert_points_equal([[np.pi / 3, np.pi], [np.pi, 5 * np.pi / 3]],
                                  bounds[1])
        self.assertEqual(2, len(colors))

    def test_calculate_node_placements(self):
        placements = _calculate_node_placements([1, 2, 3])
        self.assertEqual(0.5, placements[0])
        self.assertEqual(2, placements[1])
        self.assertEqual(4.5, placements[2])

    def test_calculate_arc_bounds(self):
        node_a = "a"
        node_b = "b"
        node_c = "c"
        node_data = {"fill_color": 0, "line_color": 0, "info": "", "size": 0}
        edges = [
            (node_a, node_c, {
                "color": 0,
                "info": "",
                "size": 1
            }),
            (node_b, node_a, {
                "color": 0,
                "info": "",
                "size": 1
            }),
            (node_b, node_c, {
                "color": 0,
                "info": "",
                "size": 2
            }),
        ]
        nodes = [
            (node_a, node_data),
            (node_b, node_data),
            (node_c, node_data),
        ]
        node_placements = _calculate_node_placements([1, 2, 3])

        bounds = _calculate_arc_bounds(nodes, edges, node_placements)
        self._assert_points_equal([[0.5, 0], [4.5, 0]], bounds[0])
        self._assert_points_equal([[2, 0], [0.5, 0]], bounds[1])
        self._assert_points_equal([[2, 0], [4.5, 0]], bounds[2])
