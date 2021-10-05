"""Test plot registry."""
import unittest

from varats.plot.plot import Plot
from varats.plot.plots import PlotConfig
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


class TestPlotConfig(unittest.TestCase):
    """Tests for the PlotConfig class."""

    def test_get_option_value_not_set(self):
        """Test if default value is returned."""
        config = PlotConfig.from_kwargs()
        self.assertEqual(10, config.font_size())

    def test_get_option_value_set(self):
        """Test if a set value overrides the default value."""
        config = PlotConfig.from_kwargs(**{"fig-title": "Test"})
        self.assertEqual("Test", config.fig_title())
        self.assertEqual(1500, config.width())

    def test_get_option_value_not_set_override(self):
        """Test if passed default overrides global default."""
        config = PlotConfig.from_kwargs(**{"show_legend": True})
        self.assertEqual(42, config.legend_size(42))

    def test_get_option_value_set_no_override(self):
        """Test if passed default does not override set value."""
        config = PlotConfig.from_kwargs(**{"height": 42})
        self.assertEqual(42, config.height(5))

    def test_get_dict(self):
        """Check that dict only contains options with set values."""
        config = PlotConfig.from_kwargs(**{"label-size": 1})
        config_dict = config.get_dict()
        self.assertIn("label-size", config_dict)
        self.assertEqual(1, config_dict["label-size"])

        self.assertNotIn("x-tick-size", config_dict)

    def test_all_options_have_accessors(self):
        for name in PlotConfig._option_decls:
            self.assertTrue(
                hasattr(PlotConfig, name.replace("-", "_")),
                f"Plot config is missing an accessor for the option '{name}'"
            )
