"""General plots module."""
import logging
import re
import sys
import typing as tp

from varats.plots.plot_utils import check_required_args

if tp.TYPE_CHECKING:
    import varats.plots.plot

LOG = logging.getLogger(__name__)


class PlotRegistry(type):
    """Registry for all supported plots."""

    to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    plots: tp.Dict[str, tp.Type[tp.Any]] = {}

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(PlotRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = PlotRegistry.to_snake_case_pattern.sub('_', name).lower()
        PlotRegistry.plots[key] = cls

    @staticmethod
    def get_plot_types_help_string() -> str:
        """
        Generates help string for visualizing all available plots.

        Returns:
            a help string that contains all available plot names.
        """
        return "The following plots are available:\n  " + "\n  ".join([
            key for key in PlotRegistry.plots if key != "plot"
        ])

    @staticmethod
    def get_class_for_plot_type(
        plot_type: str
    ) -> tp.Type['varats.plots.plot.Plot']:
        """
        Get the class for plot from the plot registry.

        Test:
        >>> PlotRegistry.get_class_for_plot_type('paper_config_overview_plot')
        <class 'varats.plots.paper_config_overview.PaperConfigOverviewPlot'>

        Args:
            plot_type: The name of the plot.

        Returns: The class implementing the plot.
        """
        from varats.plots.plot import Plot
        if plot_type not in PlotRegistry.plots:
            sys.exit(
                f"Unknown plot '{plot_type}'.\n" +
                PlotRegistry.get_plot_types_help_string()
            )

        plot_cls = PlotRegistry.plots[plot_type]
        if not issubclass(plot_cls, Plot):
            raise AssertionError()
        return plot_cls


@check_required_args(['plot_type', 'view', 'sep_stages'])
def build_plot(**kwargs: tp.Any) -> None:
    """Build the specified graph."""
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    if kwargs['sep_stages'] and not plot_type.supports_stage_separation():
        LOG.warning(
            f"{kwargs['plot_type']} does not support stage "
            "separation but separation flag '--sep-stages' was set."
        )

    plot = plot_type(**kwargs)
    plot.style = "ggplot"

    if kwargs["view"]:
        plot.show()
    else:
        plot.save(filetype='png')
