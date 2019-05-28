"""
General plots module.
"""

from enum import Enum

from varats.plots.commit_interactions import InteractionPlot
from varats.plots.plot_utils import check_required_args


class PlotTypes(Enum):
    """
    Enum of all supported plot types.
    """

    interaction_plot = InteractionPlot

    @property
    def type(self):
        return self.value


def extend_parser_with_plot_args(parser):
    """
    Extend the parser with graph related extra args.
    """
    pass


@check_required_args(['plot_type', 'view'])
def build_plot(**kwargs):
    """
    Build the specified graph.
    """
    plot_type = kwargs['plot_type'].type

    plot = plot_type(**kwargs)
    plot.style = "ggplot"

    if kwargs["view"]:
        plot.show()
    else:
        plot.save('png')
