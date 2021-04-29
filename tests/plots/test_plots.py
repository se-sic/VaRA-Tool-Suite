"""Test plot registry."""
import unittest

from varats.plot.plot import Plot
from varats.plots.discover_plots import initialize_plots


class TestPlotRegistry(unittest.TestCase):
    """Test the registry for plots."""

    def test_get_class_for_plot_type(self):
        """Tests if we can get a type based on a plot name."""
        initialize_plots()
        plot_type = Plot.get_class_for_plot_type('paper_config_overview_plot')
        self.assertEqual(
            str(plot_type),
            "<class 'varats.plots.paper_config_overview.PaperConfigOverviewPlot'>"
        )
