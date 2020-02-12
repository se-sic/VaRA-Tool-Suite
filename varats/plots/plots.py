"""
General plots module.
"""
import re
import sys
import typing as tp
import argparse

# avoid circular import
# see https://www.stefaanlippens.net/circular-imports-type-hints-python.html
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from varats.plots.plot import Plot
from varats.plots.plot_utils import check_required_args


class PlotRegistry(type):
    """
    Registry for all supported plots.
    """

    to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    plots: tp.Dict[str, tp.Type[tp.Any]] = {}

    def __init__(cls, name: str, bases: tp.Tuple[tp.Any],
                 attrs: tp.Dict[tp.Any, tp.Any]):
        super(PlotRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = PlotRegistry.to_snake_case_pattern.sub('_', name).lower()
        PlotRegistry.plots[key] = cls

    @staticmethod
    def get_plot_types_help_string() -> str:
        return "The following plots are available:\n  " + "\n  ".join(
            [key for key in PlotRegistry.plots.keys() if key != "plot"])

    @staticmethod
    def get_class_for_plot_type(plot: str) -> tp.Type['Plot']:
        """
        Get the class for plot from the plot registry.

        Test:
        >>> PlotRegistry.get_class_for_plot_type('paper_config_overview_plot')
        <class 'varats.plots.paper_config_overview.PaperConfigOverviewPlot'>

        Args:
            plot: The name of the plot.

        Returns: The class implementing the plot.
        """
        from varats.plots.plot import Plot
        if plot not in PlotRegistry.plots:
            sys.exit(f"Unknown plot '{plot}'.\n" +
                     PlotRegistry.get_plot_types_help_string())

        plot_cls = PlotRegistry.plots[plot]
        if not issubclass(plot_cls, Plot):
            raise AssertionError()
        return plot_cls


def extend_parser_with_plot_args(parser: argparse.ArgumentParser) -> None:
    """
    Extend the parser with graph related extra args.
    """
    pass


@check_required_args(['plot_type', 'view', 'sep_stages'])
def build_plot(**kwargs: tp.Any) -> None:
    """
    Build the specified graph.
    """
    plot_type = PlotRegistry.get_class_for_plot_type(kwargs['plot_type'])

    if (kwargs['sep_stages'] and not plot_type.supports_stage_separation()):
        print("Warning: {plot_type} does not support stage ".format(
            plot_type=kwargs['plot_type']) +
              "separation but separation flag '--sep-stages' was set.")

    plot = plot_type(**kwargs)
    plot.style = "ggplot"

    if kwargs["view"]:
        plot.show()
    else:
        plot.save('png')
