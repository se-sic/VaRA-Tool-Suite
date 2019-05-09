"""
General plots module.
"""

from varats.plots.commit_interactions import InteractionPlot


def extend_parser_with_plot_args(parser):
    """
    Extend the parser with graph related extra args.
    """
    pass


def build_plot(**kwargs):
    """
    Build the specified graph.
    """
    plot = InteractionPlot(**kwargs)
    plot.style = "ggplot"

    if kwargs["view"]:
        plot.show()
    else:
        plot.save('png')
