"""
General plots module.
"""

from varats.plots.commit_interactions import gen_interaction_graph 


def extend_parser_with_graph_args(parser):
    """
    Extend the parser with graph related extra args.
    """
    pass


def build_graph(**kwargs):
    """
    Build the specified graph.
    """
    gen_interaction_graph(**kwargs)
