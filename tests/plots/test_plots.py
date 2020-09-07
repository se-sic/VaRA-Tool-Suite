"""Test plot registry."""
import unittest

from varats.plots.plots import PlotRegistry


class TestPlotRegistry(unittest.TestCase):
    """Test the registry for plots."""

    def test_get_class_for_plot_type(self):
        """Tests if we can get a type based on a plot name."""
        plot_type = PlotRegistry.get_class_for_plot_type(
            'paper_config_overview_plot'
        )
        self.assertEqual(
            str(plot_type),
            "<class 'varats.plots.paper_config_overview.PaperConfigOverviewPlot'>"
        )
