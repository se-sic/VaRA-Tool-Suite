"""Test plot registry."""
import inspect
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
        config = PlotConfig.from_kwargs(view=False)
        self.assertEqual(10, config.font_size())

    def test_get_option_value_set(self):
        """Test if a set value overrides the default value."""
        config = PlotConfig.from_kwargs(view=False, fig_title="Test")
        self.assertEqual("Test", config.fig_title())
        self.assertEqual(1500, config.width())

    def test_get_option_value_not_set_override(self):
        """Test if passed default overrides global default."""
        config = PlotConfig.from_kwargs(view=False, show_legend=True)
        self.assertEqual(42, config.legend_size(42))

    def test_get_option_value_set_no_override(self):
        """Test if passed default does not override set value."""
        config = PlotConfig.from_kwargs(view=False, height=42)
        self.assertEqual(42, config.height(5))

    def test_view_get_option_value_not_set(self):
        """Test if default value is returned in view mode."""
        config = PlotConfig.from_kwargs(view=True)
        self.assertEqual(10, config.font_size())

    def test_view_get_option_value_set(self):
        """Test if a set value overrides the default value in view mode."""
        config = PlotConfig.from_kwargs(view=True, fig_title="Test", width=1)
        self.assertEqual("Test", config.fig_title())
        self.assertEqual(1, config.width())
        self.assertEqual(1000, config.height())

    def test_view_get_option_value_not_set_override(self):
        """Test if passed default overrides global default in view mode."""
        config = PlotConfig.from_kwargs(view=True, show_legend=True)
        self.assertEqual(42, config.legend_size(view_default=42))

    def test_view_get_option_value_set_no_override(self):
        """Test if passed default does not override set value in view mode."""
        config = PlotConfig.from_kwargs(view=True, height=42)
        self.assertEqual(42, config.height(view_default=5))

    def test_no_view_default_override(self):
        """Test if passed default is used over view_default in non-view mode."""
        config = PlotConfig.from_kwargs(view=False)
        self.assertEqual(4, config.height(default=4, view_default=5))

    def test_view_default_override(self):
        """Test if passed view_default is used over default in view mode."""
        config = PlotConfig.from_kwargs(view=True)
        self.assertEqual(5, config.height(default=4, view_default=5))

    def test_get_dict(self):
        """Check that dict only contains options with set values."""
        config = PlotConfig.from_kwargs(view=False, label_size=1)
        config_dict = config.get_dict()
        self.assertIn("label_size", config_dict)
        self.assertEqual(1, config_dict["label_size"])

        self.assertNotIn("x_tick_size", config_dict)

    def test_options_accessors(self):
        """Check that all plot config options have accessors."""
        config = PlotConfig.from_kwargs(view=False)

        for name, option in PlotConfig._option_decls.items():
            self.assertTrue(
                hasattr(PlotConfig, name),
                f"Plot config is missing an accessor for the option '{name}'"
            )

            accessor_fn = config.__getattribute__(name)
            signature = inspect.signature(accessor_fn)

            self.assertFalse(
                option.view_default and
                "view_default" not in signature.parameters,
                f"Plot config option {name} has view_default set but "
                f"accessor does not allow overriding. Either remove "
                f"view_default or use PCOGetterV for the accessor."
            )
            self.assertFalse(
                not option.view_default and
                "view_default" in signature.parameters,
                f"Plot config option {name} has no view_default set but "
                f"accessor allows overriding view_default. Either add a "
                f"view_default to the option or use PCOGetter for the "
                f"accessor."
            )
