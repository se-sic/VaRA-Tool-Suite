"""
General plots module.
"""

import typing as tp
import argparse
from enum import Enum

from varats.plots.commit_interactions import InteractionPlot
from varats.plots.paper_config_overview import PaperConfigOverviewPlot
from varats.plots.blame_interaction_degree import (BlameInteractionDegree,
                                                   BlameAuthorDegree)
from varats.plots.plot import Plot
from varats.plots.plot_utils import check_required_args


class PlotTypes(Enum):
    """
    Enum of all supported plot types.
    """

    interaction_plot = InteractionPlot
    paper_config_overview_plot = PaperConfigOverviewPlot
    b_interaction_degree = BlameInteractionDegree
    b_author_degree = BlameAuthorDegree

    @property
    def type(self) -> tp.Type[Plot]:
        """ Get python type from plot enum"""
        if not issubclass(self.value, Plot):
            raise AssertionError()
        return tp.cast(tp.Type[Plot], self.value)


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
    plot_type = kwargs['plot_type'].type

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
